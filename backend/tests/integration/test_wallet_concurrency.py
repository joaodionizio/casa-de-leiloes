"""Depósitos concorrentes no PostgreSQL real (Story 3.1, CAP-7, P4, AD-17).

A prova de correção é o estado final, decidido por duas transações que de fato se
sobrepõem: a sessão A trava a carteira e segura a trava sem confirmar; a sessão B,
noutra conexão e noutra thread, pede a trava e fica esperando; só então A confirma.
`pg_stat_activity`/`pg_locks` são evidência auxiliar de que B esperou: o que decide
o teste é o total que ficou no banco e o resultado que B obteve sobre o saldo que A
confirmou. Nenhum teste depende de `sleep` para provar a sobreposição.
"""

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.money import MAX_CENTS
from app.wallet import DepositRefusal, Wallet, deposit
from tests.auth_support import (
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
    seeded_id,
)
from tests.wallet_support import (
    naive_deposit,
    seed_users_with_wallets,
    set_wallet,
    wait_for_blocked_lock,
    wallet_row,
    watch_lock_attempt,
)

JOIN_SECONDS = 15


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    return db_session_factory


@pytest.fixture
def user_id():  # type: ignore[no-untyped-def]
    return seeded_id(BIDDER_EMAIL)


def service_b(
    factory: sessionmaker[Session], user_id: Any, amount: int, outcome: list[Any]
) -> threading.Thread:
    """B: sessão e conexão próprias, o mesmo serviço, confirma se aceito."""

    def work() -> None:
        try:
            with factory() as session:
                result = deposit(session, user_id, amount)
                if isinstance(result, DepositRefusal):
                    session.rollback()
                    outcome.append(result)
                else:
                    session.commit()
                    outcome.append("committed")
        except BaseException as error:  # noqa: BLE001
            outcome.append(error)

    thread = threading.Thread(target=work, name="wallet-b")
    return thread


def overlapped_deposits(
    factory: sessionmaker[Session],
    engine: Engine,
    user_id: Any,
    a_amount: int,
    b_start: Any,
) -> None:
    """Orquestra a sobreposição. `b_start()` devolve a thread de B, ainda não iniciada.

    1. A trava a carteira e deposita, sem confirmar.
    2. B começa e chega ao `SELECT ... FOR UPDATE`.
    3. Evidência auxiliar: alguém está esperando uma trava, e B ainda não terminou.
    4. A confirma; só então B pode seguir.
    """
    with factory() as session_a:
        assert isinstance(deposit(session_a, user_id, a_amount), Wallet)
        with watch_lock_attempt(engine) as attempt:
            thread_b = b_start()
            thread_b.start()
            try:
                assert attempt.reached.wait(JOIN_SECONDS), "B não chegou à trava"
                # Auxiliar: a espera de B é observável. Não é a prova de correção.
                assert wait_for_blocked_lock(engine), "ninguém esperando uma trava"
                assert thread_b.is_alive(), "B terminou sem esperar a trava de A"
            finally:
                session_a.commit()  # libera B (e, no erro, não deixa a thread presa)
                thread_b.join(JOIN_SECONDS)
        assert not thread_b.is_alive()


# --- C1: dois depósitos válidos se somam ---


def test_c1_two_overlapping_valid_deposits_both_survive(
    seeded: sessionmaker[Session], db_engine: Engine, user_id: Any
) -> None:
    set_wallet(seeded, user_id, 1000)
    outcome: list[Any] = []

    overlapped_deposits(
        seeded,
        db_engine,
        user_id,
        300,
        lambda: service_b(seeded, user_id, 500, outcome),
    )

    assert outcome == ["committed"]
    assert wallet_row(seeded, user_id) == (1000 + 300 + 500, 0)


# --- C2/C3: perto do teto, B decide sobre o saldo que A confirmou ---


def test_c2_near_the_ceiling_b_is_refused_on_the_total_a_committed(
    seeded: sessionmaker[Session], db_engine: Engine, user_id: Any
) -> None:
    set_wallet(seeded, user_id, MAX_CENTS - 10)
    outcome: list[Any] = []

    # Sobre o saldo antigo (MAX - 10), B = 6 caberia; sobre o confirmado por A
    # (MAX - 4), não cabe.
    overlapped_deposits(
        seeded, db_engine, user_id, 6, lambda: service_b(seeded, user_id, 6, outcome)
    )

    assert outcome == [DepositRefusal.BALANCE_LIMIT_EXCEEDED]
    assert wallet_row(seeded, user_id) == (MAX_CENTS - 4, 0)


