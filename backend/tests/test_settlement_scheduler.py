"""Story 4.4 operational limits, ownership and public confirmation boundary."""

import asyncio
import threading
import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import OperationalError

from app import settlement_scheduler as scheduling
from app.bid_integrity import GENESIS_HASH
from app.bids import IntegrityConflict, IntegrityFailure
from app.lot_room import RoomManager, closed_event
from app.lot_settlement import SettlementRecord, SettlementResult, SettlementStatus
from tests.bid_support import integrity

NOW = datetime(2026, 10, 28, 12, 30, 1, 123456, tzinfo=UTC)


def confirmed(lot_id=None):
    lot_id = lot_id or uuid.UUID(int=1)
    record = SettlementRecord(
        uuid.uuid4(),
        lot_id,
        "unsold",
        None,
        None,
        None,
        None,
        0,
        GENESIS_HASH,
        "a" * 64,
        NOW,
    )
    return SettlementResult(SettlementStatus.SETTLED_UNSOLD, lot_id, record, None, True)


def owner(monkeypatch, count=1):
    monkeypatch.setattr(scheduling, "settled_retries", lambda factory, ids: set())
    ids = [uuid.UUID(int=i + 1) for i in range(count)]
    keys = [(NOW, identifier) for identifier in ids]
    calls, pages = [], []
    monkeypatch.setattr(
        scheduling, "open_scan", lambda factory: scheduling.Scan(NOW, keys[-1])
    )

    def page(factory, scan, limit):
        result = [key for key in keys if scan.cursor is None or key > scan.cursor][
            :limit
        ]
        pages.append(result)
        return result

    monkeypatch.setattr(scheduling, "read_page", page)

    def settle(factory, *, lot_id, integrity):
        calls.append(lot_id)
        return confirmed(lot_id)

    monkeypatch.setattr(scheduling, "settle_lot", settle)
    return (
        scheduling.SettlementScheduler(lambda: None, integrity(), RoomManager()),
        ids,
        calls,
        pages,
    )


