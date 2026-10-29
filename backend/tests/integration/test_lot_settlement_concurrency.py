"""Story 4.3: independent PostgreSQL transactions, observed by exact backend PID."""

import threading
import time
from datetime import timedelta

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session, sessionmaker

from app.bid_rules import BidRefusal
from app.bids import PlacedBid
from app.lot_cancellation import CancellationRefusal, cancel_lot
from app.lot_settlement import prepare_settlement
from app.lots import Lot
from app.wallet import deposit
from tests import settlement_support
from tests.bid_support import (
    bid_rows,
    hold_bid,
    integrity,
    is_lot_lock,
    live_lot,
    lot_state,
    run_bid,
    tamper,
)
from tests.lot_support import db_now
from tests.settlement_support import (
    ALICE,
    BOB,
    expire,
    run_settle,
    snapshot,
    sold_lot,
)
from tests.wallet_support import wallet_row

seeded = settlement_support.seeded
TIMEOUT = 15


def pid(session):
    return session.execute(text("SELECT pg_backend_pid()")).scalar_one()


def worker(action, outcome):
    def run():
        try:
            outcome.append(action())
        except BaseException as error:
            outcome.append(error)

    return threading.Thread(target=run, daemon=True)


def wait_for_exact_block(engine, blocker, blocked):
    deadline = time.monotonic() + TIMEOUT
    with engine.connect() as observer:
        while time.monotonic() < deadline:
            waiting = observer.execute(
                text(
                    "SELECT :blocker = ANY(pg_blocking_pids(pid)) "
                    "FROM pg_stat_activity WHERE pid=:blocked "
                    "AND datname=current_database()"
                ),
                {"blocker": blocker, "blocked": blocked},
            ).scalar_one_or_none()
            observer.rollback()
            if waiting:
                return
            time.sleep(0.01)
    raise AssertionError(f"backend {blocked} did not wait for {blocker}")


def overlap(
    factory, engine, first, second, *, rollback=False, during=None, matcher=is_lot_lock
):
    """A retains a real lock; SQL listener identifies B before its blocking query."""
    results = []
    attempted = threading.Event()
    blocked_pid = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if threading.current_thread() is thread and matcher(statement):
            blocked_pid.append(connection.connection.driver_connection.info.backend_pid)
            attempted.set()

    with factory() as session:
        blocker = pid(session)
        provisional = first(session)
        thread = worker(second, results)
        event.listen(engine, "before_cursor_execute", capture)
        try:
            thread.start()
            assert attempted.wait(TIMEOUT), "B did not reach its lock statement"
            wait_for_exact_block(engine, blocker, blocked_pid[0])
            assert results == []
            if during:
                during()
        finally:
            if rollback:
                session.rollback()
            else:
                session.commit()
            thread.join(TIMEOUT)
            event.remove(engine, "before_cursor_execute", capture)
        assert not thread.is_alive()
    assert len(results) == 1
    assert not isinstance(results[0], BaseException), results
    return provisional, results[0]


def prep(session, lot_id):
    return prepare_settlement(session, lot_id=lot_id, integrity=integrity())


@pytest.mark.parametrize("sold", [False, True], ids=["unsold", "sold"])
@pytest.mark.parametrize("rollback", [False, True], ids=["commit-A", "rollback-A"])
def test_pg07_two_closers_serialize_and_only_one_transfer(
    seeded, db_engine, sold, rollback
):
    lot_id = sold_lot(seeded) if sold else live_lot(seeded)
    expire(seeded, lot_id)
    before = wallet_row(seeded, ALICE)
    prepared, result = overlap(
        seeded,
        db_engine,
        lambda session: prep(session, lot_id),
        lambda: run_settle(seeded, lot_id),
        rollback=rollback,
    )
    assert not hasattr(prepared, "transitioned")
    assert (
        result.status == ("settled_sold" if sold else "settled_unsold")
        if rollback
        else result.status == "already_settled"
    )
    assert result.transitioned is rollback
    if not rollback:
        assert result.settlement.id == prepared.settlement.id
        assert result.receipt == prepared.receipt
    assert wallet_row(seeded, ALICE) == (
        (before[0] - 12000, before[1] - 12000) if sold else before
    )
    with seeded() as observer:
        assert (
            observer.execute(
                text("SELECT count(*) FROM lot_settlements WHERE lot_id=:id"),
                {"id": lot_id},
            ).scalar_one()
            == 1
        )
        assert observer.execute(
            text("SELECT count(*) FROM receipts WHERE lot_id=:id"), {"id": lot_id}
        ).scalar_one() == int(sold)


