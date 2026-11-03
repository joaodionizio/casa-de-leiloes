"""SQL read models and snapshot projections for auction lots.

Reads share the database clock and transaction snapshot; they never settle
auctions or acquire write locks. Models and schemas remain in app.lots.
"""

import logging
import re
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

from pydantic import ValidationError
from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import CTE

from app.catalog import image_url_for
from app.lot_time import LotPhase, lot_phase
from app.lots import (
    Lot,
    LotResponse,
    MyLotsResponse,
    PrivateLotSettlementSummary,
    PublicLotDetail,
    PublicLotsResponse,
    PublicLotSummary,
    my_lot_response,
)
from app.money import MAX_CENTS

if TYPE_CHECKING:
    from app.bids import IntegrityConflict

logger = logging.getLogger("uvicorn.error")


def _clock_cte() -> CTE:
    """`clock_timestamp()` avaliado uma única vez: o CTE `MATERIALIZED` nunca é
    embutido na consulta, então o valor se repete em todas as linhas."""
    return (
        select(func.clock_timestamp().label("as_of"))
        .cte("clock")
        .prefix_with("MATERIALIZED")
    )


def public_snapshot_statement() -> Select:
    """O único statement da vitrine: o instante e todos os lotes no mesmo snapshot.
    O `LEFT OUTER JOIN` parte do CTE (uma linha), então há `as_of` mesmo sem lotes. O
    cancelado (Story 3.6, D3) é excluído na condição do JOIN, nunca num `WHERE`: o
    `WHERE` apagaria a linha do `as_of` quando só há lotes cancelados."""
    from app.lot_settlement import LotSettlement

    clock = _clock_cte()
    return (
        select(clock.c.as_of, Lot, LotSettlement.id.label("settlement_id"))
        .select_from(clock)
        .outerjoin(Lot, Lot.cancelled_at.is_(None))
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .execution_options(autoflush=False)
    )


