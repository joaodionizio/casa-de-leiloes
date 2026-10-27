"""Cancelar × primeiro lance sobre PostgreSQL real (Story 3.6; C1, C2, C3).

Mesma técnica da 3.4: a sessão A segura a trava do lote sem confirmar, B (outra conexão,
outra thread) chega ao `SELECT ... FOR UPDATE` e espera, e só então A confirma. Nenhum
`sleep` prova a sobreposição; a corrida livre usa barreira e várias rodadas, e o
veredito é sempre o estado final inteiro, nunca só o status."""

import threading
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.bid_rules import BidRefusal
from app.bids import PlacedBid
from app.lot_cancellation import CancellationRefusal, CancelledLot, cancel_lot
from app.lots import Lot
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import (
    add_bidder,
    assert_authenticated,
    assert_invariants,
    bid_rows,
    hold_bid,
    integrity,
    is_lot_lock,
    live_lot,
    lot_state,
    run_bid,
)
from tests.cancel_support import hold_cancel, run_cancel
from tests.integration.test_bid_concurrency import JOIN_SECONDS, overlapped, thread_for
from tests.wallet_support import (
    seed_users_with_wallets,
    set_wallet,
    wallet_row,
    wallet_rows,
)

ALICE = seeded_id(BIDDER_EMAIL)
START = 10_000
FUNDS = 100_000


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, FUNDS)
    return db_session_factory


def new_lot(factory: sessionmaker[Session]) -> uuid.UUID:
    return live_lot(factory, starting_bid_cents=START, min_increment_cents=1_000)


def client_as(
    monkeypatch: pytest.MonkeyPatch, factory: sessionmaker[Session], email: str
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=factory)
    assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


def assert_cancelled_with_no_bids(
    factory: sessionmaker[Session],
    lot_id: uuid.UUID,
    original_anchor: str,
    wallets_before: list[tuple],
    bidder: uuid.UUID = ALICE,
) -> None:
    lot = lot_state(factory, lot_id)
    assert lot["cancelled_at"] is not None
    assert bid_rows(factory, lot_id) == []
    assert lot["bid_count"] == 0
    assert lot["current_bid_cents"] is None and lot["current_leader_id"] is None
    assert lot["anchor_hmac"] == original_anchor  # a âncora original, sem nova HMAC
    # Nenhum compromisso financeiro: TODAS as carteiras iguais ao snapshot anterior.
    assert wallet_rows(factory) == wallets_before
    assert wallet_row(factory, bidder) == (FUNDS, 0)
    assert_authenticated(factory, lot_id)
    assert_invariants(factory)


def wallets_after_accepted_bid(
    wallets_before: list[tuple], bidder: uuid.UUID
) -> list[tuple]:
    """O único efeito financeiro legítimo do lance: o `committed` do licitante sobe o
    valor aceito. Total e todas as outras carteiras ficam como estavam."""
    return [
        (user_id, total, committed + START if user_id == bidder else committed)
        for user_id, total, committed in wallets_before
    ]


def assert_not_cancelled_with_one_bid(
    factory: sessionmaker[Session],
    lot_id: uuid.UUID,
    wallets_before: list[tuple],
    bidder: uuid.UUID = ALICE,
) -> None:
    lot = lot_state(factory, lot_id)
    assert lot["cancelled_at"] is None
    (row,) = bid_rows(factory, lot_id)
    assert row["sequence"] == 1 and row["bidder_id"] == bidder
    assert (lot["bid_count"], lot["current_bid_cents"]) == (1, START)
    assert lot["current_leader_id"] == bidder
    assert lot["final_hash"] == row["current_hash"]
    assert wallet_rows(factory) == wallets_after_accepted_bid(wallets_before, bidder)
    assert wallet_row(factory, bidder) == (FUNDS, START)  # comprometido pelo lance
    assert_authenticated(factory, lot_id)
    assert_invariants(factory)


# --- C1: o cancelamento pega a trava primeiro ---


