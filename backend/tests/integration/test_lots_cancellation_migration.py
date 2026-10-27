"""A migration `0006` no PostgreSQL real (Story 3.6, T1): `lots.cancelled_at`, aditiva,
sem default, sem backfill, sem CHECK nem índice novos, com `downgrade` simétrico."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.seed import DEMO_AUCTIONEER_ID
from tests.auth_support import seed_demo_users
from tests.bid_support import lot_state
from tests.conftest import alembic_config
from tests.lot_support import IMAGE_ID, LOT_COLUMNS, insert_lot

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_demo_users(db_session_factory)
    return db_session_factory


@pytest.fixture
def back_at_head(test_database_url: str, db_engine: Engine) -> Iterator[None]:
    yield
    command.upgrade(alembic_config(test_database_url), "head")
    db_engine.dispose()


def test_cancelled_at_is_a_nullable_timestamptz_without_a_default(
    db_engine: Engine,
) -> None:
    assert LOT_COLUMNS[-1] == "cancelled_at"
    with db_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'lots' AND column_name = 'cancelled_at' "
                "AND table_schema = 'public'"
            )
        ).one()
    assert tuple(row) == ("timestamp with time zone", "YES", None)


def test_the_migration_adds_no_check_foreign_key_or_index(db_engine: Engine) -> None:
    inspector = inspect(db_engine)
    assert not any(
        "cancelled" in (check["sqltext"] or "")
        for check in inspector.get_check_constraints("lots")
    )
    assert all(
        "cancelled_at" not in index["column_names"]
        for index in inspector.get_indexes("lots")
    )
    assert [fk["name"] for fk in inspector.get_foreign_keys("lots")] == [
        "fk_lots_auctioneer_id_users",
        "fk_lots_current_leader_id_users",
    ]


def test_new_lots_start_uncancelled(seeded: sessionmaker[Session]) -> None:
    lot_id = insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID)

    assert lot_state(seeded, lot_id)["cancelled_at"] is None


def test_existing_lots_stay_uncancelled_and_downgrade_removes_only_the_column(
    test_database_url: str,
    db_engine: Engine,
    seeded: sessionmaker[Session],
    back_at_head: None,
) -> None:
    config = alembic_config(test_database_url)
    command.downgrade(config, "0005")
    db_engine.dispose()
    legacy = uuid.uuid4()
    with db_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO lots (id, auctioneer_id, external_id, image_id, "
                "source_url, starting_bid_cents, min_increment_cents, starts_at, "
                "ends_at, created_at) VALUES (:id, :a, 27992, :image, "
                "'https://www.artic.edu/x', 10000, 1000, :s, :e, :c)"
            ),
            {
                "id": legacy,
                "a": DEMO_AUCTIONEER_ID,
                "image": IMAGE_ID,
                "s": NOW,
                "e": NOW + timedelta(days=1),
                "c": NOW,
            },
        )
    inspector = inspect(db_engine)
    assert [c["name"] for c in inspector.get_columns("lots")] == LOT_COLUMNS[:-1]
    assert "bids" in inspector.get_table_names()  # a 0005 fica intacta

    command.upgrade(config, "head")
    db_engine.dispose()

    assert lot_state(seeded, legacy)["cancelled_at"] is None  # sem backfill
    assert [c["name"] for c in inspect(db_engine).get_columns("lots")] == LOT_COLUMNS
