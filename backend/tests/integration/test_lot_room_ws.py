"""Real PostgreSQL + real ASGI sockets and REST writer, with commit barriers."""

import asyncio
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app import bids, lot_room
from app.bids import read_public_room
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    cookie_name_of,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import bid_rows, db_snapshot, live_lot, lot_state, run_bid
from tests.lot_support import db_now
from tests.wallet_support import seed_users_with_wallets, set_wallet


@pytest.fixture
def setup(monkeypatch, db_session_factory, clean_users, db_engine):
    factory = db_session_factory
    seed_users_with_wallets(factory)
    for email in (BIDDER_EMAIL, OTHER_BIDDER_EMAIL):
        set_wallet(factory, seeded_id(email), 1_000_000)
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=factory)
    with client:
        yield client, factory


ROOM_KEYS = {
    "as_of",
    "phase",
    "ends_at",
    "current_bid_cents",
    "minimum_next_bid_cents",
    "settlement_status",
    "settlement",
    "bid_count",
    "bids",
}
BID_KEYS = {"sequence", "bidder_alias", "amount_cents", "placed_at"}


def assert_public_frame(frame, factory, identifier):
    """Exact key whitelist, and no real user, e-mail, hash or anchor value anywhere."""
    assert set(frame) == {"type", "lot_id", "room"}
    assert set(frame["room"]) == ROOM_KEYS
    assert all(set(bid) == BID_KEYS for bid in frame["room"]["bids"])
    encoded = json.dumps(frame)
    forbidden = []
    for email in (BIDDER_EMAIL, OTHER_BIDDER_EMAIL, AUCTIONEER_EMAIL):
        forbidden += [email, str(seeded_id(email))]
    for row in bid_rows(factory, identifier):
        forbidden += [str(row["bidder_id"]), row["previous_hash"], row["current_hash"]]
    anchor = lot_state(factory, identifier)["anchor_hmac"]
    if anchor is not None:
        forbidden.append(
            bytes(anchor).hex() if isinstance(anchor, bytes) else str(anchor)
        )
    assert forbidden
    assert not [value for value in forbidden if value in encoded]


UNKNOWN_LOT = uuid.UUID("7c1e9a3b-5d2f-4e68-a0b4-93c5d7e1f2a6")


def post(client, identifier, amount=10000):
    return client.post(
        f"/api/lots/{identifier}/bids",
        json={"amount_cents": amount},
        headers=json_headers(HTTPS_ORIGIN),
    )


@pytest.mark.parametrize(
    "email", [None, BIDDER_EMAIL, AUCTIONEER_EMAIL, "invalid-cookie"]
)
def test_public_real_snapshot_is_one_pure_query_and_closes_session(
    setup, db_engine, email
):
    client, factory = setup
    identifier = live_lot(factory)
    if email == "invalid-cookie":
        client.cookies.set(cookie_name_of(client), "invalid")
    elif email:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    before = db_snapshot(factory)
    statements = []
    threads = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        threads.append(threading.get_ident())

    loop_thread = client.portal.call(threading.get_ident)
    event.listen(db_engine, "before_cursor_execute", record)
    try:
        with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
            frame = ws.receive_json()
            assert frame["type"] == "room_snapshot"
            assert frame["room"]["bid_count"] == 0
            assert len(statements) == 1
            for ping_id in range(1, 4):
                ws.send_json({"type": "ping", "id": ping_id})
                assert ws.receive_json() == {"type": "pong", "id": ping_id}
            assert len(statements) == 1
            assert all(thread != loop_thread for thread in threads)
            sql = statements[0].upper()
            assert "CLOCK_TIMESTAMP()" in sql and "LATERAL" in sql
            for forbidden in ("FOR UPDATE", "INSERT ", "UPDATE ", "USERS"):
                assert forbidden not in sql
            assert db_engine.pool.checkedout() == 0
    finally:
        event.remove(db_engine, "before_cursor_execute", record)
    assert_public_frame(frame, factory, identifier)
    assert db_snapshot(factory) == before


