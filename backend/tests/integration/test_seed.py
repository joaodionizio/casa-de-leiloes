"""Seed idempotente das contas e do lote demo (Story 2.2, CAP-1; Story 2.4, CAP-9)."""

import ast
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app import artic, catalog, lots, seed
from app.bid_integrity import GENESIS_HASH
from app.config import BACKEND_DIR
from app.security import hash_password, verify_password
from app.seed import (
    DEMO_ARTWORK_PATH,
    DEMO_AUCTIONEER_ID,
    DEMO_LOT_DURATION,
    DEMO_MIN_INCREMENT_CENTS,
    DEMO_PASSWORD,
    DEMO_STARTING_BID_CENTS,
    SEED_ADVISORY_LOCK_KEY,
    SEED_USERS,
    seed_users,
)
from tests.lot_support import (
    LOT_COLUMNS,
    count_lots,
    db_now,
    empty_anchor,
    insert_lot,
    integrity_secrets,
    lot_rows,
    statement_recorder,
)
from tests.wallet_support import wallet_rows

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


def seed_env(test_database_url: str, **overrides: str) -> dict[str, str]:
    """O ambiente mínimo do seed: tira do ambiente o que ele não pode precisar e põe
    `DATABASE_URL` e `AUDIT_HMAC_SECRET`. `overrides` sobrescreve ou acrescenta."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in (
            "APP_ORIGIN",
            "JWT_SECRET",
            "DATABASE_URL",
            "TEST_DATABASE_URL",
            "AUDIT_HMAC_SECRET",
            "PSEUDONYM_SECRET",
        )
    }
    env["DATABASE_URL"] = test_database_url
    env["AUDIT_HMAC_SECRET"] = os.environ["AUDIT_HMAC_SECRET"]
    env.update(overrides)
    return env


def run_seed_subprocess(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", SEED_WITHOUT_APP_MAIN],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_module_runs_alone_with_only_database_url_and_audit_secret(
    test_database_url: str, clean_users: None, db_session_factory: sessionmaker[Session]
) -> None:
    """O seed exige `DATABASE_URL` e `AUDIT_HMAC_SECRET` (P4) e não exige `APP_ORIGIN`,
    `JWT_SECRET` nem `PSEUDONYM_SECRET`; não importa `app.main`.

    Tirar as variáveis do ambiente não basta: as configurações também leem o
    `backend/.env`. Por isso o subprocesso confere `sys.modules` ao terminar, e
    `PSEUDONYM_SECRET=""` (inválido se fosse lido) sobrescreve qualquer `.env` local.
    """
    result = run_seed_subprocess(seed_env(test_database_url, PSEUDONYM_SECRET=""))

    assert result.returncode != 42, "o seed importou app.main"
    assert result.returncode == 0, result.stderr
    assert "3 user(s) inserted" in result.stderr + result.stdout
    assert "demo lot created" in result.stderr + result.stdout
    with db_session_factory() as session:
        assert len(all_rows(session)) == 3
    assert count_lots(db_session_factory) == 1
    # Story 3.1: o seed completo também cria as três carteiras, zeradas, e o log não
    # afirma contagem de carteiras (só usuários e lote, confirmados pelo commit).
    assert len(wallet_rows(db_session_factory)) == 3
    assert {row[1:] for row in wallet_rows(db_session_factory)} == {(0, 0)}
    assert "wallet" not in (result.stderr + result.stdout).lower()
    # Story 3.4: o demo nasceu com a âncora vazia assinada com o segredo do ambiente.
    (row,) = lot_rows(db_session_factory)
    lot = stored(row)
    assert lot["anchor_hmac"] == empty_anchor(lot["id"])
    assert (lot["bid_count"], lot["final_hash"]) == (0, GENESIS_HASH)


@pytest.mark.parametrize("secret", ["", "curto", "x" * 31, "é" * 15 + "a"])
def test_the_seed_fails_without_a_valid_audit_secret_and_never_echoes_it(
    test_database_url: str,
    clean_users: None,
    db_session_factory: sessionmaker[Session],
    secret: str,
) -> None:
    result = run_seed_subprocess(seed_env(test_database_url, AUDIT_HMAC_SECRET=secret))

    assert result.returncode not in (0, 42)
    output = result.stderr + result.stdout
    if secret:
        assert secret not in output
    with db_session_factory() as session:
        assert all_rows(session) == []  # falhou antes de abrir o banco
    assert count_lots(db_session_factory) == 0


def test_start_script_runs_migrations_then_seed_then_server() -> None:
    script = (Path(BACKEND_DIR) / "scripts" / "start.sh").read_text()
    order = [
        script.index("alembic upgrade head"),
        script.index("python -m app.seed"),
        script.index("exec uvicorn"),
    ]
    assert order == sorted(order)
    assert "set -eu" in script


# --- Story 2.4: lote demo ---


def run_full_seed(factory: sessionmaker[Session]) -> tuple[int, bool]:
    """O que `main()` faz: uma transação, um commit."""
    with factory() as session:
        result = seed.run_seed(session, audit_hmac_secret=integrity_secrets()[0])
        session.commit()
    return result


def demo_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.execute(
            text("SELECT count(*) FROM lots WHERE is_demo")
        ).scalar_one()


def stored(row: tuple) -> dict:
    return dict(zip(LOT_COLUMNS, row, strict=True))


def test_demo_constants_match_the_agreed_values() -> None:
    assert str(DEMO_AUCTIONEER_ID) == "219e37a5-0def-4b26-87d4-b08668f7c112"
    assert SEED_ADVISORY_LOCK_KEY == 7161131744880846180
    assert SEED_ADVISORY_LOCK_KEY.to_bytes(8, "big") == b"casaseed"
    assert DEMO_LOT_DURATION == timedelta(hours=72)
    assert DEMO_STARTING_BID_CENTS == 10000
    assert DEMO_MIN_INCREMENT_CENTS == 1000


def test_empty_database_gets_users_and_one_open_demo_lot(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    before = db_now(db_session_factory)

    assert run_full_seed(db_session_factory) == (3, True)

    after = db_now(db_session_factory)
    (row,) = lot_rows(db_session_factory)
    lot = stored(row)
    fixture = json.loads(DEMO_ARTWORK_PATH.read_text(encoding="utf-8"))
    assert lot["is_demo"] is True
    assert lot["auctioneer_id"] == DEMO_AUCTIONEER_ID
    assert lot["external_id"] == 27992
    for key, value in fixture.items():
        assert lot[key] == value, key
    assert lot["starting_bid_cents"] == 10000
    assert lot["min_increment_cents"] == 1000
    assert lot["starts_at"] == lot["created_at"]
    assert before <= lot["starts_at"] <= after
    assert lot["ends_at"] - lot["starts_at"] == timedelta(hours=72)


def test_a_second_run_creates_nothing_and_changes_no_column(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_full_seed(db_session_factory)
    before = lot_rows(db_session_factory)

    assert run_full_seed(db_session_factory) == (0, False)

    assert lot_rows(db_session_factory) == before


def test_a_closed_demo_stays_exactly_as_it_was_and_a_new_one_is_created(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    db_engine: Engine,
) -> None:
    seed_users_only(db_session_factory)
    now = db_now(db_session_factory)
    old = insert_lot(
        db_session_factory,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        is_demo=True,
        starts_at=now - timedelta(days=4),
        ends_at=now - timedelta(days=1),
        created_at=now - timedelta(days=4),
        title="Demo antigo",
    )
    before = lot_rows(db_session_factory)

    with statement_recorder(db_engine) as recorder:
        assert run_full_seed(db_session_factory) == (0, True)

    rows = lot_rows(db_session_factory)
    assert len(rows) == 2
    assert [row for row in rows if row[0] == old] == before
    for statement in recorder.statements:
        normalized = statement.lstrip().upper()
        assert not normalized.startswith("UPDATE"), statement
        assert not normalized.startswith("DELETE"), statement
        assert "FOR UPDATE" not in normalized


def test_several_old_demos_and_one_open_demo_change_nothing(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_only(db_session_factory)
    now = db_now(db_session_factory)
    for days in (5, 3):
        insert_lot(
            db_session_factory,
            auctioneer_id=DEMO_AUCTIONEER_ID,
            is_demo=True,
            starts_at=now - timedelta(days=days + 1),
            ends_at=now - timedelta(days=days),
        )
    insert_lot(
        db_session_factory,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        is_demo=True,
        ends_at=now + timedelta(hours=1),
    )
    before = lot_rows(db_session_factory)

    assert run_full_seed(db_session_factory) == (0, False)

    assert lot_rows(db_session_factory) == before


def test_a_legacy_open_demo_without_anchor_does_not_count_and_is_never_signed(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    db_engine: Engine,
) -> None:
    """Primeiro boot da 3.4 com um demo legado aberto (`anchor_hmac NULL`): o legado não
    conta, um demo assinado é criado e o legado fica exatamente como estava (P3)."""
    seed_users_only(db_session_factory)
    legacy = insert_lot(
        db_session_factory,
        anchored=False,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        is_demo=True,
        ends_at=db_now(db_session_factory) + timedelta(hours=10),
    )
    before = [row for row in lot_rows(db_session_factory) if row[0] == legacy]

    with statement_recorder(db_engine) as recorder:
        assert run_full_seed(db_session_factory) == (0, True)

    rows = lot_rows(db_session_factory)
    assert [row for row in rows if row[0] == legacy] == before
    assert stored(before[0])["anchor_hmac"] is None
    signed = [stored(row) for row in rows if row[0] != legacy]
    assert len(signed) == 1
    assert signed[0]["anchor_hmac"] == empty_anchor(signed[0]["id"])
    for statement in recorder.statements:
        normalized = statement.lstrip().upper()
        assert not normalized.startswith("UPDATE"), statement
        assert not normalized.startswith("DELETE"), statement
    # Boots seguintes: o demo assinado conta, nada é criado nem assinado.
    assert run_full_seed(db_session_factory) == (0, False)
    assert len(lot_rows(db_session_factory)) == 2


def test_a_signed_demo_counts_as_open_even_if_its_signature_is_not_checked(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    """O predicado escolhe o demo, não autentica: `anchor_hmac IS NOT NULL` basta
    (F-4). O lance continua passando pelo gate."""
    seed_users_only(db_session_factory)
    insert_lot(
        db_session_factory,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        is_demo=True,
        anchor_hmac="f" * 64,
        ends_at=db_now(db_session_factory) + timedelta(hours=1),
    )

    assert run_full_seed(db_session_factory) == (0, False)


def test_an_open_manual_lot_does_not_count_as_the_demo(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_only(db_session_factory)
    insert_lot(
        db_session_factory,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        is_demo=False,
        ends_at=db_now(db_session_factory) + timedelta(days=1),
    )

    assert run_full_seed(db_session_factory) == (0, True)

    assert count_lots(db_session_factory) == 2
    assert demo_count(db_session_factory) == 1


@pytest.mark.parametrize(
    ("offset", "created"),
    [(timedelta(seconds=5), False), (timedelta(seconds=-5), True)],
)
def test_the_boundary_of_open_is_the_database_clock(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    offset: timedelta,
    created: bool,
) -> None:
    seed_users_only(db_session_factory)
    insert_lot(
        db_session_factory,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        is_demo=True,
        starts_at=db_now(db_session_factory) - timedelta(days=1),
        ends_at=db_now(db_session_factory) + offset,
    )

    assert run_full_seed(db_session_factory) == (0, created)


def seed_users_only(factory: sessionmaker[Session]) -> None:
    run_seed(factory)


def test_the_demo_goes_through_the_shared_schedule_rule(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lots,
        "resolve_schedule",
        lambda starts_at, ends_at, now: lots.ScheduleViolation.ENDS_AT_NOT_AFTER_START,
    )

    with db_session_factory() as session:
        with pytest.raises(RuntimeError):
            seed.run_seed(session, audit_hmac_secret=integrity_secrets()[0])

    assert count_lots(db_session_factory) == 0
    with db_session_factory() as session:
        assert all_rows(session) == []  # a transação toda foi desfeita


def test_the_seed_uses_create_lot_once_with_the_fixture_snapshot(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    real = seed.create_lot

    def spy(session, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return real(session, **kwargs)

    monkeypatch.setattr(seed, "create_lot", spy)

    run_full_seed(db_session_factory)

    (call,) = calls
    assert call["is_demo"] is True
    assert call["snapshot"] == seed.load_demo_artwork()
    assert call["auctioneer_id"] == DEMO_AUCTIONEER_ID


def boom(*args: object, **kwargs: object) -> None:
    raise AssertionError("o seed não pode falar com o catálogo nem com a rede")


def test_the_seed_never_touches_the_catalog_or_the_network(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lots, "resolve_artwork_for_lot", boom)
    monkeypatch.setattr(catalog, "get_artwork", boom)
    monkeypatch.setattr(lots, "get_artwork", boom)
    monkeypatch.setattr(artic.ArticClient, "search", boom)
    monkeypatch.setattr(artic.ArticClient, "get_artwork", boom)
    monkeypatch.setattr(artic.ArticClient, "get_image", boom)
    monkeypatch.setattr(httpx.Client, "__init__", boom)

    assert run_full_seed(db_session_factory) == (3, True)
    # A guarda de rede do conftest reprovaria o teste se algum host fosse resolvido.


def test_seed_source_does_not_reference_the_catalog_or_http_client() -> None:
    tree = ast.parse(Path(seed.__file__).read_text(encoding="utf-8"))
    forbidden = {
        "resolve_artwork_for_lot",
        "get_artwork",
        "ArticClient",
        "artic_client",
        "httpx",
    }
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
            names.add((node.module or "").split(".")[-1])
        elif isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
    assert names & forbidden == set()


def test_the_seed_runs_in_read_committed(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    # O algoritmo depende disso: em REPEATABLE READ o segundo seed não veria o demo
    # que o primeiro acabou de confirmar.
    with db_session_factory() as session:
        seed.run_seed(session, audit_hmac_secret=integrity_secrets()[0])
        isolation = session.execute(text("SHOW transaction_isolation")).scalar_one()
        session.rollback()
    assert isolation == "read committed"


# --- concorrência ---


def wait_for_blocked_advisory_lock(engine: Engine, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            waiting = connection.execute(
                text(
                    "SELECT count(*) FROM pg_locks "
                    "WHERE locktype = 'advisory' AND NOT granted"
                )
            ).scalar_one()
            connection.rollback()
            if waiting:
                return
            time.sleep(0.02)
    raise AssertionError("o seed não ficou esperando pela trava consultiva")


def start_seed_thread(
    factory: sessionmaker[Session], outcome: list[object]
) -> threading.Thread:
    def work() -> None:
        try:
            outcome.append(run_full_seed(factory))
        except BaseException as error:  # noqa: BLE001
            outcome.append(error)

    thread = threading.Thread(target=work)
    thread.start()
    return thread


def test_a_seed_waits_for_the_lock_and_then_sees_the_demo_the_holder_created(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    db_engine: Engine,
) -> None:
    seed_users_only(db_session_factory)
    outcome: list[object] = []
    holder = db_engine.connect()
    thread: threading.Thread | None = None
    try:
        holder.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_ADVISORY_LOCK_KEY}
        )
        thread = start_seed_thread(db_session_factory, outcome)
        wait_for_blocked_advisory_lock(db_engine)
        assert outcome == []  # ainda bloqueado

        insert_lot(
            db_session_factory,
            auctioneer_id=DEMO_AUCTIONEER_ID,
            is_demo=True,
            ends_at=db_now(db_session_factory) + timedelta(days=1),
        )
        holder.commit()  # solta a trava
        thread.join(timeout=15)
    finally:
        holder.rollback()
        holder.close()
        if thread is not None:
            thread.join(timeout=15)

    assert outcome == [(0, False)]
    assert demo_count(db_session_factory) == 1


def test_a_seed_waiting_on_the_lock_creates_the_demo_if_the_holder_created_none(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    db_engine: Engine,
) -> None:
    seed_users_only(db_session_factory)
    outcome: list[object] = []
    holder = db_engine.connect()
    thread: threading.Thread | None = None
    try:
        holder.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_ADVISORY_LOCK_KEY}
        )
        thread = start_seed_thread(db_session_factory, outcome)
        wait_for_blocked_advisory_lock(db_engine)
        holder.rollback()  # solta a trava sem criar nada
        thread.join(timeout=15)
    finally:
        holder.rollback()
        holder.close()
        if thread is not None:
            thread.join(timeout=15)

    assert outcome == [(0, True)]
    assert demo_count(db_session_factory) == 1


@pytest.mark.parametrize("attempt", range(5))
def test_two_free_running_seeds_create_exactly_one_demo(
    db_session_factory: sessionmaker[Session], clean_users: None, attempt: int
) -> None:
    barrier = threading.Barrier(2)
    outcome: list[object] = []

    def work() -> None:
        try:
            barrier.wait(timeout=10)
            outcome.append(run_full_seed(db_session_factory))
        except BaseException as error:  # noqa: BLE001
            outcome.append(error)

    threads = [threading.Thread(target=work) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert all(isinstance(item, tuple) for item in outcome), outcome
    assert sorted(item[1] for item in outcome) == [False, True]  # type: ignore[index]
    assert sum(item[0] for item in outcome) == 3  # type: ignore[index]
    assert demo_count(db_session_factory) == 1
    with db_session_factory() as session:
        assert len(all_rows(session)) == 3
