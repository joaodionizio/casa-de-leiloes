"""Lances simultâneos sobre PostgreSQL real (Story 3.4; CAP-3, CAP-4, CA9).

A prova de correção é o estado final, decidido por transações que de fato se sobrepõem:
a sessão A segura as travas sem confirmar, B (outra conexão, outra thread) chega ao
`SELECT ... FOR UPDATE` e fica esperando, e só então A confirma. `pg_locks` é evidência
auxiliar de que B esperou. Nenhum teste depende de `sleep` para provar a sobreposição;
as corridas livres usam barreira e várias rodadas, e o veredito é o estado final."""

import threading
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.bid_rules import BidRefusal
from app.bids import PlacedBid, place_bid
from app.wallet import Wallet, deposit
from tests.auth_support import (
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import (
    add_bidder,
    assert_authenticated,
    assert_invariants,
    before_statement,
    bid_rows,
    hold_bid,
    integrity,
    is_lot_lock,
    kind_of,
    live_lot,
    lot_state,
    run_bid,
    watch_statement,
)
from tests.lot_support import db_now
from tests.wallet_support import (
    seed_users_with_wallets,
    set_wallet,
    wait_for_blocked_lock,
    wallet_row,
)

JOIN_SECONDS = 15
ALICE = seeded_id(BIDDER_EMAIL)
BOB = seeded_id(OTHER_BIDDER_EMAIL)


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, 100_000)
    set_wallet(db_session_factory, BOB, 100_000)
    return db_session_factory


def is_wallet_lock(statement: str) -> bool:
    return kind_of(" ".join(statement.split())) == "lock_wallet"


def thread_for(
    work: Callable[[], Any], outcome: list[Any], name: str
) -> threading.Thread:
    """Roda `work()` e guarda o resultado (ou a exceção) em `outcome`."""

    def target() -> None:
        try:
            outcome.append(work())
        except BaseException as error:  # noqa: BLE001
            outcome.append(error)

    return threading.Thread(target=target, name=name)


def overlapped(
    factory: sessionmaker[Session],
    engine: Engine,
    a_action: Callable[[Session], Any],
    b_start: Callable[[], threading.Thread],
    *,
    matcher: Callable[[str], bool] = is_lot_lock,
    while_blocked: Callable[[], None] | None = None,
) -> Any:
    """1. A executa `a_action` e segura as travas, sem confirmar. 2. B começa e chega
    ao statement que casa com `matcher`. 3. Evidência auxiliar: alguém espera uma
    trava e B segue vivo. 4. `while_blocked()`. 5. A confirma; só então B pode seguir.
    Devolve o que A obteve."""
    with factory() as session_a:
        a_result = a_action(session_a)
        with watch_statement(engine, matcher) as attempt:
            thread_b = b_start()
            thread_b.start()
            try:
                assert attempt.reached.wait(JOIN_SECONDS), "B não chegou à trava"
                assert wait_for_blocked_lock(engine), "ninguém esperando uma trava"
                assert thread_b.is_alive(), "B terminou sem esperar a trava de A"
                if while_blocked is not None:
                    while_blocked()
            finally:
                session_a.commit()  # libera B (e, no erro, não deixa a thread presa)
                thread_b.join(JOIN_SECONDS)
        assert not thread_b.is_alive()
    return a_result


def b_service(
    factory: sessionmaker[Session],
    lot_id: uuid.UUID,
    bidder_id: uuid.UUID,
    amount: int,
    outcome: list[Any],
) -> Callable[[], threading.Thread]:
    return lambda: thread_for(
        lambda: run_bid(factory, lot_id, bidder_id, amount), outcome, "bid-b"
    )


# --- T-CONC-2 ---


def test_the_second_bid_with_the_same_starting_value_loses_to_the_first(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=1_000)
    outcome: list[Any] = []

    first = overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, 10_000),
        b_service(seeded, lot_id, BOB, 10_000, outcome),
    )

    assert isinstance(first, PlacedBid)
    assert outcome == [BidRefusal.BELOW_MINIMUM]  # B leu o lance confirmado por A
    (row,) = bid_rows(seeded, lot_id)
    assert row["bidder_id"] == ALICE
    assert wallet_row(seeded, BOB) == (100_000, 0)
    assert_authenticated(seeded, lot_id)
    assert_invariants(seeded)


def test_the_second_bid_that_covers_the_first_extends_the_chain_and_releases_the_leader(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=1_000)
    outcome: list[Any] = []

    overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, 10_000),
        b_service(seeded, lot_id, BOB, 11_000, outcome),
    )

    (second,) = outcome
    assert isinstance(second, PlacedBid) and second.sequence == 2
    first_row, second_row = bid_rows(seeded, lot_id)
    assert second_row["previous_hash"] == first_row["current_hash"]
    assert wallet_row(seeded, ALICE) == (100_000, 0)  # liberada na mesma transação
    assert wallet_row(seeded, BOB) == (100_000, 11_000)
    assert_authenticated(seeded, lot_id)
    assert_invariants(seeded)


