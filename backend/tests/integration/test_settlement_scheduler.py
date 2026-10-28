"""Story 4.4: actual PostgreSQL discovery, lifespan, public snapshots and sockets."""

import asyncio
import threading
from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import lot_room, main
from app import settlement_scheduler as scheduling
from app.bids import read_public_room
from app.lot_room import RoomManager
from app.money import MAX_CENTS
from app.seed import DEMO_AUCTIONEER_ID
from tests.auth_support import (
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
)
from tests.bid_support import integrity, live_lot, statement_log, tamper
from tests.lot_support import db_now
from tests.settlement_support import (
    counts,
    expire,
    run_settle,
    snapshot,
    sold_lot,
)
from tests.settlement_support import seeded as seeded  # noqa: F401
from tests.wallet_support import set_wallet, wallet_rows


def scheduler(factory):
    return scheduling.SettlementScheduler(factory, integrity(), RoomManager())


@pytest.fixture(autouse=True)
def application_uses_only_test_database(db_engine, monkeypatch):
    monkeypatch.setattr(main, "get_engine", lambda: db_engine)
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)


def room(factory, identifier):
    with factory() as session:
        return read_public_room(session, identifier)


def test_f44_02_lost_commit_ack_prunes_settled_retry_and_preserves_pending(
    seeded, monkeypatch
):
    sold = sold_lot(seeded)
    pending = live_lot(seeded)
    expire(seeded, pending)
    command = scheduling.settle_lot
    calls = []
    published = []
    clock = [0.0]

    def fail_after_commit(factory, *, lot_id, integrity):
        calls.append(lot_id)
        if lot_id == pending:
            raise RuntimeError("transient")
        result = command(factory, lot_id=lot_id, integrity=integrity)
        assert result.transitioned
        raise RuntimeError("commit acknowledgement lost")

    monkeypatch.setattr(scheduling, "settle_lot", fail_after_commit)

    async def scenario():
        owner = scheduler(seeded)
        owner.monotonic = lambda: clock[0]

        async def publish(event):
            published.append(event)

        owner.manager.publish_closed = publish
        try:
            first = await owner.run_cycle()
            assert first.failures == 2 and set(owner.retries) == {sold, pending}
            assert counts(seeded, sold) == (1, 1)
            durable = snapshot(seeded)
            pending_retry = owner.retries[pending]
            delay = pending_retry.delay
            next_attempt_at = pending_retry.next_attempt_at
            assert delay == 2 and next_attempt_at == 2
            owner.scan = None
            second = await owner.run_cycle()
            assert second.attempts == 0 and sold not in owner.retries
            assert owner.retries[pending] is pending_retry
            assert pending_retry.delay == delay
            assert pending_retry.next_attempt_at == next_attempt_at
            clock[0] = 2
            owner.scan = None
            third = await owner.run_cycle()
            assert third.attempts == 1 and owner.retries[pending].delay == 4
            assert calls.count(sold) == 1 and calls.count(pending) == 2
            assert snapshot(seeded) == durable and counts(seeded, sold) == (1, 1)
            assert not published and not owner.publications
        finally:
            await owner.stop()

    asyncio.run(scenario())


@pytest.mark.parametrize("sold", [False, True], ids=["unsold", "sold"])
def test_t01_t02_t05_t18_t19_t20_persisted_result_is_the_only_public_projection(
    seeded, sold
):
    identifier = sold_lot(seeded) if sold else live_lot(seeded)
    expire(seeded, identifier)
    before = wallet_rows(seeded)

    async def scenario():
        owner = scheduler(seeded)
        published = []

        async def publish(frame):
            assert counts(seeded, identifier) == (1, int(sold))
            published.append(frame.model_dump(mode="json"))

        owner.manager.publish_closed = publish
        try:
            result = await owner.run_cycle()
            assert result.attempts == 1
            await asyncio.gather(*owner.publications)
            assert len(published) == 1
            frame = published[0]
            assert set(frame) == {
                "type",
                "lot_id",
                "outcome",
                "winner_alias",
                "final_amount_cents",
                "bid_count",
                "final_hash",
                "settled_at",
                "as_of",
            }
            assert frame["as_of"] == frame["settled_at"]
            public = room(seeded, identifier)
            assert public.settlement_status == "settled" and public.phase == "ended"
            assert public.as_of > public.settlement.settled_at
            economic = snapshot(seeded)
            owner.scan = None
            assert (await owner.run_cycle()).attempts == 0
            owner.publish_result(
                await owner.worker(lambda: run_settle(seeded, identifier))
            )
            assert len(published) == 1 and snapshot(seeded) == economic
            if sold:
                assert frame["final_amount_cents"] == 12_000 and frame["bid_count"] == 1
                assert wallet_rows(seeded) != before
            else:
                assert frame["winner_alias"] is frame["final_amount_cents"] is None
                assert wallet_rows(seeded) == before
        finally:
            await owner.stop()

    asyncio.run(scenario())


