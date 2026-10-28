"""Real PostgreSQL fixtures and complete settlement snapshots (Story 4.3)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.bids import PlacedBid
from app.lot_settlement import settle_lot
from tests.auth_support import BIDDER_EMAIL, OTHER_BIDDER_EMAIL, seeded_id
from tests.bid_support import integrity, live_lot, run_bid, tamper
from tests.lot_support import db_now
from tests.wallet_support import seed_users_with_wallets, set_wallet

ALICE = seeded_id(BIDDER_EMAIL)
BOB = seeded_id(OTHER_BIDDER_EMAIL)


@pytest.fixture
def seeded(db_session_factory: sessionmaker[Session], clean_users: None):
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, 80_000)
    set_wallet(db_session_factory, BOB, 80_000)
    return db_session_factory


def expire(factory, lot_id):
    tamper(
        factory,
        "UPDATE lots SET ends_at=:end WHERE id=:id",
        end=db_now(factory) - timedelta(seconds=1),
        id=lot_id,
    )


def sold_lot(factory, amount=12_000, bidder_id=ALICE):
    lot_id = live_lot(factory, starting_bid_cents=amount)
    assert isinstance(run_bid(factory, lot_id, bidder_id, amount), PlacedBid)
    expire(factory, lot_id)
    return lot_id


def run_settle(factory, lot_id):
    return settle_lot(factory, lot_id=lot_id, integrity=integrity())


def snapshot(factory):
    with factory() as session:
        return tuple(
            tuple(tuple(row) for row in session.execute(text(sql)))
            for sql in (
                "SELECT * FROM lots ORDER BY id",
                "SELECT * FROM bids ORDER BY lot_id, sequence",
                "SELECT * FROM wallets ORDER BY user_id",
                "SELECT * FROM lot_settlements ORDER BY lot_id",
                "SELECT * FROM receipts ORDER BY lot_id",
            )
        )


def counts(factory, lot_id: uuid.UUID):
    with factory() as session:
        return tuple(
            session.execute(text(sql), {"id": lot_id}).scalar_one()
            for sql in (
                "SELECT count(*) FROM lot_settlements WHERE lot_id=:id",
                "SELECT count(*) FROM receipts WHERE lot_id=:id",
            )
        )
