"""Story 4.4: operational owners over real, independently observed PG locks."""

import asyncio
import threading
from datetime import timedelta
from functools import partial

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session, sessionmaker

from app import lot_room
from app import settlement_scheduler as orchestration
from app.bid_rules import BidRefusal
from app.bids import PlacedBid
from app.lot_room import RoomManager
from app.lot_settlement import settle_lot
from app.settlement_scheduler import Scan, SettlementScheduler
from tests import settlement_support
from tests.bid_support import (
    hold_bid,
    integrity,
    is_lot_lock,
    live_lot,
    lot_state,
    run_bid,
)
from tests.integration.test_lot_settlement_concurrency import (
    wait_for_exact_block,
)
from tests.lot_support import db_now
from tests.settlement_support import ALICE, BOB, counts, snapshot, sold_lot
from tests.wallet_support import wallet_row

seeded = settlement_support.seeded
TIMEOUT = 10


async def drain(owner):
    await asyncio.gather(*owner.publications)


def test_t08_t30_stale_candidate_waits_for_bid_and_rereads_cumulative_end(
    seeded, db_engine, monkeypatch
):
    original_end = db_now(seeded) + timedelta(seconds=1)
    lot_id = live_lot(seeded, ends_at=original_end)
    frames = []
    monkeypatch.setattr(
        orchestration,
        "open_scan",
        lambda factory: Scan(original_end, (original_end, lot_id)),
    )
    monkeypatch.setattr(
        orchestration,
        "read_page",
        lambda factory, scan, limit: [] if scan.cursor else [(original_end, lot_id)],
    )

    async def close():
        manager = RoomManager()

        async def publish(frame):
            frames.append(frame)

        manager.publish_closed = publish
        owner = SettlementScheduler(seeded, integrity(), manager)
        result = await owner.run_cycle()
        await drain(owner)
        await owner.stop()
        return result

    def wait_original_end():
        with seeded() as observer:
            observer.execute(
                text(
                    "SELECT pg_sleep(GREATEST(EXTRACT(EPOCH FROM "
                    "(CAST(:end AS timestamptz)-clock_timestamp())),0)+0.01)"
                ),
                {"end": original_end},
            )

    attempted = threading.Event()
    blocked, results = [], []
    with seeded() as session:
        blocker = session.scalar(text("SELECT pg_backend_pid()"))
        accepted = hold_bid(session, lot_id, ALICE, 12000)

        def capture(connection, cursor, statement, parameters, context, executemany):
            if is_lot_lock(statement):
                backend = connection.connection.driver_connection.info.backend_pid
                if backend != blocker:
                    blocked.append(backend)
                    attempted.set()

        thread = threading.Thread(target=lambda: results.append(asyncio.run(close())))
        event.listen(db_engine, "before_cursor_execute", capture)
        try:
            thread.start()
            assert attempted.wait(TIMEOUT)
            wait_for_exact_block(db_engine, blocker, blocked[0])
            wait_original_end()
        finally:
            session.commit()
            thread.join(TIMEOUT)
            event.remove(db_engine, "before_cursor_execute", capture)
        assert not thread.is_alive()
    assert len(results) == 1
    result = results[0]
    assert isinstance(accepted, PlacedBid) and accepted.anti_sniping_applied
    assert accepted.ends_at == original_end + timedelta(minutes=2)
    assert result.attempts == 1 and result.failures == 0
    assert frames == [] and counts(seeded, lot_id) == (0, 0)
    assert lot_state(seeded, lot_id)["ends_at"] == accepted.ends_at
    second = run_bid(seeded, lot_id, BOB, 13000)
    assert isinstance(second, PlacedBid)
    assert second.ends_at == original_end + timedelta(minutes=4)


