"""HTTP endpoints for bidding; transaction boundaries remain explicit."""

import logging
import uuid

from fastapi import Depends, FastAPI, Response
from sqlalchemy.orm import Session

from app import bids as bid_domain
from app.access import NO_STORE, AccessPolicy, api_route, require_bidder
from app.bid_rules import BidRefusal
from app.bids import (
    IntegrityConflict,
    MyLotBidsResponse,
    PlaceBidRequest,
    PlaceBidResponse,
    PublicBidRoomResponse,
)
from app.config import IntegrityConfig
from app.db import get_session
from app.errors import LOT_INTEGRITY_CONFLICT, error_response, error_responses
from app.lots import get_integrity_config
from app.users import User

logger = logging.getLogger("uvicorn.error")


def register_bid_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/lots/{lot_id}/bids",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicBidRoomResponse,
        responses=error_responses(404, 422),
    )
    def public_bid_room(
        lot_id: uuid.UUID,
        response: Response,
        session: Session = Depends(get_session),
    ) -> PublicBidRoomResponse | Response:
        result = bid_domain.read_public_room(session, lot_id)
        session.rollback()  # encerra a transação de leitura antes de responder
        if result is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result

    @api_route(
        app,
        "/api/lots/{lot_id}/bids/mine",
        methods=["GET"],
        policy=AccessPolicy.BIDDER,
        response_model=MyLotBidsResponse,
        responses=error_responses(401, 403, 404, 422),
    )
    def my_lot_bids(
        lot_id: uuid.UUID,
        response: Response,
        user: User = Depends(require_bidder),
        session: Session = Depends(get_session),
        integrity: IntegrityConfig = Depends(get_integrity_config),
    ) -> MyLotBidsResponse | Response:
        user_id = user.id
        result = bid_domain.read_my_bids(
            session, lot_id=lot_id, user_id=user_id, integrity=integrity
        )
        session.rollback()
        if result is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result

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

        outcome = bid_domain.place_bid(
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
        from app.lot_room import signal_committed

        signal_committed(app, lot_id)
        logger.info(
            "bid accepted: lot_id=%s sequence=%d anti_sniping=%s",
            lot_id,
            outcome.sequence,
            outcome.anti_sniping_applied,
        )
        response.headers["Cache-Control"] = "no-store"
        return bid_domain.place_bid_response(outcome)