def test_t03_t04_t34_candidates_recheck_extension_cancellation_and_existing_settlement(
    seeded, monkeypatch
):
    future = live_lot(seeded)
    stale, cancelled, already = [live_lot(seeded) for _ in range(3)]
    for identifier in (stale, cancelled, already):
        expire(seeded, identifier)
    scan = scheduling.open_scan(seeded)
    assert {identifier for _, identifier in scheduling.read_page(seeded, scan, 50)} == {
        stale,
        cancelled,
        already,
    }
    tamper(
        seeded,
        "UPDATE lots SET ends_at=:end WHERE id=:id",
        end=db_now(seeded) + timedelta(hours=1),
        id=stale,
    )
    # Synthetic stale selection: cancellation is already durable when invoked.
    # The expired domain itself correctly refuses a cancellation command.
    tamper(
        seeded,
        "UPDATE lots SET cancelled_at=:now WHERE id=:id",
        now=db_now(seeded),
        id=cancelled,
    )
    run_settle(seeded, already)
    keys = [(scan.cutoff, identifier) for identifier in (stale, cancelled, already)]
    monkeypatch.setattr(
        scheduling,
        "read_page",
        lambda factory, current, limit: keys if current.cursor is None else [],
    )

    async def scenario():
        owner = scheduler(seeded)
        owner.scan = scan
        result = await owner.run_cycle()
        assert result.attempts == 3 and result.failures == 0
        assert not owner.publications
        await owner.stop()

    asyncio.run(scenario())
    assert (
        counts(seeded, future)
        == counts(seeded, stale)
        == counts(seeded, cancelled)
        == (0, 0)
    )


@pytest.mark.settlement_lifecycle
def test_t06_t07_t35_t36_lifespan_recovers_the_entire_initial_population_before_traffic(
    seeded, db_engine, monkeypatch
):
    # More than the attempt budget proves startup cannot stop at its first batch.
    identifiers = [live_lot(seeded) for _ in range(53)]
    for identifier in identifiers:
        expire(seeded, identifier)
    future = live_lot(seeded)
    broken = live_lot(seeded)
    expire(seeded, broken)
    tamper(seeded, "UPDATE lots SET anchor_hmac=NULL WHERE id=:id", id=broken)
    already = live_lot(seeded)
    expire(seeded, already)
    run_settle(seeded, already)
    monkeypatch.setattr(main, "get_engine", lambda: db_engine)
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)
    first = main.create_app(app_origin=HTTPS_ORIGIN)
    with TestClient(first) as client:
        assert all(counts(seeded, identifier) == (1, 0) for identifier in identifiers)
        assert counts(seeded, future) == (0, 0)
        assert counts(seeded, broken) == (0, 0)
        assert counts(seeded, already) == (1, 0)
        assert client.get("/health").status_code == 200
        assert first.state.settlement_scheduler.task is not None
        task = first.state.settlement_scheduler.task
    assert task.done() and not first.state.settlement_scheduler.workers
    economic = snapshot(seeded)
    with TestClient(main.create_app(app_origin=HTTPS_ORIGIN)) as client:
        assert client.get("/health").status_code == 200
        assert snapshot(seeded) == economic


