"""Process-owned discovery and orchestration; settlement alone owns money/commit."""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from itertools import islice

from anyio import to_thread
from sqlalchemy import exists, select, true, tuple_
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.bids import IntegrityConflict
from app.config import IntegrityConfig
from app.lot_room import ClosedEvent, RoomManager, closed_event
from app.lot_settlement import (
    LotSettlement,
    SettlementFinancialConflict,
    SettlementRefusal,
    SettlementResult,
    SettlementStatus,
    settle_lot,
)
from app.lots import Lot, _clock_cte
from app.wallet import MissingWalletError

logger = logging.getLogger("uvicorn.error")
INTERVAL = 2
DRAIN_TIMEOUT = 30
PAGE_SIZE = 50
MAX_ROWS = 200
MAX_ATTEMPTS = 50
PERMANENT_COOLDOWN = 300
Key = tuple[datetime, uuid.UUID]


@dataclass
class Scan:
    cutoff: datetime
    upper: Key
    cursor: Key | None = None


@dataclass
class Retry:
    next_attempt_at: float
    delay: float


@dataclass
class CycleResult:
    rows: int = 0
    attempts: int = 0
    failures: int = 0
    skipped: bool = False
    complete: bool = False
    systemic: bool = False


def _pending(cutoff):
    return (
        Lot.cancelled_at.is_(None),
        Lot.ends_at <= cutoff,
        ~exists().where(LotSettlement.lot_id == Lot.id),
    )


def open_scan(factory: Callable[[], Session]) -> Scan | None:
    with factory() as session:
        clock = _clock_cte()
        upper = (
            select(Lot.ends_at, Lot.id)
            .where(*_pending(clock.c.as_of))
            .order_by(Lot.ends_at.desc(), Lot.id.desc())
            .limit(1)
            .lateral("upper_bound")
        )
        row = session.execute(
            select(clock.c.as_of, upper.c.ends_at, upper.c.id)
            .select_from(clock)
            .outerjoin(upper, true())
        ).one()
        return None if row.id is None else Scan(row.as_of, (row.ends_at, row.id))


def read_page(factory: Callable[[], Session], scan: Scan, limit: int) -> list[Key]:
    with factory() as session:
        statement = (
            select(Lot.ends_at, Lot.id)
            .where(*_pending(scan.cutoff))
            .where(tuple_(Lot.ends_at, Lot.id) <= scan.upper)
            .order_by(Lot.ends_at, Lot.id)
            .limit(limit)
        )
        if scan.cursor is not None:
            statement = statement.where(tuple_(Lot.ends_at, Lot.id) > scan.cursor)
        return [(row.ends_at, row.id) for row in session.execute(statement)]