def test_real_window_and_total_and_temporal_phases(setup):
    client, factory = setup
    identifier = live_lot(factory, min_increment_cents=1)
    for index in range(51):
        email = BIDDER_EMAIL if index % 2 == 0 else OTHER_BIDDER_EMAIL
        assert isinstance(
            run_bid(factory, identifier, seeded_id(email), 10000 + index),
            bids.PlacedBid,
        )
    with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
        room = ws.receive_json()["room"]
        assert room["bid_count"] == 51
        assert [bid["sequence"] for bid in room["bids"]] == list(range(51, 1, -1))
        rows = bid_rows(factory, identifier)
        assert room["bids"][0]["bidder_alias"] == rows[-1]["bidder_alias"]
        encoded = str(room)
        for row in rows:
            assert str(row["bidder_id"]) not in encoded
            assert row["current_hash"] not in encoded
        assert set(room["bids"][0]) == {
            "sequence",
            "bidder_alias",
            "amount_cents",
            "placed_at",
        }
    now = db_now(factory)
    for phase, starts, ends in [
        ("scheduled", now + timedelta(hours=1), now + timedelta(hours=2)),
        ("ended", now - timedelta(hours=2), now - timedelta(hours=1)),
    ]:
        identifier = live_lot(factory, starts_at=starts, ends_at=ends)
        before = db_snapshot(factory)
        with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
            assert ws.receive_json()["room"]["phase"] == phase
        assert db_snapshot(factory) == before


def test_commit_barrier_two_clients_isolation_and_ant_sniping(setup, monkeypatch):
    client, factory = setup
    identifier = live_lot(factory, ends_at=db_now(factory) + timedelta(seconds=90))
    original_end = lot_state(factory, identifier)["ends_at"]
    other_id = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    reached, release = threading.Event(), threading.Event()
    signals, queued = [], []
    original_service, original_commit = bids.place_bid, Session.commit
    original_signal, original_enqueue = (
        lot_room.signal_committed,
        lot_room.RoomManager.enqueue,
    )

    def service(session, **kwargs):
        result = original_service(session, **kwargs)
        session.info["room_writer"] = True
        return result

    def commit(session):
        if session.info.get("room_writer"):
            reached.set()
            assert release.wait(5)
        return original_commit(session)

    def signal(app, lot_id, *args, **kwargs):
        assert len(bid_rows(factory, lot_id)) == 1  # independent committed read
        signals.append(lot_id)
        return original_signal(app, lot_id, *args, **kwargs)

    def enqueue(manager, room, value):
        queued.append(value)
        return original_enqueue(manager, room, value)

    monkeypatch.setattr(bids, "place_bid", service)
    monkeypatch.setattr(Session, "commit", commit)
    monkeypatch.setattr(lot_room, "signal_committed", signal)
    monkeypatch.setattr(lot_room.RoomManager, "enqueue", enqueue)
    with (
        client.websocket_connect(f"/ws/lots/{identifier}") as first,
        client.websocket_connect(f"/ws/lots/{identifier}") as second,
        client.websocket_connect(f"/ws/lots/{other_id}") as other,
    ):
        first.receive_json()
        second.receive_json()
        other.receive_json()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(post, client, identifier)
            try:
                assert reached.wait(5)
                assert not signals and not queued
                assert bid_rows(factory, identifier) == []
                with factory() as session:
                    assert read_public_room(session, identifier).bid_count == 0
            finally:
                release.set()
            response = future.result(5)
        assert response.status_code == 201
        one, two = first.receive_json(), second.receive_json()
        assert one == two and one["type"] == "bid_accepted"
        assert one["room"]["bid_count"] == 1
        assert_public_frame(one, factory, identifier)
        placed = response.json()["bid"]
        assert datetime.fromisoformat(
            one["room"]["ends_at"]
        ) == original_end + timedelta(minutes=2)
        assert datetime.fromisoformat(one["room"]["ends_at"]) != datetime.fromisoformat(
            placed["placed_at"]
        ) + timedelta(minutes=2)
        assert (
            datetime.fromisoformat(one["room"]["ends_at"])
            == lot_state(factory, identifier)["ends_at"]
        )
        assert len(queued) == 1 and queued[0].lot_id == identifier
        assert len(signals) == 1
    assert not client.app.state.room_manager.rooms


