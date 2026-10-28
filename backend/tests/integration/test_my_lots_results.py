"""Private results: real PostgreSQL snapshot, ownership and read purity (4.5)."""

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import event, select, text

from app import lot_settlement, lots
from app.lots import (
    Lot,
    MyLotsResponse,
    PrivateLotSettlementSummary,
    read_my_lots_snapshot,
)
from app.money import MAX_CENTS
from app.seed import DEMO_AUCTIONEER_ID
from app.settlement_scheduler import SettlementScheduler
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    login,
)
from tests.bid_support import live_lot, tamper
from tests.integration.test_my_lots import add_other_auctioneer
from tests.lot_support import db_now, insert_lot, statement_recorder
from tests.settlement_support import (
    ALICE,
    expire,
    run_settle,
    snapshot,
    sold_lot,
)
from tests.settlement_support import (
    seeded as settlement_seeded,
)
from tests.wallet_support import set_wallet

URL = "/api/lots/mine"
seeded = settlement_seeded
SUMMARY_KEYS = {
    "outcome",
    "winner_alias",
    "final_amount_cents",
    "bid_count",
    "settled_at",
}


@pytest.fixture
def owner(monkeypatch, seeded):
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    return client


@pytest.fixture
def publication_spies(owner, monkeypatch):
    """Observe both the scheduler signal and the app's actual broadcaster."""
    manager = owner.app.state.room_manager
    spies = []
    for name in ("publish_closed", "publish_bid", "publish_cancellation"):
        spy = AsyncMock(side_effect=AssertionError("private read published an event"))
        monkeypatch.setattr(manager, name, spy)
        spies.append(spy)
    for target, name in ((SettlementScheduler, "publish_result"), (manager, "enqueue")):
        spy = Mock(side_effect=AssertionError("private read signalled publication"))
        monkeypatch.setattr(target, name, spy)
        spies.append(spy)
    yield spies
    for spy in spies:
        spy.assert_not_called()


@contextmanager
def incompatible_receipt(factory, engine, *, lot_id, settlement_id, target_table):
    """Drop only the selected test FK; remove the fixture and restore its exact DDL."""
    receipt_id = uuid.uuid4()
    statement = text(
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid='receipts'::regclass "
        "AND confrelid=CAST(:target AS regclass) AND contype='f'"
    )
    with engine.connect() as connection:
        original_fk = tuple(
            connection.execute(statement, {"target": target_table}).one()
        )
    name, definition = original_fk
    quoted_name = engine.dialect.identifier_preparer.quote(name)
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE receipts DROP CONSTRAINT {quoted_name}"))
    try:
        tamper(
            factory,
            "INSERT INTO receipts "
            "(id, lot_id, settlement_id, winning_bid_sequence, winner_alias, "
            "final_amount_cents, settled_at, bid_count, final_hash) VALUES "
            "(:rid, :id, :sid, 1, 'Licitante-AAAAAAAAAAAAAAAA', 13000, :at, 1, :hash)",
            rid=receipt_id,
            id=lot_id,
            sid=settlement_id,
            at=db_now(factory),
            hash="a" * 64,
        )
        yield receipt_id
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM receipts WHERE id=:id"), {"id": receipt_id}
            )
            connection.execute(
                text(f"ALTER TABLE receipts ADD CONSTRAINT {quoted_name} {definition}")
            )
            restored_fk = tuple(
                connection.execute(statement, {"target": target_table}).one()
            )
            assert restored_fk == original_fk


def results(response):
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"as_of", "items", "total_received_cents"}
    return body, {item["id"]: item for item in body["items"]}


def unsold_lot(factory):
    lot_id = live_lot(factory)
    expire(factory, lot_id)
    assert run_settle(factory, lot_id).status == "settled_unsold"
    return lot_id


