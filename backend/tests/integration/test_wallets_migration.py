"""A migration `0004` cria e remove `wallets` no PostgreSQL real (Story 3.1, CAP-1,
CAP-2, CAP-3). Dinheiro sempre como parâmetro inteiro, nunca `float`."""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.money import MAX_CENTS
from tests.conftest import alembic_config

INSERT_USER = text(
    "INSERT INTO users (id, email, password_hash, role) "
    "VALUES (:id, :email, 'hash', :role)"
)
INSERT_WALLET = text(
    "INSERT INTO wallets (user_id, total_balance_cents, committed_balance_cents) "
    "VALUES (:user_id, :total, :committed)"
)
COLUMNS = ["user_id", "total_balance_cents", "committed_balance_cents"]


def add_user(engine: Engine, role: str = "BIDDER") -> uuid.UUID:
    user_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            INSERT_USER,
            {"id": user_id, "email": f"{user_id}@example.com", "role": role},
        )
    return user_id


def add_wallet(
    engine: Engine, user_id: uuid.UUID, total: int = 0, committed: int = 0
) -> None:
    with engine.begin() as connection:
        connection.execute(
            INSERT_WALLET, {"user_id": user_id, "total": total, "committed": committed}
        )


def refusal_of(error: pytest.ExceptionInfo[IntegrityError]) -> str:
    return str(error.value.orig)


@pytest.fixture
def bidder(db_engine: Engine, clean_users: None) -> uuid.UUID:
    return add_user(db_engine)


# --- estrutura ---


def test_wallets_has_exactly_the_agreed_columns(db_engine: Engine) -> None:
    columns = {c["name"]: c for c in inspect(db_engine).get_columns("wallets")}

    assert list(columns) == COLUMNS
    for forbidden in ("id", "available_balance_cents", "created_at", "updated_at"):
        assert forbidden not in columns
    assert all(column["nullable"] is False for column in columns.values())


def test_real_postgresql_column_types_and_defaults(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_name = 'wallets' "
                "AND table_schema = 'public'"
            )
        ).all()
    columns = {
        name: (data_type, nullable, default)
        for name, data_type, nullable, default in rows
    }

    assert columns["user_id"] == ("uuid", "NO", None)
    assert columns["total_balance_cents"] == ("bigint", "NO", "0")
    assert columns["committed_balance_cents"] == ("bigint", "NO", "0")


def test_constraint_names_and_foreign_key(db_engine: Engine) -> None:
    inspector = inspect(db_engine)

    assert inspector.get_pk_constraint("wallets")["name"] == "pk_wallets"
    assert inspector.get_pk_constraint("wallets")["constrained_columns"] == ["user_id"]
    assert sorted(c["name"] for c in inspector.get_check_constraints("wallets")) == [
        "ck_wallets_committed_range",
        "ck_wallets_committed_within_total",
        "ck_wallets_total_range",
    ]
    assert inspector.get_indexes("wallets") == []
    (foreign_key,) = inspector.get_foreign_keys("wallets")
    assert foreign_key["name"] == "fk_wallets_user_id_users"
    assert foreign_key["referred_table"] == "users"
    assert foreign_key["constrained_columns"] == ["user_id"]
    assert foreign_key["options"].get("ondelete") == "RESTRICT"


def test_a_new_wallet_defaults_to_zero_and_zero(
    db_engine: Engine, bidder: uuid.UUID
) -> None:
    with db_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO wallets (user_id) VALUES (:id)"), {"id": bidder}
        )
        row = connection.execute(
            text("SELECT total_balance_cents, committed_balance_cents FROM wallets")
        ).one()
    assert tuple(row) == (0, 0)


# --- identidade (P1) ---


def test_unknown_user_is_refused(db_engine: Engine, clean_users: None) -> None:
    with pytest.raises(IntegrityError) as error:
        add_wallet(db_engine, uuid.uuid4())
    assert "fk_wallets_user_id_users" in refusal_of(error)


def test_a_second_wallet_for_the_same_user_is_refused(
    db_engine: Engine, bidder: uuid.UUID
) -> None:
    add_wallet(db_engine, bidder)
    with pytest.raises(IntegrityError) as error:
        add_wallet(db_engine, bidder)
    assert "pk_wallets" in refusal_of(error)


def test_deleting_a_user_that_has_a_wallet_is_refused(
    db_engine: Engine, bidder: uuid.UUID
) -> None:
    add_wallet(db_engine, bidder)
    with pytest.raises(IntegrityError) as error:
        with db_engine.begin() as connection:
            connection.execute(text("DELETE FROM users"))
    assert "fk_wallets_user_id_users" in refusal_of(error)


# --- invariantes no PostgreSQL (AD-3, P3) ---


# O PostgreSQL informa a primeira CHECK que falha, e algumas linhas violam mais de uma
# (um total negativo também deixa `committed > total`). Por isso cada caso lista as
# CHECKs aceitáveis, todas ligadas à regra violada.
TOTAL_RANGE = "ck_wallets_total_range"
COMMITTED_RANGE = "ck_wallets_committed_range"
WITHIN_TOTAL = "ck_wallets_committed_within_total"


