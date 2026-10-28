"""Read-only participation and persisted wins for the authenticated bidder."""

import logging
import re
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Literal

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.access import NO_STORE, AccessPolicy, api_route, require_bidder
from app.bids import Bid, IntegrityConflict, IntegrityFailure
from app.catalog import image_url_for
from app.db import get_session
from app.errors import error_response, error_responses
from app.lot_settlement import LotSettlement, Receipt, _structural_conflict
from app.lots import Lot, LotPhase, PrivateLotSettlementSummary, _clock_cte, lot_phase
from app.users import User

logger = logging.getLogger("uvicorn.error")


class MyWin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lot_id: uuid.UUID
    title: str | None
    artist_display: str | None
    image_url: str
    phase: Literal["scheduled", "live", "ended", "cancelled"]
    settlement_status: Literal["pending", "settled", "not_applicable"]
    result: Literal["won", "not_won"] | None
    winner_alias: str | None
    final_amount_cents: int | None
    settled_at: datetime | None
    bid_count: int


class MyWinsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime
    items: list[MyWin]


def read_my_wins_snapshot(session: Session, user_id: uuid.UUID):
    clock = _clock_cte()
    participation = exists().where(Bid.lot_id == Lot.id, Bid.bidder_id == user_id)
    own_sale = (
        exists()
        .where(
            LotSettlement.lot_id == Lot.id,
            LotSettlement.outcome == "sold",
            LotSettlement.winner_user_id == user_id,
        )
        .correlate(Lot)
    )
    rows = session.execute(
        select(
            clock.c.as_of,
            *[column.label("l_" + column.name) for column in Lot.__table__.columns],
            *[
                column.label("s_" + column.name)
                for column in LotSettlement.__table__.columns
            ],
            *[column.label("r_" + column.name) for column in Receipt.__table__.columns],
        )
        .select_from(clock)
        .outerjoin(Lot, or_(participation, own_sale))
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .outerjoin(Receipt, Receipt.lot_id == Lot.id)
        .order_by(Lot.created_at.desc().nulls_last(), Lot.id.desc().nulls_last())
        .execution_options(autoflush=False)
    ).all()
    as_of = rows[0].as_of.astimezone(UTC)
    items = []
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
            return conflict
        won = (
            settlement is not None
            and settlement.outcome == "sold"
            and settlement.winner_user_id == user_id
        )
        cancelled = lot.cancelled_at is not None
        items.append(
            MyWin(
                lot_id=lot.id,
                title=lot.title,
                artist_display=lot.artist_display,
                image_url=image_url_for(lot.image_id),
                phase="cancelled"
                if cancelled
                else lot_phase(lot.starts_at, lot.ends_at, as_of).value,
                settlement_status="not_applicable"
                if cancelled
                else "settled"
                if settlement
                else "pending",
                result="won" if won else "not_won" if settlement or cancelled else None,
                winner_alias=receipt.winner_alias if won else None,
                final_amount_cents=receipt.final_amount_cents if won else None,
                settled_at=receipt.settled_at.astimezone(UTC) if won else None,
                bid_count=receipt.bid_count if won else lot.bid_count,
            )
        )
    return MyWinsResponse(as_of=as_of, items=items)


def register_my_wins_routes(app: FastAPI):
    @api_route(
        app,
        "/api/me/wins",
        methods=["GET"],
        policy=AccessPolicy.BIDDER,
        response_model=MyWinsResponse,
        responses=error_responses(401, 403, 409, 500),
    )
    def my_wins(
        response: Response,
        user: User = Depends(require_bidder),
        session: Session = Depends(get_session),
    ):
        try:
            result = read_my_wins_snapshot(session, user.id)
        except Exception:
            logger.error("private wins read failed category=operational")
            return error_response(500, "internal_error", headers=NO_STORE)
        finally:
            session.rollback()
        if isinstance(result, IntegrityConflict):
            return error_response(409, "lot_integrity_conflict", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result