def test_mixed_results_use_only_persisted_summaries_and_own_total(owner, seeded):
    first = sold_lot(seeded, amount=13_000)
    original = run_settle(seeded, first)
    second = sold_lot(seeded, amount=25_000)
    run_settle(seeded, second)
    unsold = unsold_lot(seeded)
    pending = sold_lot(seeded, amount=11_000)
    live = live_lot(seeded)
    now = db_now(seeded)
    scheduled = insert_lot(
        seeded,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
    )
    cancelled = insert_lot(
        seeded,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        cancelled_at=now,
        ends_at=now - timedelta(hours=1),
    )
    other = add_other_auctioneer(seeded)
    foreign = sold_lot(seeded, amount=7_000)
    run_settle(seeded, foreign)
    tamper(
        seeded,
        "UPDATE lots SET auctioneer_id=:owner WHERE id=:id",
        owner=other,
        id=foreign,
    )
    before = snapshot(seeded)

    body, items = results(owner.get(URL + f"?auctioneer_id={other}&lot_id={foreign}"))

    assert body["total_received_cents"] == 38_000
    assert str(foreign) not in items and str(foreign) not in str(body)
    sold = items[str(first)]["settlement"]
    assert set(sold) == SUMMARY_KEYS
    assert sold == {
        "outcome": "sold",
        "winner_alias": original.settlement.winner_alias,
        "final_amount_cents": 13_000,
        "bid_count": 1,
        "settled_at": original.settlement.settled_at.astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    assert items[str(first)]["settlement_status"] == "settled"
    assert items[str(unsold)]["settlement"] == {
        "outcome": "unsold",
        "winner_alias": None,
        "final_amount_cents": None,
        "bid_count": 0,
        "settled_at": items[str(unsold)]["settlement"]["settled_at"],
    }
    for lot_id, phase in (
        (pending, "ended"),
        (live, "live"),
        (scheduled, "scheduled"),
        (cancelled, "ended"),
    ):
        assert items[str(lot_id)]["phase"] == phase
        assert items[str(lot_id)]["settlement_status"] == "pending"
        assert items[str(lot_id)]["settlement"] is None
    for private in (
        "winner_user_id",
        "winning_bid_sequence",
        "anchor_hmac",
        "final_hash",
        "receipt",
        "wallet",
        "email",
        str(ALICE),
    ):
        assert private not in str(body)
    assert snapshot(seeded) == before


@pytest.mark.parametrize("size", [1, 30, 101])
def test_query_count_is_constant_and_projection_omits_private_tables(
    owner, seeded, db_engine, size, monkeypatch, publication_spies
):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    for _ in range(size - 1):
        live_lot(seeded)
    before = snapshot(seeded)

    def forbidden(*args, **kwargs):
        pytest.fail("read called a settlement command or per-item reader")

    for name in ("settle_lot", "prepare_settlement", "read_settlement", "read_receipt"):
        monkeypatch.setattr(lot_settlement, name, forbidden)
    with statement_recorder(db_engine) as recorder:
        body, _ = results(owner.get(URL))
    assert len(body["items"]) == size
    business = [
        sql for sql in recorder.statements if "WITH clock AS MATERIALIZED" in sql
    ]
    assert len(business) == 1
    assert business[0].count("clock_timestamp()") == 1
    assert "anchor_hmac" not in business[0] and "wallet" not in business[0]
    assert (
        len(recorder.statements) == 2
    )  # fixed user authentication + one business statement
    assert all(
        sql.lstrip().upper().startswith(("SELECT", "WITH"))
        and "FOR UPDATE" not in sql.upper()
        for sql in recorder.statements
    )
    assert snapshot(seeded) == before


@pytest.mark.parametrize("condition", ["unsold_with_receipt", "orphan_receipt"])
def test_private_list_rejects_intrusive_or_orphan_receipt_without_repair(
    owner, seeded, db_engine, monkeypatch, publication_spies, condition
):
    healthy = sold_lot(seeded, amount=13_000)
    run_settle(seeded, healthy)
    if condition == "unsold_with_receipt":
        lot_id = unsold_lot(seeded)
        with seeded() as session:
            settlement_id = session.execute(
                text("SELECT id FROM lot_settlements WHERE lot_id=:id"), {"id": lot_id}
            ).scalar_one()
        target_table = "bids"
    else:
        lot_id = sold_lot(seeded, amount=13_000)
        settlement_id = uuid.uuid4()
        target_table = "lot_settlements"
    original = snapshot(seeded)

    def forbidden(*args, **kwargs):
        pytest.fail("private read attempted settlement or repair")

    for name in ("settle_lot", "prepare_settlement", "read_settlement", "read_receipt"):
        monkeypatch.setattr(lot_settlement, name, forbidden)
    with incompatible_receipt(
        seeded,
        db_engine,
        lot_id=lot_id,
        settlement_id=settlement_id,
        target_table=target_table,
    ) as receipt_id:
        before = snapshot(seeded)
        with statement_recorder(db_engine) as recorder:
            response = owner.get(URL)
        assert response.status_code == 409
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "status": 409,
            "code": "lot_integrity_conflict",
            "message": "Não foi possível concluir a operação porque a integridade "
            "do lote não pôde ser confirmada.",
        }
        for private in (
            str(lot_id),
            str(settlement_id),
            str(receipt_id),
            "Licitante-AAAAAAAAAAAAAAAA",
            "a" * 64,
            "items",
            "total_received_cents",
        ):
            assert private not in response.text
        assert snapshot(seeded) == before
        assert all(
            sql.lstrip().upper().startswith(("SELECT", "WITH"))
            and "FOR UPDATE" not in sql.upper()
            for sql in recorder.statements
        )
    assert snapshot(seeded) == original


