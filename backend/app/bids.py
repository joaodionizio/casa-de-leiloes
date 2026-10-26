"""Lance transacional (Story 3.4; AD-3, AD-5, AD-6, AD-7, AD-8, AD-13, AD-20, AD-21).

Um módulo, como `lots.py` e `wallet.py`: modelo `Bid`, o gate que autentica o estado
anterior, o serviço `place_bid` e a rota `POST /api/lots/{lot_id}/bids`. As regras vêm
de `bid_rules` (3.2), os bytes, hashes, alias e HMAC de `bid_integrity` (3.3), a hora de
`database_now`, a trava do lote de `lock_lot` e a da carteira de `lock_wallet`. Este
módulo só as compõe, numa única transação do PostgreSQL.

Ordem (D1, `transaction-contract.md`): trava do lote → `clock_timestamp()` → gate (a
cadeia, a âncora e o vínculo do líder, antes de qualquer regra de negócio) → regras
pré-carteira → carteiras em `user_id` crescente → saldo → efeitos. O banco recebe três
statements de escrita: `UPDATE wallets`, `INSERT bids` e **um** `UPDATE lots` final
(a CHECK `(bid_count = 0) = (current_bid_cents IS NULL)` não é adiável, então o lote
nunca é gravado em duas partes). O serviço não faz commit nem rollback: a rota decide.

Premissa (`current-state.md` §4): toda escrita em `bids` e no estado de lance do lote
passa pela trava do lote. As futuras 3.6, 4.3 e 6.6 a herdam, com o mesmo gate.

Este módulo não importa `app.main`.
"""

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.engine import Row
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.access import NO_STORE, AccessPolicy, api_route, require_bidder
from app.bid_integrity import (
    GENESIS_HASH,
    AnchorState,
    CanonicalBid,
    VerifiableBid,
    compute_anchor_hmac,
    compute_bid_hash,
    generate_bidder_alias,
    verify_anchor_hmac,
    verify_bid_chain,
)
from app.bid_rules import (
    BidAttempt,
    BidRefusal,
    CurrentBid,
    LotBidState,
    evaluate_post_wallet,
    evaluate_pre_wallet,
)
from app.config import IntegrityConfig
from app.db import Base, get_session
from app.errors import LOT_INTEGRITY_CONFLICT, error_response, error_responses
from app.lots import database_now, get_integrity_config, lock_lot
from app.money import MAX_CENTS, Cents
from app.users import User
from app.wallet import (
    Wallet,
    WalletResponse,
    available_cents,
    lock_wallet,
    wallet_response,
)

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")


class Bid(Base):
    """Espelha a migration `0005`; o esquema dos testes vem sempre dela. Sem
    `relationship()`: a ordem dos statements é explícita (D1)."""

    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint(
            "lot_id", "previous_hash", name="uq_bids_lot_id_previous_hash"
        ),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        CheckConstraint(
            f"amount_cents > 0 AND amount_cents <= {MAX_CENTS}", name="amount_range"
        ),
        CheckConstraint(
            "bidder_alias ~ '^Licitante-[0-9A-F]{16}$'", name="bidder_alias_format"
        ),
        CheckConstraint(
            "previous_hash ~ '^[0-9a-f]{64}$'", name="previous_hash_format"
        ),
        CheckConstraint("current_hash ~ '^[0-9a-f]{64}$'", name="current_hash_format"),
        CheckConstraint("canonical_version = 1", name="canonical_version"),
    )

    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), primary_key=True
    )
    sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Privado: não entra nos bytes canônicos v1 e nunca sai pela API pública.
    bidder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    bidder_alias: Mapped[str] = mapped_column(Text)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    # Sem default: é o `now` do passo 3, o mesmo do `CanonicalBid`.
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_hash: Mapped[str] = mapped_column(Text)
    current_hash: Mapped[str] = mapped_column(Text)
    canonical_version: Mapped[int] = mapped_column(SmallInteger)


# --- gate: autentica o estado anterior antes de qualquer regra (P1, P2, S-01) ---