@pytest.mark.parametrize("via_http", [False, True], ids=["service", "http"])
def test_c1_cancel_first_makes_the_waiting_bid_lot_cancelled(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    via_http: bool,
) -> None:
    lot_id = new_lot(seeded)
    original_anchor = lot_state(seeded, lot_id)["anchor_hmac"]
    wallets_before = wallet_rows(seeded)
    outcome: list[Any] = []
    if via_http:
        bidder = client_as(monkeypatch, seeded, BIDDER_EMAIL)
        b_start: Callable[[], threading.Thread] = lambda: thread_for(  # noqa: E731
            lambda: bidder.post(
                f"/api/lots/{lot_id}/bids",
                json={"amount_cents": START},
                headers=json_headers(HTTPS_ORIGIN),
            ),
            outcome,
            "bid-b",
        )
    else:
        b_start = lambda: thread_for(  # noqa: E731
            lambda: run_bid(seeded, lot_id, ALICE, START), outcome, "bid-b"
        )

    first = overlapped(seeded, db_engine, lambda s: hold_cancel(s, lot_id), b_start)

    assert isinstance(first, CancelledLot)
    (second,) = outcome
    if via_http:
        assert (second.status_code, second.json()["code"]) == (422, "lot_cancelled")
    else:
        assert second is BidRefusal.LOT_CANCELLED
    assert_cancelled_with_no_bids(seeded, lot_id, original_anchor, wallets_before)


# --- C2: o lance pega a trava primeiro ---


@pytest.mark.parametrize("via_http", [False, True], ids=["service", "http"])
def test_c2_bid_first_makes_the_waiting_cancel_lot_has_bids(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    via_http: bool,
) -> None:
    lot_id = new_lot(seeded)
    wallets_before = wallet_rows(seeded)
    outcome: list[Any] = []

    if via_http:
        auctioneer = client_as(monkeypatch, seeded, AUCTIONEER_EMAIL)

        def work() -> Any:
            return auctioneer.post(
                f"/api/lots/{lot_id}/cancel", headers=json_headers(HTTPS_ORIGIN)
            )

    else:

        def work() -> Any:
            # O lote vazio já está no identity map de B antes de A confirmar: a trava
            # precisa devolver a versão confirmada, não a que B já tinha carregado.
            with seeded() as session:
                preloaded = session.get(Lot, lot_id)
                assert preloaded is not None and preloaded.bid_count == 0
                result = cancel_lot(
                    session,
                    lot_id=lot_id,
                    auctioneer_id=preloaded.auctioneer_id,
                    integrity=integrity(),
                )
                session.rollback()
                return result

    first = overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, START),
        lambda: thread_for(work, outcome, "cancel-b"),
        matcher=is_lot_lock,
    )

    assert isinstance(first, PlacedBid)
    (second,) = outcome
    if via_http:
        assert (second.status_code, second.json()["code"]) == (422, "lot_has_bids")
    else:
        assert second is CancellationRefusal.LOT_HAS_BIDS
    assert_not_cancelled_with_one_bid(seeded, lot_id, wallets_before)


# --- C3: corrida livre, nunca um estado híbrido ---

ROUNDS = 5


def race_once(
    factory: sessionmaker[Session], lot_id: uuid.UUID, bidder: uuid.UUID
) -> tuple[Any, Any]:
    """Cancelamento e primeiro lance liberados juntos por uma barreira."""
    barrier = threading.Barrier(2)
    cancel_out: list[Any] = []
    bid_out: list[Any] = []

    def cancel_work() -> Any:
        barrier.wait(timeout=JOIN_SECONDS)
        return run_cancel(factory, lot_id)

    def bid_work() -> Any:
        barrier.wait(timeout=JOIN_SECONDS)
        return run_bid(factory, lot_id, bidder, START)

    threads = [
        thread_for(cancel_work, cancel_out, "cancel"),
        thread_for(bid_work, bid_out, "bid"),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_SECONDS)
    assert not any(thread.is_alive() for thread in threads)
    (cancelled,), (bid,) = cancel_out, bid_out
    return cancelled, bid


def test_c3_free_race_ends_in_exactly_one_of_the_two_valid_states(
    seeded: sessionmaker[Session],
) -> None:
    for _ in range(ROUNDS):
        bidder = add_bidder(seeded, FUNDS)  # um licitante novo por rodada
        lot_id = new_lot(seeded)
        original_anchor = lot_state(seeded, lot_id)["anchor_hmac"]
        wallets_before = wallet_rows(seeded)  # todas as carteiras, antes da corrida

        cancelled, bid = race_once(seeded, lot_id, bidder)

        # Nunca cancelado com lance, nem lance aceito sem efeito, nem erro de banco.
        if isinstance(cancelled, CancelledLot):
            assert bid is BidRefusal.LOT_CANCELLED
            assert_cancelled_with_no_bids(
                seeded, lot_id, original_anchor, wallets_before, bidder
            )
        else:
            assert cancelled is CancellationRefusal.LOT_HAS_BIDS
            assert isinstance(bid, PlacedBid)
            assert_not_cancelled_with_one_bid(seeded, lot_id, wallets_before, bidder)
