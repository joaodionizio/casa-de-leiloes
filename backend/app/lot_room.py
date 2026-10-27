"""Public room transport, one process; committed state is always reread.

Only the application loop touches the manager. Financial transactions never hold
its coordination lock. Each socket has one sender and a bounded queue.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from anyio import CancelScope, CapacityLimiter, from_thread, to_thread
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select

from app.access import AccessPolicy, websocket_route
from app.bids import PublicBidRoomResponse, read_public_room
from app.csrf import parse_origin
from app.db import create_session_factory, get_engine
from app.lots import Lot

logger = logging.getLogger("uvicorn.error")
QUEUE_CAPACITY = 8
SILENCE_TIMEOUT = 60
TRANSPORT_TIMEOUT = 10
MAX_SAFE_INTEGER = 2**53 - 1


class RoomEvent(BaseModel):
    type: Literal["room_snapshot", "bid_accepted"]
    lot_id: uuid.UUID
    room: PublicBidRoomResponse


class CancellationEvent(BaseModel):
    type: Literal["lot_cancelled"] = "lot_cancelled"
    lot_id: uuid.UUID
    cancelled_at: datetime


def read_room(lot_id: uuid.UUID) -> PublicBidRoomResponse | None:
    # Created, used and closed in this worker, never retained by a socket.
    with create_session_factory(get_engine())() as session:
        return read_public_room(session, lot_id)


def read_cancellation(lot_id: uuid.UUID) -> datetime | None:
    with create_session_factory(get_engine())() as session:
        cancelled_at = session.scalar(select(Lot.cancelled_at).where(Lot.id == lot_id))
        # Same UTC semantics as the other public reads, whatever the session TimeZone.
        return None if cancelled_at is None else cancelled_at.astimezone(UTC)


class Pong(BaseModel):
    type: Literal["pong"] = "pong"
    id: int


@dataclass(eq=False)
class Subscriber:
    queue: asyncio.Queue[RoomEvent | CancellationEvent | Pong] = field(
        default_factory=lambda: asyncio.Queue(QUEUE_CAPACITY)
    )
    stopped: asyncio.Event = field(default_factory=asyncio.Event)
    last_activity: float = field(default_factory=time.monotonic)
    activity: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass
class Room:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    subscribers: set[Subscriber] = field(default_factory=set)
    users: int = 0


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[uuid.UUID, Room] = {}
        # Writers waiting at from_thread.run must not consume the readers pool.
        self.read_limiter = CapacityLimiter(4)
        self.reads: set[asyncio.Task] = set()

    @asynccontextmanager
    async def coordinated(self, lot_id: uuid.UUID) -> AsyncIterator[Room]:
        room = self.rooms.setdefault(lot_id, Room())
        room.users += 1
        try:
            async with room.lock:
                yield room
        finally:
            room.users -= 1
            if not room.users and not room.subscribers:
                self.rooms.pop(lot_id, None)

    async def subscribe(self, lot_id: uuid.UUID) -> Subscriber | None:
        async with self.coordinated(lot_id) as room:
            # Detach only the wait on abandonment. The worker keeps its limiter
            # lease until SQL/Session finish, so abandoned clients cannot bypass 4.
            reading = asyncio.create_task(
                to_thread.run_sync(read_room, lot_id, limiter=self.read_limiter)
            )
            self.reads.add(reading)

            def finished(task: asyncio.Task) -> None:
                self.reads.discard(task)
                if not task.cancelled():
                    task.exception()  # Consume a late error after the owner left.

            reading.add_done_callback(finished)
            snapshot = await asyncio.shield(reading)
            if snapshot is None:
                return None
            subscriber = Subscriber()
            subscriber.queue.put_nowait(
                RoomEvent(type="room_snapshot", lot_id=lot_id, room=snapshot)
            )
            room.subscribers.add(subscriber)
            return subscriber

    async def remove(self, lot_id: uuid.UUID, subscriber: Subscriber) -> None:
        # No network/SQL wait: loop-owned sets can be changed without the read lock.
        subscriber.stopped.set()
        room = self.rooms.get(lot_id)
        if room is not None:
            room.subscribers.discard(subscriber)
            if not room.users and not room.subscribers:
                self.rooms.pop(lot_id, None)

    def enqueue(self, room: Room, event: RoomEvent | CancellationEvent) -> None:
        for subscriber in tuple(room.subscribers):
            try:
                subscriber.queue.put_nowait(event)
            except asyncio.QueueFull:
                room.subscribers.discard(subscriber)
                subscriber.stopped.set()
                # lot_id is public; nothing about the client is recorded.
                logger.warning(
                    "room subscriber evicted: queue full lot_id=%s", event.lot_id
                )

    async def publish_bid(self, lot_id: uuid.UUID) -> None:
        async with self.coordinated(lot_id) as room:
            if not room.subscribers:
                return
            snapshot = await to_thread.run_sync(
                read_room, lot_id, limiter=self.read_limiter
            )
            # A cancellation may have committed before this signal was handled.
            # Its own terminal signal is serialized here and cannot be undone.
            if snapshot is not None:
                self.enqueue(
                    room, RoomEvent(type="bid_accepted", lot_id=lot_id, room=snapshot)
                )

    async def publish_cancellation(self, lot_id: uuid.UUID) -> None:
        async with self.coordinated(lot_id) as room:
            if not room.subscribers:
                return
            cancelled_at = await to_thread.run_sync(
                read_cancellation, lot_id, limiter=self.read_limiter
            )
            if cancelled_at is None:
                return
            self.enqueue(
                room, CancellationEvent(lot_id=lot_id, cancelled_at=cancelled_at)
            )
            # Terminal subscribers can drain their queue but never receive again.
            room.subscribers.clear()

    async def isolate(self, lot_id: uuid.UUID) -> None:
        async with self.coordinated(lot_id) as room:
            for subscriber in room.subscribers:
                subscriber.stopped.set()
            if room.subscribers:
                logger.warning(
                    "room subscribers isolated lot_id=%s count=%d",
                    lot_id,
                    len(room.subscribers),
                )
            room.subscribers.clear()


def signal_committed(app: FastAPI, lot_id: uuid.UUID, cancelled: bool = False) -> None:
    """Called only from an AnyIO route worker, strictly after successful commit.

    A publication failure cannot turn an already accepted write into a refusal.
    Generic logs deliberately omit exception text/tracebacks and private data.
    """
    manager: RoomManager = app.state.room_manager
    try:
        if not cancelled:
            from_thread.run(manager.publish_bid, lot_id)
        else:
            from_thread.run(manager.publish_cancellation, lot_id)
    except Exception as error:
        logger.error(
            "room publication failed lot_id=%s error=%s", lot_id, type(error).__name__
        )
        try:
            from_thread.run(manager.isolate, lot_id)
        except Exception as isolation_error:
            logger.error(
                "room isolation failed lot_id=%s error=%s",
                lot_id,
                type(isolation_error).__name__,
            )


async def close_transport(websocket: WebSocket, code: int) -> None:
    try:
        await asyncio.wait_for(websocket.close(code=code), TRANSPORT_TIMEOUT)
    except (TimeoutError, RuntimeError, WebSocketDisconnect):
        pass


async def send_events(websocket: WebSocket, subscriber: Subscriber) -> int:
    while True:
        event = await subscriber.queue.get()
        await asyncio.wait_for(
            websocket.send_json(event.model_dump(mode="json")), TRANSPORT_TIMEOUT
        )
        if isinstance(event, CancellationEvent):
            return 1000


async def receive_commands(websocket: WebSocket, subscriber: Subscriber) -> int | None:
    previous_id = 0
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return None
        if message.get("bytes") is not None:
            return 1003
        try:
            payload = json.loads(message.get("text", ""))
        except (ValueError, TypeError):
            return 1008
        if (
            not isinstance(payload, dict)
            or set(payload) != {"type", "id"}
            or payload["type"] != "ping"
            or type(payload["id"]) is not int
            or not previous_id < payload["id"] <= MAX_SAFE_INTEGER
            or payload["id"] != previous_id + 1
        ):
            return 1008
        # Expired silence cannot be revived by a callback processed late.
        now = time.monotonic()
        if now >= subscriber.last_activity + SILENCE_TIMEOUT:
            return 1011
        previous_id = payload["id"]
        subscriber.last_activity = now
        subscriber.activity.set()
        try:
            subscriber.queue.put_nowait(Pong(id=previous_id))
        except asyncio.QueueFull:
            subscriber.stopped.set()
            return 1011


async def watch_silence(subscriber: Subscriber) -> int:
    while True:
        subscriber.activity.clear()
        remaining = subscriber.last_activity + SILENCE_TIMEOUT - time.monotonic()
        if remaining <= 0:
            return 1011
        try:
            await asyncio.wait_for(subscriber.activity.wait(), remaining)
        except TimeoutError:
            return 1011


async def wait_disconnect(websocket: WebSocket) -> None:
    # Before accept the only legitimate input is connect/disconnect.
    while (await websocket.receive())["type"] != "websocket.disconnect":
        pass


def register_room_routes(app: FastAPI, app_origin: str) -> None:
    manager = RoomManager()
    app.state.room_manager = manager
    allowed = parse_origin(app_origin)

    @websocket_route(app, "/ws/lots/{lot_id}", policy=AccessPolicy.PUBLIC)
    async def lot_room(websocket: WebSocket, lot_id: str) -> None:
        origins = websocket.headers.getlist("origin")
        if origins and (len(origins) != 1 or parse_origin(origins[0]) != allowed):
            await close_transport(websocket, 1008)
            return
        try:
            identifier = uuid.UUID(lot_id)
        except ValueError:
            await close_transport(websocket, 1008)
            return
        subscriber = None
        subscribing = None
        tasks: list[asyncio.Task] = []
        accepted = False
        close_code = None
        try:
            subscribing = asyncio.create_task(manager.subscribe(identifier))
            disconnected = asyncio.create_task(wait_disconnect(websocket))
            tasks = [subscribing, disconnected]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if disconnected in done:
                # If both completed, retain the subscriber for the common cleanup.
                if subscribing.done() and not subscribing.cancelled():
                    subscriber = subscribing.result()
                return
            disconnected.cancel()
            await asyncio.gather(disconnected, return_exceptions=True)
            subscriber = subscribing.result()
            if subscriber is None:
                await close_transport(websocket, 1008)
                return
            await websocket.accept()
            accepted = True
            subscriber.last_activity = time.monotonic()
            sender = asyncio.create_task(send_events(websocket, subscriber))
            receiver = asyncio.create_task(receive_commands(websocket, subscriber))
            stopped = asyncio.create_task(subscriber.stopped.wait())
            watchdog = asyncio.create_task(watch_silence(subscriber))
            tasks = [sender, receiver, stopped, watchdog]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if stopped in done:
                close_code = 1011
            elif watchdog in done:
                close_code = watchdog.result()
            elif sender in done:
                close_code = sender.result()
            else:
                close_code = receiver.result()
        except WebSocketDisconnect:
            pass
        except Exception as error:
            # Only the class name: the message may carry private data.
            logger.error(
                "room connection failed lot_id=%s error=%s",
                identifier,
                type(error).__name__,
            )
            close_code = 1011 if accepted else 1008
        finally:
            for task in tasks:
                task.cancel()
            with CancelScope(shield=True):
                await asyncio.gather(*tasks, return_exceptions=True)
                # Cancellation may race a completed subscribe before its result was
                # assigned above. Recover ownership before removing the registration.
                if subscriber is None and subscribing is not None:
                    if subscribing.done() and not subscribing.cancelled():
                        try:
                            subscriber = subscribing.result()
                        except Exception:
                            pass
                if subscriber is not None:
                    await manager.remove(identifier, subscriber)
                if close_code is not None:
                    await close_transport(websocket, close_code)