class IntegrityFailure(StrEnum):
    """Categoria interna, só para log e testes: o cliente vê um código só (P7)."""

    MISSING_ANCHOR = "missing_anchor"
    MALFORMED_STATE = "malformed_state"
    CHAIN_MISMATCH = "chain_mismatch"
    ANCHOR_MISMATCH = "anchor_mismatch"
    SUMMARY_MISMATCH = "summary_mismatch"
    OPERATIONAL_MISMATCH = "operational_mismatch"


@dataclass(frozen=True)
class IntegrityConflict:
    reason: IntegrityFailure


@dataclass(frozen=True)
class AuthenticatedLot:
    """Só o gate o cria: contagem, hash final e lance atual vinculados ao histórico."""

    bid_count: int
    final_hash: str
    current: CurrentBid | None


def read_history(session: Session, lot_id: uuid.UUID) -> Sequence[Row[Any]]:
    """O histórico do lote como linhas de colunas, na ordem da sequência. Lido depois
    da trava e da hora; entidades ORM não: o identity map poderia servir estado antigo
    (D4)."""
    return session.execute(
        select(
            Bid.lot_id,
            Bid.sequence,
            Bid.bidder_id,
            Bid.bidder_alias,
            Bid.amount_cents,
            Bid.placed_at,
            Bid.previous_hash,
            Bid.current_hash,
            Bid.canonical_version,
        )
        .where(Bid.lot_id == lot_id)
        .order_by(Bid.sequence)
    ).all()


def authenticate_previous_state(
    lot: Any, rows: Sequence[Any], *, integrity: IntegrityConfig, lot_id: uuid.UUID
) -> AuthenticatedLot | IntegrityConflict:
    """Cadeia, âncora, resumo e vínculo do líder (receita §9 da 3.3 mais P2).

    Nada foi escrito ainda e nada é reparado nem reassinado. O `lot_id` é o da rota:
    uma âncora copiada de outro lote não confere (S-02). Só o `ValueError` da montagem
    dos objetos a partir das linhas vira `MALFORMED_STATE`; captura mais ampla
    esconderia bug. O alias recalculado é só o do líder atual, para vinculá-lo ao
    alias já autenticado do último evento; nenhum alias histórico é recalculado."""
    if lot.anchor_hmac is None:
        return IntegrityConflict(IntegrityFailure.MISSING_ANCHOR)
    try:
        state = AnchorState(
            v=1, lot_id=lot_id, bid_count=lot.bid_count, final_hash=lot.final_hash
        )
        records = tuple(
            VerifiableBid(
                bid=CanonicalBid(
                    v=row.canonical_version,
                    lot_id=row.lot_id,
                    sequence=row.sequence,
                    bidder_alias=row.bidder_alias,
                    amount_cents=row.amount_cents,
                    timestamp=row.placed_at,
                    previous_hash=row.previous_hash,
                ),
                current_hash=row.current_hash,
            )
            for row in rows
        )
        # Os dois resultados antes de combinar (3.3, §9.1).
        chain_ok = verify_bid_chain(records, lot_id=lot_id)
        anchor_ok = verify_anchor_hmac(
            state, lot.anchor_hmac, audit_hmac_secret=integrity.audit_hmac_secret
        )
    except ValueError:
        return IntegrityConflict(IntegrityFailure.MALFORMED_STATE)
    if not chain_ok:
        return IntegrityConflict(IntegrityFailure.CHAIN_MISMATCH)
    if not anchor_ok:
        return IntegrityConflict(IntegrityFailure.ANCHOR_MISMATCH)
    last_hash = records[-1].current_hash if records else GENESIS_HASH
    if state.bid_count != len(records) or state.final_hash != last_hash:
        return IntegrityConflict(IntegrityFailure.SUMMARY_MISMATCH)

    if state.bid_count == 0:
        if lot.current_bid_cents is not None or lot.current_leader_id is not None:
            return IntegrityConflict(IntegrityFailure.OPERATIONAL_MISMATCH)
        return AuthenticatedLot(bid_count=0, final_hash=GENESIS_HASH, current=None)

    last = records[-1].bid
    if (
        last.sequence != state.bid_count
        or lot.current_bid_cents != last.amount_cents
        or lot.current_leader_id is None
        or lot.current_leader_id != rows[-1].bidder_id
        or generate_bidder_alias(
            lot_id=lot_id,
            user_id=lot.current_leader_id,
            pseudonym_secret=integrity.pseudonym_secret,
        )
        != last.bidder_alias
    ):
        return IntegrityConflict(IntegrityFailure.OPERATIONAL_MISMATCH)
    return AuthenticatedLot(
        bid_count=state.bid_count,
        final_hash=state.final_hash,
        current=CurrentBid(
            amount_cents=lot.current_bid_cents, leader_id=lot.current_leader_id
        ),
    )


