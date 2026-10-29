"""Public read-only audit: one PostgreSQL snapshot, explicit public projection.

Canonical v1 is sorted UTF-8 JSON without whitespace, with fields amount_cents,
bidder_alias, lot_id, previous_hash, sequence, timestamp and v. timestamp is UTC
with six fractional digits and Z (the API calls it placed_at). SHA-256 hashes
those bytes; genesis is 64 zeroes. HMAC is an internal server authentication,
not an independently reproducible public proof. Historical aliases stay persisted.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import AccessPolicy, api_route
from app.bid_integrity import (
    GENESIS_HASH,
    AnchorState,
    CanonicalBid,
    VerifiableBid,
    verify_anchor_hmac,
    verify_bid_chain,
)
from app.bids import Bid, PublicSettlement
from app.config import IntegrityConfig
from app.db import get_session
from app.errors import error_response, error_responses
from app.lot_settlement import LotSettlement, Receipt, _structural_conflict
from app.lot_time import lot_phase
from app.lots import Lot, _clock_cte, get_integrity_config

logger = logging.getLogger("uvicorn.error")
NO_STORE = {"Cache-Control": "no-store"}


class PublicAuditBid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int
    bidder_alias: str
    amount_cents: int
    placed_at: datetime
    canonical_version: int
    previous_hash: str
    current_hash: str


class PublicAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: uuid.UUID
    as_of: datetime
    integrity: Literal["verified", "adulterated"]
    phase: Literal["scheduled", "live", "ended", "cancelled"] | None = None
    settlement_status: Literal["pending", "settled", "not_applicable"] | None = None
    settlement: PublicSettlement | None = None
    bid_count: int | None = None
    final_hash: str | None = None
    bids: list[PublicAuditBid] = []


def audit_statement(lot_id: uuid.UUID):
    clock = _clock_cte()
    # Column-only rows avoid stale identity-map state and implicit ORM loads.
    tables = (("l", Lot), ("b", Bid), ("s", LotSettlement), ("r", Receipt))
    return (
        select(
            clock.c.as_of,
            *[
                column.label(prefix + "_" + column.name)
                for prefix, model in tables
                for column in model.__table__.columns
            ],
        )
        .select_from(clock)
        .outerjoin(Lot, Lot.id == lot_id)
        .outerjoin(Bid, Bid.lot_id == Lot.id)
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .outerjoin(Receipt, Receipt.lot_id == Lot.id)
        .order_by(Bid.sequence)
        .execution_options(autoflush=False)
    )


def _project(row, prefix, identity="id"):
    from types import SimpleNamespace

    values = {
        key[len(prefix) + 1 :]: value
        for key, value in row._mapping.items()
        if key.startswith(prefix + "_")
    }
    return SimpleNamespace(**values) if values[identity] is not None else None


def _verified(lot, bids, settlement, receipt, as_of, integrity):
    try:
        state = AnchorState(
            v=1, lot_id=lot.id, bid_count=lot.bid_count, final_hash=lot.final_hash
        )
        records = tuple(
            VerifiableBid(
                bid=CanonicalBid(
                    v=b.canonical_version,
                    lot_id=b.lot_id,
                    sequence=b.sequence,
                    bidder_alias=b.bidder_alias,
                    amount_cents=b.amount_cents,
                    timestamp=b.placed_at,
                    previous_hash=b.previous_hash,
                ),
                current_hash=b.current_hash,
            )
            for b in bids
        )
        chain_ok = verify_bid_chain(records, lot_id=lot.id)
        anchor_ok = verify_anchor_hmac(
            state, lot.anchor_hmac, audit_hmac_secret=integrity.audit_hmac_secret
        )
        phase = lot_phase(lot.starts_at, lot.ends_at, as_of)
    except ValueError:
        return False
    if not chain_ok or not anchor_ok:
        return False
    if state.bid_count != len(bids) or state.final_hash != (
        records[-1].current_hash if records else GENESIS_HASH
    ):
        return False
    last = bids[-1] if bids else None
    if last:
        if (
            lot.current_bid_cents != last.amount_cents
            or lot.current_leader_id != last.bidder_id
            or last.bidder_id == lot.auctioneer_id
        ):
            return False
    elif lot.current_bid_cents is not None or lot.current_leader_id is not None:
        return False
    if _structural_conflict(settlement, receipt):
        return False
    if lot.cancelled_at is not None and settlement is not None:
        return False
    if settlement:
        if (
            phase != "ended"
            or settlement.settled_at < lot.ends_at
            or settlement.settled_at > as_of
            or settlement.bid_count != state.bid_count
            or settlement.final_hash != state.final_hash
            or settlement.anchor_hmac != lot.anchor_hmac
        ):
            return False
        if last:
            if (
                settlement.outcome != "sold"
                or settlement.winner_user_id != last.bidder_id
                or settlement.winner_alias != last.bidder_alias
                or settlement.winning_bid_sequence != last.sequence
                or settlement.final_amount_cents != last.amount_cents
            ):
                return False
        elif settlement.outcome != "unsold":
            return False
    return True


def read_audit(session: Session, lot_id: uuid.UUID, integrity: IntegrityConfig):
    rows = session.execute(audit_statement(lot_id)).all()
    lot = _project(rows[0], "l")
    if lot is None:
        return None
    as_of = rows[0].as_of.astimezone(UTC)
    bids = [bid for row in rows if (bid := _project(row, "b", "sequence"))]
    settlement, receipt = _project(rows[0], "s"), _project(rows[0], "r")
    if not _verified(lot, bids, settlement, receipt, as_of, integrity):
        return PublicAudit(lot_id=lot_id, as_of=as_of, integrity="adulterated")
    return PublicAudit(
        lot_id=lot_id,
        as_of=as_of,
        integrity="verified",
        phase="cancelled"
        if lot.cancelled_at
        else lot_phase(lot.starts_at, lot.ends_at, as_of),
        settlement_status=(
            "not_applicable"
            if lot.cancelled_at
            else "settled"
            if settlement
            else "pending"
        ),
        settlement=PublicSettlement(
            **{
                name: getattr(settlement, name)
                for name in PublicSettlement.model_fields
            }
        )
        if settlement
        else None,
        bid_count=lot.bid_count,
        final_hash=lot.final_hash,
        bids=[
            PublicAuditBid(
                **{name: getattr(bid, name) for name in PublicAuditBid.model_fields}
            )
            for bid in bids
        ],
    )


def register_audit_routes(app: FastAPI):
    @api_route(
        app,
        "/api/lots/{lot_id}/audit",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicAudit,
        responses=error_responses(404, 422, 500),
    )
    def audit(
        lot_id: uuid.UUID,
        response: Response,
        session: Session = Depends(get_session),
        integrity: IntegrityConfig = Depends(get_integrity_config),
    ) -> PublicAudit | Response:
        try:
            result = read_audit(session, lot_id, integrity)
        except Exception:
            logger.error("public audit failed category=operational")
            return error_response(500, "internal_error", headers=NO_STORE)
        finally:
            session.rollback()
        if result is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result