@pytest.mark.parametrize(
    "failure",
    ["refusal", "missing", "integrity", "wallet_flush", "after_insert", "commit"],
)
def test_failure_or_rollback_never_signals(setup, monkeypatch, failure):
    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    signals = []
    monkeypatch.setattr(
        lot_room, "signal_committed", lambda *args, **kwargs: signals.append(1)
    )
    if failure == "integrity":
        from tests.bid_support import tamper

        tamper(
            factory,
            "UPDATE lots SET anchor_hmac = NULL WHERE id = :id",
            id=identifier,
        )
    before = db_snapshot(factory)

    def fail(*args, **kwargs):
        raise RuntimeError("injected")

    if failure == "wallet_flush":
        monkeypatch.setattr(bids, "generate_bidder_alias", fail)
    if failure == "after_insert":
        original = bids.place_bid

        def service(session, **kwargs):
            original(session, **kwargs)
            raise RuntimeError("injected")

        monkeypatch.setattr(bids, "place_bid", service)
    if failure == "commit":
        monkeypatch.setattr(
            Session,
            "commit",
            lambda session: (_ for _ in ()).throw(RuntimeError("injected")),
        )
    try:
        response = post(
            client,
            UNKNOWN_LOT if failure == "missing" else identifier,
            1 if failure == "refusal" else 10000,
        )
        assert response.status_code == (
            404 if failure == "missing" else 409 if failure == "integrity" else 422
        )
    except RuntimeError:
        assert failure in ("wallet_flush", "after_insert", "commit")
    assert signals == []
    assert db_snapshot(factory) == before


def test_publication_failure_preserves_201(setup, monkeypatch):
    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200

    async def fail(*args):
        raise RuntimeError("injected")

    monkeypatch.setattr(client.app.state.room_manager, "publish_bid", fail)
    assert post(client, identifier).status_code == 201
    assert len(bid_rows(factory, identifier)) == 1


def test_cancel_post_commit_terminal_idempotent_and_hidden(setup, monkeypatch):
    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    published = []
    signals = []
    original = lot_room.read_cancellation
    original_signal = lot_room.signal_committed

    def signal(*args, **kwargs):
        signals.append(args[1])
        return original_signal(*args, **kwargs)

    monkeypatch.setattr(lot_room, "signal_committed", signal)

    def read(identifier):
        stored = lot_state(factory, identifier)["cancelled_at"]
        assert stored is not None
        result = original(identifier)
        assert result == stored
        published.append(result)
        return result

    monkeypatch.setattr(lot_room, "read_cancellation", read)
    with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
        ws.receive_json()
        response = client.post(
            f"/api/lots/{identifier}/cancel", headers=json_headers(HTTPS_ORIGIN)
        )
        assert response.status_code == 200
        terminal = ws.receive_json()
        assert terminal == {
            "type": "lot_cancelled",
            "lot_id": str(identifier),
            "cancelled_at": response.json()["cancelled_at"],
        }
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 1000
    assert (
        client.post(
            f"/api/lots/{identifier}/cancel", headers=json_headers(HTTPS_ORIGIN)
        ).status_code
        == 200
    )
    assert len(published) == 1
    # The repeat is a no-op transition: no signal at all, with or without subscribers.
    assert signals == [identifier]
    for hidden in (identifier, UNKNOWN_LOT):
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect(f"/ws/lots/{hidden}"):
                pass
        assert closed.value.code == 1008
    assert not client.app.state.room_manager.rooms


def test_real_commits_inverted_signals_and_initial_read_barrier(setup, monkeypatch):
    client, factory = setup
    identifier = live_lot(factory)
    manager = client.app.state.room_manager
    entered, release = threading.Event(), threading.Event()
    original_read = lot_room.read_room
    once = [True]

    def read(lot_id):
        result = original_read(lot_id)
        if once.pop() if once else False:
            entered.set()
            assert release.wait(5)
        return result

    monkeypatch.setattr(lot_room, "read_room", read)
    future = client.portal.start_task_soon(manager.subscribe, identifier)
    try:
        assert entered.wait(5)
        assert isinstance(
            run_bid(factory, identifier, seeded_id(BIDDER_EMAIL), 10000), bids.PlacedBid
        )
        assert isinstance(
            run_bid(factory, identifier, seeded_id(OTHER_BIDDER_EMAIL), 11000),
            bids.PlacedBid,
        )
        publishing = client.portal.start_task_soon(manager.publish_bid, identifier)
    finally:
        release.set()
    subscriber = future.result(5)
    publishing.result(5)  # B signal, waiting behind initial read
    client.portal.call(manager.publish_bid, identifier)  # A signal delivered late
    frames = [subscriber.queue.get_nowait() for _ in range(3)]
    assert frames[0].type == "room_snapshot"
    assert [frame.room.bid_count for frame in frames] == [0, 2, 2]
    assert (
        frames[-1].room.current_bid_cents
        == lot_state(factory, identifier)["current_bid_cents"]
    )
    client.portal.call(manager.remove, identifier, subscriber)
    assert not manager.rooms