@pytest.mark.parametrize("rollback_first", [False, True], ids=["commit", "abort-A"])
@pytest.mark.parametrize("sold", [False, True], ids=["unsold", "sold"])
def test_t10_two_operational_owners_one_transition_and_frame(
    seeded, db_engine, monkeypatch, rollback_first, sold
):
    lot_id = sold_lot(seeded) if sold else live_lot(seeded)
    settlement_support.expire(seeded, lot_id)
    before_wallet = wallet_row(seeded, ALICE)
    entered, release, attempted = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    blocker, blocked = [], []

    class HeldSession(Session):
        def commit(self):
            blocker.append(
                self.connection().connection.driver_connection.info.backend_pid
            )
            entered.set()
            assert release.wait(TIMEOUT)
            if rollback_first:
                raise RuntimeError("synthetic abort before commit")
            return super().commit()

    held = sessionmaker(bind=db_engine, class_=HeldSession, expire_on_commit=False)

    def capture(connection, cursor, statement, parameters, context, executemany):
        if entered.is_set() and is_lot_lock(statement):
            backend = connection.connection.driver_connection.info.backend_pid
            if backend != blocker[0]:
                blocked.append(backend)
                attempted.set()

    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)

    async def scenario():
        manager = RoomManager()
        first_sub = await manager.subscribe(lot_id)
        second_sub = await manager.subscribe(lot_id)
        first_sub.queue.get_nowait()
        second_sub.queue.get_nowait()
        owners = [
            SettlementScheduler(factory, integrity(), manager)
            for factory in (held, seeded)
        ]
        first = asyncio.create_task(owners[0].run_cycle())
        second = None
        try:
            assert await asyncio.to_thread(entered.wait, TIMEOUT)
            event.listen(db_engine, "before_cursor_execute", capture)
            second = asyncio.create_task(owners[1].run_cycle())
            assert await asyncio.to_thread(attempted.wait, TIMEOUT)
            await asyncio.to_thread(
                wait_for_exact_block, db_engine, blocker[0], blocked[0]
            )
            assert first_sub.queue.empty() and second_sub.queue.empty()
            assert counts(seeded, lot_id) == (0, 0)
        finally:
            release.set()
            await asyncio.gather(*[task for task in (first, second) if task])
            event.remove(db_engine, "before_cursor_execute", capture)
            for owner in owners:
                await drain(owner)
        for subscriber in (first_sub, second_sub):
            assert subscriber.queue.get_nowait().type == "lot_closed"
            assert subscriber.queue.empty()
            await manager.remove(lot_id, subscriber)
        for owner in owners:
            await owner.stop()
        assert not manager.rooms

    asyncio.run(scenario())
    assert counts(seeded, lot_id) == (1, int(sold))
    assert wallet_row(seeded, ALICE) == (
        (before_wallet[0] - 12000, before_wallet[1] - 12000) if sold else before_wallet
    )
    assert db_engine.pool.checkedout() == 0


def test_t09_closer_commit_releases_waiting_bid_without_reopening(
    seeded, db_engine, monkeypatch
):
    lot_id = sold_lot(seeded)
    before = lot_state(seeded, lot_id)
    entered, release, attempted = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    blocker, blocked, frames = [], [], []

    class HeldSession(Session):
        def commit(self):
            blocker.append(
                self.connection().connection.driver_connection.info.backend_pid
            )
            entered.set()
            assert release.wait(TIMEOUT)
            return super().commit()

    held = sessionmaker(bind=db_engine, class_=HeldSession, expire_on_commit=False)

    def capture(connection, cursor, statement, parameters, context, executemany):
        if entered.is_set() and is_lot_lock(statement):
            backend = connection.connection.driver_connection.info.backend_pid
            if backend != blocker[0]:
                blocked.append(backend)
                attempted.set()

    async def scenario():
        manager = RoomManager()

        async def publish(frame):
            # Observe persistence independently at the actual publication boundary.
            assert counts(seeded, lot_id) == (1, 1)
            frames.append(frame)

        manager.publish_closed = publish
        owner = SettlementScheduler(held, integrity(), manager)
        closing = asyncio.create_task(owner.run_cycle())
        bidding = None
        try:
            assert await asyncio.to_thread(entered.wait, TIMEOUT)
            assert frames == [] and counts(seeded, lot_id) == (0, 0)
            event.listen(db_engine, "before_cursor_execute", capture)
            bidding = asyncio.create_task(
                asyncio.to_thread(run_bid, seeded, lot_id, BOB, 13000)
            )
            assert await asyncio.to_thread(attempted.wait, TIMEOUT)
            await asyncio.to_thread(
                wait_for_exact_block, db_engine, blocker[0], blocked[0]
            )
        finally:
            release.set()
            await closing
            event.remove(db_engine, "before_cursor_execute", capture)
        assert await bidding == BidRefusal.LOT_ENDED
        await drain(owner)
        assert len(frames) == 1
        await owner.stop()

    asyncio.run(scenario())
    assert lot_state(seeded, lot_id) == before
    assert wallet_row(seeded, BOB)[1] == 0
    assert counts(seeded, lot_id) == (1, 1)


