"""T33: bounded real PostgreSQL pages advance over an old cooldown backlog."""

import asyncio

from app import settlement_scheduler as scheduling
from app.lot_room import RoomManager
from tests import settlement_support
from tests.bid_support import integrity, live_lot
from tests.settlement_support import counts, expire

seeded = settlement_support.seeded


def test_t33_real_pages_progress_over_200_cooldowns_and_wrap(seeded, monkeypatch):
    ids = [live_lot(seeded) for _ in range(225)]
    for identifier in ids:
        expire(seeded, identifier)
    initial = scheduling.open_scan(seeded)
    # Database ordering, including its UUID tie breaker, defines the population.
    ordered = []
    while page := scheduling.read_page(seeded, initial, 50):
        ordered.extend(identifier for _, identifier in page)
        initial.cursor = page[-1]
    assert len(ordered) == 225
    pages, attempted, published = [], [], []
    real_page, real_command = scheduling.read_page, scheduling.settle_lot

    def page(factory, scan, limit):
        result = real_page(factory, scan, limit)
        assert len(result) <= limit <= 50
        pages.append(len(result))
        return result

    def settle(factory, **kwargs):
        attempted.append(kwargs["lot_id"])
        return real_command(factory, **kwargs)

    monkeypatch.setattr(scheduling, "read_page", page)
    monkeypatch.setattr(scheduling, "settle_lot", settle)

    async def scenario():
        clock = [0.0]
        manager = RoomManager()

        async def publish(frame):
            published.append(frame.lot_id)

        manager.publish_closed = publish
        owner = scheduling.SettlementScheduler(
            seeded, integrity(), manager, monotonic=lambda: clock[0]
        )
        for identifier in ordered[:205]:
            owner._retry(identifier, True)

        async def cycle():
            start = len(pages)
            result = await owner.run_cycle()
            assert sum(pages[start:]) == result.rows <= 200
            assert result.attempts <= 50
            return result

        first = await cycle()
        assert first.rows == 200 and first.attempts == 0
        assert owner.scan.cursor[1] == ordered[199]
        second = await cycle()
        assert second.attempts == 20
        assert attempted == ordered[205:]
        assert all(counts(seeded, identifier) == (1, 0) for identifier in ordered[205:])
        # Finish the scan, wrap, and verify the prefix remains on cooldown.
        for _ in range(3):
            await cycle()
        assert attempted == ordered[205:]
        clock[0] = 300
        for _ in range(8):
            await cycle()
        await asyncio.gather(*owner.publications)
        assert set(attempted) == set(ordered) and len(attempted) == 225
        assert set(published) == set(ordered) and len(published) == 225
        assert not owner.retries
        await owner.stop()

    asyncio.run(scenario())