def test_t03_t05_t18_t19_t20_only_confirmed_transition_can_publish():
    async def scenario():
        scheduler = scheduling.SettlementScheduler(
            lambda: None, integrity(), RoomManager()
        )
        calls = []

        async def publish(event):
            calls.append(event)

        scheduler.manager.publish_closed = publish
        result = confirmed()
        scheduler.publish_result(
            replace(result, status=SettlementStatus.ALREADY_SETTLED, transitioned=False)
        )
        scheduler.publish_result(
            SettlementResult(SettlementStatus.NOT_DUE, result.lot_id, None, None, False)
        )
        assert not scheduler.publications
        for invalid in [
            replace(result, transitioned=False),
            replace(result, settlement=None),
            replace(result, status=SettlementStatus.SETTLED_SOLD),
        ]:
            with pytest.raises(ValueError):
                scheduler.publish_result(invalid)
        scheduler.publish_result(result)
        await asyncio.gather(*scheduler.publications)
        assert len(calls) == 1
        event = calls[0].model_dump(mode="json")
        assert set(event) == {
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
        assert event["as_of"] == event["settled_at"] == "2026-10-28T12:30:01.123456Z"
        assert event["winner_alias"] is event["final_amount_cents"] is None
        assert "a" * 64 not in str(event)
        await scheduler.stop()

    asyncio.run(scenario())


def test_t10_guard_skips_without_queuing(monkeypatch):
    async def scenario():
        scheduler, _, calls, _ = owner(monkeypatch)
        entered, release = threading.Event(), threading.Event()

        def settle(*args, **kwargs):
            entered.set()
            assert release.wait(5)
            return confirmed(kwargs["lot_id"])

        monkeypatch.setattr(scheduling, "settle_lot", settle)
        first = asyncio.create_task(scheduler.run_cycle())
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            second = await scheduler.run_cycle()
            assert second.skipped and second.attempts == 0
        finally:
            release.set()
            await first
            await scheduler.stop()
        assert not calls and not scheduler.guard.locked()

    asyncio.run(scenario())


def test_t11_t12_t13_cooldown_is_300_seconds_and_other_lots_progress(monkeypatch):
    async def scenario():
        scheduler, ids, calls, _ = owner(monkeypatch, 2)
        clock = [0.0]
        scheduler.monotonic = lambda: clock[0]

        def settle(factory, *, lot_id, integrity):
            calls.append(lot_id)
            return (
                IntegrityConflict(IntegrityFailure.MISSING_ANCHOR)
                if lot_id == ids[0]
                else confirmed(lot_id)
            )

        monkeypatch.setattr(scheduling, "settle_lot", settle)
        await scheduler.run_cycle()
        assert calls == ids and scheduler.retries[ids[0]].next_attempt_at == 300
        scheduler.scan = None
        clock[0] = 299.99
        await scheduler.run_cycle()
        assert calls.count(ids[0]) == 1
        scheduler.scan = None
        clock[0] = 300
        await scheduler.run_cycle()
        assert calls.count(ids[0]) == 2
        await scheduler.stop()

    asyncio.run(scenario())


def test_t14_transient_backoff_is_per_id_and_future_cycle_only(monkeypatch):
    async def scenario():
        scheduler, ids, calls, _ = owner(monkeypatch)
        clock = [0.0]
        scheduler.monotonic = lambda: clock[0]

        def fail(*args, **kwargs):
            calls.append(kwargs["lot_id"])
            raise RuntimeError("private synthetic marker")

        monkeypatch.setattr(scheduling, "settle_lot", fail)
        for delay in [2, 4, 8, 16, 30, 30]:
            scheduler.scan = None
            await scheduler.run_cycle()
            assert scheduler.retries[ids[0]].delay == delay
            clock[0] += delay
        assert len(calls) == 6
        await scheduler.stop()

    asyncio.run(scenario())


def test_retry_pruning_rotates_more_than_one_page(monkeypatch):
    async def scenario():
        scheduler = scheduling.SettlementScheduler(
            lambda: None, integrity(), RoomManager()
        )
        ids = [uuid.UUID(int=i + 1) for i in range(60)]
        original = {identifier: scheduling.Retry(100, 2) for identifier in ids}
        scheduler.retries.update(original)
        settled = {ids[5], ids[55]}
        inspected = []

        def find_settled(factory, batch):
            inspected.append(list(batch))
            return settled.intersection(batch)

        monkeypatch.setattr(scheduling, "settled_retries", find_settled)
        monkeypatch.setattr(scheduling, "open_scan", lambda factory: None)
        try:
            await scheduler.run_cycle()
            assert inspected[0] == ids[:50]
            assert ids[5] not in scheduler.retries and ids[55] in scheduler.retries
            await scheduler.run_cycle()
            assert len(inspected[1]) <= 50
            assert set(ids[50:]).issubset(inspected[1])
            assert settled.isdisjoint(scheduler.retries)
            assert set(scheduler.retries) == set(ids) - settled
            for identifier, retry in scheduler.retries.items():
                assert retry is original[identifier]
                assert retry.delay == 2 and retry.next_attempt_at == 100
        finally:
            await scheduler.stop()

    asyncio.run(scenario())


def test_t14_t36_systemic_discovery_fails_startup_and_backs_off(monkeypatch):
    async def scenario():
        scheduler, _, _, _ = owner(monkeypatch)

        def fail(factory):
            raise OperationalError("private SQL", {}, RuntimeError("private detail"))

        monkeypatch.setattr(scheduling, "open_scan", fail)
        with pytest.raises(RuntimeError, match="inicialização"):
            await scheduler.catch_up()
        assert scheduler.task is None
        assert (await scheduler.run_cycle()).skipped
        await scheduler.stop()

    asyncio.run(scenario())


def test_t16_t39_publication_wait_never_blocks_the_next_lot(monkeypatch, caplog):
    async def scenario():
        scheduler, ids, calls, _ = owner(monkeypatch, 2)
        entered, release = asyncio.Event(), asyncio.Event()
        invalidations = []

        async def publish(event):
            entered.set()
            await release.wait()
            raise RuntimeError("private publication marker")

        async def invalidate(identifier):
            invalidations.append(identifier)

        scheduler.manager.publish_closed = publish
        scheduler.manager.invalidate = invalidate
        await scheduler.run_cycle()
        await entered.wait()
        assert calls == ids and len(scheduler.publications) == 2
        release.set()
        await scheduler.stop()
        assert set(invalidations) == set(ids)
        assert "private publication marker" not in caplog.text

    asyncio.run(scenario())


def test_t33_cursor_counts_returned_rows_and_does_not_skip_unexamined_page(monkeypatch):
    async def scenario():
        scheduler, ids, calls, pages = owner(monkeypatch, 270)
        for identifier in ids[:10]:
            scheduler._retry(identifier, True)
        first = await scheduler.run_cycle()
        assert (first.rows, first.attempts) == (100, 50)
        assert calls == ids[10:60]
        assert scheduler.scan.cursor[1] == ids[59]
        second = await scheduler.run_cycle()
        assert second.attempts == 50 and calls[50:] == ids[60:110]
        scheduler.scan = None
        for identifier in ids[:220]:
            scheduler._retry(identifier, True)
        start = len(calls)
        cycle = await scheduler.run_cycle()
        assert cycle.rows == 200 and cycle.attempts == 0
        cycle = await scheduler.run_cycle()
        assert cycle.rows <= 200 and cycle.attempts == 50
        assert calls[start:] == ids[220:270]
        await scheduler.run_cycle()
        assert scheduler.scan is None
        assert max(map(len, pages)) <= 50
        await scheduler.stop()

    asyncio.run(scenario())


def test_t27_t39_shutdown_retains_worker_past_one_global_drain_deadline(
    monkeypatch, caplog
):
    async def scenario():
        scheduler, _, _, _ = owner(monkeypatch)
        monkeypatch.setattr(scheduling, "DRAIN_TIMEOUT", 0)
        entered, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )

        def work():
            entered.set()
            try:
                assert release.wait(5)
            finally:
                finished.set()

        waiting = asyncio.create_task(scheduler.worker(work))
        assert await asyncio.to_thread(entered.wait, 5)
        stopping = asyncio.create_task(scheduler.stop())
        try:
            await asyncio.sleep(0)
            assert not stopping.done() and scheduler.workers
            assert "drain exceeded" in caplog.text
            assert not finished.is_set()
        finally:
            release.set()
            await asyncio.gather(waiting, stopping)
        assert finished.is_set() and not scheduler.workers
        assert (await scheduler.run_cycle()).skipped

    asyncio.run(scenario())


def test_t27_start_is_idempotent_sleep_is_interrupted_without_a_cycle(monkeypatch):
    async def scenario():
        scheduler, _, calls, _ = owner(monkeypatch)
        scheduler.start()
        task = scheduler.task
        scheduler.start()
        assert scheduler.task is task
        await asyncio.sleep(0)
        await scheduler.stop()
        assert not calls and task.done()

    asyncio.run(scenario())


def test_t18_builder_reads_only_the_persisted_result():
    result = confirmed()
    assert closed_event(result.settlement).as_of == result.settlement.settled_at