@pytest.mark.parametrize(
    "change",
    [
        "DELETE FROM receipts WHERE lot_id=:id",
        "UPDATE receipts SET final_amount_cents=final_amount_cents+1 WHERE lot_id=:id",
        "UPDATE receipts SET winner_alias='Licitante-0000000000000000' "
        "WHERE lot_id=:id",
        "UPDATE lots SET cancelled_at=clock_timestamp() WHERE id=:id",
        "UPDATE lots SET bid_count=bid_count+1 WHERE id=:id",
        "UPDATE lots SET final_hash=repeat('a',64) WHERE id=:id",
        "UPDATE lots SET current_bid_cents=current_bid_cents+1 WHERE id=:id",
        "UPDATE lot_settlements SET settled_at=settled_at-interval '2 hours' "
        "WHERE lot_id=:id",
        "UPDATE lots SET ends_at=clock_timestamp()+interval '1 hour' WHERE id=:id",
    ],
)
def test_inconsistent_pair_or_lot_fails_entire_read_without_repair(
    owner, seeded, change, db_engine
):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    unsold_lot(seeded)
    tamper(seeded, change, id=lot_id)
    before = snapshot(seeded)
    with statement_recorder(db_engine) as recorder:
        response = owner.get(URL)
    assert response.status_code == 409
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": 409,
        "code": "lot_integrity_conflict",
        "message": "Não foi possível concluir a operação porque a integridade do lote "
        "não pôde ser confirmada.",
    }
    assert snapshot(seeded) == before
    assert all(
        "FOR UPDATE" not in sql and sql.lstrip().upper().startswith(("SELECT", "WITH"))
        for sql in recorder.statements
    )


def test_winner_pointer_mismatch_is_private_conflict(owner, seeded):
    from tests.settlement_support import BOB

    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    tamper(
        seeded,
        "UPDATE lot_settlements SET winner_user_id=:winner WHERE lot_id=:id",
        winner=BOB,
        id=lot_id,
    )
    response = owner.get(URL)
    assert response.status_code == 409 and str(BOB) not in response.text