def test_the_same_bidder_twice_is_already_winning_the_second_time(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)
    outcome: list[Any] = []

    overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, 10_000),
        b_service(seeded, lot_id, ALICE, 50_000, outcome),
    )

    assert outcome == [BidRefusal.ALREADY_WINNING]
    assert len(bid_rows(seeded, lot_id)) == 1
    assert wallet_row(seeded, ALICE) == (100_000, 10_000)


def test_the_second_bid_arriving_over_http_sees_the_first(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=1_000)
    bob = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    assert login(bob, HTTPS_ORIGIN, OTHER_BIDDER_EMAIL).status_code == 200
    outcome: list[Any] = []

    def post(amount: int) -> Any:
        return bob.post(
            f"/api/lots/{lot_id}/bids",
            json={"amount_cents": amount},
            headers=json_headers(HTTPS_ORIGIN),
        )

    overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, 10_000),
        lambda: thread_for(lambda: post(10_500), outcome, "bid-http"),
    )
    (refused,) = outcome
    assert (refused.status_code, refused.json()["code"]) == (422, "below_minimum")

    outcome.clear()
    assert post(11_000).status_code == 201  # o mesmo cliente, agora sem corrida
    assert [r["sequence"] for r in bid_rows(seeded, lot_id)] == [1, 2]
    assert_invariants(seeded)


# --- T-SNIPE (3): o segundo lê o fim que o primeiro prorrogou ---


@pytest.mark.parametrize(
    "wait_for_window", [False, True], ids=["outside-new-window", "inside-new-window"]
)
def test_the_second_bid_reads_the_extended_end_under_real_lock(
    seeded: sessionmaker[Session],
    db_engine: Engine,
    wait_for_window: bool,
) -> None:
    ends_at = db_now(seeded) + timedelta(seconds=5 if wait_for_window else 60)
    lot_id = live_lot(seeded, ends_at=ends_at)
    outcome: list[Any] = []

    def enter_extended_window() -> None:
        # B já está bloqueado na trava real. Espero o fim original passar para
        # que seu clock_timestamp pós-trava entre na janela do fim prorrogado.
        # Não troco relógio, não altero dados nem simulo ordem de aquisição.
        with seeded() as observer:
            observer.execute(
                text(
                    "SELECT pg_sleep(GREATEST(EXTRACT(EPOCH FROM "
                    "(CAST(:end AS timestamptz) - clock_timestamp())), 0))"
                ),
                {"end": ends_at},
            )

    first = overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, 10_000),
        b_service(seeded, lot_id, BOB, 11_000, outcome),
        while_blocked=enter_extended_window if wait_for_window else None,
    )

    assert first.anti_sniping_applied is True
    assert first.ends_at == ends_at + timedelta(minutes=2)
    (second,) = outcome
    assert isinstance(second, PlacedBid)
    assert second.placed_at > first.placed_at
    assert second.anti_sniping_applied is wait_for_window
    expected = (
        first.ends_at + timedelta(minutes=2) if wait_for_window else first.ends_at
    )
    assert second.ends_at == expected
    assert second.ends_at != second.placed_at + timedelta(minutes=2)
    assert_authenticated(seeded, lot_id)
    assert_invariants(seeded)
    assert lot_state(seeded, lot_id)["ends_at"] == second.ends_at


# --- T-CLOCK (b): a hora vem depois da espera pela trava ---


def test_the_waiting_bid_takes_its_instant_after_the_first_one_commits(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)
    outcome: list[Any] = []
    observed: list[Any] = []

    first = overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, ALICE, 10_000),
        b_service(seeded, lot_id, BOB, 11_000, outcome),
        # B já está esperando a trava do lote e A ainda não confirmou.
        while_blocked=lambda: observed.append(db_now(seeded)),
    )

    (second,) = outcome
    (t1,) = observed
    assert isinstance(second, PlacedBid)
    assert first.placed_at < t1 < second.placed_at
    first_row, second_row = bid_rows(seeded, lot_id)
    assert first_row["placed_at"] == first.placed_at
    assert second_row["placed_at"] == second.placed_at


# --- T-CONC-N: corrida livre ---


