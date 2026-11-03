"""HTTP endpoints for lots. Domain and persistence remain in app.lots."""

import logging
import uuid

from fastapi import Depends, FastAPI, Response
from sqlalchemy.orm import Session

from app import lots as lot_domain
from app.access import NO_STORE, AccessPolicy, api_route, require_auctioneer
from app.artic import ArticClient, CatalogUnavailable
from app.catalog import get_artic_client
from app.config import IntegrityConfig
from app.db import get_session
from app.errors import (
    ARTWORK_NOT_ELIGIBLE,
    CATALOG_UNAVAILABLE,
    LOT_INTEGRITY_CONFLICT,
    error_response,
    error_responses,
)
from app.lots import (
    ArtworkRefusal,
    CreateLotRequest,
    LotResponse,
    MyLotsResponse,
    PublicLotDetailResponse,
    PublicLotsResponse,
    ScheduleViolation,
    get_integrity_config,
)
from app.users import User

logger = logging.getLogger("uvicorn.error")


def _violation_response(violation: ScheduleViolation) -> Response:
    field = (
        "starts_at"
        if violation == ScheduleViolation.STARTS_AT_NOT_IN_FUTURE
        else "ends_at"
    )
    return error_response(
        422,
        "validation_error",
        details=[{"loc": ["body", field], "type": violation.value}],
        headers=NO_STORE,
    )


def register_lot_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/lots",
        methods=["POST"],
        policy=AccessPolicy.AUCTIONEER,
        status_code=201,
        response_model=LotResponse,
        responses=error_responses(401, 403, 422, 503),
    )
    def create(
        body: CreateLotRequest,
        response: Response,
        user: User = Depends(require_auctioneer),
        session: Session = Depends(get_session),
        client: ArticClient = Depends(get_artic_client),
        integrity: IntegrityConfig = Depends(get_integrity_config),
    ) -> LotResponse | Response:
        # D1: guardo o id antes do rollback (que expira o `User`) e encerro a
        # leitura da autenticação antes da AIC. Nenhuma transação fica aberta
        # durante a chamada externa, que leva até alguns segundos.
        auctioneer_id = user.id
        session.rollback()

        # Validação que não depende de `now` sai antes da AIC (não gasta a cota).
        if lot_domain.ends_not_after_scheduled_start(body.starts_at, body.ends_at):
            return _violation_response(ScheduleViolation.ENDS_AT_NOT_AFTER_START)

        try:
            resolved = lot_domain.resolve_artwork_for_lot(client, body.external_id)
        except CatalogUnavailable as error:
            # Só a categoria vai ao log: nunca o corpo, o usuário nem a resposta da AIC.
            logger.warning(
                "artic request failed: operation=create_lot reason=%s", error.reason
            )
            return error_response(503, CATALOG_UNAVAILABLE, headers=NO_STORE)
        if isinstance(resolved, ArtworkRefusal):
            logger.info("lot creation refused: reason=%s", resolved)
            return error_response(422, ARTWORK_NOT_ELIGIBLE, headers=NO_STORE)

        # Transação de escrita: um único instante do banco para as regras e para o
        # `created_at`; a transação só insere e confirma.
        now = lot_domain.database_now(session)
        result = lot_domain.create_lot(
            session,
            snapshot=resolved,
            terms=body,
            auctioneer_id=auctioneer_id,
            now=now,
            audit_hmac_secret=integrity.audit_hmac_secret,
        )
        if isinstance(result, ScheduleViolation):
            session.rollback()
            return _violation_response(result)
        session.commit()

        response.headers["Cache-Control"] = "no-store"
        return lot_domain.lot_response(result)

    # Registrada antes de `/api/lots/{lot_id}` (2.5, D4): senão "mine" cairia no
    # parâmetro.
    @api_route(
        app,
        "/api/lots/mine",
        methods=["GET"],
        policy=AccessPolicy.AUCTIONEER,
        response_model=MyLotsResponse,
        responses=error_responses(401, 403, 409, 500),
    )
    def my_lots(
        response: Response,
        user: User = Depends(require_auctioneer),
        session: Session = Depends(get_session),
    ) -> MyLotsResponse | Response:
        # Leitura pura (AD-19): um SELECT, só o dono da sessão, sem a AIC, sem limite.
        # Inclui os cancelados (D3); a fase vem do `as_of` do banco, não do navegador.
        from app.bids import IntegrityConflict

        try:
            result = lot_domain.read_my_lots_snapshot(session, user.id)
        except Exception:
            logger.error("private lot read failed category=operational")
            return error_response(500, "internal_error", headers=NO_STORE)
        finally:
            session.rollback()
        if isinstance(result, IntegrityConflict):
            return error_response(409, LOT_INTEGRITY_CONFLICT, headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result

    @api_route(
        app,
        "/api/lots",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicLotsResponse,
    )
    def public_lots(
        response: Response, session: Session = Depends(get_session)
    ) -> PublicLotsResponse:
        # Leitura pública (AD-19): um único statement `SELECT`, sem trava, sem a AIC e
        # sem sessão. O instante e as linhas vêm do mesmo snapshot (P2 refinada).
        as_of, lots, settled_lot_ids = lot_domain.read_public_snapshot(session)
        result = lot_domain.build_public_lots(lots, as_of, settled_lot_ids)
        session.rollback()  # encerra a transação de leitura antes da resposta (D2)
        response.headers["Cache-Control"] = "no-store"
        return result

    # Sempre depois de `/api/lots/mine` (D4).
    @api_route(
        app,
        "/api/lots/{lot_id}",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicLotDetailResponse,
        responses=error_responses(404, 422),
    )
    def public_lot(
        lot_id: uuid.UUID,
        response: Response,
        session: Session = Depends(get_session),
    ) -> PublicLotDetailResponse | Response:
        as_of, lot, has_settlement = lot_domain.read_public_lot_snapshot(
            session, lot_id
        )
        result = (
            None
            if lot is None
            else PublicLotDetailResponse(
                as_of=as_of,
                lot=lot_domain.public_lot_detail(
                    lot, as_of, has_settlement=has_settlement
                ),
            )
        )
        session.rollback()
        if result is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result