def test_pg05_pg35_bid_first_cumulative_extension_blocks_closer(
    seeded, db_engine, monkeypatch
):
    import app.lot_settlement as settlement

    original_end = db_now(seeded) + timedelta(seconds=2)
    lot_id = live_lot(seeded, ends_at=original_end)
    observed = []
    real_clock = settlement.database_now

    def clock(session):
        value = real_clock(session)
        observed.append(value)
        return value

    monkeypatch.setattr(settlement, "database_now", clock)

    def wait_past_original_end():
        with seeded() as observer:
            observer.execute(
                text(
                    "SELECT pg_sleep(GREATEST(EXTRACT(EPOCH FROM "
                    "(CAST(:end AS timestamptz)-clock_timestamp())),0)+0.01)"
                ),
                {"end": original_end},
            )

    first, result = overlap(
        seeded,
        db_engine,
        lambda session: hold_bid(session, lot_id, ALICE, 12000),
        lambda: run_settle(seeded, lot_id),
        during=wait_past_original_end,
    )
    assert isinstance(first, PlacedBid)
    assert first.anti_sniping_applied
    assert first.ends_at == original_end + timedelta(minutes=2)
    assert original_end < observed[0] < first.ends_at
    assert result.status == "not_due" and result.transitioned is False
    assert lot_state(seeded, lot_id)["ends_at"] == first.ends_at
    assert wallet_row(seeded, ALICE)[1] == 12000
    # A second real bid inside the new window adds another two minutes.
    second = run_bid(seeded, lot_id, BOB, 13000)
    assert isinstance(second, PlacedBid)
    assert second.ends_at == original_end + timedelta(minutes=4)
    assert run_settle(seeded, lot_id).status == "not_due"
    with seeded() as observer:
        assert (
            observer.execute(
                text("SELECT count(*) FROM lot_settlements WHERE lot_id=:id"),
                {"id": lot_id},
            ).scalar_one()
            == 0
        )


def test_pg06_closer_first_prevents_bid_without_reopening(seeded, db_engine):
    lot_id = sold_lot(seeded)
    expire(seeded, lot_id)
    old = lot_state(seeded, lot_id)
    _, refused = overlap(
        seeded,
        db_engine,
        lambda session: prep(session, lot_id),
        lambda: run_bid(seeded, lot_id, BOB, 13000),
    )
    assert refused == BidRefusal.LOT_ENDED
    assert lot_state(seeded, lot_id) == old
    assert len(bid_rows(seeded, lot_id)) == 1
    assert wallet_row(seeded, BOB)[1] == 0


def test_pg04_preloaded_lot_is_refreshed_after_lock_wait(seeded, db_engine):
    lot_id = live_lot(seeded)
    old_end = lot_state(seeded, lot_id)["ends_at"]
    ready = threading.Event()
    outcomes = []
    with seeded() as waiting_session:
        stale = waiting_session.get(Lot, lot_id)
        assert stale.ends_at == old_end
        with seeded() as writer:
            writer.execute(
                text("SELECT id FROM lots WHERE id=:id FOR UPDATE"), {"id": lot_id}
            )
            writer.execute(
                text(
                    "UPDATE lots SET ends_at=ends_at+interval '2 minutes' WHERE id=:id"
                ),
                {"id": lot_id},
            )
            blocker = pid(writer)
            waiter_pid = pid(waiting_session)
            thread = worker(
                lambda: (ready.set(), prep(waiting_session, lot_id))[1], outcomes
            )
            thread.start()
            try:
                assert ready.wait(TIMEOUT)
                wait_for_exact_block(db_engine, blocker, waiter_pid)
            finally:
                writer.commit()
                thread.join(TIMEOUT)
        assert not thread.is_alive()
        assert stale.ends_at == old_end + timedelta(minutes=2)
        assert outcomes[0].status == "not_due"
        waiting_session.rollback()


