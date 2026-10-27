"""O serviço de lance sobre PostgreSQL real (Story 3.4; CAP-1, CAP-4, CAP-5, CAP-6).

Regras de negócio, contabilidade das carteiras, anti-sniping, hora do banco, ordem dos
statements, cadeia gravada e reuso dos primitives. A concorrência fica em
`test_bid_concurrency.py`; as adulterações, em `test_bid_integrity_gate.py`."""

import hashlib
import re
import uuid
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import bids
from app.bid_integrity import (
    GENESIS_HASH,
    CanonicalBid,
    canonical_bid_bytes,
    compute_bid_hash,
    generate_bidder_alias,
)
from app.bid_rules import BidRefusal
from app.bids import IntegrityConflict, PlacedBid
from app.money import MAX_CENTS
from tests.auth_support import BIDDER_EMAIL, OTHER_BIDDER_EMAIL, seeded_id
from tests.bid_support import (
    add_bidder,
    assert_authenticated,
    assert_invariants,
    bid_rows,
    call_log,
    db_snapshot,
    hold_bid,
    live_lot,
    locked_wallet_ids,
    lot_state,
    lot_update_columns,
    run_bid,
    service_trace,
    statement_log,
    tamper,
)
from tests.lot_support import db_now, integrity_secrets
from tests.wallet_support import seed_users_with_wallets, set_wallet, wallet_row

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


def accepted(result: Any) -> PlacedBid:
    assert isinstance(result, PlacedBid), result
    return result


# --- T-FIRST / T-NEXT ---


def test_the_first_bid_must_reach_the_starting_bid(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000)

    assert run_bid(seeded, lot_id, ALICE, 9_999) is BidRefusal.BELOW_MINIMUM
    placed = accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    assert placed.sequence == 1
    (row,) = bid_rows(seeded, lot_id)
    assert row["previous_hash"] == GENESIS_HASH
    assert (row["amount_cents"], row["bidder_id"]) == (10_000, ALICE)
    lot = lot_state(seeded, lot_id)
    assert (lot["current_bid_cents"], lot["current_leader_id"]) == (10_000, ALICE)
    assert lot["bid_count"] == 1 and lot["final_hash"] == row["current_hash"]
    assert_authenticated(seeded, lot_id)
    assert_invariants(seeded)


def test_the_next_bid_must_reach_the_current_bid_plus_the_increment(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=1_000)
    accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    assert run_bid(seeded, lot_id, BOB, 10_999) is BidRefusal.BELOW_MINIMUM
    placed = accepted(run_bid(seeded, lot_id, BOB, 11_000))

    assert placed.sequence == 2
    first, second = bid_rows(seeded, lot_id)
    assert second["previous_hash"] == first["current_hash"]
    assert_authenticated(seeded, lot_id)
    assert_invariants(seeded)


def test_a_bid_in_a_lot_that_does_not_exist_is_none(
    seeded: sessionmaker[Session],
) -> None:
    before = db_snapshot(seeded)

    assert run_bid(seeded, uuid.uuid4(), ALICE, 10_000) is None

    assert db_snapshot(seeded) == before


# --- T-SELF ---