def settled_retries(
    factory: Callable[[], Session], ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Only inspect a bounded batch of retry IDs; settlement is authoritative."""
    with factory() as session:
        return set(
            session.scalars(
                select(LotSettlement.lot_id).where(LotSettlement.lot_id.in_(ids))
            )
        )


def systemic_failure(error: Exception) -> bool:
    if not isinstance(error, DBAPIError):
        return False
    state = getattr(error.orig, "sqlstate", None)
    return (
        error.connection_invalidated
        or state is None
        or state.startswith("08")
        or state in {"57P01", "57P02", "57P03", "53300"}
    )


class SettlementScheduler:
    def __init__(
        self,
        factory: Callable[[], Session],
        integrity: IntegrityConfig,
        manager: RoomManager,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.factory, self.integrity, self.manager = factory, integrity, manager
        self.monotonic = monotonic
        self.scan: Scan | None = None
        self.retries: dict[uuid.UUID, Retry] = {}
        self.guard = asyncio.Lock()
        self.stopping = False
        self.wake = asyncio.Event()
        self.task: asyncio.Task | None = None
        self.workers: set[asyncio.Task] = set()
        self.publications: set[asyncio.Task] = set()
        self.global_delay = INTERVAL
        self.global_retry_at = 0.0
        self.active_cycles: set[asyncio.Task] = set()

    async def worker(self, operation, *args):
        # Shield the task itself, not only the AnyIO wait: its Session/lease remains
        # owned even when the calling coroutine is cancelled during shutdown.
        task = asyncio.create_task(to_thread.run_sync(partial(operation, *args)))
        self.workers.add(task)

        def finished(done):
            self.workers.discard(done)
            if not done.cancelled():
                done.exception()

        task.add_done_callback(finished)
        return await asyncio.shield(task)

    def _retry(self, lot_id: uuid.UUID, permanent: bool) -> None:
        old = self.retries.get(lot_id)
        delay = (
            PERMANENT_COOLDOWN if permanent else min(30, old.delay * 2 if old else 2)
        )
        self.retries[lot_id] = Retry(self.monotonic() + delay, delay)

    async def _publish(self, event: ClosedEvent) -> None:
        try:
            await self.manager.publish_closed(event)
        except Exception as error:
            logger.error(
                "settlement publication failed lot_id=%s category=publish error=%s",
                event.lot_id,
                type(error).__name__,
            )
            try:
                await self.manager.invalidate(event.lot_id)
            except Exception as failure:
                logger.error(
                    "settlement invalidation failed lot_id=%s error=%s",
                    event.lot_id,
                    type(failure).__name__,
                )

    def publish_result(self, result: SettlementResult) -> None:
        # Validate every discriminant before exposing any public terminal state.
        new = result.status in (
            SettlementStatus.SETTLED_SOLD,
            SettlementStatus.SETTLED_UNSOLD,
        )
        if new != result.transitioned:
            raise ValueError("invalid settlement transition")
        if result.status == SettlementStatus.NOT_DUE:
            if result.settlement is not None or result.receipt is not None:
                raise ValueError("invalid pending settlement")
            return
        if (
            result.status not in (*tuple(SettlementStatus),)
            or result.settlement is None
        ):
            raise ValueError("invalid settlement result")
        record = result.settlement
        if record.lot_id != result.lot_id or record.outcome not in ("sold", "unsold"):
            raise ValueError("invalid settlement identity")
        if (record.outcome == "sold") != (result.receipt is not None):
            raise ValueError("invalid settlement receipt")
        if new and result.status != "settled_" + record.outcome:
            raise ValueError("invalid settlement outcome")
        if not new or self.stopping:
            return
        event = closed_event(record)
        task = asyncio.create_task(self._publish(event))
        self.publications.add(task)

        def finished(done):
            self.publications.discard(done)
            if not done.cancelled():
                done.exception()

        task.add_done_callback(finished)

    async def run_cycle(self, source: str = "scheduler") -> CycleResult:
        result = CycleResult()
        if (
            self.stopping
            or self.guard.locked()
            or self.monotonic() < self.global_retry_at
        ):
            result.skipped = True
            logger.info("settlement cycle source=%s status=SKIP", source)
            return result
        started = self.monotonic()
        async with self.guard:
            owner = asyncio.current_task()
            self.active_cycles.add(owner)
            try:
                # Rotate survivors so every retry is eventually checked, including
                # those absent from candidate pages. Preserve each Retry unchanged.
                ids = list(islice(self.retries, PAGE_SIZE))
                if ids:
                    settled = await self.worker(settled_retries, self.factory, ids)
                    for lot_id in ids:
                        retry = self.retries.pop(lot_id)
                        if lot_id not in settled:
                            self.retries[lot_id] = retry
                if self.scan is None:
                    self.scan = await self.worker(open_scan, self.factory)
                if self.scan is None:
                    result.complete = True
                while self.scan is not None and not self.stopping:
                    page = await self.worker(
                        read_page,
                        self.factory,
                        self.scan,
                        min(PAGE_SIZE, MAX_ROWS - result.rows),
                    )
                    result.rows += len(page)
                    if not page:
                        self.scan = None
                        result.complete = True
                        break
                    for key in page:
                        if self.stopping or result.attempts >= MAX_ATTEMPTS:
                            break
                        self.scan.cursor = key
                        lot_id = key[1]
                        retry = self.retries.get(lot_id)
                        if (
                            retry is not None
                            and self.monotonic() < retry.next_attempt_at
                        ):
                            continue
                        result.attempts += 1
                        try:
                            outcome = await self.worker(
                                partial(
                                    settle_lot,
                                    self.factory,
                                    lot_id=lot_id,
                                    integrity=self.integrity,
                                )
                            )
                            if isinstance(outcome, IntegrityConflict):
                                self._retry(lot_id, True)
                                result.failures += 1
                                logger.error(
                                    "settlement failed source=%s lot_id=%s "
                                    "category=integrity",
                                    source,
                                    lot_id,
                                )
                            elif (
                                outcome is None
                                or outcome == SettlementRefusal.LOT_CANCELLED
                            ):
                                self.retries.pop(lot_id, None)
                            elif isinstance(outcome, SettlementResult):
                                self.publish_result(outcome)
                                self.retries.pop(lot_id, None)
                                logger.info(
                                    "settlement outcome source=%s lot_id=%s status=%s",
                                    source,
                                    lot_id,
                                    outcome.status,
                                )
                            else:
                                raise ValueError("invalid settlement command result")
                        except Exception as error:
                            result.failures += 1
                            permanent = isinstance(
                                error,
                                (
                                    SettlementFinancialConflict,
                                    MissingWalletError,
                                    IntegrityError,
                                ),
                            )
                            self._retry(lot_id, permanent)
                            logger.error(
                                "settlement failed source=%s lot_id=%s "
                                "category=%s error=%s",
                                source,
                                lot_id,
                                "invariant" if permanent else "operational",
                                type(error).__name__,
                            )
                            if systemic_failure(error):
                                result.systemic = True
                                break
                    if (
                        result.systemic
                        or result.attempts >= MAX_ATTEMPTS
                        or result.rows >= MAX_ROWS
                    ):
                        break
                if not result.systemic:
                    self.global_delay = INTERVAL
                    self.global_retry_at = 0
            except Exception as error:
                # Discovery failure means the scan itself is unreliable.
                result.systemic = True
                logger.error(
                    "settlement discovery failed source=%s error=%s",
                    source,
                    type(error).__name__,
                )
            finally:
                self.active_cycles.discard(owner)
                if result.systemic:
                    self.global_retry_at = self.monotonic() + self.global_delay
                    self.global_delay = min(30, self.global_delay * 2)
                logger.info(
                    "settlement cycle source=%s rows=%d attempts=%d "
                    "failures=%d complete=%s limit_reached=%s backlog=%s duration=%.3f",
                    source,
                    result.rows,
                    result.attempts,
                    result.failures,
                    result.complete,
                    result.rows >= MAX_ROWS or result.attempts >= MAX_ATTEMPTS,
                    not result.complete,
                    self.monotonic() - started,
                )
        return result

    async def catch_up(self) -> None:
        logger.info("settlement catch-up source=startup status=start")
        while not self.stopping:
            result = await self.run_cycle("startup")
            if result.systemic:
                raise RuntimeError(
                    "Não foi possível recuperar os fechamentos na inicialização."
                )
            if result.complete:
                logger.info("settlement catch-up source=startup status=complete")
                return

    def start(self) -> None:
        if not self.stopping and (self.task is None or self.task.done()):
            self.task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while not self.stopping:
            delay = max(INTERVAL, self.global_retry_at - self.monotonic())
            try:
                await asyncio.wait_for(self.wake.wait(), delay)
            except TimeoutError:
                pass
            if not self.stopping:
                await self.run_cycle()

    async def stop(self) -> None:
        deadline = self.monotonic() + DRAIN_TIMEOUT
        self.stopping = True
        self.wake.set()
        self.manager.begin_shutdown()
        reported = False
        # One global deadline; beyond it retain ownership and wait for safe cleanup.
        # No wait_for/cancel of a synchronous worker is interpreted as rollback.
        while True:
            pending = (
                ({self.task} if self.task and not self.task.done() else set())
                | self.workers
                | self.publications
                | self.active_cycles
                | self.manager.pending_tasks()
            )
            pending = {
                task
                for task in pending
                if task is not asyncio.current_task() and not task.done()
            }
            if not pending:
                break
            remaining = deadline - self.monotonic()
            if remaining <= 0 and not reported:
                reported = True
                logger.error(
                    "settlement drain exceeded category=shutdown workers=%d "
                    "publications=%d room_tasks=%d confirmation=unknown_or_confirmed",
                    len(self.workers),
                    len(self.publications),
                    len(self.manager.pending_tasks()),
                )
            if reported:
                await asyncio.gather(*pending, return_exceptions=True)
            else:
                await asyncio.wait(pending, timeout=max(0, remaining))
        logger.info("settlement shutdown status=drained exceeded=%s", reported)