@pytest.mark.parametrize("abort", [False, True], ids=["commit", "abort"])
def test_pg20_command_success_is_not_visible_before_real_commit(
    seeded, db_engine, abort, monkeypatch
):
    import app.lot_room as room

    lot_id = sold_lot(seeded)
    expire(seeded, lot_id)
    before = snapshot(seeded)
    reached, release = threading.Event(), threading.Event()
    outcomes = []

    def forbidden(*args, **kwargs):
        raise AssertionError("settlement must not publish")

    monkeypatch.setattr(room, "signal_committed", forbidden)

    class HeldSession(Session):
        def commit(self):
            reached.set()
            assert release.wait(TIMEOUT)
            if abort:
                raise RuntimeError("test abort before commit")
            return super().commit()

    factory = sessionmaker(bind=db_engine, class_=HeldSession, expire_on_commit=False)
    thread = worker(lambda: run_settle(factory, lot_id), outcomes)
    thread.start()
    try:
        assert reached.wait(TIMEOUT)
        assert outcomes == []
        assert snapshot(seeded) == before
    finally:
        release.set()
        thread.join(TIMEOUT)
    assert not thread.is_alive()
    if abort:
        assert isinstance(outcomes[0], RuntimeError)
        assert snapshot(seeded) == before
    else:
        assert outcomes[0].status == "settled_sold"
        assert outcomes[0].transitioned is True
        assert snapshot(seeded) != before


def test_pg19_deposit_and_close_use_confirmed_wallet_balance(seeded, db_engine):
    lot_id = sold_lot(seeded)
    expire(seeded, lot_id)
    before = wallet_row(seeded, ALICE)

    def wallet_lock(statement):
        return "FOR UPDATE" in statement.upper() and "FROM wallets" in statement

    _, result = overlap(
        seeded,
        db_engine,
        lambda session: deposit(session, ALICE, 5000),
        lambda: run_settle(seeded, lot_id),
        matcher=wallet_lock,
    )
    assert result.status == "settled_sold"
    assert wallet_row(seeded, ALICE) == (before[0] + 5000 - 12000, before[1] - 12000)


@pytest.mark.parametrize("with_bid", [False, True], ids=["empty", "with-bid"])
def test_pg21_cancel_first_prevents_settlement_and_close_first_prevents_cancel(
    seeded, db_engine, with_bid
):
    from app.seed import DEMO_AUCTIONEER_ID

    lot_id = live_lot(seeded)
    if with_bid:
        assert isinstance(run_bid(seeded, lot_id, ALICE, 12000), PlacedBid)
    deadline = db_now(seeded) + timedelta(seconds=1)
    tamper(seeded, "UPDATE lots SET ends_at=:end WHERE id=:id", end=deadline, id=lot_id)
    before = wallet_row(seeded, ALICE)

    def wait_until_due():
        with seeded() as observer:
            observer.execute(
                text(
                    "SELECT pg_sleep(GREATEST(EXTRACT(EPOCH FROM "
                    "(CAST(:end AS timestamptz)-clock_timestamp())),0)+0.01)"
                ),
                {"end": deadline},
            )

    _, result = overlap(
        seeded,
        db_engine,
        lambda session: cancel_lot(
            session,
            lot_id=lot_id,
            auctioneer_id=DEMO_AUCTIONEER_ID,
            integrity=integrity(),
        ),
        lambda: run_settle(seeded, lot_id),
        during=wait_until_due,
    )
    assert result == "lot_cancelled"
    assert wallet_row(seeded, ALICE) == (
        before[0],
        before[1] - (12000 if with_bid else 0),
    )
    lot_two = sold_lot(seeded) if with_bid else live_lot(seeded)
    expire(seeded, lot_two)

    def cancel_second():
        with seeded() as session:
            value = cancel_lot(
                session,
                lot_id=lot_two,
                auctioneer_id=DEMO_AUCTIONEER_ID,
                integrity=integrity(),
            )
            session.rollback()
            return value

    _, refusal = overlap(
        seeded, db_engine, lambda session: prep(session, lot_two), cancel_second
    )
    assert refusal == CancellationRefusal.LOT_ENDED
    assert wallet_row(seeded, ALICE) == (before[0] - (12000 if with_bid else 0), 0)


