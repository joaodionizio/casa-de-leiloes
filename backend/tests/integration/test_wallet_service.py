"""Serviço da carteira e garantia de carteiras no seed (Story 3.1, CAP-1, CAP-5,
CAP-9). PostgreSQL real."""

import logging
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import seed
from app.money import MAX_CENTS
from app.seed import SEED_USERS, seed_users
from app.wallet import (
    DepositRefusal,
    MissingWalletError,
    Wallet,
    deposit,
    ensure_wallets,
    lock_wallet,
    read_wallet,
)
from tests.auth_support import BIDDER_EMAIL, OTHER_BIDDER_EMAIL, seeded_id
from tests.lot_support import integrity_secrets, statement_recorder
from tests.wallet_support import (
    delete_wallet,
    seed_users_with_wallets,
    set_wallet,
    wallet_row,
    wallet_rows,
)

SEEDED_IDS = sorted(seed_user.id for seed_user in SEED_USERS)


def run_full_seed(factory: sessionmaker[Session]) -> tuple[int, bool]:
    """O que `main()` faz: uma transação, um commit."""
    with factory() as session:
        result = seed.run_seed(session, audit_hmac_secret=integrity_secrets()[0])
        session.commit()
    return result


def users_only(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        seed_users(session)
        session.commit()


# --- ensure_wallets ---


def test_ensure_wallets_creates_one_zero_wallet_per_user(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    users_only(db_session_factory)

    with db_session_factory() as session:
        assert ensure_wallets(session) == 3
        session.commit()
        assert ensure_wallets(session) == 0

    assert wallet_rows(db_session_factory) == [(i, 0, 0) for i in SEEDED_IDS]


def test_ensure_wallets_covers_a_user_that_is_not_a_seeded_one(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_with_wallets(db_session_factory)
    extra = uuid.uuid4()
    with db_session_factory() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, 'extra@example.com', 'h', 'BIDDER')"
            ),
            {"id": extra},
        )
        session.commit()

    with db_session_factory() as session:
        assert ensure_wallets(session) == 1
        session.commit()

    assert wallet_row(db_session_factory, extra) == (0, 0)


def test_ensure_wallets_never_touches_an_existing_balance(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)
    set_wallet(db_session_factory, bidder, 500, 200)

    with db_session_factory() as session:
        assert ensure_wallets(session) == 0
        session.commit()

    assert wallet_row(db_session_factory, bidder) == (500, 200)


# --- seed ---


