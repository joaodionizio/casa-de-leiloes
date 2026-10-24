"""A migration `0002` cria e remove `users` (Story 2.2, CAP-11)."""

import uuid
from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config

INSERT = text(
    "INSERT INTO users (id, email, password_hash, role) "
    "VALUES (:id, :email, 'hash', :role)"
)


def new_row(email: str = "a@example.com", role: str = "BIDDER") -> dict[str, object]:
    return {"id": uuid.uuid4(), "email": email, "role": role}


def test_users_table_has_the_agreed_columns_and_constraints(
    db_engine: Engine,
) -> None:
    inspector = inspect(db_engine)
    columns = {column["name"]: column for column in inspector.get_columns("users")}

    assert list(columns) == ["id", "email", "password_hash", "role"]
    assert all(column["nullable"] is False for column in columns.values())
    assert str(columns["email"]["type"]) == "VARCHAR(254)"
    assert str(columns["role"]["type"]) == "VARCHAR(16)"
    assert inspector.get_pk_constraint("users")["name"] == "pk_users"
    assert [c["name"] for c in inspector.get_unique_constraints("users")] == [
        "uq_users_email"
    ]
    assert sorted(c["name"] for c in inspector.get_check_constraints("users")) == [
        "ck_users_email_lowercase",
        "ck_users_role",
    ]
    # Sem default no banco para o id: os IDs do seed são fixos.
    assert columns["id"]["default"] is None


def test_valid_row_is_accepted(db_engine: Engine, clean_users: None) -> None:
    with db_engine.begin() as connection:
        connection.execute(INSERT, new_row(role="BIDDER"))
        connection.execute(INSERT, new_row("b@example.com", role="AUCTIONEER"))


@pytest.mark.parametrize(
    "row",
    [
        pytest.param({"role": "ADMIN"}, id="papel fora da lista"),
        pytest.param({"role": "bidder"}, id="papel em minúsculas"),
        pytest.param({"email": "Maiusculo@example.com"}, id="e-mail com maiúscula"),
    ],
)
def test_check_constraints_refuse_invalid_values(
    db_engine: Engine, clean_users: None, row: dict[str, object]
) -> None:
    with pytest.raises(IntegrityError):
        with db_engine.begin() as connection:
            connection.execute(INSERT, {**new_row(), **row})


def test_duplicate_email_is_refused(db_engine: Engine, clean_users: None) -> None:
    with db_engine.begin() as connection:
        connection.execute(INSERT, new_row("dup@example.com"))
    with pytest.raises(IntegrityError):
        with db_engine.begin() as connection:
            connection.execute(INSERT, new_row("dup@example.com"))


@pytest.fixture
def back_at_head(test_database_url: str, db_engine: Engine) -> Iterator[None]:
    """Garante que o banco _test volte a `head`, mesmo se o teste falhar."""
    yield
    command.upgrade(alembic_config(test_database_url), "head")
    db_engine.dispose()


def test_downgrade_removes_the_table_and_upgrade_recreates_it(
    test_database_url: str, db_engine: Engine, back_at_head: None
) -> None:
    config = alembic_config(test_database_url)

    command.downgrade(config, "0001")
    db_engine.dispose()
    assert "users" not in inspect(db_engine).get_table_names()

    command.upgrade(config, "head")
    db_engine.dispose()
    assert "users" in inspect(db_engine).get_table_names()
