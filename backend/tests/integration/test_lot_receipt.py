"""Public receipt contract against persisted PostgreSQL state."""

import uuid

# ruff: noqa: F811
from datetime import datetime, timedelta

import pytest

from app.lot_settlement import Receipt
from tests.auth_support import HTTPS_ORIGIN, build_client
from tests.bid_support import live_lot, statement_log, tamper
from tests.lot_support import db_now
from tests.settlement_support import (
    ALICE,
    BOB,
    expire,
    run_settle,
    seeded,  # noqa: F401
    snapshot,
    sold_lot,
)  # noqa: F401


@pytest.fixture
def client(monkeypatch, seeded):
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    client.app.state.artic_client = object()
    return client


def test_sold_public_receipt_is_persisted_private_and_read_only(
    client, seeded, db_engine
):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    with seeded() as session:
        receipt = session.query(Receipt).filter_by(lot_id=lot_id).one()
        expected = {
            name: getattr(receipt, name)
            for name in (
                "winner_alias",
                "final_amount_cents",
                "settled_at",
                "bid_count",
                "final_hash",
                "winning_bid_sequence",
            )
        }
    before = snapshot(seeded)
    with statement_log(db_engine) as log:
        response = client.get(f"/api/lots/{lot_id}/receipt")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert set(data) == {"lot_id", "title", "artist_display", "image_url", *expected}
    for key, value in expected.items():
        assert (
            datetime.fromisoformat(data[key]) if key == "settled_at" else data[key]
        ) == value
    for forbidden in (
        "winner_user_id",
        "email",
        "wallet",
        "hmac",
        "committed",
        str(ALICE),
        str(BOB),
    ):
        assert forbidden not in response.text.lower()
    assert len(log.statements) == 1
    assert all(
        term not in log.statements[0].upper()
        for term in ("FOR UPDATE", "WALLETS", "USERS")
    )
    assert snapshot(seeded) == before


@pytest.mark.parametrize(
    "state", ["pending", "scheduled", "expired", "unsold", "cancelled"]
)
def test_no_receipt(client, seeded, state):
    lot_id = live_lot(seeded)
    if state == "scheduled":
        now = db_now(seeded)
        tamper(
            seeded,  # noqa: F401
            "UPDATE lots SET starts_at=:start, ends_at=:end WHERE id=:id",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            id=lot_id,
        )
    if state in ("expired", "unsold"):
        expire(seeded, lot_id)
    if state == "unsold":
        run_settle(seeded, lot_id)
    if state == "cancelled":
        tamper(
            seeded,  # noqa: F401
            "UPDATE lots SET cancelled_at=:now WHERE id=:id",
            now=db_now(seeded),
            id=lot_id,
        )
    before = snapshot(seeded)
    assert client.get(f"/api/lots/{lot_id}/receipt").status_code == 404
    assert snapshot(seeded) == before


def test_inconsistent_receipt_fails_without_repair(client, seeded):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    tamper(
        seeded,  # noqa: F401
        "UPDATE receipts SET final_amount_cents=final_amount_cents+1 WHERE lot_id=:id",
        id=lot_id,
    )
    before = snapshot(seeded)
    response = client.get(f"/api/lots/{lot_id}/receipt")
    assert response.status_code == 409
    assert "winner_alias" not in response.text
    assert snapshot(seeded) == before


def test_missing_and_invalid(client):
    assert client.get(f"/api/lots/{uuid.uuid4()}/receipt").status_code == 404
    assert client.get("/api/lots/invalid/receipt").status_code == 422