@pytest.mark.parametrize("mode", ["confirmed", "commit_abort", "lost_ack"])
def test_t15_t37_commit_barrier_real_abort_and_ambiguous_confirmation(
    seeded, db_engine, mode
):
    lot_id = sold_lot(seeded)
    before = snapshot(seeded)
    entered, release = threading.Event(), threading.Event()
    frames = []

    class HeldSession(Session):
        def commit(self):
            entered.set()
            assert release.wait(TIMEOUT)
            super().commit()
            if mode == "lost_ack":
                raise RuntimeError("synthetic confirmation loss after real COMMIT")

    factory = sessionmaker(bind=db_engine, class_=HeldSession, expire_on_commit=False)
    if mode == "commit_abort":
        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE FUNCTION abort_scheduler_commit() RETURNS trigger "
                    "LANGUAGE plpgsql "
                    "AS $$ BEGIN RAISE EXCEPTION 'synthetic deferred abort'; END $$"
                )
            )
            connection.execute(
                text(
                    "CREATE CONSTRAINT TRIGGER abort_scheduler_commit AFTER INSERT "
                    "ON lot_settlements "
                    "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                    "EXECUTE FUNCTION abort_scheduler_commit()"
                )
            )

    async def scenario():
        manager = RoomManager()

        async def publish(frame):
            assert counts(seeded, lot_id) == (1, 1)
            frames.append(frame)

        manager.publish_closed = publish
        owner = SettlementScheduler(factory, integrity(), manager)
        scheduled = []
        real_publish_result = owner.publish_result

        def request_publication(result):
            scheduled.append(result)
            real_publish_result(result)

        owner.publish_result = request_publication
        cycling = asyncio.create_task(owner.run_cycle())
        try:
            assert await asyncio.to_thread(entered.wait, TIMEOUT)
            assert frames == [] and not owner.publications
            assert scheduled == []
            assert snapshot(seeded) == before
        finally:
            release.set()
            result = await cycling
            await drain(owner)
        assert result.failures == int(mode != "confirmed")
        if mode == "confirmed":
            assert len(frames) == 1
        else:
            assert frames == []
        if mode == "lost_ack":
            persisted = snapshot(seeded)
            repeated = await owner.worker(
                partial(settle_lot, seeded, lot_id=lot_id, integrity=integrity())
            )
            assert repeated.status == "already_settled" and not repeated.transitioned
            owner.publish_result(repeated)
            await drain(owner)
            assert frames == [] and snapshot(seeded) == persisted
        await owner.stop()

    try:
        asyncio.run(scenario())
        assert counts(seeded, lot_id) == ((0, 0) if mode == "commit_abort" else (1, 1))
        if mode == "commit_abort":
            assert snapshot(seeded) == before
    finally:
        release.set()
        if mode == "commit_abort":
            with db_engine.begin() as connection:
                connection.execute(
                    text("DROP TRIGGER abort_scheduler_commit ON lot_settlements")
                )
                connection.execute(text("DROP FUNCTION abort_scheduler_commit()"))
    assert db_engine.pool.checkedout() == 0


def test_t27_t39_stop_retains_real_commit_worker_beyond_global_drain(
    seeded, db_engine, monkeypatch, caplog
):
    lot_id = sold_lot(seeded)
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()

    class HeldSession(Session):
        settlement_work = False

        def commit(self):
            self.settlement_work = True
            entered.set()
            assert release.wait(TIMEOUT)
            return super().commit()

        def close(self):
            super().close()
            if self.settlement_work:
                closed.set()

    assert orchestration.DRAIN_TIMEOUT == 30
    monkeypatch.setattr(orchestration, "DRAIN_TIMEOUT", 0.02)
    factory = sessionmaker(bind=db_engine, class_=HeldSession, expire_on_commit=False)

    async def scenario():
        owner = SettlementScheduler(factory, integrity(), RoomManager())
        cycling = asyncio.create_task(owner.run_cycle())
        stopping = None
        try:
            assert await asyncio.to_thread(entered.wait, TIMEOUT)
            stopping = asyncio.create_task(owner.stop())
            deadline = asyncio.get_running_loop().time() + TIMEOUT
            while not any(
                "drain exceeded" in record.getMessage() for record in caplog.records
            ):
                assert asyncio.get_running_loop().time() < deadline
                await asyncio.sleep(0.005)
            assert owner.stopping and owner.workers
            assert not stopping.done() and not cycling.done() and not closed.is_set()
            assert (await owner.run_cycle()).skipped
            assert counts(seeded, lot_id) == (0, 0)
            assert db_engine.pool.checkedout() >= 1
        finally:
            release.set()
            await cycling
            if stopping:
                await stopping
        assert closed.is_set() and not owner.workers and not owner.publications
        assert counts(seeded, lot_id) == (1, 1)

    asyncio.run(scenario())
    assert db_engine.pool.checkedout() == 0
