"""Deterministic transport coordination; no timing-based absence assertions."""

import asyncio
import threading
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import lot_room
from app.bids import PublicBidRoomResponse
from app.lot_room import QUEUE_CAPACITY, RoomManager
from app.main import create_app

# Fixed ids keep pytest node ids stable (--lf, xdist, cache).
LOT = uuid.UUID("5f3a1c52-9d2e-4b7a-8c31-0a6d4e9b7f10")
OTHER_LOT = uuid.UUID("b2c4e6a8-1f3d-4a5b-9c7e-2d4f6a8c0e12")


def snapshot(count=0):
    return PublicBidRoomResponse(
        as_of=datetime.now(UTC),
        phase="live",
        ends_at=datetime.now(UTC),
        current_bid_cents=None,
        minimum_next_bid_cents=10000,
        bid_count=count,
        bids=[],
    )


@pytest.mark.parametrize(
    "origin", [None, "https://testserver", "https://TESTSERVER:443"]
)
@pytest.mark.parametrize("cookie", [None, "invalid"])
def test_public_snapshot_origin_and_commands(monkeypatch, origin, cookie):
    loop_thread = threading.get_ident()
    workers = []

    def read(identifier):
        workers.append(threading.get_ident())
        assert identifier == LOT
        return snapshot()

    monkeypatch.setattr(lot_room, "read_room", read)
    with TestClient(create_app(app_origin="https://testserver")) as client:
        headers = {} if origin is None else {"origin": origin}
        if cookie:
            headers["cookie"] = f"__Host-session={cookie}"
        with client.websocket_connect(f"/ws/lots/{LOT}", headers=headers) as ws:
            body = ws.receive_json()
            assert set(body) == {"type", "lot_id", "room"}
            assert body["type"] == "room_snapshot"
            assert set(body["room"]) == {
                "as_of",
                "phase",
                "ends_at",
                "current_bid_cents",
                "minimum_next_bid_cents",
                "bid_count",
                "bids",
            }
            ws.send_json({"type": "bid", "amount_cents": 10000})
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1008
        assert not client.app.state.room_manager.rooms
    assert workers and all(worker != loop_thread for worker in workers)


@pytest.mark.parametrize(
    "origin",
    [
        "http://testserver",
        "https://evil.example",
        "null",
        "",
        "https://testserver/",
        "broken",
    ],
)
def test_bad_origin_rejected_before_read(monkeypatch, origin):
    reads = []
    monkeypatch.setattr(
        lot_room, "read_room", lambda identifier: reads.append(identifier)
    )
    with TestClient(create_app(app_origin="https://testserver")) as client:
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect(
                f"/ws/lots/{LOT}", headers={"origin": origin}
            ):
                pass
        assert closed.value.code == 1008
    assert reads == []


def test_origin_policy_alone_decides_for_an_existing_lot(monkeypatch):
    # The lot exists and the read would succeed: only Origin decides accept or refuse.
    reads = []

    def read(identifier):
        reads.append(identifier)
        return snapshot()

    monkeypatch.setattr(lot_room, "read_room", read)
    with TestClient(create_app(app_origin="https://testserver")) as client:
        with client.websocket_connect(
            f"/ws/lots/{LOT}", headers={"origin": "https://testserver"}
        ) as ws:
            assert ws.receive_json()["type"] == "room_snapshot"
        assert reads == [LOT]
        reads.clear()
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect(
                f"/ws/lots/{LOT}", headers={"origin": "https://evil.example"}
            ):
                pass
        assert closed.value.code == 1008
        assert reads == []


def raw_scope(path, headers):
    return {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(name.encode(), value.encode()) for name, value in headers],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "subprotocols": [],
    }


async def start_raw(app, headers):
    """Drive the ASGI app directly: repeat a header, cancel the task."""
    sent = []
    accepted = asyncio.Event()
    incoming = asyncio.Queue()
    incoming.put_nowait({"type": "websocket.connect"})

    async def receive():
        return await incoming.get()

    async def send(message):
        sent.append(message)
        if message["type"] == "websocket.accept":
            accepted.set()

    task = asyncio.create_task(
        app(raw_scope(f"/ws/lots/{LOT}", headers), receive, send)
    )
    return task, sent, accepted


