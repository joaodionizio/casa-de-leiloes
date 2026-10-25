"""A migration `0003` cria e remove `lots` no PostgreSQL real (Story 2.4, CAP-4, CAP-11,
A4). Dinheiro sempre como parâmetro inteiro, nunca `float`."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.lots import MAX_CENTS
from app.seed import DEMO_AUCTIONEER_ID
from tests.conftest import alembic_config
from tests.lot_support import IMAGE_ID, LOT_COLUMNS

INSERT_USER = text(
    "INSERT INTO users (id, email, password_hash, role) "
    "VALUES (:id, :email, 'hash', 'AUCTIONEER')"
)
INSERT_LOT = text(
    "INSERT INTO lots (id, auctioneer_id, external_id, image_id, source_url, "
    "starting_bid_cents, min_increment_cents, starts_at, ends_at, created_at) "
    "VALUES (:id, :auctioneer_id, :external_id, :image_id, :source_url, "
    ":starting_bid_cents, :min_increment_cents, :starts_at, :ends_at, :created_at)"
)
NOW = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def owner(db_engine: Engine, clean_users: None) -> uuid.UUID:
    with db_engine.begin() as connection:
        connection.execute(
            INSERT_USER, {"id": DEMO_AUCTIONEER_ID, "email": "dono@example.com"}
        )
    return DEMO_AUCTIONEER_ID


def lot_row(owner: uuid.UUID, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": uuid.uuid4(),
        "auctioneer_id": owner,
        "external_id": 27992,
        "image_id": IMAGE_ID,
        "source_url": "https://www.artic.edu/artworks/27992",
        "starting_bid_cents": 10000,
        "min_increment_cents": 1000,
        "starts_at": NOW,
        "ends_at": NOW + timedelta(days=1),
        "created_at": NOW,
    }
    row.update(overrides)
    return row


def insert(engine: Engine, row: dict[str, Any]) -> None:
    with engine.begin() as connection:
        connection.execute(INSERT_LOT, row)


def constraint_name_in(error: IntegrityError) -> str:
    return str(error.value.orig)


# --- estrutura ---


def test_lots_table_has_the_agreed_columns_types_and_nullability(
    db_engine: Engine,
) -> None:
    inspector = inspect(db_engine)
    columns = {column["name"]: column for column in inspector.get_columns("lots")}

    assert list(columns) == LOT_COLUMNS
    text_columns = [
        "title",
        "artist_display",
        "date_display",
        "medium_display",
        "dimensions",
        "department_title",
        "artwork_type_title",
        "credit_line",
    ]
    for name in LOT_COLUMNS:
        assert columns[name]["nullable"] is (name in text_columns), name
    # Os tipos reais, como o PostgreSQL os guarda, estão no teste seguinte.


def test_real_postgresql_column_types(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT column_name, data_type, character_maximum_length "
                "FROM information_schema.columns WHERE table_name = 'lots' "
                "AND table_schema = 'public'"
            )
        ).all()
    types = {name: (data_type, length) for name, data_type, length in rows}

    assert sorted(types) == sorted(LOT_COLUMNS)
    for name in (
        "title",
        "artist_display",
        "date_display",
        "medium_display",
        "dimensions",
        "department_title",
        "artwork_type_title",
        "credit_line",
        "source_url",
    ):
        assert types[name] == ("text", None), name
    assert types["image_id"] == ("character varying", 36)
    assert types["external_id"] == ("integer", None)
    assert types["starting_bid_cents"] == ("bigint", None)
    assert types["min_increment_cents"] == ("bigint", None)
    for name in ("starts_at", "ends_at", "created_at"):
        assert types[name] == ("timestamp with time zone", None), name
    assert types["id"] == ("uuid", None)
    assert types["auctioneer_id"] == ("uuid", None)
    assert types["is_demo"] == ("boolean", None)


def test_defaults_names_and_foreign_key(db_engine: Engine) -> None:
    inspector = inspect(db_engine)
    columns = {column["name"]: column for column in inspector.get_columns("lots")}

    assert "false" in str(columns["is_demo"]["default"])
    assert columns["id"]["default"] is None
    assert columns["created_at"]["default"] is None
    assert inspector.get_pk_constraint("lots")["name"] == "pk_lots"
    assert sorted(c["name"] for c in inspector.get_check_constraints("lots")) == [
        "ck_lots_ends_after_starts",
        "ck_lots_external_id_positive",
        "ck_lots_image_id_format",
        "ck_lots_min_increment_range",
        "ck_lots_starting_bid_range",
    ]
    assert [index["name"] for index in inspector.get_indexes("lots")] == [
        "ix_lots_auctioneer_id"
    ]
    (foreign_key,) = inspector.get_foreign_keys("lots")
    assert foreign_key["name"] == "fk_lots_auctioneer_id_users"
    assert foreign_key["referred_table"] == "users"
    assert foreign_key["constrained_columns"] == ["auctioneer_id"]
    assert foreign_key["options"].get("ondelete") == "RESTRICT"
    # P7: a mesma obra pode originar vários lotes.
    assert inspector.get_unique_constraints("lots") == []


# --- FK ---


def test_unknown_auctioneer_is_refused(db_engine: Engine, owner: uuid.UUID) -> None:
    with pytest.raises(IntegrityError) as error:
        insert(db_engine, lot_row(uuid.uuid4()))
    assert "fk_lots_auctioneer_id_users" in constraint_name_in(error)


def test_deleting_a_user_that_owns_a_lot_is_refused(
    db_engine: Engine, owner: uuid.UUID
) -> None:
    insert(db_engine, lot_row(owner))
    with pytest.raises(IntegrityError) as error:
        with db_engine.begin() as connection:
            connection.execute(text("DELETE FROM users"))
    assert "fk_lots_auctioneer_id_users" in constraint_name_in(error)


# --- dinheiro (A4) ---


@pytest.mark.parametrize(
    ("column", "constraint"),
    [
        ("starting_bid_cents", "ck_lots_starting_bid_range"),
        ("min_increment_cents", "ck_lots_min_increment_range"),
    ],
)
def test_money_range_in_the_database(
    db_engine: Engine, owner: uuid.UUID, column: str, constraint: str
) -> None:
    # Dentro da faixa: o mínimo e o máximo exatos.
    insert(db_engine, lot_row(owner, **{column: 1}))
    insert(db_engine, lot_row(owner, **{column: MAX_CENTS}))
    # Fora: zero, negativo e máximo + 1.
    for value in (0, -1, MAX_CENTS + 1):
        with pytest.raises(IntegrityError) as error:
            insert(db_engine, lot_row(owner, **{column: value}))
        assert constraint in constraint_name_in(error)


def test_money_check_literal_matches_the_application_limit(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        definitions = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname IN ('ck_lots_starting_bid_range', "
                "'ck_lots_min_increment_range')"
            )
        ).all()
    assert len(definitions) == 2
    assert MAX_CENTS == 2**53 - 1 == 9007199254740991
    for _, definition in definitions:
        assert str(MAX_CENTS) in definition


# --- tempo e snapshot ---


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(seconds=-1)])
def test_end_must_be_after_start(
    db_engine: Engine, owner: uuid.UUID, delta: timedelta
) -> None:
    with pytest.raises(IntegrityError) as error:
        insert(db_engine, lot_row(owner, ends_at=NOW + delta))
    assert "ck_lots_ends_after_starts" in constraint_name_in(error)


def test_one_microsecond_after_start_is_accepted(
    db_engine: Engine, owner: uuid.UUID
) -> None:
    insert(db_engine, lot_row(owner, ends_at=NOW + timedelta(microseconds=1)))


def test_external_id_must_be_positive(db_engine: Engine, owner: uuid.UUID) -> None:
    with pytest.raises(IntegrityError) as error:
        insert(db_engine, lot_row(owner, external_id=0))
    assert "ck_lots_external_id_positive" in constraint_name_in(error)


@pytest.mark.parametrize(
    "image_id",
    ["../evil", IMAGE_ID.upper(), "", IMAGE_ID[:-1] + "g", " " + IMAGE_ID[1:]],
)
def test_image_id_must_match_the_iiif_identifier_format(
    db_engine: Engine, owner: uuid.UUID, image_id: str
) -> None:
    with pytest.raises(IntegrityError) as error:
        insert(db_engine, lot_row(owner, image_id=image_id))
    assert "ck_lots_image_id_format" in constraint_name_in(error)


def test_same_artwork_can_become_many_lots(db_engine: Engine, owner: uuid.UUID) -> None:
    insert(db_engine, lot_row(owner))
    insert(db_engine, lot_row(owner))
    with db_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM lots")).scalar_one() == 2


def test_optional_texts_may_be_null_but_required_snapshot_fields_may_not(
    db_engine: Engine, owner: uuid.UUID
) -> None:
    insert(db_engine, lot_row(owner))  # title & co. ausentes → NULL
    for column in ("source_url", "image_id"):
        with pytest.raises(IntegrityError):
            insert(db_engine, lot_row(owner, **{column: None}))


def test_is_demo_defaults_to_false(db_engine: Engine, owner: uuid.UUID) -> None:
    insert(db_engine, lot_row(owner))
    with db_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT is_demo FROM lots")).scalar_one() is False
        )


# --- downgrade ---


@pytest.fixture
def back_at_head(test_database_url: str, db_engine: Engine) -> Iterator[None]:
    yield
    command.upgrade(alembic_config(test_database_url), "head")
    db_engine.dispose()


def test_downgrade_removes_lots_and_keeps_users(
    test_database_url: str, db_engine: Engine, back_at_head: None
) -> None:
    config = alembic_config(test_database_url)

    command.downgrade(config, "0002")
    db_engine.dispose()
    tables = inspect(db_engine).get_table_names()
    assert "lots" not in tables
    assert "users" in tables

    command.upgrade(config, "head")
    db_engine.dispose()
    assert "lots" in inspect(db_engine).get_table_names()