def free_race(
    factory: sessionmaker[Session],
    lots: list[uuid.UUID],
    users: list[uuid.UUID],
    rounds_per_user: int,
) -> list[Any]:
    barrier = threading.Barrier(len(users))
    outcome: list[Any] = []
    lock = threading.Lock()

    def work(index: int, user: uuid.UUID) -> None:
        try:
            barrier.wait(timeout=10)
            for attempt in range(rounds_per_user):
                lot_id = lots[(index + attempt) % len(lots)]
                amount = 10_000 + 1_000 * (attempt * len(users) + index)
                result = run_bid(factory, lot_id, user, amount)
                with lock:
                    outcome.append(result)
        except BaseException as error:  # noqa: BLE001
            with lock:
                outcome.append(error)

    threads = [
        threading.Thread(target=work, args=(index, user))
        for index, user in enumerate(users)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_SECONDS * 2)
    assert not any(thread.is_alive() for thread in threads)
    return outcome


@pytest.mark.parametrize("lot_count", [1, 2])
@pytest.mark.parametrize("attempt", range(5))
def test_free_running_bids_leave_a_serial_consistent_state(
    seeded: sessionmaker[Session], attempt: int, lot_count: int
) -> None:
    users = [add_bidder(seeded, 1_000_000) for _ in range(4)]
    lots = [
        live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=1_000)
        for _ in range(lot_count)
    ]

    outcome = free_race(seeded, lots, users, rounds_per_user=3)

    # Nenhum 500 e nenhuma exceção: só aceites ou recusas de negócio.
    assert len(outcome) == 12
    for item in outcome:
        assert isinstance(item, (PlacedBid, BidRefusal)), item
        if isinstance(item, BidRefusal):
            assert item in (BidRefusal.BELOW_MINIMUM, BidRefusal.ALREADY_WINNING)
    accepted = [item for item in outcome if isinstance(item, PlacedBid)]
    assert accepted, "nenhum lance foi aceito"
    total_bids = 0
    for lot_id in lots:
        rows = bid_rows(seeded, lot_id)
        total_bids += len(rows)
        # Resultado de alguma ordem serial: cada lance cobre o anterior pelo mínimo e
        # o líder nunca se cobre.
        for before, after in zip(rows, rows[1:], strict=False):
            assert after["amount_cents"] >= before["amount_cents"] + 1_000
            assert after["bidder_id"] != before["bidder_id"]
        if rows:
            assert rows[0]["amount_cents"] >= 10_000
    assert total_bids == len(accepted)
    assert_invariants(seeded)  # I1 a I5, inclusive o comprometido de cada licitante


# --- T-DEADLOCK ---


