"""T06/T17/T36: durable settlement survives an application lost-publication window."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import lot_room, main
from app import settlement_scheduler as scheduling
from app.lot_cancellation import cancel_lot
from app.seed import DEMO_AUCTIONEER_ID
from tests import settlement_support
from tests.auth_support import HTTPS_ORIGIN
from tests.bid_support import integrity, live_lot, tamper
from tests.settlement_support import counts, expire, snapshot, sold_lot

seeded = settlement_support.seeded


@pytest.mark.settlement_lifecycle
@pytest.mark.parametrize("sold", [False, True], ids=["unsold", "sold"])
def test_t06_t17_t36_commit_without_publish_restart_and_mixed_catchup(
    seeded, db_engine, monkeypatch, sold
):
    monkeypatch.setattr(main, "get_engine", lambda: db_engine)
    monkeypatch.setattr(lot_room, "get_engine", lambda: db_engine)
    published = []
    original_publish = lot_room.RoomManager.publish_closed

    async def capture(manager, frame):
        published.append(frame.lot_id)
        await original_publish(manager, frame)

    monkeypatch.setattr(lot_room.RoomManager, "publish_closed", capture)
    committed = []
    first = main.create_app(app_origin=HTTPS_ORIGIN)
    with TestClient(first) as client:
        identifier = sold_lot(seeded) if sold else live_lot(seeded)
        expire(seeded, identifier)
        owner = first.state.settlement_scheduler
        # Crash window injection: the real command returns confirmed, then the
        # process loses its local publication opportunity. No financial fake.
        owner.publish_result = lambda result: committed.append(result)
        client.portal.call(owner.run_cycle)
        assert len(committed) == 1 and committed[0].transitioned
        assert counts(seeded, identifier) == (1, int(sold))
        assert published == [] and not owner.publications
    assert owner.task.done() and not owner.workers
    durable = snapshot(seeded)

    # An additional downtime population exercises the actual next startup.
    pending_sold = sold_lot(seeded)
    pending_unsold = live_lot(seeded)
    expire(seeded, pending_unsold)
    cancelled = live_lot(seeded)
    with seeded() as session:
        cancelled_result = cancel_lot(
            session,
            lot_id=cancelled,
            auctioneer_id=DEMO_AUCTIONEER_ID,
            integrity=integrity(),
        )
        assert cancelled_result is not None
        session.commit()
    expire(seeded, cancelled)
    future = live_lot(seeded)
    broken = live_lot(seeded)
    expire(seeded, broken)
    tamper(seeded, "UPDATE lots SET anchor_hmac=NULL WHERE id=:id", id=broken)
    attempted = []
    command = scheduling.settle_lot

    def recorded(factory, **kwargs):
        attempted.append(kwargs["lot_id"])
        return command(factory, **kwargs)

    monkeypatch.setattr(scheduling, "settle_lot", recorded)
    second = main.create_app(app_origin=HTTPS_ORIGIN)
    with TestClient(second) as client:
        assert identifier not in attempted  # No replay or second financial attempt.
        assert set(attempted) == {pending_sold, pending_unsold, broken}
        assert counts(seeded, pending_sold) == (1, 1)
        assert counts(seeded, pending_unsold) == (1, 0)
        assert (
            counts(seeded, cancelled)
            == counts(seeded, future)
            == counts(seeded, broken)
            == (0, 0)
        )

        async def drain():
            await asyncio.gather(*second.state.settlement_scheduler.publications)

        client.portal.call(drain)
        assert identifier not in published
        assert set(published) == {pending_sold, pending_unsold}
        stable = snapshot(seeded)
        with client.websocket_connect(f"/ws/lots/{identifier}") as socket:
            frame = socket.receive_json()
            assert frame["type"] == "room_snapshot"
            assert frame["room"]["settlement_status"] == "settled"
            assert frame["room"]["settlement"]["outcome"] == (
                "sold" if sold else "unsold"
            )
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
            assert closed.value.code == 1000
        assert snapshot(seeded) == stable
        assert counts(seeded, identifier) == (1, int(sold))
        # Original settlement/receipt rows remain byte-for-byte equivalent values.
        with seeded() as session:
            original = committed[0].settlement
            stored = session.get(scheduling.LotSettlement, original.id)
            assert stored.settled_at == original.settled_at
            assert stored.final_hash == original.final_hash
    assert second.state.settlement_scheduler.task.done()
    assert durable != () and db_engine.pool.checkedout() == 0