def test_total_zero_and_maximum_and_overflow_fail_atomically(owner, seeded):
    assert results(owner.get(URL))[0]["total_received_cents"] == 0
    unsold_lot(seeded)
    assert results(owner.get(URL))[0]["total_received_cents"] == 0
    set_wallet(seeded, ALICE, MAX_CENTS)
    lot_id = sold_lot(seeded, amount=MAX_CENTS)
    run_settle(seeded, lot_id)
    body, _ = results(owner.get(URL))
    assert body["total_received_cents"] == MAX_CENTS
    # Another real sale would hit the seller wallet ceiling. The read aggregate has
    # its own guard, tested after an explicit test-only wallet reset.
    set_wallet(seeded, DEMO_AUCTIONEER_ID, 0)
    set_wallet(seeded, ALICE, 1)
    second = sold_lot(seeded, amount=1)
    run_settle(seeded, second)
    before = snapshot(seeded)
    response = owner.get(URL)
    assert response.status_code == 409
    assert "total_received_cents" not in response.text
    assert snapshot(seeded) == before


def test_read_does_not_block_on_a_held_lot_lock(seeded):
    lot_id = live_lot(seeded)
    with seeded() as writer, seeded() as reader:
        writer.execute(select(Lot).where(Lot.id == lot_id).with_for_update()).one()
        reader.execute(text("SET LOCAL statement_timeout = '500ms'"))
        result = read_my_lots_snapshot(reader, DEMO_AUCTIONEER_ID)
        assert isinstance(result, MyLotsResponse) and len(result.items) == 1


def test_commit_during_statement_is_seen_only_in_next_snapshot(
    owner, seeded, db_engine
):
    lot_id = sold_lot(seeded, amount=13_000)
    fired = False

    def after_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal fired
        if not fired and "WITH clock AS MATERIALIZED" in statement:
            fired = True
            run_settle(seeded, lot_id)

    event.listen(db_engine, "after_cursor_execute", after_execute)
    try:
        old, items = results(owner.get(URL))
    finally:
        event.remove(db_engine, "after_cursor_execute", after_execute)
    assert fired
    assert old["total_received_cents"] == 0 and items[str(lot_id)]["settlement"] is None
    new, items = results(owner.get(URL))
    assert (
        new["total_received_cents"] == 13_000
        and items[str(lot_id)]["settlement"]["outcome"] == "sold"
    )


def test_operational_error_is_generic_no_store(owner, monkeypatch):
    def fail(*args):
        raise RuntimeError("PRIVATE SQL / WINNER / HMAC")

    monkeypatch.setattr(lots, "read_my_lots_snapshot", fail)
    response = owner.get(URL)
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {"status", "code", "message"}
    assert (
        "PRIVATE" not in response.text and response.json()["code"] == "internal_error"
    )


def test_bidder_and_anonymous_never_execute_business_read(
    monkeypatch, seeded, db_engine
):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    for email, status in ((None, 401), (BIDDER_EMAIL, 403)):
        client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
        if email:
            assert login(client, HTTPS_ORIGIN, email).status_code == 200
        with statement_recorder(db_engine) as recorder:
            response = client.get(URL)
        assert (
            response.status_code == status
            and response.headers["cache-control"] == "no-store"
        )
        assert not any(
            "lot_settlements" in sql or "receipts" in sql for sql in recorder.statements
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("final_amount_cents", True),
        ("final_amount_cents", 1.1),
        ("final_amount_cents", "13000"),
        ("final_amount_cents", MAX_CENTS + 1),
        ("bid_count", True),
        ("bid_count", -1),
        ("winner_alias", "person@example.com"),
        ("settled_at", datetime(2026, 10, 28)),
    ],
)
def test_summary_strict_types_and_ranges(field, value):
    data = dict(
        outcome="sold",
        winner_alias="Licitante-0123456789ABCDEF",
        final_amount_cents=13_000,
        bid_count=1,
        settled_at=datetime(2026, 10, 28, tzinfo=UTC),
    )
    data[field] = value
    with pytest.raises(ValidationError):
        PrivateLotSettlementSummary(**data)