def test_pg17_existing_http_reads_never_settle_pending_expired_lot(
    seeded, db_engine, monkeypatch
):
    from tests.auth_support import BIDDER_EMAIL, HTTPS_ORIGIN, build_client, login
    from tests.bid_support import statement_log

    lot_id = live_lot(seeded)
    expire(seeded, lot_id)
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    before = snapshot(seeded)
    with statement_log(db_engine) as log:
        for path in (
            "/api/lots",
            f"/api/lots/{lot_id}",
            f"/api/lots/{lot_id}/bids",
            f"/api/lots/{lot_id}/bids/mine",
        ):
            response = client.get(path)
            assert response.status_code == 200
            # Refresh repeats a read; unsupported methods retain existing behavior.
            assert client.get(path).status_code == 200
            assert client.head(path).status_code in (200, 405)
            assert client.options(path).status_code in (200, 405)
    assert not any(
        statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        or "FOR UPDATE" in statement.upper()
        for statement in log.statements
    )
    assert snapshot(seeded) == before


def test_pg18_expired_handshake_reconnect_and_heartbeat_remain_pure(
    seeded, db_engine, monkeypatch
):
    from app import lot_room
    from tests.auth_support import HTTPS_ORIGIN, build_client
    from tests.bid_support import statement_log

    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)
    lot_id = live_lot(seeded)
    expire(seeded, lot_id)
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    before = snapshot(seeded)
    with client:
        with statement_log(db_engine) as log:
            for _ in range(2):
                with client.websocket_connect(f"/ws/lots/{lot_id}") as websocket:
                    frame = websocket.receive_json()
                    assert frame["type"] == "room_snapshot"
                    assert frame["room"]["phase"] == "ended"
                    count = len(log.statements)
                    for ping_id in range(1, 4):
                        websocket.send_json({"type": "ping", "id": ping_id})
                        assert websocket.receive_json() == {
                            "type": "pong",
                            "id": ping_id,
                        }
                    assert len(log.statements) == count
        assert not any(
            statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
            or "FOR UPDATE" in statement.upper()
            for statement in log.statements
        )
    assert snapshot(seeded) == before


@pytest.mark.parametrize(
    "overflow", [False, True], ids=["both-credit", "second-overflows"]
)
def test_pg19_two_lots_serialize_shared_seller_preserving_other_reserves(
    seeded, db_engine, overflow
):
    from app.lot_settlement import SettlementFinancialConflict
    from app.money import MAX_CENTS
    from app.seed import DEMO_AUCTIONEER_ID
    from tests.settlement_support import counts
    from tests.wallet_support import set_wallet

    other = live_lot(seeded, starting_bid_cents=20_000)
    assert isinstance(run_bid(seeded, other, ALICE, 20_000), PlacedBid)
    first_lot = sold_lot(seeded, amount=12_000, bidder_id=ALICE)
    second_lot = sold_lot(seeded, amount=10_000, bidder_id=BOB)
    seller_total = MAX_CENTS - 12_000 if overflow else 5_000
    set_wallet(seeded, DEMO_AUCTIONEER_ID, seller_total)
    before_second = wallet_row(seeded, BOB)
    other_before = lot_state(seeded, other)

    def second():
        try:
            return run_settle(seeded, second_lot)
        except SettlementFinancialConflict as conflict:
            return ("financial_conflict", conflict)

    def wallet_lock(statement):
        sql = statement.upper()
        return "FROM WALLETS" in sql and "FOR UPDATE" in sql

    first, result = overlap(
        seeded,
        db_engine,
        lambda session: prep(session, first_lot),
        second,
        matcher=wallet_lock,
    )
    assert first.status == "settled_sold"
    assert wallet_row(seeded, ALICE) == (68_000, 20_000)
    assert lot_state(seeded, other) == other_before
    assert counts(seeded, other) == (0, 0)
    assert counts(seeded, first_lot) == (1, 1)
    if overflow:
        assert result[0] == "financial_conflict"
        assert isinstance(result[1], SettlementFinancialConflict)
        assert result[1].reason == "credit_limit_exceeded"
        assert wallet_row(seeded, BOB) == before_second
        assert counts(seeded, second_lot) == (0, 0)
        assert wallet_row(seeded, DEMO_AUCTIONEER_ID) == (MAX_CENTS, 0)
    else:
        assert result.status == "settled_sold"
        assert wallet_row(seeded, BOB) == (70_000, 0)
        assert wallet_row(seeded, DEMO_AUCTIONEER_ID) == (27_000, 0)
        assert counts(seeded, second_lot) == (1, 1)