def test_repeated_origin_header_is_refused_while_a_single_one_connects(monkeypatch):
    reads = []

    def read(identifier):
        reads.append(identifier)
        return snapshot()

    monkeypatch.setattr(lot_room, "read_room", read)

    async def scenario():
        app = create_app(app_origin="https://testserver")
        origin = ("origin", "https://testserver")
        task, sent, accepted = await start_raw(app, [origin])
        await asyncio.wait_for(accepted.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert reads == [LOT]
        reads.clear()
        task, sent, _ = await start_raw(app, [origin, origin])
        await asyncio.wait_for(task, 5)
        assert [message["type"] for message in sent] == ["websocket.close"]
        assert sent[0]["code"] == 1008
        assert reads == []

    asyncio.run(scenario())


def test_cancelling_the_handler_cleans_up_and_propagates(monkeypatch):
    monkeypatch.setattr(lot_room, "read_room", lambda identifier: snapshot())

    async def scenario():
        app = create_app(app_origin="https://testserver")
        task, sent, accepted = await start_raw(app, [])
        await asyncio.wait_for(accepted.wait(), 5)
        assert LOT in app.state.room_manager.rooms
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
        assert not app.state.room_manager.rooms
        assert all(message["type"] != "websocket.close" for message in sent)

    asyncio.run(scenario())


@pytest.mark.parametrize("identifier", ["invalid", str(LOT)])
def test_missing_invalid_and_cancelled_refuse_handshake(monkeypatch, identifier):
    monkeypatch.setattr(lot_room, "read_room", lambda identifier: None)
    with TestClient(create_app(app_origin="https://testserver")) as client:
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect(f"/ws/lots/{identifier}"):
                pass
        assert closed.value.code == 1008
        assert not client.app.state.room_manager.rooms


def test_binary_and_internal_failure_are_generic(monkeypatch):
    monkeypatch.setattr(lot_room, "read_room", lambda identifier: snapshot())
    with TestClient(create_app(app_origin="https://testserver")) as client:
        with client.websocket_connect(f"/ws/lots/{LOT}") as ws:
            ws.receive_json()
            ws.send_bytes(b"bid")
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1003


def test_snapshot_publication_lock_inverted_signals_and_slow_client(monkeypatch):
    async def scenario():
        manager = RoomManager()
        state = {"count": 0}
        loop_thread = threading.get_ident()
        entered, release = threading.Event(), threading.Event()
        block = {"yes": False}

        def read(identifier):
            assert threading.get_ident() != loop_thread
            value = state["count"]
            if block["yes"]:
                block["yes"] = False
                entered.set()
                assert release.wait(5)
            return snapshot(value)

        monkeypatch.setattr(lot_room, "read_room", read)
        first = await manager.subscribe(LOT)
        other_id = OTHER_LOT
        other = await manager.subscribe(other_id)
        assert first.queue.get_nowait().type == "room_snapshot"
        other.queue.get_nowait()
        state["count"] = 1
        block["yes"] = True
        publication = asyncio.create_task(manager.publish_bid(LOT))
        assert await asyncio.to_thread(entered.wait, 5)
        state["count"] = 2
        connection = asyncio.create_task(manager.subscribe(LOT))
        release.set()
        await publication
        second = await connection
        # Initial read serialized after the in-flight publication.
        assert second.queue.get_nowait().type == "room_snapshot"
        await manager.publish_bid(LOT)  # B signal
        await manager.publish_bid(LOT)  # delayed A signal rereads B
        assert [first.queue.get_nowait().room.bid_count for _ in range(3)] == [1, 2, 2]
        assert [second.queue.get_nowait().room.bid_count for _ in range(2)] == [2, 2]
        assert other.queue.empty()
        # Fill one connection only; the healthy connection keeps draining.
        for _ in range(QUEUE_CAPACITY + 1):
            await manager.publish_bid(LOT)
            second.queue.get_nowait()
        assert first.stopped.is_set()
        assert not second.stopped.is_set()
        monkeypatch.setattr(
            lot_room, "read_cancellation", lambda identifier: datetime.now(UTC)
        )
        await manager.publish_cancellation(LOT)
        assert second.queue.get_nowait().type == "lot_cancelled"
        await manager.publish_bid(LOT)
        assert second.queue.empty()
        await manager.remove(LOT, second)
        await manager.remove(other_id, other)
        assert not manager.rooms

    asyncio.run(scenario())


def test_sender_failure_closes_generic_1011_and_cleans_manager(monkeypatch):
    async def fail(websocket, subscriber):
        raise RuntimeError("private diagnostic must not reach client")

    monkeypatch.setattr(lot_room, "read_room", lambda identifier: snapshot())
    monkeypatch.setattr(lot_room, "send_events", fail)
    with TestClient(create_app(app_origin="https://testserver")) as client:
        with client.websocket_connect(f"/ws/lots/{LOT}") as ws:
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1011
            assert closed.value.reason == ""
        assert not client.app.state.room_manager.rooms
