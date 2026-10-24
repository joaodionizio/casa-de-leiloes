"""Seed idempotente das contas de demonstração (Story 2.2, CAP-1)."""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config import BACKEND_DIR
from app.security import hash_password, verify_password
from app.seed import DEMO_PASSWORD, SEED_USERS, seed_users

EXPECTED = {
    "219e37a5-0def-4b26-87d4-b08668f7c112": ("auctioneer@example.com", "AUCTIONEER"),
    "64d28807-1bfc-47cd-950e-37dbf962d7af": ("bidder1@example.com", "BIDDER"),
    "b5e863a7-4317-4a28-a622-9182cfa00842": ("bidder2@example.com", "BIDDER"),
}


def all_rows(session: Session) -> list[tuple]:
    return [
        tuple(row)
        for row in session.execute(
            text("SELECT id, email, password_hash, role FROM users ORDER BY id")
        )
    ]


def run_seed(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        inserted = seed_users(session)
        session.commit()
    return inserted


def test_seed_users_are_exactly_one_auctioneer_and_two_bidders() -> None:
    assert {str(s.id): (s.email, s.role.value) for s in SEED_USERS} == EXPECTED
    assert sorted(s.role.value for s in SEED_USERS) == [
        "AUCTIONEER",
        "BIDDER",
        "BIDDER",
    ]


def test_empty_database_gets_three_users_with_argon2_hashes(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    assert run_seed(db_session_factory) == 3

    with db_session_factory() as session:
        rows = all_rows(session)
    assert len(rows) == 3
    for user_id, email, password_hash, role in rows:
        assert EXPECTED[str(user_id)] == (email, role)
        assert password_hash.startswith("$argon2id$")
        assert DEMO_PASSWORD not in password_hash
        assert verify_password(password_hash, DEMO_PASSWORD)


def test_second_run_inserts_nothing_and_changes_no_column(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_seed(db_session_factory)
    with db_session_factory() as session:
        before = all_rows(session)

    assert run_seed(db_session_factory) == 0

    with db_session_factory() as session:
        assert all_rows(session) == before


def test_existing_account_is_never_altered_even_if_edited(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_seed(db_session_factory)
    edited_hash = hash_password("outra-senha-1!")
    with db_session_factory() as session:
        session.execute(
            text(
                "UPDATE users SET role = 'AUCTIONEER', password_hash = :h "
                "WHERE email = 'bidder1@example.com'"
            ),
            {"h": edited_hash},
        )
        session.commit()

    assert run_seed(db_session_factory) == 0

    with db_session_factory() as session:
        row = session.execute(
            text(
                "SELECT role, password_hash FROM users "
                "WHERE email = 'bidder1@example.com'"
            )
        ).one()
    assert row == ("AUCTIONEER", edited_hash)


def test_only_the_missing_accounts_are_inserted(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_seed(db_session_factory)
    with db_session_factory() as session:
        session.execute(text("DELETE FROM users WHERE email = 'bidder2@example.com'"))
        session.commit()

    assert run_seed(db_session_factory) == 1


def test_seeded_email_already_used_by_another_id_fails(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    with db_session_factory() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, 'bidder1@example.com', 'h', 'BIDDER')"
            ),
            {"id": uuid.uuid4()},
        )
        session.commit()

    with pytest.raises(IntegrityError):
        run_seed(db_session_factory)


# Roda `app.seed` como `python -m app.seed` faria e sai com 42 se `app.main` (o
# boot completo, que exige APP_ORIGIN e JWT_SECRET) tiver sido importado.
SEED_WITHOUT_APP_MAIN = (
    "import runpy, sys\n"
    "runpy.run_module('app.seed', run_name='__main__', alter_sys=True)\n"
    "sys.exit(42 if 'app.main' in sys.modules else 0)\n"
)


def test_module_runs_alone_with_only_database_url(
    test_database_url: str, clean_users: None, db_session_factory: sessionmaker[Session]
) -> None:
    """O seed não exige APP_ORIGIN nem JWT_SECRET e não importa `app.main`.

    Tirar as variáveis do ambiente não basta: as configurações também leem o
    `backend/.env`. Por isso o subprocesso confere `sys.modules` ao terminar.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("APP_ORIGIN", "JWT_SECRET", "DATABASE_URL", "TEST_DATABASE_URL")
    }
    env["DATABASE_URL"] = test_database_url

    result = subprocess.run(
        [sys.executable, "-c", SEED_WITHOUT_APP_MAIN],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 42, "o seed importou app.main"
    assert result.returncode == 0, result.stderr
    assert "3 user(s) inserted" in result.stderr + result.stdout
    with db_session_factory() as session:
        assert len(all_rows(session)) == 3


def test_start_script_runs_migrations_then_seed_then_server() -> None:
    script = (Path(BACKEND_DIR) / "scripts" / "start.sh").read_text()
    order = [
        script.index("alembic upgrade head"),
        script.index("python -m app.seed"),
        script.index("exec uvicorn"),
    ]
    assert order == sorted(order)
    assert "set -eu" in script