def test_empty_database_seed_creates_three_zero_wallets(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    # O retorno de `run_seed` não muda: `(usuários, lote demo criado)`.
    assert run_full_seed(db_session_factory) == (3, True)

    assert wallet_rows(db_session_factory) == [(i, 0, 0) for i in SEEDED_IDS]


def test_seed_is_idempotent_for_wallets(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_full_seed(db_session_factory)
    before = wallet_rows(db_session_factory)

    assert run_full_seed(db_session_factory) == (0, False)

    assert wallet_rows(db_session_factory) == before


def test_seed_never_alters_an_existing_balance(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_full_seed(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)
    set_wallet(db_session_factory, bidder, 123456, 789)

    run_full_seed(db_session_factory)

    assert wallet_row(db_session_factory, bidder) == (123456, 789)


def test_seed_issues_no_update_or_delete_on_wallets(
    db_session_factory: sessionmaker[Session], clean_users: None, db_engine: Engine
) -> None:
    run_full_seed(db_session_factory)

    with statement_recorder(db_engine) as recorder:
        run_full_seed(db_session_factory)

    for statement in recorder.statements:
        normalized = statement.lstrip().upper()
        assert not normalized.startswith(("UPDATE", "DELETE")), statement


def test_seed_completes_a_wallet_that_is_missing_without_touching_the_others(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_full_seed(db_session_factory)
    first, second = seeded_id(BIDDER_EMAIL), seeded_id(OTHER_BIDDER_EMAIL)
    set_wallet(db_session_factory, first, 900)
    delete_wallet(db_session_factory, second)

    run_full_seed(db_session_factory)

    assert wallet_row(db_session_factory, first) == (900, 0)
    assert wallet_row(db_session_factory, second) == (0, 0)


def test_seed_does_not_preload_any_demo_money(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    run_full_seed(db_session_factory)

    assert {
        (total, committed) for _, total, committed in wallet_rows(db_session_factory)
    } == {(0, 0)}


def test_seed_does_not_log_a_wallet_count_before_the_commit(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """O log do seed só afirma o que o commit já confirmou: `run_seed` não loga
    contagem de carteiras antes do commit."""
    with caplog.at_level(logging.DEBUG):
        with db_session_factory() as session:
            seed.run_seed(session, audit_hmac_secret=integrity_secrets()[0])
            during = [r.getMessage() for r in caplog.records]
            session.rollback()

    assert not any("wallet" in message.lower() for message in during)


# --- equivalência: banco existente (backfill) = banco limpo (seed) ---


def test_scenario_a_and_scenario_b_end_in_the_same_state(
    test_database_url: str,
    db_engine: Engine,
    db_session_factory: sessionmaker[Session],
    clean_users: None,
) -> None:
    from alembic import command

    from tests.conftest import alembic_config

    # B: banco limpo, o seed cria usuários e carteiras.
    run_full_seed(db_session_factory)
    state_b = wallet_rows(db_session_factory)

    # A: os mesmos usuários já existiam antes da `0004`; o backfill cria as carteiras.
    config = alembic_config(test_database_url)
    try:
        command.downgrade(config, "0003")
        db_engine.dispose()
        command.upgrade(config, "head")
        db_engine.dispose()
        state_a = wallet_rows(db_session_factory)
    finally:
        command.upgrade(config, "head")
        db_engine.dispose()

    # A: o downgrade apagou as carteiras e o upgrade refez a partir de `users`.
    assert state_a == state_b == [(i, 0, 0) for i in SEEDED_IDS]


# --- leitura e travas ---


def test_read_and_lock_of_a_missing_wallet_raise_and_create_nothing(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    users_only(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)

    with db_session_factory() as session:
        with pytest.raises(MissingWalletError):
            read_wallet(session, bidder)
        session.rollback()
        with pytest.raises(MissingWalletError):
            lock_wallet(session, bidder)
        session.rollback()
        with pytest.raises(MissingWalletError):
            deposit(session, bidder, 100)
        session.rollback()

    assert wallet_rows(db_session_factory) == []
    assert str(MissingWalletError()) == "wallet missing for authenticated user"


# --- depósito ---


def test_deposit_adds_exactly_and_keeps_committed(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)
    set_wallet(db_session_factory, bidder, 1000, 400)

    with db_session_factory() as session:
        result = deposit(session, bidder, 250)
        assert isinstance(result, Wallet)
        session.commit()

    assert wallet_row(db_session_factory, bidder) == (1250, 400)


def test_deposit_up_to_the_exact_ceiling_is_accepted(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)
    set_wallet(db_session_factory, bidder, MAX_CENTS - 10)

    with db_session_factory() as session:
        assert isinstance(deposit(session, bidder, 10), Wallet)
        session.commit()

    assert wallet_row(db_session_factory, bidder) == (MAX_CENTS, 0)


def test_deposit_above_the_ceiling_is_refused_and_writes_nothing(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)
    set_wallet(db_session_factory, bidder, MAX_CENTS - 10)

    with db_session_factory() as session:
        assert deposit(session, bidder, 11) is DepositRefusal.BALANCE_LIMIT_EXCEEDED
        session.rollback()

    assert wallet_row(db_session_factory, bidder) == (MAX_CENTS - 10, 0)


@pytest.mark.parametrize("amount", [0, -500])
def test_a_non_positive_deposit_raises_and_writes_nothing(
    db_session_factory: sessionmaker[Session], clean_users: None, amount: int
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)
    set_wallet(db_session_factory, bidder, 1000)

    with db_session_factory() as session:
        with pytest.raises(ValueError):
            deposit(session, bidder, amount)
        session.rollback()

    assert wallet_row(db_session_factory, bidder) == (1000, 0)


def test_deposit_touches_only_the_owners_wallet(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> None:
    seed_users_with_wallets(db_session_factory)
    first, second = seeded_id(BIDDER_EMAIL), seeded_id(OTHER_BIDDER_EMAIL)

    with db_session_factory() as session:
        deposit(session, first, 700)
        session.commit()

    assert wallet_row(db_session_factory, first) == (700, 0)
    assert wallet_row(db_session_factory, second) == (0, 0)


def test_a_failure_after_the_update_and_before_the_commit_writes_nothing(
    db_session_factory: sessionmaker[Session],
    clean_users: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)

    def broken_commit(self: Session) -> None:
        raise RuntimeError("falha antes do commit")

    with db_session_factory() as session:
        deposit(session, bidder, 500)
        monkeypatch.setattr(Session, "commit", broken_commit)
        with pytest.raises(RuntimeError):
            session.commit()
        monkeypatch.undo()
        session.rollback()

    assert wallet_row(db_session_factory, bidder) == (0, 0)


def test_the_lock_statement_is_a_for_update_select_with_a_fresh_read(
    db_session_factory: sessionmaker[Session], clean_users: None, db_engine: Engine
) -> None:
    seed_users_with_wallets(db_session_factory)
    bidder = seeded_id(BIDDER_EMAIL)

    with db_session_factory() as session:
        stale = session.get(Wallet, bidder)  # a Session já conhece o objeto
        assert stale is not None and stale.total_balance_cents == 0
        set_wallet(db_session_factory, bidder, 900)  # outra transação confirma
        with statement_recorder(db_engine) as recorder:
            locked_total = lock_wallet(session, bidder).total_balance_cents
        session.rollback()

    # `populate_existing`: o objeto já presente na Session reflete o saldo confirmado.
    assert locked_total == 900
    (statement,) = recorder.statements
    assert statement.lstrip().upper().startswith("SELECT")
    assert "FOR UPDATE" in statement.upper()