# --- serviço (não faz commit nem rollback; a rota decide) ---


@dataclass(frozen=True)
class PlacedBid:
    sequence: int
    bidder_alias: str
    amount_cents: int
    placed_at: datetime  # o `now` do passo 3, UTC
    ends_at: datetime  # `BidAccepted.ends_at`: o fim efetivo
    anti_sniping_applied: bool
    wallet: Wallet  # carteira travada do licitante, já atualizada


def place_bid(
    session: Session,
    *,
    lot_id: uuid.UUID,
    bidder_id: uuid.UUID,
    amount_cents: int,
    integrity: IntegrityConfig,
) -> PlacedBid | BidRefusal | IntegrityConflict | None:
    """Um lance numa só transação. `None` = lote inexistente. Recusa e conflito de
    integridade acontecem antes de qualquer escrita; o chamador faz o rollback."""
    lot = lock_lot(session, lot_id)  # 2: lote primeiro
    if lot is None:
        return None
    now = database_now(session)  # 3: um único instante, depois da trava

    rows = read_history(session, lot_id)  # 4: gate antes de qualquer regra (P1)
    authenticated = authenticate_previous_state(
        lot, rows, integrity=integrity, lot_id=lot_id
    )
    if isinstance(authenticated, IntegrityConflict):
        return authenticated
    current = authenticated.current

    state = LotBidState(  # 5: regras pré-carteira sobre o estado autenticado
        starts_at=lot.starts_at,
        ends_at=lot.ends_at,
        starting_bid_cents=lot.starting_bid_cents,
        min_increment_cents=lot.min_increment_cents,
        current=current,
    )
    eligible = evaluate_pre_wallet(
        state, BidAttempt(bidder_id=bidder_id, amount_cents=amount_cents), now
    )
    if isinstance(eligible, BidRefusal):
        return eligible
    if current is not None and current.leader_id == bidder_id:
        raise RuntimeError("leader reached the wallet step")  # inalcançável

    # 6-7: licitante e líder anterior, travados em user_id crescente (AD-8).
    user_ids = {bidder_id} | ({current.leader_id} if current is not None else set())
    wallets = {user_id: lock_wallet(session, user_id) for user_id in sorted(user_ids)}
    bidder_wallet = wallets[bidder_id]
    accepted = evaluate_post_wallet(  # 8: saldo da carteira travada e anti-sniping
        eligible,
        available_cents(
            bidder_wallet.total_balance_cents, bidder_wallet.committed_balance_cents
        ),
    )
    if isinstance(accepted, BidRefusal):
        return accepted

    if current is not None:  # 9: o líder anterior volta ao disponível
        wallets[current.leader_id].committed_balance_cents -= current.amount_cents
    bidder_wallet.committed_balance_cents += amount_cents  # 10
    session.flush()  # F1: UPDATE wallets

    sequence = authenticated.bid_count + 1  # 13: a contagem autenticada, não o máximo
    alias = generate_bidder_alias(  # 14
        lot_id=lot_id, user_id=bidder_id, pseudonym_secret=integrity.pseudonym_secret
    )
    current_hash = compute_bid_hash(  # 15-16: o mesmo `now` do placed_at
        CanonicalBid(
            v=1,
            lot_id=lot_id,
            sequence=sequence,
            bidder_alias=alias,
            amount_cents=amount_cents,
            timestamp=now,
            previous_hash=authenticated.final_hash,
        )
    )
    session.add(
        Bid(
            lot_id=lot_id,
            sequence=sequence,
            bidder_id=bidder_id,
            bidder_alias=alias,
            amount_cents=amount_cents,
            placed_at=now,
            previous_hash=authenticated.final_hash,
            current_hash=current_hash,
            canonical_version=1,
        )
    )
    session.flush()  # F2: INSERT bids

    anchor_hmac = compute_anchor_hmac(  # 17: sobre o estado novo, só depois do gate
        AnchorState(v=1, lot_id=lot_id, bid_count=sequence, final_hash=current_hash),
        audit_hmac_secret=integrity.audit_hmac_secret,
    )
    # 11-12 e 17: o lote só muda aqui, de uma vez; `ends_at` só se houve extensão.
    lot.current_bid_cents = amount_cents
    lot.current_leader_id = bidder_id
    lot.bid_count = sequence
    lot.final_hash = current_hash
    lot.anchor_hmac = anchor_hmac
    if accepted.anti_sniping_applied:
        lot.ends_at = accepted.ends_at
    session.flush()  # F3: um UPDATE lots

    return PlacedBid(
        sequence=sequence,
        bidder_alias=alias,
        amount_cents=amount_cents,
        placed_at=now,
        ends_at=accepted.ends_at,
        anti_sniping_applied=accepted.anti_sniping_applied,
        wallet=bidder_wallet,
    )