def test_the_leader_cannot_cover_their_own_bid_and_no_wallet_is_locked(
    seeded: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    lot_id = live_lot(seeded)
    accepted(run_bid(seeded, lot_id, ALICE, 10_000))
    before = db_snapshot(seeded)
    events = call_log(monkeypatch)

    assert run_bid(seeded, lot_id, ALICE, 50_000) is BidRefusal.ALREADY_WINNING

    assert db_snapshot(seeded) == before
    assert "lock_wallet" not in events
    assert "evaluate_post_wallet" not in events


# --- T-BAL ---


def test_the_available_balance_discounts_what_is_committed_in_another_lot(
    seeded: sessionmaker[Session],
) -> None:
    set_wallet(seeded, ALICE, 10_000)
    other = live_lot(seeded, starting_bid_cents=5_000)
    accepted(run_bid(seeded, other, ALICE, 5_000))
    lot_id = live_lot(seeded, starting_bid_cents=1_000)
    before = db_snapshot(seeded)

    assert run_bid(seeded, lot_id, ALICE, 6_000) is BidRefusal.INSUFFICIENT_BALANCE
    assert db_snapshot(seeded) == before

    placed = accepted(run_bid(seeded, lot_id, ALICE, 5_000))  # exatamente o disponível

    assert wallet_row(seeded, ALICE) == (10_000, 10_000)
    assert placed.wallet.committed_balance_cents == 10_000
    assert_invariants(seeded)


# --- T-OUTBID ---


def test_outbidding_releases_the_old_leader_and_keeps_their_other_commitments(
    seeded: sessionmaker[Session],
) -> None:
    lot_one = live_lot(seeded, starting_bid_cents=10_000)
    lot_two = live_lot(seeded, starting_bid_cents=20_000)
    accepted(run_bid(seeded, lot_one, ALICE, 10_000))
    accepted(run_bid(seeded, lot_two, ALICE, 20_000))
    assert wallet_row(seeded, ALICE) == (100_000, 30_000)

    placed = accepted(run_bid(seeded, lot_one, BOB, 12_000))

    # Alice devolve só o lance atual deste lote; o do outro lote continua comprometido.
    assert wallet_row(seeded, ALICE) == (100_000, 20_000)
    assert wallet_row(seeded, BOB) == (100_000, 12_000)
    assert placed.wallet.user_id == BOB
    assert (
        placed.wallet.total_balance_cents,
        placed.wallet.committed_balance_cents,
    ) == (
        100_000,
        12_000,
    )
    lot = lot_state(seeded, lot_one)
    assert (lot["current_bid_cents"], lot["current_leader_id"]) == (12_000, BOB)
    assert lot_state(seeded, lot_two)["current_leader_id"] == ALICE
    assert_invariants(seeded)


def test_a_bid_that_overbids_the_same_user_in_a_third_lot_never_assigns_the_amount(
    seeded: sessionmaker[Session],
) -> None:
    """O comprometido é somado e subtraído, nunca atribuído: o que Bob já tem em outro
    lote sobrevive ao lance novo."""
    lot_one = live_lot(seeded, starting_bid_cents=10_000)
    lot_two = live_lot(seeded, starting_bid_cents=7_000)
    accepted(run_bid(seeded, lot_two, BOB, 7_000))

    accepted(run_bid(seeded, lot_one, BOB, 10_000))

    assert wallet_row(seeded, BOB) == (100_000, 17_000)
    assert_invariants(seeded)


# --- T-PHASE ---


def test_a_scheduled_lot_refuses_with_lot_not_started_and_changes_nothing(
    seeded: sessionmaker[Session],
) -> None:
    now = db_now(seeded)
    lot_id = live_lot(
        seeded, starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=3)
    )
    before = db_snapshot(seeded)

    assert run_bid(seeded, lot_id, ALICE, 10_000) is BidRefusal.LOT_NOT_STARTED

    assert db_snapshot(seeded) == before


def test_an_ended_lot_refuses_with_lot_ended_and_is_never_settled_or_reopened(
    seeded: sessionmaker[Session],
) -> None:
    now = db_now(seeded)
    lot_id = live_lot(
        seeded, starts_at=now - timedelta(hours=2), ends_at=now - timedelta(hours=1)
    )
    before = db_snapshot(seeded)

    assert run_bid(seeded, lot_id, ALICE, 10_000) is BidRefusal.LOT_ENDED

    assert db_snapshot(seeded) == before


# --- T-SNIPE (1), (2), (4) ---


