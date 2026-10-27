"""Public room transport, one process; committed state is always reread.

Only the application loop touches the manager. Financial transactions never hold
its coordination lock. Each socket has one sender and a bounded queue.
"""

import asyncio
import logging
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


@dataclass(eq=False)
class Subscriber:
    queue: asyncio.Queue[RoomEvent | CancellationEvent] = field(
        default_factory=lambda: asyncio.Queue(QUEUE_CAPACITY)
    )
    stopped: asyncio.Event = field(default_factory=asyncio.Event)


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
            snapshot = await to_thread.run_sync(
                read_room, lot_id, limiter=self.read_limiter
            )
            if snapshot is None:
                return None
            subscriber = Subscriber()
            subscriber.queue.put_nowait(
                RoomEvent(type="room_snapshot", lot_id=lot_id, room=snapshot)
            )
            room.subscribers.add(subscriber)
            return subscriber

    async def remove(self, lot_id: uuid.UUID, subscriber: Subscriber) -> None:
        async with self.coordinated(lot_id) as room:
            room.subscribers.discard(subscriber)
            subscriber.stopped.set()

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


async def send_events(websocket: WebSocket, subscriber: Subscriber) -> int:
    while True:
        event = await subscriber.queue.get()
        await websocket.send_json(event.model_dump(mode="json"))
        if isinstance(event, CancellationEvent):
            return 1000


async def receive_commands(websocket: WebSocket) -> int | None:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        return None
    return 1003 if message.get("bytes") is not None else 1008


def register_room_routes(app: FastAPI, app_origin: str) -> None:
    manager = RoomManager()
    app.state.room_manager = manager
    allowed = parse_origin(app_origin)

    @websocket_route(app, "/ws/lots/{lot_id}", policy=AccessPolicy.PUBLIC)
    async def lot_room(websocket: WebSocket, lot_id: str) -> None:
        origins = websocket.headers.getlist("origin")
        if origins and (len(origins) != 1 or parse_origin(origins[0]) != allowed):
            await websocket.close(code=1008)
            return
        try:
            identifier = uuid.UUID(lot_id)
        except ValueError:
            await websocket.close(code=1008)
            return
        subscriber = None
        tasks: list[asyncio.Task] = []
        accepted = False
        close_code = None
        try:
            subscriber = await manager.subscribe(identifier)
            if subscriber is None:
                await websocket.close(code=1008)
                return
            await websocket.accept()
            accepted = True
            sender = asyncio.create_task(send_events(websocket, subscriber))
            receiver = asyncio.create_task(receive_commands(websocket))
            stopped = asyncio.create_task(subscriber.stopped.wait())
            tasks = [sender, receiver, stopped]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if stopped in done:
                close_code = 1011
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
                if subscriber is not None:
                    await manager.remove(identifier, subscriber)
                if close_code is not None:
                    await websocket.close(code=close_code)