@pytest.mark.settlement_lifecycle
def test_t36_systemic_startup_error_never_yields_traffic(seeded, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def unavailable(factory):
        raise OperationalError(
            "synthetic SQL marker", {}, RuntimeError("private marker")
        )

    monkeypatch.setattr(scheduling, "open_scan", unavailable)
    app = main.create_app(app_origin=HTTPS_ORIGIN)
    with pytest.raises(RuntimeError, match="inicialização"):
        with TestClient(app):
            pytest.fail("Startup should not admit traffic")
    assert app.state.settlement_scheduler.task is None
    assert app.state.settlement_scheduler.stopping
    assert not app.state.settlement_scheduler.workers


def test_t16_live_publication_failure_preserves_commit_and_invalidates_only_its_room(
    seeded, monkeypatch, caplog
):
    broken, healthy = [live_lot(seeded) for _ in range(2)]

    async def scenario():
        owner = scheduler(seeded)
        one = await owner.manager.subscribe(broken)
        two = await owner.manager.subscribe(healthy)
        one.queue.get_nowait()
        two.queue.get_nowait()
        original = owner.manager.publish_closed

        async def publish(frame):
            if frame.lot_id == broken:
                raise RuntimeError("private publication marker")
            await original(frame)

        monkeypatch.setattr(owner.manager, "publish_closed", publish)
        expire(seeded, broken)
        expire(seeded, healthy)
        await owner.run_cycle()
        await asyncio.gather(*owner.publications)
        assert counts(seeded, broken) == counts(seeded, healthy) == (1, 0)
        assert one.stopped.is_set() and one.queue.empty()
        assert not two.stopped.is_set() and two.queue.get_nowait().type == "lot_closed"
        before = snapshot(seeded)
        owner.scan = None
        assert (await owner.run_cycle()).attempts == 0
        assert snapshot(seeded) == before
        await owner.stop()

    asyncio.run(scenario())
    assert "publication failed" in caplog.text
    assert "private publication marker" not in caplog.text


def test_t11_t12_t13_real_financial_and_integrity_failures_leave_other_lots_progressing(
    seeded, caplog
):
    broken = live_lot(seeded)
    expire(seeded, broken)
    tamper(seeded, "UPDATE lots SET anchor_hmac=NULL WHERE id=:id", id=broken)
    capped = sold_lot(seeded)
    set_wallet(seeded, DEMO_AUCTIONEER_ID, MAX_CENTS)
    healthy = live_lot(seeded)
    expire(seeded, healthy)
    before = wallet_rows(seeded)

    async def scenario():
        owner = scheduler(seeded)
        result = await owner.run_cycle()
        assert result.attempts == 3 and result.failures == 2
        assert set(owner.retries) == {broken, capped}
        assert all(state.delay == 300 for state in owner.retries.values())
        assert counts(seeded, broken) == counts(seeded, capped) == (0, 0)
        assert counts(seeded, healthy) == (1, 0)
        assert wallet_rows(seeded) == before
        await owner.stop()

    asyncio.run(scenario())
    assert "category=integrity" in caplog.text and "category=invariant" in caplog.text


@pytest.mark.parametrize("sold", [False, True], ids=["unsold", "sold"])
def test_t17_t21_t23_t29_two_live_sockets_then_restart_snapshot_first_terminal(
    seeded, db_engine, monkeypatch, sold
):
    identifier = sold_lot(seeded) if sold else live_lot(seeded)
    # Keep pending during subscription; only an explicit operational cycle closes it.
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    with client:
        owner = client.app.state.settlement_scheduler
        with (
            client.websocket_connect(f"/ws/lots/{identifier}") as one,
            client.websocket_connect(f"/ws/lots/{identifier}") as two,
        ):
            assert one.receive_json()["room"]["settlement_status"] == "pending"
            assert two.receive_json()["room"]["settlement_status"] == "pending"
            expire(seeded, identifier)
            client.portal.call(owner.run_cycle)
            first, second = one.receive_json(), two.receive_json()
            assert first == second and first["type"] == "lot_closed"
            for socket in (one, two):
                with pytest.raises(WebSocketDisconnect) as closed:
                    socket.receive_json()
                assert closed.value.code == 1000
    economic = snapshot(seeded)
    # App/manager replaced: no local terminal state exists, and no replay is needed.
    with build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded) as restarted:

        def forbidden(*args, **kwargs):
            raise AssertionError("handshake must never settle")

        monkeypatch.setattr(scheduling, "settle_lot", forbidden)
        with restarted.websocket_connect(f"/ws/lots/{identifier}") as socket:
            frame = socket.receive_json()
            assert frame["type"] == "room_snapshot"
            assert frame["room"]["settlement_status"] == "settled"
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
            assert closed.value.code == 1000
        assert snapshot(seeded) == economic