def test_post_can_publish_with_one_default_worker(setup):
    from anyio import to_thread

    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200

    async def limit(tokens):
        limiter = to_thread.current_default_thread_limiter()
        previous = limiter.total_tokens
        limiter.total_tokens = tokens
        return previous

    with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
        ws.receive_json()
        previous = client.portal.call(limit, 1)
        try:
            with ThreadPoolExecutor(1) as pool:
                response = pool.submit(post, client, identifier).result(5)
            assert response.status_code == 201
            assert ws.receive_json()["room"]["bid_count"] == 1
        finally:
            client.portal.call(limit, previous)


@pytest.mark.parametrize("rollback", [False, True])
def test_cancellation_commit_barrier_or_rollback_never_publishes_early(
    setup, monkeypatch, rollback
):
    from app import lot_cancellation

    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    entered, release = threading.Event(), threading.Event()
    original_service, original_commit = lot_cancellation.cancel_lot, Session.commit
    signals = []
    original_signal = lot_room.signal_committed

    def service(session, **kwargs):
        result = original_service(session, **kwargs)
        session.info["cancel_writer"] = True
        return result

    def commit(session):
        if session.info.get("cancel_writer"):
            entered.set()
            assert release.wait(5)
            if rollback:
                raise RuntimeError("injected")
        return original_commit(session)

    def signal(*args, **kwargs):
        signals.append(1)
        return original_signal(*args, **kwargs)

    monkeypatch.setattr(lot_cancellation, "cancel_lot", service)
    monkeypatch.setattr(Session, "commit", commit)
    monkeypatch.setattr(lot_room, "signal_committed", signal)
    with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
        ws.receive_json()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(
                client.post,
                f"/api/lots/{identifier}/cancel",
                headers=json_headers(HTTPS_ORIGIN),
            )
            try:
                assert entered.wait(5)
                assert signals == []
                assert lot_state(factory, identifier)["cancelled_at"] is None
            finally:
                release.set()
            if rollback:
                with pytest.raises(RuntimeError):
                    future.result(5)
                assert signals == []
                assert lot_state(factory, identifier)["cancelled_at"] is None
            else:
                assert future.result(5).status_code == 200
                assert ws.receive_json()["type"] == "lot_cancelled"
                assert signals == [1]


@pytest.mark.parametrize("cancel_first", [False, True])
def test_bid_cancel_lock_orders_publish_only_winning_transition(
    setup, monkeypatch, cancel_first
):
    from app import lot_cancellation
    from tests.auth_support import seeded_id
    from tests.bid_support import integrity

    client, factory = setup
    identifier = live_lot(factory)
    manager = client.app.state.room_manager
    subscriber = client.portal.call(manager.subscribe, identifier)
    subscriber.queue.get_nowait()
    # Hold the same real database lock used by each writer, start the opposite
    # writer in another connection, then commit and signal the lock winner.
    with factory() as first, ThreadPoolExecutor(1) as pool:
        if cancel_first:
            outcome = lot_cancellation.cancel_lot(
                first,
                lot_id=identifier,
                auctioneer_id=seeded_id(AUCTIONEER_EMAIL),
                integrity=integrity(),
            )
            waiting = pool.submit(
                run_bid, factory, identifier, seeded_id(BIDDER_EMAIL), 10000
            )
        else:
            outcome = bids.place_bid(
                first,
                lot_id=identifier,
                bidder_id=seeded_id(BIDDER_EMAIL),
                amount_cents=10000,
                integrity=integrity(),
            )
            from tests.cancel_support import run_cancel

            waiting = pool.submit(run_cancel, factory, identifier)
        assert outcome is not None
        first.commit()
        client.portal.call(
            manager.publish_cancellation if cancel_first else manager.publish_bid,
            identifier,
        )
        rejected = waiting.result(5)
        if cancel_first:
            assert rejected is bids.BidRefusal.LOT_CANCELLED
        else:
            assert rejected is lot_cancellation.CancellationRefusal.LOT_HAS_BIDS
        frame = subscriber.queue.get_nowait()
        assert frame.type == ("lot_cancelled" if cancel_first else "bid_accepted")
        assert subscriber.queue.empty()
        client.portal.call(manager.remove, identifier, subscriber)


