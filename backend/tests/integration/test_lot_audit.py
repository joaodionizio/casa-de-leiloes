"""Audit guarantees exercised against PostgreSQL, never a simulated history."""

import uuid

# Imported pytest fixtures are intentionally shadowed by test parameters.
# ruff: noqa: F811
from datetime import timedelta

import pytest

from app import lot_audit
from app.bids import PlacedBid
from tests.auth_support import HTTPS_ORIGIN, build_client
from tests.bid_support import (
    bid_rows,
    drop_checks,  # noqa: F401
    integrity,
    live_lot,
    run_bid,
    statement_log,
    tamper,
)
from tests.integration import test_bid_integrity_gate as gates
from tests.lot_support import db_now
from tests.settlement_support import (
    ALICE,
    BOB,
    expire,
    run_settle,
    seeded,  # noqa: F401
    snapshot,
    sold_lot,
)


@pytest.fixture
def client(monkeypatch, seeded):
    return build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)


def get(client, lot_id):
    response = client.get(f"/api/lots/{lot_id}/audit")
    assert response.headers["cache-control"] == "no-store"
    return response


def assert_retained(data, lot_id):
    assert data == {
        "lot_id": str(lot_id),
        "as_of": data["as_of"],
        "integrity": "adulterated",
        "phase": None,
        "settlement_status": None,
        "settlement": None,
        "bid_count": None,
        "final_hash": None,
        "bids": [],
    }


@pytest.mark.parametrize(
    "state", ["scheduled", "live", "expired", "sold", "unsold", "cancelled"]
)
def test_public_state_matrix_and_read_purity(client, seeded, db_engine, state):
    lot_id = sold_lot(seeded) if state == "sold" else live_lot(seeded)
    if state == "scheduled":
        tamper(
            seeded,
            "UPDATE lots SET starts_at=:start, ends_at=:end WHERE id=:id",
            start=db_now(seeded) + timedelta(hours=1),
            end=db_now(seeded) + timedelta(hours=2),
            id=lot_id,
        )
    if state in ("expired", "unsold"):
        expire(seeded, lot_id)
    if state in ("sold", "unsold"):
        run_settle(seeded, lot_id)
    if state == "cancelled":
        tamper(
            seeded,
            "UPDATE lots SET cancelled_at=:now WHERE id=:id",
            now=db_now(seeded),
            id=lot_id,
        )
    before = snapshot(seeded)
    with statement_log(db_engine) as log:
        response = get(client, lot_id)
    assert response.status_code == 200
    data = response.json()
    assert data["integrity"] == "verified"
    assert data["phase"] == (
        "ended" if state in ("expired", "sold", "unsold") else state
    )
    assert data["settlement_status"] == (
        "settled"
        if state in ("sold", "unsold")
        else "not_applicable"
        if state == "cancelled"
        else "pending"
    )
    assert (data["settlement"] or {}).get("outcome") == (
        state if state in ("sold", "unsold") else None
    )
    assert len(log.statements) == 1
    sql = log.statements[0].upper()
    assert "FOR UPDATE" not in sql and "WALLETS" not in sql and "USERS" not in sql
    assert snapshot(seeded) == before


def test_complete_history_public_projection_and_persisted_aliases(
    client, seeded, db_engine
):
    lot_id = live_lot(seeded, starting_bid_cents=10, min_increment_cents=1)
    for index in range(100):
        assert isinstance(
            run_bid(seeded, lot_id, ALICE if index % 2 == 0 else BOB, 10 + index),
            PlacedBid,
        )
    # Rotating pseudonym configuration must not change or invalidate persisted aliases.
    from app.config import IntegrityConfig
    from app.lots import get_integrity_config

    client.app.dependency_overrides[get_integrity_config] = lambda: IntegrityConfig(
        audit_hmac_secret=integrity().audit_hmac_secret,
        pseudonym_secret=b"different-pseudonym-key-for-test-only",
    )
    client.app.state.artic_client = object()  # no external catalog capability
    with statement_log(db_engine) as log:
        response = get(client, lot_id)
    assert len(log.statements) == 1
    data = response.json()
    rows = bid_rows(seeded, lot_id)
    assert data["integrity"] == "verified" and len(data["bids"]) == 100
    for actual, row in zip(data["bids"], rows, strict=True):
        assert set(actual) == set(lot_audit.PublicAuditBid.model_fields)
        for key in actual:
            if key == "placed_at":
                from datetime import datetime

                assert datetime.fromisoformat(actual[key]) == row[key]
            else:
                assert actual[key] == row[key]
    assert data["final_hash"] == rows[-1]["current_hash"]
    assert str(ALICE) not in response.text and str(BOB) not in response.text
    assert "bidder_id" not in response.text and "anchor_hmac" not in response.text


