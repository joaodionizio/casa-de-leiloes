"""Carteira e depósito simulado (Story 3.1, AD-3, AD-8, AD-11, AD-19, AD-30).

Um módulo, como `lots.py`: modelo, schemas, regra pura, serviço e rotas. A carteira é
o estado agregado atual do licitante (1:1 com `users`): total e comprometido, em
centavos. O disponível é sempre derivado (`total - committed`), nunca persistido.

O depósito é a primeira escrita financeira do sistema. Ele lê o saldo só depois de
travar a linha (`SELECT ... FOR UPDATE`), então dois depósitos concorrentes na mesma
carteira nunca se perdem. Trava uma carteira só e nenhum lote (AD-8).

Este módulo não importa `app.lots`, `app.catalog`, `app.artic` nem `app.main`: o seed o
importa e roda sem `APP_ORIGIN`, sem `JWT_SECRET` e sem rede.
"""

import uuid
from enum import StrEnum

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, exists, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.access import NO_STORE, AccessPolicy, api_route, require_bidder
from app.db import Base, get_session
from app.errors import BALANCE_LIMIT_EXCEEDED, error_response, error_responses
from app.money import MAX_CENTS, Cents
from app.users import User


class Wallet(Base):
    """Espelha a migration `0004`; o esquema dos testes vem sempre dela. Sem
    `available_balance_cents`, sem `id` e sem timestamps (P1, P5)."""

    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint(
            f"total_balance_cents >= 0 AND total_balance_cents <= {MAX_CENTS}",
            name="total_range",
        ),
        CheckConstraint(
            f"committed_balance_cents >= 0 AND committed_balance_cents <= {MAX_CENTS}",
            name="committed_range",
        ),
        CheckConstraint(
            "committed_balance_cents <= total_balance_cents",
            name="committed_within_total",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    total_balance_cents: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0")
    )
    committed_balance_cents: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0")
    )


class MissingWalletError(RuntimeError):
    """Usuário autenticado sem carteira: violação de invariante (P2, D6). Não é
    tratada na rota; o handler global responde 500 genérico e o traceback fica só no
    log do servidor. A mensagem não leva e-mail nem ID."""

    def __init__(self) -> None:
        super().__init__("wallet missing for authenticated user")


class DepositRefusal(StrEnum):
    BALANCE_LIMIT_EXCEEDED = "balance_limit_exceeded"


# --- regra pura (sem banco) ---


def available_cents(total: int, committed: int) -> int:
    return total - committed


def apply_deposit(total: int, amount: int) -> int | DepositRefusal:
    """O novo total, ou a recusa se ele passaria do teto técnico.

    O valor precisa ser um `Cents` (inteiro em `1..MAX_CENTS`, nunca `bool`), como na
    API. A rota já o garante pelo `DepositRequest`; esta guarda protege a regra de um
    chamador interno (um depósito não pode virar débito). Violação é erro de
    programação: `ValueError`, que numa requisição vira o 500 genérico."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("deposit amount must be integer cents")
    if not 0 < amount <= MAX_CENTS:
        raise ValueError("deposit amount out of range")
    new_total = total + amount
    if new_total > MAX_CENTS:
        return DepositRefusal.BALANCE_LIMIT_EXCEEDED
    return new_total


# --- serviço (nenhum faz commit; a rota decide) ---


def ensure_wallets(session: Session) -> int:
    """Dá uma carteira zerada a todo usuário que não tem uma e devolve quantas
    inseriu. Só `INSERT`: nunca altera saldo existente. É o único caminho de criação
    de carteira fora da migration (P2); nenhuma requisição o chama."""
    inserted = session.execute(
        insert(Wallet)
        .from_select(
            ["user_id"],
            select(User.id).where(~exists().where(Wallet.user_id == User.id)),
        )
        .on_conflict_do_nothing(index_elements=[Wallet.user_id])
        .returning(Wallet.user_id)
    )
    return len(inserted.all())


def read_wallet(session: Session, user_id: uuid.UUID) -> Wallet:
    """Leitura simples, sem trava (AD-19)."""
    wallet = session.get(Wallet, user_id)
    if wallet is None:
        raise MissingWalletError
    return wallet


def lock_wallet(session: Session, user_id: uuid.UUID) -> Wallet:
    """Trava a linha e devolve o saldo confirmado mais recente. `populate_existing`
    força a releitura mesmo que a `Session` já tenha o objeto: depois de esperar a
    trava, o saldo usado é o que a outra transação confirmou (P4)."""
    wallet = session.scalars(
        select(Wallet)
        .where(Wallet.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if wallet is None:
        raise MissingWalletError
    return wallet


def deposit(
    session: Session, user_id: uuid.UUID, amount_cents: int
) -> Wallet | DepositRefusal:
    """Soma `amount_cents` ao total sob a trava da carteira. A recusa não altera
    nada; a rota faz o rollback que libera a trava."""
    wallet = lock_wallet(session, user_id)
    result = apply_deposit(wallet.total_balance_cents, amount_cents)
    if isinstance(result, DepositRefusal):
        return result
    wallet.total_balance_cents = result
    session.flush()
    return wallet


# --- contratos HTTP ---


class DepositRequest(BaseModel):
    """Corpo do depósito: só o valor. O dono é sempre o usuário da sessão."""

    model_config = ConfigDict(extra="forbid")

    amount_cents: Cents


class WalletResponse(BaseModel):
    total_balance_cents: int
    committed_balance_cents: int
    available_balance_cents: int


def wallet_response(wallet: Wallet) -> WalletResponse:
    return WalletResponse(
        total_balance_cents=wallet.total_balance_cents,
        committed_balance_cents=wallet.committed_balance_cents,
        available_balance_cents=available_cents(
            wallet.total_balance_cents, wallet.committed_balance_cents
        ),
    )


def register_wallet_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/wallet",
        methods=["GET"],
        policy=AccessPolicy.BIDDER,
        response_model=WalletResponse,
        responses=error_responses(401, 403),
    )
    def read_own_wallet(
        response: Response,
        user: User = Depends(require_bidder),
        session: Session = Depends(get_session),
    ) -> WalletResponse:
        # Leitura pura (AD-19): só SELECT, sem trava e sem criar carteira ausente.
        result = wallet_response(read_wallet(session, user.id))
        session.rollback()  # encerra a leitura antes da resposta
        response.headers["Cache-Control"] = "no-store"
        return result

    @api_route(
        app,
        "/api/wallet/deposit",
        methods=["POST"],
        policy=AccessPolicy.BIDDER,
        response_model=WalletResponse,
        responses=error_responses(401, 403, 422),
    )
    def deposit_to_own_wallet(
        body: DepositRequest,
        response: Response,
        user: User = Depends(require_bidder),
        session: Session = Depends(get_session),
    ) -> WalletResponse | Response:
        # Uma transação curta: trava a carteira, relê, valida o teto, atualiza e
        # confirma. Nenhuma chamada externa e nenhuma outra trava dentro dela.
        outcome = deposit(session, user.id, body.amount_cents)
        if isinstance(outcome, DepositRefusal):
            session.rollback()  # libera a trava antes de responder
            return error_response(422, BALANCE_LIMIT_EXCEEDED, headers=NO_STORE)
        session.commit()
        response.headers["Cache-Control"] = "no-store"
        return wallet_response(outcome)