def test_publication_failure_isolates_the_connected_sockets(setup, monkeypatch, caplog):
    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200

    async def fail(*args):
        raise RuntimeError("private diagnostic")

    monkeypatch.setattr(client.app.state.room_manager, "publish_bid", fail)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
            assert ws.receive_json()["type"] == "room_snapshot"
            assert post(client, identifier).status_code == 201
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1011
    assert len(bid_rows(factory, identifier)) == 1
    assert not client.app.state.room_manager.rooms
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "room publication failed" in message
        and str(identifier) in message
        and "RuntimeError" in message
        for message in messages
    )
    assert any(
        "isolated" in message and str(identifier) in message for message in messages
    )
    assert not any("private diagnostic" in message for message in messages)


def test_full_queue_evicts_only_the_slow_client_through_real_posts(
    setup, monkeypatch, caplog
):
    client, factory = setup
    identifier = live_lot(factory, min_increment_cents=1)
    original = lot_room.send_events
    started = threading.Event()
    calls = []

    async def selective(websocket, subscriber):
        calls.append(subscriber)
        if len(calls) == 1:
            started.set()
            await asyncio.Event().wait()  # a client that never drains its queue
        return await original(websocket, subscriber)

    monkeypatch.setattr(lot_room, "send_events", selective)
    emails = (BIDDER_EMAIL, OTHER_BIDDER_EMAIL)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        with client.websocket_connect(f"/ws/lots/{identifier}") as slow:
            assert started.wait(5)
            with client.websocket_connect(f"/ws/lots/{identifier}") as healthy:
                assert healthy.receive_json()["type"] == "room_snapshot"
                # The snapshot plus QUEUE_CAPACITY - 1 events fill the stuck queue; the
                # next publication overflows it. The leader cannot cover itself, so the
                # bidders alternate.
                for index in range(lot_room.QUEUE_CAPACITY + 1):
                    assert (
                        login(client, HTTPS_ORIGIN, emails[index % 2]).status_code
                        == 200
                    )
                    assert post(client, identifier, 10000 + index).status_code == 201
                    frame = healthy.receive_json()
                    assert frame["type"] == "bid_accepted"
                    assert frame["room"]["bid_count"] == index + 1
                with pytest.raises(WebSocketDisconnect) as closed:
                    slow.receive_json()
                assert closed.value.code == 1011
        assert len(bid_rows(factory, identifier)) == lot_room.QUEUE_CAPACITY + 1
    assert not client.app.state.room_manager.rooms
    evictions = [r.getMessage() for r in caplog.records if "evicted" in r.getMessage()]
    assert len(evictions) == 1 and str(identifier) in evictions[0]
    assert not any(email in evictions[0] for email in emails)


@pytest.mark.parametrize(
    "refusal", ["forbidden", "has_bids", "ended", "integrity", "missing"]
)
def test_cancellation_refusals_never_signal(setup, monkeypatch, refusal):
    client, factory = setup
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    now = db_now(factory)
    if refusal == "forbidden":
        identifier = live_lot(factory, auctioneer_id=seeded_id(BIDDER_EMAIL))
    elif refusal == "ended":
        identifier = live_lot(
            factory,
            starts_at=now - timedelta(hours=2),
            ends_at=now - timedelta(hours=1),
        )
    else:
        identifier = live_lot(factory)
    if refusal == "has_bids":
        assert isinstance(
            run_bid(factory, identifier, seeded_id(BIDDER_EMAIL), 10000), bids.PlacedBid
        )
    if refusal == "integrity":
        from tests.bid_support import tamper

        tamper(
            factory, "UPDATE lots SET anchor_hmac = NULL WHERE id = :id", id=identifier
        )
    if refusal == "missing":
        identifier = UNKNOWN_LOT
    signals = []
    monkeypatch.setattr(
        lot_room, "signal_committed", lambda *args, **kwargs: signals.append(1)
    )
    before = db_snapshot(factory)
    response = client.post(
        f"/api/lots/{identifier}/cancel", headers=json_headers(HTTPS_ORIGIN)
    )
    assert (
        response.status_code
        == {
            "forbidden": 403,
            "has_bids": 422,
            "ended": 422,
            "integrity": 409,
            "missing": 404,
        }[refusal]
    )
    assert signals == []
    assert db_snapshot(factory) == before


def test_legacy_room_is_public_read_only(setup):
    client, factory = setup
    identifier = live_lot(factory, anchored=False)
    before = db_snapshot(factory)
    with client.websocket_connect(f"/ws/lots/{identifier}") as ws:
        assert ws.receive_json()["room"]["bid_count"] == 0
    assert lot_state(factory, identifier)["anchor_hmac"] is None
    assert db_snapshot(factory) == before