# --- contratos HTTP ---


class PlaceBidRequest(BaseModel):
    """Corpo do lance: só o valor. O licitante é sempre o usuário da sessão."""

    model_config = ConfigDict(extra="forbid")

    amount_cents: Cents


class AcceptedBidResponse(BaseModel):
    """O lance em representação pública: o alias é público e do próprio usuário."""

    sequence: int
    bidder_alias: str
    amount_cents: int
    placed_at: datetime


class BidLotStateResponse(BaseModel):
    current_bid_cents: int
    ends_at: datetime
    anti_sniping_applied: bool


class PlaceBidResponse(BaseModel):
    bid: AcceptedBidResponse
    lot: BidLotStateResponse
    wallet: WalletResponse


def place_bid_response(placed: PlacedBid) -> PlaceBidResponse:
    return PlaceBidResponse(
        bid=AcceptedBidResponse(
            sequence=placed.sequence,
            bidder_alias=placed.bidder_alias,
            amount_cents=placed.amount_cents,
            placed_at=placed.placed_at,
        ),
        lot=BidLotStateResponse(
            current_bid_cents=placed.amount_cents,
            ends_at=placed.ends_at,
            anti_sniping_applied=placed.anti_sniping_applied,
        ),
        wallet=wallet_response(placed.wallet),
    )


def register_bid_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/lots/{lot_id}/bids",
        methods=["POST"],
        policy=AccessPolicy.BIDDER,
        status_code=201,
        response_model=PlaceBidResponse,
        responses=error_responses(401, 403, 404, 409, 422),
    )
    def place_bid_route(
        lot_id: uuid.UUID,
        body: PlaceBidRequest,
        response: Response,
        user: User = Depends(require_bidder),
        session: Session = Depends(get_session),
        integrity: IntegrityConfig = Depends(get_integrity_config),
    ) -> PlaceBidResponse | Response:
        # D5: guardo o id e encerro a leitura da autenticação, para a transação do
        # lance começar limpa e o `User` não ficar no identity map.
        bidder_id = user.id
        session.rollback()

        outcome = place_bid(
            session,
            lot_id=lot_id,
            bidder_id=bidder_id,
            amount_cents=body.amount_cents,
            integrity=integrity,
        )
        if outcome is None:
            session.rollback()
            return error_response(404, "not_found", headers=NO_STORE)
        if isinstance(outcome, IntegrityConflict):
            session.rollback()  # libera as travas antes de responder
            # Só a categoria e o lote (público) vão ao log, nunca alias, usuário,
            # hash, HMAC nem segredo.
            logger.warning(
                "bid refused: integrity conflict lot_id=%s reason=%s",
                lot_id,
                outcome.reason.value,
            )
            return error_response(409, LOT_INTEGRITY_CONFLICT, headers=NO_STORE)
        if isinstance(outcome, BidRefusal):
            session.rollback()
            return error_response(422, outcome.value, headers=NO_STORE)

        session.commit()
        logger.info(
            "bid accepted: lot_id=%s sequence=%d anti_sniping=%s",
            lot_id,
            outcome.sequence,
            outcome.anti_sniping_applied,
        )
        response.headers["Cache-Control"] = "no-store"
        return place_bid_response(outcome)
