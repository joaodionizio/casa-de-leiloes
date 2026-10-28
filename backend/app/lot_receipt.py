"""Public, read-only projection of the persisted sale receipt."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.access import AccessPolicy, api_route
from app.catalog import image_url_for
from app.config import IntegrityConfig
from app.db import get_session
from app.errors import error_response, error_responses
from app.lot_audit import NO_STORE, _project, _verified, audit_statement
from app.lot_settlement import _structural_conflict
from app.lots import get_integrity_config

logger = logging.getLogger("uvicorn.error")


class PublicReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: uuid.UUID
    title: str | None
    artist_display: str | None
    image_url: str
    winner_alias: str
    winning_bid_sequence: int
    final_amount_cents: int
    settled_at: datetime
    bid_count: int
    final_hash: str


def read_public_receipt(
    session: Session, lot_id: uuid.UUID, integrity: IntegrityConfig
):
    rows = session.execute(audit_statement(lot_id)).all()
    lot = _project(rows[0], "l")
    if lot is None:
        return None
    settlement, receipt = _project(rows[0], "s"), _project(rows[0], "r")
    if _structural_conflict(settlement, receipt) or (lot.cancelled_at and settlement):
        return False
    if settlement is None or settlement.outcome == "unsold":
        return None
    bids = [bid for row in rows if (bid := _project(row, "b", "sequence"))]
    if not _verified(
        lot, bids, settlement, receipt, rows[0].as_of.astimezone(UTC), integrity
    ):
        return False
    return PublicReceipt(
        lot_id=receipt.lot_id,
        title=lot.title,
        artist_display=lot.artist_display,
        image_url=image_url_for(lot.image_id),
        winner_alias=receipt.winner_alias,
        winning_bid_sequence=receipt.winning_bid_sequence,
        final_amount_cents=receipt.final_amount_cents,
        settled_at=receipt.settled_at,
        bid_count=receipt.bid_count,
        final_hash=receipt.final_hash,
    )


def register_receipt_routes(app: FastAPI):
    @api_route(
        app,
        "/api/lots/{lot_id}/receipt",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicReceipt,
        responses=error_responses(404, 409, 422, 500),
    )
    def receipt(
        lot_id: uuid.UUID,
        response: Response,
        session: Session = Depends(get_session),
        integrity: IntegrityConfig = Depends(get_integrity_config),
    ) -> PublicReceipt | Response:
        try:
            result = read_public_receipt(session, lot_id, integrity)
        except Exception:
            logger.error("public receipt failed category=operational")
            return error_response(500, "internal_error", headers=NO_STORE)
        finally:
            session.rollback()
        if result is False:
            return error_response(409, "lot_integrity_conflict", headers=NO_STORE)
        if result is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result