def test_t16_t38_failed_publication_invalidates_an_inflight_old_subscribe(
    seeded, db_engine, monkeypatch
):
    identifier = live_lot(seeded)
    entered, release = threading.Event(), threading.Event()
    original_read = lot_room.read_room
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)

    def held_read(lot_id):
        value = original_read(lot_id)
        entered.set()
        assert release.wait(5)
        return value

    monkeypatch.setattr(lot_room, "read_room", held_read)

    async def scenario():
        manager = RoomManager()
        subscribe = asyncio.create_task(manager.subscribe(identifier))
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            invalidation = asyncio.create_task(manager.invalidate(identifier))
            await asyncio.sleep(0)
            release.set()
            subscriber = await subscribe
            await invalidation
            assert subscriber.stopped.is_set()
            assert not manager.rooms
        finally:
            release.set()
            await asyncio.gather(subscribe, return_exceptions=True)

    asyncio.run(scenario())


@pytest.mark.parametrize("condition", ["pending", "financial_cap", "integrity"])
def test_t28_t29_t31_t32_expired_post_and_all_reads_remain_pure_even_during_cooldown(
    seeded, db_engine, monkeypatch, condition
):
    from app import lot_settlement

    identifier = sold_lot(seeded)
    if condition == "financial_cap":
        set_wallet(seeded, DEMO_AUCTIONEER_ID, MAX_CENTS)
    elif condition == "integrity":
        tamper(seeded, "UPDATE lots SET anchor_hmac=NULL WHERE id=:id", id=identifier)
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)

    def forbidden(*args, **kwargs):
        raise AssertionError("HTTP/handshake cannot call settlement")

    monkeypatch.setattr(scheduling, "settle_lot", forbidden)
    monkeypatch.setattr(lot_settlement, "settle_lot", forbidden)
    with client:
        assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
        owner = client.app.state.settlement_scheduler
        owner._retry(identifier, True)
        state = replace(owner.retries[identifier])
        before = snapshot(seeded)
        for _ in range(2):
            response = client.post(
                f"/api/lots/{identifier}/bids",
                json={"amount_cents": 13_000},
                headers=json_headers(HTTPS_ORIGIN),
            )
            assert response.status_code == (409 if condition == "integrity" else 422)
            assert response.json()["code"] == (
                "lot_integrity_conflict" if condition == "integrity" else "lot_ended"
            )
        with statement_log(db_engine) as statements:
            public = client.get(f"/api/lots/{identifier}/bids")
            assert public.json()["settlement_status"] == "pending"
            for method in (client.head, client.options):
                method(f"/api/lots/{identifier}/bids")
            with client.websocket_connect(f"/ws/lots/{identifier}") as socket:
                assert socket.receive_json()["room"]["settlement_status"] == "pending"
                socket.send_json({"type": "ping", "id": 1})
                assert socket.receive_json()["type"] == "pong"
        assert not any(
            sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
            or "FOR UPDATE" in sql.upper()
            for sql in statements.statements
        )
        assert owner.retries[identifier] == state and not owner.publications
        assert snapshot(seeded) == before


def test_t40_public_snapshot_rejects_incoherent_sold_receipt_in_one_pure_statement(
    seeded, db_engine
):
    identifier = sold_lot(seeded)
    run_settle(seeded, identifier)
    tamper(seeded, "DELETE FROM receipts WHERE lot_id=:id", id=identifier)
    with statement_log(db_engine) as statements, seeded() as session:
        with pytest.raises(RuntimeError, match="resultado"):
            read_public_room(session, identifier)
    assert len(statements.statements) == 1
    sql = statements.statements[0].upper()
    assert "MATERIALIZED" in sql and "LOT_SETTLEMENTS" in sql and "RECEIPTS" in sql
    assert not any(word in sql for word in ("FOR UPDATE", "USERS", "WALLETS"))