def test_reconnect_after_committed_write_loses_transport_before_publication(
    setup, monkeypatch
):
    client, factory = setup
    identifier = live_lot(factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    reached, release = threading.Event(), threading.Event()
    original = lot_room.signal_committed
    posts = []

    def signal(app, lot_id, *args, **kwargs):
        assert len(bid_rows(factory, lot_id)) == 1
        reached.set()
        assert release.wait(5)
        return original(app, lot_id, *args, **kwargs)

    monkeypatch.setattr(lot_room, "signal_committed", signal)
    with ThreadPoolExecutor(1) as pool:
        try:
            with client.websocket_connect(f"/ws/lots/{identifier}") as old:
                assert old.receive_json()["room"]["bid_count"] == 0
                future = pool.submit(post, client, identifier)
                posts.append(future)
                assert reached.wait(5)
                # Context closes before publication can run: committed event is lost.
        finally:
            release.set()
        assert future.result(5).status_code == 201
    with client.websocket_connect(f"/ws/lots/{identifier}") as recovered:
        frame = recovered.receive_json()
        assert frame["type"] == "room_snapshot"
        assert frame["room"]["bid_count"] == 1
        assert frame["room"]["current_bid_cents"] == 10000
        assert len(frame["room"]["bids"]) == 1
        assert (
            datetime.fromisoformat(frame["room"]["ends_at"])
            == lot_state(factory, identifier)["ends_at"]
        )
    assert len(posts) == 1
    assert not client.app.state.room_manager.rooms


def test_reconnect_recovers_missed_window_and_total_without_replay(setup):
    client, factory = setup
    identifier = live_lot(factory, min_increment_cents=1)
    with client.websocket_connect(f"/ws/lots/{identifier}") as before:
        assert before.receive_json()["room"]["bid_count"] == 0
    for index in range(51):
        email = BIDDER_EMAIL if index % 2 == 0 else OTHER_BIDDER_EMAIL
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
        assert post(client, identifier, 10000 + index).status_code == 201
    with client.websocket_connect(f"/ws/lots/{identifier}") as recovered:
        frame = recovered.receive_json()
        assert frame["type"] == "room_snapshot"
        assert frame["room"]["bid_count"] == 51
        assert frame["room"]["current_bid_cents"] == 10050
        assert [bid["sequence"] for bid in frame["room"]["bids"]] == list(
            range(51, 1, -1)
        )
        recovered.send_json({"type": "ping", "id": 1})
        assert recovered.receive_json() == {"type": "pong", "id": 1}
    assert not client.app.state.room_manager.rooms


def test_disconnected_cancellation_recovers_only_generic_public_404(setup):
    client, factory = setup
    identifier = live_lot(factory)
    with client.websocket_connect(f"/ws/lots/{identifier}") as before:
        assert before.receive_json()["type"] == "room_snapshot"
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    assert (
        client.post(
            f"/api/lots/{identifier}/cancel", headers=json_headers(HTTPS_ORIGIN)
        ).status_code
        == 200
    )
    client.cookies.clear()
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/lots/{identifier}"):
            pass
    assert closed.value.code == 1008
    response = client.get(f"/api/lots/{identifier}/bids")
    assert response.status_code == 404
    assert "cancelled_at" not in response.text
    assert not client.app.state.room_manager.rooms


def test_abandon_during_real_sql_releases_session_and_registration(
    setup, monkeypatch, db_engine
):
    from tests.test_lot_room import raw_scope

    client, factory = setup
    identifier = live_lot(factory)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    original = lot_room.read_room

    def block(connection, cursor, statement, parameters, context, executemany):
        entered.set()
        assert release.wait(5)

    def read(lot_id):
        try:
            return original(lot_id)
        finally:
            finished.set()

    monkeypatch.setattr(lot_room, "read_room", read)
    event.listen(db_engine, "before_cursor_execute", block)

    async def scenario():
        incoming = asyncio.Queue()
        incoming.put_nowait({"type": "websocket.connect"})
        sent = []

        async def send(message):
            sent.append(message)

        task = asyncio.create_task(
            client.app(raw_scope(f"/ws/lots/{identifier}", []), incoming.get, send)
        )
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            assert db_engine.pool.checkedout() == 1
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 5)
            assert not client.app.state.room_manager.rooms
        finally:
            release.set()
            assert await asyncio.to_thread(finished.wait, 5)
        assert db_engine.pool.checkedout() == 0
        assert not client.app.state.room_manager.rooms
        assert sent == []

    try:
        asyncio.run(scenario())
    finally:
        release.set()
        event.remove(db_engine, "before_cursor_execute", block)