@pytest.mark.parametrize(
    ("total", "committed", "constraints"),
    [
        (-1, 0, {TOTAL_RANGE, WITHIN_TOTAL}),
        (MAX_CENTS + 1, 0, {TOTAL_RANGE}),
        (0, -1, {COMMITTED_RANGE}),
        (MAX_CENTS + 1, MAX_CENTS + 1, {TOTAL_RANGE, COMMITTED_RANGE}),
        (5, 6, {WITHIN_TOTAL}),
    ],
)
def test_an_insert_that_breaks_an_invariant_is_refused_by_name(
    db_engine: Engine,
    bidder: uuid.UUID,
    total: int,
    committed: int,
    constraints: set[str],
) -> None:
    with pytest.raises(IntegrityError) as error:
        add_wallet(db_engine, bidder, total, committed)
    assert any(name in refusal_of(error) for name in constraints)


@pytest.mark.parametrize(
    ("total", "committed"),
    [(0, 0), (5, 5), (5, 0), (MAX_CENTS, 0), (MAX_CENTS, MAX_CENTS)],
)
def test_the_boundaries_are_accepted(
    db_engine: Engine, bidder: uuid.UUID, total: int, committed: int
) -> None:
    add_wallet(db_engine, bidder, total, committed)


def test_the_committed_ceiling_is_enforced_on_its_own_column(
    db_engine: Engine, bidder: uuid.UUID
) -> None:
    # Com `committed <= total` e o teto do total, o comprometido nunca passaria do
    # teto sozinho pela CHECK relativa. A CHECK própria existe e tem o literal certo.
    with db_engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_wallets_committed_range'"
            )
        ).scalar_one()
    assert str(MAX_CENTS) in definition


@pytest.mark.parametrize(
    ("column", "value", "constraints"),
    [
        ("total_balance_cents", -1, {TOTAL_RANGE, WITHIN_TOTAL}),
        ("total_balance_cents", MAX_CENTS + 1, {TOTAL_RANGE}),
        ("committed_balance_cents", -1, {COMMITTED_RANGE}),
        ("committed_balance_cents", 1, {WITHIN_TOTAL}),
    ],
)
def test_an_update_that_breaks_an_invariant_is_refused(
    db_engine: Engine,
    bidder: uuid.UUID,
    column: str,
    value: int,
    constraints: set[str],
) -> None:
    add_wallet(db_engine, bidder)
    with pytest.raises(IntegrityError) as error:
        with db_engine.begin() as connection:
            connection.execute(
                text(f"UPDATE wallets SET {column} = :v"),  # noqa: S608
                {"v": value},
            )
    assert any(name in refusal_of(error) for name in constraints)


def test_committed_may_equal_total_after_an_update(
    db_engine: Engine, bidder: uuid.UUID
) -> None:
    add_wallet(db_engine, bidder, 100, 0)
    with db_engine.begin() as connection:
        connection.execute(text("UPDATE wallets SET committed_balance_cents = 100"))


# --- um limite só (A4, P3) ---


def test_every_money_check_literal_matches_the_application_limit(
    db_engine: Engine,
) -> None:
    names = (
        "ck_lots_starting_bid_range",
        "ck_lots_min_increment_range",
        "ck_wallets_total_range",
        "ck_wallets_committed_range",
    )
    with db_engine.connect() as connection:
        definitions = dict(
            connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = ANY(:names)"
                ),
                {"names": list(names)},
            ).all()
        )
    assert sorted(definitions) == sorted(names)
    assert MAX_CENTS == 2**53 - 1 == 9007199254740991
    for name, definition in definitions.items():
        assert str(MAX_CENTS) in definition, name


# --- cenário A: banco já existente (backfill) ---


@pytest.fixture
def back_at_head(test_database_url: str, db_engine: Engine) -> Iterator[None]:
    yield
    command.upgrade(alembic_config(test_database_url), "head")
    db_engine.dispose()


def wallet_state(engine: Engine) -> list[tuple[Any, ...]]:
    with engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT user_id, total_balance_cents, committed_balance_cents "
                    "FROM wallets ORDER BY user_id"
                )
            )
        ]


def test_scenario_a_backfill_gives_every_existing_user_a_zero_wallet(
    test_database_url: str, db_engine: Engine, clean_users: None, back_at_head: None
) -> None:
    config = alembic_config(test_database_url)
    command.downgrade(config, "0003")
    db_engine.dispose()
    ids = []
    for role in ("BIDDER", "BIDDER", "AUCTIONEER"):
        ids.append(add_user(db_engine, role))
    with db_engine.connect() as connection:
        users_before = connection.execute(
            text("SELECT id, email, password_hash, role FROM users ORDER BY id")
        ).all()

    command.upgrade(config, "head")
    db_engine.dispose()

    assert wallet_state(db_engine) == sorted((i, 0, 0) for i in ids)
    with db_engine.connect() as connection:
        users_after = connection.execute(
            text("SELECT id, email, password_hash, role FROM users ORDER BY id")
        ).all()
    assert users_after == users_before


def test_the_migration_on_an_empty_database_inserts_no_wallet(
    test_database_url: str, db_engine: Engine, clean_users: None, back_at_head: None
) -> None:
    config = alembic_config(test_database_url)
    command.downgrade(config, "0003")
    command.upgrade(config, "head")
    db_engine.dispose()

    assert wallet_state(db_engine) == []


# --- downgrade ---


def test_downgrade_removes_wallets_and_keeps_users_and_lots(
    test_database_url: str, db_engine: Engine, back_at_head: None
) -> None:
    config = alembic_config(test_database_url)

    command.downgrade(config, "0003")
    db_engine.dispose()
    tables = inspect(db_engine).get_table_names()
    assert "wallets" not in tables
    assert {"users", "lots"} <= set(tables)

    command.upgrade(config, "head")
    db_engine.dispose()
    assert "wallets" in inspect(db_engine).get_table_names()
