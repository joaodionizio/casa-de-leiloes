"""Private participation and wins snapshots on real PostgreSQL."""

from sqlalchemy import text

from app.bids import PlacedBid
from app.my_wins import read_my_wins_snapshot
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    login,
)
from tests.bid_support import live_lot, run_bid, tamper
from tests.lot_support import db_now, statement_recorder
from tests.settlement_support import (
    ALICE,
    BOB,
    expire,
    run_settle,
    snapshot,
    sold_lot,
)
from tests.settlement_support import (
    seeded as seeded_fixture,
)

seeded = seeded_fixture

URL = "/api/me/wins"
KEYS = {
    "lot_id",
    "title",
    "artist_display",
    "image_url",
    "phase",
    "settlement_status",
    "result",
    "winner_alias",
    "final_amount_cents",
    "settled_at",
    "bid_count",
}


def client_for(monkeypatch, seeded, email=BIDDER_EMAIL):
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    if email:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


def test_empty_and_access(monkeypatch, seeded):
    client = client_for(monkeypatch, seeded)
    response = client.get(URL)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"] == []
    assert response.json()["as_of"].endswith("Z")
    for email, status in [(None, 401), (AUCTIONEER_EMAIL, 403)]:
        response = client_for(monkeypatch, seeded, email).get(URL)
        assert response.status_code == status
        assert response.headers["cache-control"] == "no-store"


def test_matrix_isolation_receipt_privacy_and_no_effects(
    monkeypatch, seeded, db_engine
):
    own = sold_lot(seeded)
    run_settle(seeded, own)
    lost = live_lot(seeded)
    assert isinstance(run_bid(seeded, lost, ALICE, 10_000), PlacedBid)
    assert isinstance(run_bid(seeded, lost, BOB, 11_000), PlacedBid)
    expire(seeded, lost)
    run_settle(seeded, lost)
    exclusive = sold_lot(seeded, bidder_id=BOB)
    run_settle(seeded, exclusive)
    live = live_lot(seeded)
    assert isinstance(run_bid(seeded, live, ALICE, 10_000), PlacedBid)
    assert isinstance(run_bid(seeded, live, BOB, 11_000), PlacedBid)
    assert isinstance(run_bid(seeded, live, ALICE, 12_000), PlacedBid)
    pending = sold_lot(seeded)
    client = client_for(monkeypatch, seeded)
    before = snapshot(seeded)
    with statement_recorder(db_engine) as recorder:
        response = client.get(URL + f"?user_id={BOB}")
    assert response.status_code == 200
    assert snapshot(seeded) == before
    assert all(
        sql.lstrip().upper().startswith(("SELECT", "WITH"))
        and "FOR UPDATE" not in sql.upper()
        for sql in recorder.statements
    )
    assert len(recorder.statements) == 2  # session identity and one consistent snapshot
    items = {item["lot_id"]: item for item in response.json()["items"]}
    assert set(items) == {str(id) for id in (own, lost, live, pending)}
    won = items[str(own)]
    assert set(won) == KEYS
    assert won["result"] == "won" and won["phase"] == "ended"
    with seeded() as session:
        receipt = session.execute(
            text(
                "SELECT winner_alias, final_amount_cents FROM receipts WHERE lot_id=:id"
            ),
            {"id": own},
        ).one()
    assert won["winner_alias"] == receipt.winner_alias
    assert won["final_amount_cents"] == receipt.final_amount_cents
    assert items[str(lost)]["result"] == "not_won"
    assert items[str(live)]["result"] is None
    assert items[str(live)]["bid_count"] == 3
    assert items[str(pending)]["phase"] == "ended"
    assert items[str(pending)]["settlement_status"] == "pending"
    for id in (lost, live, pending):
        for field in ("winner_alias", "final_amount_cents", "settled_at"):
            assert items[str(id)][field] is None
    for private in (
        str(ALICE),
        str(BOB),
        "winner_user_id",
        "anchor_hmac",
        "final_hash",
        "wallet",
        "email",
    ):
        assert private not in response.text
    other = client_for(monkeypatch, seeded, OTHER_BIDDER_EMAIL).get(URL).json()["items"]
    assert str(own) not in [item["lot_id"] for item in other]
    assert str(exclusive) in [item["lot_id"] for item in other]