def test_a_bid_inside_the_window_renews_the_end_to_the_locked_instant_plus_two_minutes(
    seeded: sessionmaker[Session],
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ends_at = db_now(seeded) + timedelta(seconds=60)
    lot_id = live_lot(seeded, ends_at=ends_at)
    stored_end = lot_state(seeded, lot_id)["ends_at"]
    read_instants: list[Any] = []
    real = bids.database_now

    def spy(session: Session) -> Any:
        instant = real(session)
        read_instants.append(instant)
        return instant

    monkeypatch.setattr(bids, "database_now", spy)

    with statement_log(db_engine) as log:
        placed = accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    # AD-5 (revisada em 27/10/2026): novo fim = `now` + 2 min, com o `clock_timestamp()`
    # lido uma única vez depois da trava do lote (AD-6), o mesmo do `placed_at`.
    trace = service_trace(log)
    assert trace[:2] == ["lock_lot", "clock"] and trace.count("clock") == 1
    (instant,) = read_instants
    assert placed.anti_sniping_applied is True
    assert placed.placed_at == instant
    assert placed.ends_at == instant + timedelta(minutes=2)
    assert lot_state(seeded, lot_id)["ends_at"] == instant + timedelta(minutes=2)
    # Não é mais o fim lido + 2 min (regra anterior, descartada).
    assert placed.ends_at != stored_end + timedelta(minutes=2)
    assert placed.ends_at > stored_end


def clock_at(monkeypatch: pytest.MonkeyPatch, instant: Any) -> None:
    """Fixa o instante que o serviço lê depois da trava, para provar o limite exato dos
    2 minutos no caminho real (trava, histórico, carteiras, gravação) em PostgreSQL."""
    monkeypatch.setattr(bids, "database_now", lambda session: instant)


@pytest.mark.parametrize(
    ("remaining", "applied"),
    [
        pytest.param(timedelta(minutes=2), False, id="exactly-2min"),
        pytest.param(
            timedelta(minutes=2) - timedelta(microseconds=1), True, id="2min-1us"
        ),
        pytest.param(timedelta(minutes=1), True, id="1min"),
        pytest.param(timedelta(microseconds=1), True, id="1us"),
        pytest.param(timedelta(minutes=2, microseconds=1), False, id="2min+1us"),
    ],
)
def test_the_window_boundaries_on_the_real_path_use_the_locked_instant(
    seeded: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    remaining: timedelta,
    applied: bool,
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(minutes=10))
    stored_end = lot_state(seeded, lot_id)["ends_at"]
    instant = stored_end - remaining
    clock_at(monkeypatch, instant)

    placed = accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    expected_end = instant + timedelta(minutes=2) if applied else stored_end
    assert placed.placed_at == instant
    assert placed.anti_sniping_applied is applied
    assert placed.ends_at == expected_end
    assert lot_state(seeded, lot_id)["ends_at"] == expected_end
    assert_authenticated(seeded, lot_id)


def test_exactly_two_minutes_remaining_does_not_write_ends_at(
    seeded: sessionmaker[Session],
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(minutes=10))
    stored_end = lot_state(seeded, lot_id)["ends_at"]
    clock_at(monkeypatch, stored_end - timedelta(minutes=2))

    with statement_log(db_engine) as log:
        placed = accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    assert placed.anti_sniping_applied is False and placed.ends_at == stored_end
    assert "ends_at" not in lot_update_columns(log)


@pytest.mark.parametrize(
    "after_end",
    [timedelta(0), timedelta(microseconds=1), timedelta(minutes=5)],
    ids=["at-end", "end+1us", "end+5min"],
)
def test_a_bid_at_or_after_the_end_is_refused_and_never_changes_the_end(
    seeded: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    after_end: timedelta,
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(minutes=10))
    stored_end = lot_state(seeded, lot_id)["ends_at"]
    before = db_snapshot(seeded)
    clock_at(monkeypatch, stored_end + after_end)

    assert run_bid(seeded, lot_id, ALICE, 10_000) is BidRefusal.LOT_ENDED

    assert db_snapshot(seeded) == before
    assert lot_state(seeded, lot_id)["ends_at"] == stored_end


def test_a_second_valid_bid_in_the_window_renews_again_from_its_own_instant(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(seconds=60))

    first = accepted(run_bid(seeded, lot_id, ALICE, 10_000))
    second = accepted(run_bid(seeded, lot_id, BOB, 11_000))

    # O fim da primeira renovação deixa menos de 2 min (o segundo instante é posterior).
    assert first.anti_sniping_applied is True
    assert first.ends_at == first.placed_at + timedelta(minutes=2)
    assert second.placed_at > first.placed_at
    assert second.anti_sniping_applied is True
    assert second.ends_at == second.placed_at + timedelta(minutes=2)
    assert second.ends_at > first.ends_at
    assert lot_state(seeded, lot_id)["ends_at"] == second.ends_at
    assert_authenticated(seeded, lot_id)


def test_a_bid_outside_the_window_leaves_the_end_alone(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded)  # fim em +1 h
    stored_end = lot_state(seeded, lot_id)["ends_at"]

    placed = accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    assert placed.anti_sniping_applied is False
    assert placed.ends_at == stored_end
    assert lot_state(seeded, lot_id)["ends_at"] == stored_end


def test_refused_bids_inside_the_window_never_extend_the_end(
    seeded: sessionmaker[Session],
) -> None:
    ends_at = db_now(seeded) + timedelta(seconds=60)
    lot_id = live_lot(seeded, ends_at=ends_at, starting_bid_cents=10_000)
    set_wallet(seeded, ALICE, 5_000)
    before = db_snapshot(seeded)

    assert run_bid(seeded, lot_id, BOB, 9_999) is BidRefusal.BELOW_MINIMUM  # mínimo
    assert run_bid(seeded, lot_id, ALICE, 10_000) is BidRefusal.INSUFFICIENT_BALANCE

    assert db_snapshot(seeded) == before


# --- T-CLOCK (a) e (c) ---


def test_the_lot_is_locked_before_the_single_database_clock_read(
    seeded: sessionmaker[Session],
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lot_id = live_lot(seeded)
    read_instants: list[Any] = []
    real = bids.database_now

    def spy(session: Session) -> Any:
        instant = real(session)
        read_instants.append(instant)
        return instant

    monkeypatch.setattr(bids, "database_now", spy)

    with statement_log(db_engine) as log:
        placed = accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    trace = service_trace(log)
    assert trace[:2] == ["lock_lot", "clock"]
    assert trace.count("clock") == 1  # nenhum relógio Python, nenhum segundo instante
    assert not log.saw("now()") and not log.saw("CURRENT_TIMESTAMP")
    (instant,) = read_instants
    (row,) = bid_rows(seeded, lot_id)
    assert row["placed_at"] == instant == placed.placed_at  # µs idênticos


def test_the_canonical_bytes_of_the_stored_row_reproduce_the_stored_hash(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded)
    accepted(run_bid(seeded, lot_id, ALICE, 10_000))
    (row,) = bid_rows(seeded, lot_id)

    canonical = CanonicalBid(
        v=row["canonical_version"],
        lot_id=row["lot_id"],
        sequence=row["sequence"],
        bidder_alias=row["bidder_alias"],
        amount_cents=row["amount_cents"],
        timestamp=row["placed_at"],
        previous_hash=row["previous_hash"],
    )

    payload = canonical_bid_bytes(canonical)
    # Seis casas e `Z`, mesmo que a fração fosse zero.
    assert re.search(rb'"timestamp":"[^"]+\.\d{6}Z"', payload)
    assert hashlib.sha256(payload).hexdigest() == row["current_hash"]
    assert compute_bid_hash(canonical) == row["current_hash"]


def test_the_service_runs_in_read_committed(seeded: sessionmaker[Session]) -> None:
    lot_id = live_lot(seeded)
    with seeded() as session:
        accepted(hold_bid(session, lot_id, ALICE, 10_000))
        isolation = session.execute(text("SHOW transaction_isolation")).scalar_one()
        session.rollback()
    assert isolation == "read committed"


# --- T-ORDER ---


def two_users_in_order(seeded: sessionmaker[Session]) -> tuple[uuid.UUID, uuid.UUID]:
    first, second = add_bidder(seeded, 100_000), add_bidder(seeded, 100_000)
    return (min(first, second), max(first, second))


@pytest.mark.parametrize("leader_is_lower", [True, False])
@pytest.mark.parametrize("extension", [False, True])
def test_the_statements_run_in_the_contract_order(
    seeded: sessionmaker[Session],
    db_engine: Engine,
    leader_is_lower: bool,
    extension: bool,
) -> None:
    lower, higher = two_users_in_order(seeded)
    leader, challenger = (lower, higher) if leader_is_lower else (higher, lower)
    lot_id = live_lot(seeded)  # fim em +1 h: o primeiro lance não estende
    accepted(run_bid(seeded, lot_id, leader, 10_000))
    if extension:  # o fim não é autenticado pela âncora v1: dentro da janela de 2 min
        tamper(
            seeded,
            "UPDATE lots SET ends_at = :ends_at WHERE id = :id",
            ends_at=db_now(seeded) + timedelta(seconds=60),
            id=lot_id,
        )

    with statement_log(db_engine) as log:
        accepted(run_bid(seeded, lot_id, challenger, 11_000))

    assert service_trace(log) == [
        "lock_lot",
        "clock",
        "history",
        "lock_wallet",
        "lock_wallet",
        "update_wallets",
        "insert_bid",
        "update_lot",
    ]
    # Carteiras em `user_id` crescente, qualquer que seja o papel de cada uma.
    assert locked_wallet_ids(log) == [lower, higher]
    # A releitura do histórico é por colunas, ordenada, e nunca por agregação.
    (history,) = [s for s in log.statements if s.upper().startswith("SELECT BIDS.")]
    assert "ORDER BY bids.sequence" in history
    assert not re.search(r"\b(max|min|count)\(", history, re.IGNORECASE)
    # Um único `UPDATE lots`, coerente; `ends_at` só quando houve extensão.
    base = [
        "current_bid_cents",
        "current_leader_id",
        "bid_count",
        "final_hash",
        "anchor_hmac",
    ]
    columns = lot_update_columns(log)
    assert sorted(columns) == sorted(base + (["ends_at"] if extension else []))


def test_a_refusal_before_the_wallet_step_never_selects_wallets(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)
    accepted(run_bid(seeded, lot_id, ALICE, 10_000))

    with statement_log(db_engine) as log:
        assert run_bid(seeded, lot_id, BOB, 10_999) is BidRefusal.BELOW_MINIMUM

    assert service_trace(log) == ["lock_lot", "clock", "history"]


def test_the_bidder_wallet_alone_is_locked_when_there_is_no_leader(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)

    with statement_log(db_engine) as log:
        accepted(run_bid(seeded, lot_id, BOB, 10_000))

    assert locked_wallet_ids(log) == [BOB]


# --- T-CHAIN ---


def test_five_accepted_bids_form_a_continuous_authenticated_chain(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=1_000)
    other_lot = live_lot(seeded)
    amounts = [10_000, 11_000, 13_000, 14_000, 20_000]
    users = [ALICE, BOB, ALICE, BOB, ALICE]
    for amount, user in zip(amounts, users, strict=True):
        accepted(run_bid(seeded, lot_id, user, amount))
    accepted(run_bid(seeded, other_lot, ALICE, 10_000))

    rows = bid_rows(seeded, lot_id)
    assert [row["sequence"] for row in rows] == [1, 2, 3, 4, 5]
    assert [row["amount_cents"] for row in rows] == amounts
    assert rows[0]["previous_hash"] == GENESIS_HASH
    for before, after in zip(rows, rows[1:], strict=False):
        assert after["previous_hash"] == before["current_hash"]
    assert_authenticated(seeded, lot_id)
    assert_authenticated(seeded, other_lot)
    _, pseudonym = integrity_secrets()
    for row, user in zip(rows, users, strict=True):
        assert row["bidder_id"] == user
        assert row["bidder_alias"] == generate_bidder_alias(
            lot_id=lot_id, user_id=user, pseudonym_secret=pseudonym
        )
    # O mesmo usuário tem pseudônimos diferentes em lotes diferentes.
    assert bid_rows(seeded, other_lot)[0]["bidder_alias"] != rows[0]["bidder_alias"]
    assert_invariants(seeded)


# --- T-REUSE ---


def test_an_accepted_bid_calls_each_primitive_in_the_contract_order(
    seeded: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    lot_id = live_lot(seeded)
    accepted(run_bid(seeded, lot_id, ALICE, 10_000))
    events = call_log(monkeypatch)
    wallet_args: list[tuple[int, int]] = []
    real_available = bids.available_cents

    def spy_available(total: int, committed: int) -> int:
        wallet_args.append((total, committed))
        return real_available(total, committed)

    monkeypatch.setattr(bids, "available_cents", spy_available)

    accepted(run_bid(seeded, lot_id, BOB, 11_000))

    # Ordem semântica (SR-01): o gate (cadeia e âncora) vem antes da pré-carteira.
    assert events == [
        "lock_lot",
        "database_now",
        "verify_bid_chain",
        "verify_anchor_hmac",
        "evaluate_pre_wallet",
        "lock_wallet",
        "lock_wallet",
        "available_cents",
        "evaluate_post_wallet",
    ]
    # `available_cents` recebe o saldo da carteira travada do licitante, uma só vez.
    assert wallet_args == [(100_000, 0)]


def test_an_integrity_conflict_never_reaches_the_business_rules(
    seeded: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    lot_id = live_lot(seeded, anchored=False)  # legado: sem âncora
    events = call_log(monkeypatch)

    result = run_bid(seeded, lot_id, ALICE, 10_000)

    assert isinstance(result, IntegrityConflict)
    assert "evaluate_pre_wallet" not in events
    assert "lock_wallet" not in events
    assert events[:2] == ["lock_lot", "database_now"]


def test_a_refusal_before_the_wallet_step_skips_the_post_step(
    seeded: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    lot_id = live_lot(seeded)
    events = call_log(monkeypatch)

    assert run_bid(seeded, lot_id, BOB, 9_999) is BidRefusal.BELOW_MINIMUM

    assert events.count("evaluate_pre_wallet") == 1
    assert "evaluate_post_wallet" not in events and "lock_wallet" not in events
    assert events.count("database_now") == 1


def test_bids_module_uses_the_integrity_primitives_by_name_and_no_clock() -> None:
    import ast
    from pathlib import Path

    source = Path(bids.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {"evaluate_pre_wallet", "evaluate_post_wallet", "lock_wallet"} <= imported
    assert {"database_now", "lock_lot", "available_cents"} <= imported
    assert "MAX(" not in source.upper().replace("MAX_CENTS", "")
    assert "datetime.now" not in source and "utcnow" not in source
    assert "now()" not in source and "CURRENT_TIMESTAMP" not in source.upper()
    assert "app.main" not in {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }


def test_max_cents_is_the_upper_bound_of_the_amount(
    seeded: sessionmaker[Session],
) -> None:
    set_wallet(seeded, ALICE, MAX_CENTS)
    lot_id = live_lot(seeded, starting_bid_cents=MAX_CENTS)

    placed = accepted(run_bid(seeded, lot_id, ALICE, MAX_CENTS))

    assert placed.wallet.committed_balance_cents == MAX_CENTS
    assert run_bid(seeded, lot_id, BOB, MAX_CENTS) is BidRefusal.BELOW_MINIMUM