def test_crossed_leaders_in_two_lots_finish_without_deadlock(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    user_one, user_two = add_bidder(seeded, 100_000), add_bidder(seeded, 100_000)
    lot_one = live_lot(seeded, starting_bid_cents=10_000)
    lot_two = live_lot(seeded, starting_bid_cents=10_000)
    assert isinstance(run_bid(seeded, lot_one, user_one, 10_000), PlacedBid)
    assert isinstance(run_bid(seeded, lot_two, user_two, 10_000), PlacedBid)
    # Cada thread já tem o seu lote travado quando chega ao primeiro `SELECT wallets`.
    barrier = threading.Barrier(2)
    outcome: list[Any] = []

    with before_statement(db_engine, is_wallet_lock, lambda: barrier.wait(timeout=10)):
        threads = [
            thread_for(
                lambda: run_bid(seeded, lot_one, user_two, 11_000), outcome, "u2-in-l1"
            ),
            thread_for(
                lambda: run_bid(seeded, lot_two, user_one, 11_000), outcome, "u1-in-l2"
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(JOIN_SECONDS)

    assert not any(thread.is_alive() for thread in threads)
    assert len(outcome) == 2 and all(isinstance(r, PlacedBid) for r in outcome), outcome
    assert lot_state(seeded, lot_one)["current_leader_id"] == user_two
    assert lot_state(seeded, lot_two)["current_leader_id"] == user_one
    assert wallet_row(seeded, user_one) == (100_000, 11_000)
    assert wallet_row(seeded, user_two) == (100_000, 11_000)
    assert_invariants(seeded)


def role_ordered_locks(
    engine: Engine,
    first: uuid.UUID,
    second: uuid.UUID,
    barrier: threading.Barrier,
    outcome: list[Any],
) -> None:
    """O padrão inseguro, só para o controle negativo: trava a carteira do novo líder
    primeiro e a do líder anterior depois, por papel e não por `user_id`."""
    try:
        with engine.begin() as connection:
            connection.execute(
                text("SELECT user_id FROM wallets WHERE user_id = :id FOR UPDATE"),
                {"id": first},
            )
            barrier.wait(timeout=10)
            connection.execute(
                text("SELECT user_id FROM wallets WHERE user_id = :id FOR UPDATE"),
                {"id": second},
            )
        outcome.append("committed")
    except BaseException as error:  # noqa: BLE001
        outcome.append(error)


def test_negative_control_role_ordered_locks_do_deadlock(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    """Sem a ordem por `user_id`, o mesmo cenário produz SQLSTATE 40P01. Prova que o
    teste acima detectaria a violação do protocolo de travas (AD-8)."""
    user_one, user_two = add_bidder(seeded, 100_000), add_bidder(seeded, 100_000)
    barrier = threading.Barrier(2)
    outcome: list[Any] = []
    threads = [
        threading.Thread(
            target=role_ordered_locks,
            args=(db_engine, new_leader, old_leader, barrier, outcome),
        )
        for new_leader, old_leader in ((user_two, user_one), (user_one, user_two))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_SECONDS)

    assert not any(thread.is_alive() for thread in threads)
    deadlocks = [
        item
        for item in outcome
        if isinstance(item, OperationalError)
        and getattr(item.orig, "sqlstate", None) == "40P01"
    ]
    assert len(deadlocks) == 1, outcome
    assert outcome.count("committed") == 1  # a outra segue depois do aborto


# --- T-DEPOSIT ---


def test_a_deposit_waits_for_the_wallet_a_bid_is_holding(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    set_wallet(seeded, BOB, 20_000)
    lot_id = live_lot(seeded, starting_bid_cents=10_000)
    outcome: list[Any] = []

    def deposit_b() -> Any:
        with seeded() as session:
            result = deposit(session, BOB, 5_000)
            session.commit()
            return result

    overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, BOB, 10_000),
        lambda: thread_for(deposit_b, outcome, "deposit-b"),
        matcher=is_wallet_lock,
    )

    (wallet,) = outcome
    assert isinstance(wallet, Wallet)
    assert wallet_row(seeded, BOB) == (25_000, 10_000)  # nenhum dos dois se perdeu
    assert_invariants(seeded)


def test_a_bid_waiting_for_the_wallet_uses_the_balance_a_deposit_committed(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    set_wallet(seeded, BOB, 5_000)
    lot_id = live_lot(seeded, starting_bid_cents=8_000)
    outcome: list[Any] = []

    def deposit_a(session: Session) -> Wallet:
        result = deposit(session, BOB, 4_000)
        assert isinstance(result, Wallet)
        return result

    overlapped(
        seeded,
        db_engine,
        deposit_a,
        b_service(seeded, lot_id, BOB, 8_000, outcome),
        matcher=is_wallet_lock,
    )

    # Só cabe com o depósito: 8 000 > 5 000, mas 8 000 <= 9 000.
    (placed,) = outcome
    assert isinstance(placed, PlacedBid), placed
    assert wallet_row(seeded, BOB) == (9_000, 8_000)
    assert_invariants(seeded)


def test_a_bid_with_the_wallet_already_loaded_in_the_session_still_sees_the_deposit(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    """A `Session` do lance já tem a carteira no identity map (saldo antigo). Sem
    `populate_existing` na trava, o lance usaria 5 000 e seria recusado."""
    set_wallet(seeded, BOB, 5_000)
    lot_id = live_lot(seeded, starting_bid_cents=8_000)
    outcome: list[Any] = []

    def bid_with_preloaded_wallet() -> Any:
        with seeded() as session:
            stale = session.get(Wallet, BOB)
            assert stale is not None and stale.total_balance_cents == 5_000
            result = place_bid(
                session,
                lot_id=lot_id,
                bidder_id=BOB,
                amount_cents=8_000,
                integrity=integrity(),
            )
            if isinstance(result, PlacedBid):
                session.commit()
            return result

    def deposit_a(session: Session) -> Wallet:
        result = deposit(session, BOB, 4_000)
        assert isinstance(result, Wallet)
        return result

    overlapped(
        seeded,
        db_engine,
        deposit_a,
        lambda: thread_for(bid_with_preloaded_wallet, outcome, "bid-preloaded"),
        matcher=is_wallet_lock,
    )

    (placed,) = outcome
    assert isinstance(placed, PlacedBid), placed
    assert wallet_row(seeded, BOB) == (9_000, 8_000)


def test_a_deposit_over_http_and_a_bid_over_http_do_not_lose_each_other(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    set_wallet(seeded, BOB, 20_000)
    lot_id = live_lot(seeded, starting_bid_cents=10_000)
    client: TestClient = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    assert login(client, HTTPS_ORIGIN, OTHER_BIDDER_EMAIL).status_code == 200
    outcome: list[Any] = []

    def post_deposit() -> Any:
        return client.post(
            "/api/wallet/deposit",
            json={"amount_cents": 5_000},
            headers=json_headers(HTTPS_ORIGIN),
        )

    overlapped(
        seeded,
        db_engine,
        lambda s: hold_bid(s, lot_id, BOB, 10_000),
        lambda: thread_for(post_deposit, outcome, "deposit-http"),
        matcher=is_wallet_lock,
    )

    (response,) = outcome
    assert response.status_code == 200
    assert response.json()["total_balance_cents"] == 25_000
    assert wallet_row(seeded, BOB) == (25_000, 10_000)
    assert_invariants(seeded)
