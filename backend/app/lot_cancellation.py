"""Cancelamento do lote pelo leiloeiro (Story 3.6; AD-6, AD-7, AD-8, AD-11, AD-13).

Um módulo próprio: `bids.py` já importa `lots.py`, então o serviço não pode morar em
`lots.py`. Importa a trava, a hora e o gate que já existem (`lock_lot`, `database_now`,
`read_history`, `authenticate_previous_state`); não copia nem move nada da 3.4.

Ordem (`transaction-contract.md`): trava do lote → `clock_timestamp()` → dono → gate →
já cancelado → lances → fim → `UPDATE`. O dono vem antes do gate para não expor a
integridade de um lote alheio; o gate vem antes de decidir "sem lances" (a contagem é a
autenticada, nunca `lot.bid_count` cru) e antes da idempotência (um lote cancelado e
adulterado responde 409, não 200). O cancelamento trava **só o lote**: nenhuma carteira,
nenhum lance, nenhuma âncora muda. O serviço não faz commit nem rollback; a rota decide.

Este módulo não importa `app.main`.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.access import NO_STORE, AccessPolicy, api_route, require_auctioneer
from app.bids import IntegrityConflict, authenticate_previous_state, read_history
from app.config import IntegrityConfig
from app.db import get_session
from app.errors import (
    LOT_ENDED,
    LOT_HAS_BIDS,
    LOT_INTEGRITY_CONFLICT,
    error_response,
    error_responses,
)
from app.lots import database_now, get_integrity_config, lock_lot
from app.users import User

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")


class CancellationRefusal(StrEnum):
    FORBIDDEN = "forbidden"
    LOT_HAS_BIDS = LOT_HAS_BIDS
    LOT_ENDED = LOT_ENDED


@dataclass(frozen=True)
class CancelledLot:
    id: uuid.UUID
    cancelled_at: datetime  # UTC
    transitioned: bool = True


def cancel_lot(
    session: Session,
    *,
    lot_id: uuid.UUID,
    auctioneer_id: uuid.UUID,
    integrity: IntegrityConfig,
) -> CancelledLot | CancellationRefusal | IntegrityConflict | None:
    """Cancela um lote sem lances. `None` = lote inexistente. Recusa e conflito de
    integridade acontecem antes de qualquer escrita; o chamador faz o rollback."""
    lot = lock_lot(session, lot_id)  # 1: lote primeiro, e só ele
    if lot is None:
        return None
    now = database_now(session)  # 2: um único instante, depois da trava

    if lot.auctioneer_id != auctioneer_id:  # 3: dono, antes do gate
        return CancellationRefusal.FORBIDDEN

    rows = read_history(session, lot_id)  # 4: o gate da 3.4, sem cópia
    authenticated = authenticate_previous_state(
        lot, rows, integrity=integrity, lot_id=lot_id
    )
    if isinstance(authenticated, IntegrityConflict):
        return authenticated

    if lot.cancelled_at is not None:  # 5: idempotente, sem novo UPDATE nem timestamp
        return CancelledLot(
            id=lot.id, cancelled_at=lot.cancelled_at.astimezone(UTC), transitioned=False
        )
    if authenticated.bid_count > 0:  # 6: a contagem autenticada decide
        return CancellationRefusal.LOT_HAS_BIDS
    if now >= lot.ends_at:  # 7: a igualdade já é encerrado
        return CancellationRefusal.LOT_ENDED

    lot.cancelled_at = now  # 8: o mesmo instante do passo 2; um UPDATE de uma coluna
    session.flush()
    return CancelledLot(id=lot.id, cancelled_at=now)


class CancelLotResponse(BaseModel):
    id: uuid.UUID
    cancelled_at: datetime


def register_lot_cancellation_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/lots/{lot_id}/cancel",
        methods=["POST"],
        policy=AccessPolicy.AUCTIONEER,
        status_code=200,
        response_model=CancelLotResponse,
        responses=error_responses(401, 403, 404, 409, 422),
    )
    def cancel_lot_route(
        lot_id: uuid.UUID,
        response: Response,
        user: User = Depends(require_auctioneer),
        session: Session = Depends(get_session),
        integrity: IntegrityConfig = Depends(get_integrity_config),
    ) -> CancelLotResponse | Response:
        # Como no lance (3.4, D5): guardo o id e encerro a leitura da autenticação,
        # para a transação do cancelamento começar limpa. Sem corpo: a identidade é
        # sempre a da sessão.
        auctioneer_id = user.id
        session.rollback()

        outcome = cancel_lot(
            session, lot_id=lot_id, auctioneer_id=auctioneer_id, integrity=integrity
        )
        if outcome is None:
            session.rollback()
            return error_response(404, "not_found", headers=NO_STORE)
        if isinstance(outcome, IntegrityConflict):
            session.rollback()  # libera a trava antes de responder
            # Só a categoria e o lote (público) vão ao log, nunca o motivo ao cliente.
            logger.warning(
                "cancellation refused: integrity conflict lot_id=%s reason=%s",
                lot_id,
                outcome.reason.value,
            )
            return error_response(409, LOT_INTEGRITY_CONFLICT, headers=NO_STORE)
        if outcome is CancellationRefusal.FORBIDDEN:
            session.rollback()
            return error_response(403, "forbidden", headers=NO_STORE)
        if isinstance(outcome, CancellationRefusal):
            session.rollback()
            return error_response(422, outcome.value, headers=NO_STORE)

        session.commit()
        if outcome.transitioned:
            from app.lot_room import signal_committed

            signal_committed(app, lot_id, cancelled=True)
        logger.info("lot cancelled: lot_id=%s", lot_id)
        response.headers["Cache-Control"] = "no-store"
        return CancelLotResponse(id=outcome.id, cancelled_at=outcome.cancelled_at)
