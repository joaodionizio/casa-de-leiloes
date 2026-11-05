"""Read-only snapshots of a bid room and authenticated participation.

The placement service and its transaction order remain in app.bids. These
functions never mutate balances or settle a lot.
"""

import logging
import uuid
from datetime import UTC
from types import SimpleNamespace
from typing import Any

from sqlalchemy import and_, func, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app import bids as bid_domain
from app.bid_rules import CurrentBid, LotBidState, minimum_bid_cents
from app.bids import (
    ROOM_BID_LIMIT,
    AcceptedBidResponse,
    Bid,
    MyLotBidsResponse,
    PublicBidRoomResponse,
    PublicSettlement,
)
from app.config import IntegrityConfig
from app.lot_time import lot_phase
from app.lots import Lot, _clock_cte

logger = logging.getLogger("uvicorn.error")


def public_room_statement(lot_id: uuid.UUID) -> Select[Any]:
    """O único statement da sala pública: o instante, o lote e os 50 lances mais
    recentes no mesmo snapshot. O `LEFT OUTER JOIN` parte do CTE (uma linha), então há
    `as_of` mesmo sem lote; o LATERAL sem linhas deixa a lista vazia. Projeta só
    colunas públicas: nunca `bidder_id`, hashes nem HMAC."""
    from app.lot_settlement import LotSettlement, Receipt

    clock = _clock_cte()
    recent = (
        select(Bid.sequence, Bid.bidder_alias, Bid.amount_cents, Bid.placed_at)
        .where(Bid.lot_id == Lot.id)
        .order_by(Bid.sequence.desc())
        .limit(ROOM_BID_LIMIT)
        .lateral("recent")
    )
    return (
        select(
            clock.c.as_of,
            Lot.id.label("lot_id"),
            Lot.starts_at,
            Lot.ends_at,
            Lot.starting_bid_cents,
            Lot.min_increment_cents,
            Lot.current_bid_cents,
            Lot.current_leader_id,
            Lot.bid_count,
            Lot.final_hash,
            *[
                getattr(LotSettlement, name).label("s_" + name)
                for name in (
                    "id",
                    "lot_id",
                    "outcome",
                    "winner_user_id",
                    "winner_alias",
                    "winning_bid_sequence",
                    "final_amount_cents",
                    "bid_count",
                    "final_hash",
                    "settled_at",
                )
            ],
            *[
                getattr(Receipt, name).label("r_" + name)
                for name in (
                    "id",
                    "lot_id",
                    "settlement_id",
                    "winner_alias",
                    "winning_bid_sequence",
                    "final_amount_cents",
                    "bid_count",
                    "final_hash",
                    "settled_at",
                )
            ],
            recent.c.sequence,
            recent.c.bidder_alias,
            recent.c.amount_cents,
            recent.c.placed_at,
        )
        .select_from(clock)
        # O cancelado (Story 3.6, D3) fica fora na condição do JOIN, nunca num WHERE:
        # o `as_of` e o caso vazio sobrevivem.
        .outerjoin(Lot, and_(Lot.id == lot_id, Lot.cancelled_at.is_(None)))
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .outerjoin(Receipt, Receipt.lot_id == Lot.id)
        .outerjoin(recent, true())
        .order_by(recent.c.sequence.desc().nulls_last())
    )


def read_public_room(
    session: Session, lot_id: uuid.UUID
) -> PublicBidRoomResponse | None:
    rows = session.execute(public_room_statement(lot_id)).all()
    first = rows[0]  # o CTE garante ao menos uma linha
    if first.lot_id is None:
        return None
    from app.lot_settlement import _structural_conflict

    def projected(prefix):
        values = {
            name[2:]: value
            for name, value in first._mapping.items()
            if name.startswith(prefix)
        }
        return SimpleNamespace(**values) if values["id"] is not None else None

    settlement, receipt = projected("s_"), projected("r_")
    conflict = _structural_conflict(settlement, receipt)
    if conflict or (
        settlement is not None
        and (
            settlement.lot_id != lot_id
            or settlement.settled_at < first.ends_at
            or settlement.bid_count != first.bid_count
            or settlement.final_hash != first.final_hash
            or settlement.final_amount_cents != first.current_bid_cents
            or settlement.winner_user_id != first.current_leader_id
        )
    ):
        logger.error(
            "public room failed lot_id=%s category=settlement_structure", lot_id
        )
        raise RuntimeError("Não foi possível consultar o resultado do lote.")
    as_of = first.as_of.astimezone(UTC)
    current = (
        None
        if first.current_bid_cents is None
        else CurrentBid(
            amount_cents=first.current_bid_cents, leader_id=first.current_leader_id
        )
    )
    minimum = minimum_bid_cents(
        LotBidState(
            starts_at=first.starts_at,
            ends_at=first.ends_at,
            starting_bid_cents=first.starting_bid_cents,
            min_increment_cents=first.min_increment_cents,
            current=current,
        )
    )
    return PublicBidRoomResponse(
        as_of=as_of,
        phase=lot_phase(first.starts_at, first.ends_at, as_of),
        ends_at=first.ends_at.astimezone(UTC),
        current_bid_cents=first.current_bid_cents,
        minimum_next_bid_cents=minimum,
        bid_count=first.bid_count,
        settlement_status="settled" if settlement else "pending",
        settlement=PublicSettlement(
            outcome=settlement.outcome,
            winner_alias=settlement.winner_alias,
            final_amount_cents=settlement.final_amount_cents,
            bid_count=settlement.bid_count,
            final_hash=settlement.final_hash,
            settled_at=settlement.settled_at.astimezone(UTC),
        )
        if settlement
        else None,
        bids=[
            AcceptedBidResponse(
                sequence=row.sequence,
                bidder_alias=row.bidder_alias,
                amount_cents=row.amount_cents,
                placed_at=row.placed_at.astimezone(UTC),
            )
            for row in rows
            if row.sequence is not None
        ],
    )


def my_bids_statement(lot_id: uuid.UUID, bidder_alias: str) -> Select[Any]:
    """Um statement de negócio: existência do lote, contagem completa e valor do maior
    `sequence` do próprio alias. Não materializa o histórico."""
    mine = (Bid.lot_id == Lot.id, Bid.bidder_alias == bidder_alias)
    count = select(func.count()).select_from(Bid).where(*mine).scalar_subquery()
    last = (
        select(Bid.amount_cents)
        .where(*mine)
        .order_by(Bid.sequence.desc())
        .limit(1)
        .scalar_subquery()
    )
    # Sem JOIN: aqui o `WHERE` é o correto, e o lote cancelado (Story 3.6, D3) vira
    # zero linhas, isto é, 404.
    return select(count.label("my_bid_count"), last.label("last_bid_cents")).where(
        Lot.id == lot_id, Lot.cancelled_at.is_(None)
    )


def read_my_bids(
    session: Session,
    *,
    lot_id: uuid.UUID,
    user_id: uuid.UUID,
    integrity: IntegrityConfig,
) -> MyLotBidsResponse | None:
    # Só o alias da sessão é calculado; aliases históricos nunca são recalculados.
    alias = bid_domain.generate_bidder_alias(
        lot_id=lot_id, user_id=user_id, pseudonym_secret=integrity.pseudonym_secret
    )
    row = session.execute(my_bids_statement(lot_id, alias)).one_or_none()
    if row is None:
        return None
    return MyLotBidsResponse(
        bidder_alias=alias,
        my_bid_count=row.my_bid_count,
        last_bid_cents=row.last_bid_cents,
    )
