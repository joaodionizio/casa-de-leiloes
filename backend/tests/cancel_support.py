"""Apoio dos testes de cancelamento (Story 3.6): o serviço numa sessão própria, com e
sem confirmação, e a fotografia "nada mudou" de um lote."""

import uuid
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.lot_cancellation import CancelledLot, cancel_lot
from app.seed import DEMO_AUCTIONEER_ID
from tests.bid_support import bid_rows, integrity, lot_state
from tests.wallet_support import wallet_rows


def run_cancel(
    factory: sessionmaker[Session],
    lot_id: uuid.UUID,
    auctioneer_id: uuid.UUID = DEMO_AUCTIONEER_ID,
) -> Any:
    """O serviço numa `Session` própria: confirma se cancelou (ou se já estava), senão
    desfaz. Devolve o resultado do serviço."""
    with factory() as session:
        result = cancel_lot(
            session, lot_id=lot_id, auctioneer_id=auctioneer_id, integrity=integrity()
        )
        if isinstance(result, CancelledLot):
            session.commit()
        else:
            session.rollback()
        return result


def hold_cancel(
    session: Session,
    lot_id: uuid.UUID,
    auctioneer_id: uuid.UUID = DEMO_AUCTIONEER_ID,
) -> Any:
    """O serviço sem confirmar: a sessão segue segurando a trava do lote."""
    return cancel_lot(
        session, lot_id=lot_id, auctioneer_id=auctioneer_id, integrity=integrity()
    )


def untouched(
    factory: sessionmaker[Session], lot_id: uuid.UUID
) -> tuple[dict[str, Any], list[dict[str, Any]], list[tuple]]:
    """O lote (sem `cancelled_at`), seus lances e todas as carteiras: o que um
    cancelamento nunca pode alterar."""
    lot = lot_state(factory, lot_id)
    lot.pop("cancelled_at")
    return lot, bid_rows(factory, lot_id), wallet_rows(factory)