@pytest.mark.parametrize("attack", ["g1", "g13", "g20", "g4", "g2", "g10", "g9_filled"])
def test_sql_tampering_withholds_every_untrusted_field(
    client, seeded, db_engine, attack
):
    lot_id = gates.chained_lot(seeded)
    case = gates.Case(seeded, lot_id, lambda *args: pytest.fail("unexpected DDL"))
    getattr(gates, attack)(case)
    before = snapshot(seeded)
    with statement_log(db_engine) as log:
        assert_retained(get(client, lot_id).json(), lot_id)
    assert len(log.statements) == 1 and snapshot(seeded) == before


@pytest.mark.parametrize(
    "table,change",
    [
        ("lot_settlements", "winner_user_id=:other"),
        ("lot_settlements", "anchor_hmac=repeat('a',64)"),
        ("lot_settlements", "settled_at=settled_at-interval '1 day'"),
        ("receipts", "final_amount_cents=final_amount_cents+1"),
    ],
)
def test_settlement_and_receipt_conflicts_are_withheld(client, seeded, table, change):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    tamper(
        seeded, f"UPDATE {table} SET {change} WHERE lot_id=:id", id=lot_id, other=BOB
    )
    before = snapshot(seeded)
    assert_retained(get(client, lot_id).json(), lot_id)
    assert snapshot(seeded) == before


def test_injected_private_alias_is_never_serialized(client, seeded, drop_checks):
    lot_id = gates.chained_lot(seeded)
    drop_checks("ck_bids_bidder_alias_format")
    tamper(
        seeded,
        "UPDATE bids SET bidder_alias='private@example.com' "
        "WHERE lot_id=:id AND sequence=1",
        id=lot_id,
    )
    response = get(client, lot_id)
    assert "private@example.com" not in response.text
    assert_retained(response.json(), lot_id)


def test_missing_invalid_uuid_and_operational_failure(client, monkeypatch):
    assert get(client, uuid.uuid4()).status_code == 404
    assert client.get("/api/lots/not-a-uuid/audit").status_code == 422

    def fail(*args):
        raise RuntimeError("synthetic database outage")

    monkeypatch.setattr(lot_audit, "read_audit", fail)
    response = get(client, uuid.uuid4())
    assert response.status_code == 500 and "integrity" not in response.text


def test_empty_legacy_anchor_is_not_trusted(client, seeded):
    lot_id = live_lot(seeded)
    tamper(seeded, "UPDATE lots SET anchor_hmac=NULL WHERE id=:id", id=lot_id)
    before = snapshot(seeded)
    assert_retained(get(client, lot_id).json(), lot_id)
    assert snapshot(seeded) == before


def test_dirty_caller_session_never_autoflushes(seeded, db_engine):
    from app.wallet import Wallet

    lot_id = live_lot(seeded)
    before = snapshot(seeded)
    with seeded() as session:
        wallet = session.get(Wallet, ALICE)
        wallet.total_balance_cents += 1
        with statement_log(db_engine) as log:
            assert (
                lot_audit.read_audit(session, lot_id, integrity()).integrity
                == "verified"
            )
        assert len(log.statements) == 1
        assert "UPDATE" not in log.statements[0].upper()
        session.rollback()
    assert snapshot(seeded) == before