def my_lots_statement(auctioneer_id: uuid.UUID) -> Select:
    """O statement da lista do leiloeiro (Story 3.6, D7): o instante e os lotes do dono
    no mesmo snapshot, **inclusive os cancelados**. Parte do CTE, então há `as_of` mesmo
    sem lotes; a ordem é a de sempre, `created_at DESC, id DESC`."""
    from app.lot_settlement import LotSettlement, Receipt

    clock = _clock_cte()
    lot_columns = [name for name in LotResponse.model_fields if name != "image_url"] + [
        "cancelled_at",
        "bid_count",
        "current_bid_cents",
        "current_leader_id",
        "final_hash",
    ]
    settlement_columns = (
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
    receipt_columns = (
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
    return (
        select(
            clock.c.as_of,
            *[getattr(Lot, name).label("l_" + name) for name in lot_columns],
            *[
                getattr(LotSettlement, name).label("s_" + name)
                for name in settlement_columns
            ],
            *[getattr(Receipt, name).label("r_" + name) for name in receipt_columns],
        )
        .select_from(clock)
        .outerjoin(Lot, Lot.auctioneer_id == auctioneer_id)
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .outerjoin(Receipt, Receipt.lot_id == Lot.id)
        .order_by(Lot.created_at.desc().nulls_last(), Lot.id.desc().nulls_last())
        .execution_options(autoflush=False)
    )


def read_my_lots_snapshot(
    session: Session, auctioneer_id: uuid.UUID
) -> "MyLotsResponse | IntegrityConflict":
    from app.bids import IntegrityConflict, IntegrityFailure
    from app.lot_settlement import _structural_conflict

    rows = session.execute(my_lots_statement(auctioneer_id)).all()
    as_of = rows[0].as_of.astimezone(UTC)
    items = []
    total = 0
    for row in rows:

        def projected(prefix, row=row):
            values = {
                name[2:]: value
                for name, value in row._mapping.items()
                if name.startswith(prefix)
            }
            return SimpleNamespace(**values) if values["id"] is not None else None

        lot, settlement, receipt = projected("l_"), projected("s_"), projected("r_")
        if lot is None:
            continue
        conflict = _structural_conflict(settlement, receipt)
        summary = None
        if settlement is not None and not conflict:
            try:
                summary = PrivateLotSettlementSummary(
                    **{
                        name: getattr(settlement, name)
                        for name in PrivateLotSettlementSummary.model_fields
                    }
                )
                valid = (
                    lot.cancelled_at is None
                    and lot_phase(lot.starts_at, lot.ends_at, as_of) == LotPhase.ENDED
                    and settlement.lot_id == lot.id
                    and summary.settled_at >= lot.ends_at
                    and settlement.bid_count == lot.bid_count
                    and settlement.final_hash == lot.final_hash
                    and re.fullmatch(r"[0-9a-f]{64}", settlement.final_hash) is not None
                    and settlement.final_amount_cents == lot.current_bid_cents
                    and settlement.winner_user_id == lot.current_leader_id
                    and (
                        settlement.outcome != "sold"
                        or (
                            settlement.winner_user_id is not None
                            and settlement.winning_bid_sequence == settlement.bid_count
                        )
                    )
                )
            except ValidationError:
                valid = False
            if not valid:
                conflict = IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
        if conflict:
            logger.error(
                "private lot read failed lot_id=%s category=settlement_structure",
                lot.id,
            )
            return conflict
        items.append(my_lot_response(lot, as_of, summary))
        if summary and summary.outcome == "sold":
            total += summary.final_amount_cents
    if total > MAX_CENTS:
        logger.error("private lot read failed category=total_range")
        return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
    return MyLotsResponse(as_of=as_of, items=items, total_received_cents=total)


def read_public_snapshot(
    session: Session,
) -> tuple[datetime, list[Lot], set[uuid.UUID]]:
    rows = session.execute(public_snapshot_statement()).all()
    as_of = rows[0].as_of.astimezone(UTC)
    return (
        as_of,
        [row.Lot for row in rows if row.Lot is not None],
        {row.Lot.id for row in rows if row.settlement_id is not None},
    )


def read_public_lot_snapshot(
    session: Session, lot_id: uuid.UUID
) -> tuple[datetime, Lot | None, bool]:
    # A condição do id (e a do cancelamento, D3) fica no JOIN, nunca num WHERE: o WHERE
    # apagaria a linha do `as_of` quando o lote não existe ou está cancelado.
    from app.lot_settlement import LotSettlement

    clock = _clock_cte()
    row = session.execute(
        select(clock.c.as_of, Lot, LotSettlement.id.label("settlement_id"))
        .select_from(clock)
        .outerjoin(Lot, and_(Lot.id == lot_id, Lot.cancelled_at.is_(None)))
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .execution_options(autoflush=False)
    ).one()
    return row.as_of.astimezone(UTC), row.Lot, row.settlement_id is not None


def public_lot_summary(
    lot: Lot, as_of: datetime, *, has_settlement: bool
) -> PublicLotSummary:
    return PublicLotSummary(
        id=lot.id,
        title=lot.title,
        artist_display=lot.artist_display,
        date_display=lot.date_display,
        image_url=image_url_for(lot.image_id),
        starting_bid_cents=lot.starting_bid_cents,
        current_bid_cents=lot.current_bid_cents,
        starts_at=lot.starts_at.astimezone(UTC),
        ends_at=lot.ends_at.astimezone(UTC),
        phase=lot_phase(lot.starts_at, lot.ends_at, as_of),
        settlement_status="settled" if has_settlement else "pending",
    )


def public_lot_detail(
    lot: Lot, as_of: datetime, *, has_settlement: bool
) -> PublicLotDetail:
    return PublicLotDetail(
        **public_lot_summary(lot, as_of, has_settlement=has_settlement).model_dump(),
        external_id=lot.external_id,
        medium_display=lot.medium_display,
        dimensions=lot.dimensions,
        department_title=lot.department_title,
        artwork_type_title=lot.artwork_type_title,
        credit_line=lot.credit_line,
        source_url=lot.source_url,
        min_increment_cents=lot.min_increment_cents,
    )


def build_public_lots(
    lots: list[Lot], as_of: datetime, settled_lot_ids: set[uuid.UUID]
) -> PublicLotsResponse:
    """Classifica todos os lotes com o MESMO `as_of` e ordena cada grupo (P4, D3):
    ao vivo `ends_at ASC`, agendados `starts_at ASC`, encerrados `ends_at DESC`;
    `id ASC` desempata nos três."""
    by_phase: dict[LotPhase, list[Lot]] = {phase: [] for phase in LotPhase}
    for lot in lots:
        by_phase[lot_phase(lot.starts_at, lot.ends_at, as_of)].append(lot)
    live = sorted(by_phase[LotPhase.LIVE], key=lambda lot: (lot.ends_at, lot.id))
    scheduled = sorted(
        by_phase[LotPhase.SCHEDULED], key=lambda lot: (lot.starts_at, lot.id)
    )
    # `reverse=True` preserva a estabilidade: o `id ASC` do primeiro sort sobrevive.
    ended = sorted(by_phase[LotPhase.ENDED], key=lambda lot: lot.id)
    ended.sort(key=lambda lot: lot.ends_at, reverse=True)
    return PublicLotsResponse(
        as_of=as_of,
        live=[
            public_lot_summary(lot, as_of, has_settlement=lot.id in settled_lot_ids)
            for lot in live
        ],
        scheduled=[
            public_lot_summary(lot, as_of, has_settlement=lot.id in settled_lot_ids)
            for lot in scheduled
        ],
        ended=[
            public_lot_summary(lot, as_of, has_settlement=lot.id in settled_lot_ids)
            for lot in ended
        ],
    )