def test_c3_near_the_ceiling_b_is_accepted_when_it_fits_the_new_total(
    seeded: sessionmaker[Session], db_engine: Engine, user_id: Any
) -> None:
    set_wallet(seeded, user_id, MAX_CENTS - 10)
    outcome: list[Any] = []

    overlapped_deposits(
        seeded, db_engine, user_id, 6, lambda: service_b(seeded, user_id, 4, outcome)
    )

    assert outcome == ["committed"]
    assert wallet_row(seeded, user_id) == (MAX_CENTS, 0)


# --- C4: o mesmo arranjo pelo HTTP ---


def bidder_client(
    monkeypatch: pytest.MonkeyPatch, factory: sessionmaker[Session]
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=factory)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    return client


def http_b(client: TestClient, amount: int, outcome: list[Any]) -> threading.Thread:
    def work() -> None:
        try:
            outcome.append(
                client.post(
                    "/api/wallet/deposit",
                    json={"amount_cents": amount},
                    headers=json_headers(HTTPS_ORIGIN),
                )
            )
        except BaseException as error:  # noqa: BLE001
            outcome.append(error)

    return threading.Thread(target=work, name="wallet-b")


def test_c4_http_near_the_ceiling_b_gets_balance_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    user_id: Any,
) -> None:
    client = bidder_client(monkeypatch, seeded)
    set_wallet(seeded, user_id, MAX_CENTS - 10)
    outcome: list[Any] = []

    overlapped_deposits(
        seeded, db_engine, user_id, 6, lambda: http_b(client, 6, outcome)
    )

    (response,) = outcome
    assert response.status_code == 422
    assert response.json()["code"] == "balance_limit_exceeded"
    assert wallet_row(seeded, user_id) == (MAX_CENTS - 4, 0)


def test_c4b_http_overlapping_deposits_both_survive(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    user_id: Any,
) -> None:
    client = bidder_client(monkeypatch, seeded)
    outcome: list[Any] = []

    overlapped_deposits(
        seeded, db_engine, user_id, 300, lambda: http_b(client, 500, outcome)
    )

    (response,) = outcome
    assert response.status_code == 200
    # A resposta de B traz o total que inclui o depósito de A.
    assert response.json()["total_balance_cents"] == 800
    assert wallet_row(seeded, user_id) == (800, 0)


# --- C5: corrida livre, sem orquestração ---


@pytest.mark.parametrize("attempt", range(5))
def test_c5_free_running_http_deposits_never_lose_one(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    user_id: Any,
    attempt: int,
) -> None:
    clients = [bidder_client(monkeypatch, seeded) for _ in range(2)]
    amounts = [700, 1300]
    barrier = threading.Barrier(2)
    outcome: list[Any] = []

    def work(client: TestClient, amount: int) -> None:
        try:
            barrier.wait(timeout=10)
            outcome.append(
                client.post(
                    "/api/wallet/deposit",
                    json={"amount_cents": amount},
                    headers=json_headers(HTTPS_ORIGIN),
                )
            )
        except BaseException as error:  # noqa: BLE001
            outcome.append(error)

    threads = [
        threading.Thread(target=work, args=(client, amount))
        for client, amount in zip(clients, amounts, strict=True)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_SECONDS)

    assert [getattr(item, "status_code", item) for item in outcome] == [200, 200]
    assert wallet_row(seeded, user_id) == (sum(amounts), 0)


# --- C6: controle negativo ---


def test_c6_negative_control_the_unsafe_pattern_loses_a_deposit(
    seeded: sessionmaker[Session], user_id: Any
) -> None:
    """Sem a trava (leitura fora dela, soma em Python, escrita do valor absoluto),
    o mesmo cenário perde um depósito. Prova que os testes acima detectariam a falta
    da proteção."""
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=naive_deposit, args=(seeded, user_id, amount, barrier))
        for amount in (300, 500)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_SECONDS)

    total, committed = wallet_row(seeded, user_id) or (-1, -1)
    assert total in (300, 500)  # só um dos dois valores sobrevive
    assert total != 300 + 500
    assert committed == 0


# --- C7: a leitura não espera a trava do depósito ---


def test_c7_a_read_does_not_wait_for_a_deposit_holding_the_lock(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    user_id: Any,
) -> None:
    client = bidder_client(monkeypatch, seeded)
    set_wallet(seeded, user_id, 1000)
    outcome: list[Any] = []

    with seeded() as session_a:
        deposit(session_a, user_id, 300)  # segura a trava, sem confirmar
        reader = threading.Thread(
            target=lambda: outcome.append(client.get("/api/wallet"))
        )
        reader.start()
        reader.join(JOIN_SECONDS)
        finished = not reader.is_alive()
        session_a.rollback()
        reader.join(JOIN_SECONDS)

    assert finished, "a leitura ficou esperando a trava do depósito"
    (response,) = outcome
    assert response.status_code == 200
    # O que a leitura vê é o valor confirmado (MVCC), não o depósito pendente de A.
    assert response.json()["total_balance_cents"] == 1000