def test_structural_conflict_is_safe_and_never_repairs(monkeypatch, seeded):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    tamper(
        seeded,
        "UPDATE receipts SET final_amount_cents=final_amount_cents+1 WHERE lot_id=:id",
        id=lot_id,
    )
    before = snapshot(seeded)
    response = client_for(monkeypatch, seeded).get(URL)
    assert response.status_code == 409
    assert response.json()["code"] == "lot_integrity_conflict"
    assert response.headers["cache-control"] == "no-store"
    assert snapshot(seeded) == before


def test_clock_order_constant_query_and_no_autoflush(seeded, db_engine):
    first = sold_lot(seeded)
    second = sold_lot(seeded)
    now = db_now(seeded)
    tamper(
        seeded,
        "UPDATE lots SET created_at=:now WHERE id IN (:first, :second)",
        now=now,
        first=first,
        second=second,
    )
    with seeded() as session:
        from app.lots import Lot

        lot = session.get(Lot, first)
        lot.title = "Unflushed local change"
        with statement_recorder(db_engine) as recorder:
            response = read_my_wins_snapshot(session, ALICE)
        assert len(recorder.statements) == 1
        assert [item.lot_id for item in response.items] == sorted(
            [first, second], reverse=True
        )
        assert response.items[0].title != "Unflushed local change"
        session.rollback()


def test_local_data_without_external_api(monkeypatch, seeded):
    import httpx

    def no_network(*args, **kwargs):
        raise AssertionError("external API must not be used")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    lot_id = sold_lot(seeded)
    with seeded() as session:
        response = read_my_wins_snapshot(session, ALICE)
    assert response.items[0].lot_id == lot_id


def test_exceptional_scheduled_cancelled_and_unsold_participation(monkeypatch, seeded):
    import uuid
    from datetime import timedelta

    scheduled, cancelled, unsold = [sold_lot(seeded) for _ in range(3)]
    now = db_now(seeded)
    tamper(
        seeded,
        "UPDATE lots SET starts_at=:start, ends_at=:end WHERE id=:id",
        start=now + timedelta(hours=1),
        end=now + timedelta(hours=2),
        id=scheduled,
    )
    tamper(
        seeded, "UPDATE lots SET cancelled_at=:now WHERE id=:id", now=now, id=cancelled
    )
    # Exceptional historical participation: structural reads deliberately do not
    # audit every bid. The persisted lot and settlement must still agree.
    tamper(
        seeded,
        "UPDATE lots SET current_bid_cents=NULL, current_leader_id=NULL, "
        "bid_count=0, final_hash=:genesis WHERE id=:id",
        genesis="0" * 64,
        id=unsold,
    )
    tamper(
        seeded,
        "INSERT INTO lot_settlements (id, lot_id, outcome, bid_count, final_hash, "
        "anchor_hmac, settled_at) VALUES "
        "(:settlement, :lot, 'unsold', 0, :genesis, :anchor, :now)",
        settlement=uuid.uuid4(),
        lot=unsold,
        genesis="0" * 64,
        anchor="0" * 64,
        now=now,
    )
    response = client_for(monkeypatch, seeded).get(URL)
    assert response.status_code == 200
    items = {item["lot_id"]: item for item in response.json()["items"]}
    assert items[str(scheduled)]["phase"] == "scheduled"
    assert items[str(scheduled)]["result"] is None
    assert items[str(cancelled)]["phase"] == "cancelled"
    assert items[str(cancelled)]["settlement_status"] == "not_applicable"
    assert items[str(cancelled)]["result"] == "not_won"
    assert items[str(unsold)]["settlement_status"] == "settled"
    assert items[str(unsold)]["result"] == "not_won"
    assert all(item["winner_alias"] is None for item in items.values())


def test_own_sold_is_included_without_own_historical_participation(monkeypatch, seeded):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    # Read source of truth is settlement.winner_user_id, not reconstructed bids.
    tamper(
        seeded,
        "UPDATE bids SET bidder_id=:other WHERE lot_id=:id",
        other=BOB,
        id=lot_id,
    )
    response = client_for(monkeypatch, seeded).get(URL)
    assert response.status_code == 200
    assert response.json()["items"][0]["result"] == "won"


def test_unexpected_failure_is_generic_and_not_cached(monkeypatch, seeded):
    from app import my_wins

    def fail(*args):
        raise RuntimeError("private operational detail")

    monkeypatch.setattr(my_wins, "read_my_wins_snapshot", fail)
    response = client_for(monkeypatch, seeded).get(URL)
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert response.headers["cache-control"] == "no-store"
    assert "private operational detail" not in response.text
