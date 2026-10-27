"""Regra pura da aceitação do lance, sem banco, HTTP nem relógio (Story 3.2, test-plan;
AD-5, AD-7, AD-26; P1 a P13, C1). Todo `now` é fixo e injetado."""

import dataclasses
import inspect
import uuid
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from types import SimpleNamespace

import pytest

import app.bid_rules as bid_rules
from app.bid_rules import (
    BidAccepted,
    BidAttempt,
    BidRefusal,
    CurrentBid,
    EligibleBid,
    LotBidState,
    evaluate_bid,
    evaluate_post_wallet,
    evaluate_pre_wallet,
    minimum_bid_cents,
)
from app.errors import MESSAGES
from app.lot_time import LotPhase, lot_phase
from app.money import MAX_CENTS

START = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
END = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
BEFORE = START - timedelta(hours=1)  # agendado
LIVE = START + timedelta(hours=1)  # ao vivo, restante 5 h (sem anti-sniping)
MICRO = timedelta(microseconds=1)
TWO_MIN = timedelta(minutes=2)
BIDDER = uuid.UUID(int=1)
OTHER = uuid.UUID(int=2)
STARTING = 10_000
INCREMENT = 1_000
CURRENT_AMOUNT = 20_000  # mínimo seguinte: 21_000
NAIVE = datetime(2026, 10, 25, 12, 0)
MINUS_THREE = timezone(timedelta(hours=-3))
PLUS_NINE = timezone(timedelta(hours=9))
PLUS_FIVE_THIRTY = timezone(timedelta(hours=5, minutes=30))


class FoldOffset(tzinfo):
    """Offset −3 h com fold=0 e −4 h com fold=1: uma hora ambígua sem depender da base
    de fusos do sistema."""

    def utcoffset(self, dt):
        return timedelta(hours=-4 if dt.fold else -3)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return None


def lot_state(
    *,
    starts_at: datetime = START,
    ends_at: datetime = END,
    starting: int = STARTING,
    increment: int = INCREMENT,
    current: CurrentBid | None = None,
) -> LotBidState:
    return LotBidState(
        starts_at=starts_at,
        ends_at=ends_at,
        starting_bid_cents=starting,
        min_increment_cents=increment,
        current=current,
    )


def leader(who: uuid.UUID, amount: int = CURRENT_AMOUNT) -> CurrentBid:
    return CurrentBid(amount_cents=amount, leader_id=who)


def attempt(amount: int, bidder: uuid.UUID = BIDDER) -> BidAttempt:
    return BidAttempt(bidder_id=bidder, amount_cents=amount)


def accepted(ends_at: datetime = END, extended: bool = False) -> BidAccepted:
    return BidAccepted(ends_at=ends_at, anti_sniping_applied=extended)


def eligible_bid() -> EligibleBid:
    result = evaluate_pre_wallet(lot_state(), attempt(STARTING), LIVE)
    assert isinstance(result, EligibleBid)
    return result


def count_calls(monkeypatch: pytest.MonkeyPatch, name: str) -> list[int]:
    """Troca `bid_rules.<name>` por um espião que conta e delega ao original."""
    calls: list[int] = []
    original = getattr(bid_rules, name)

    def spy(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(bid_rules, name, spy)
    return calls


# --- tipos e invariantes (P7, P10, D3 a D6, D9) ---

MONEY_FIELDS = [
    pytest.param(
        lambda v: CurrentBid(amount_cents=v, leader_id=OTHER),
        id="CurrentBid.amount_cents",
    ),
    pytest.param(lambda v: lot_state(starting=v), id="LotBidState.starting_bid_cents"),
    pytest.param(
        lambda v: lot_state(increment=v), id="LotBidState.min_increment_cents"
    ),
    pytest.param(lambda v: attempt(v), id="BidAttempt.amount_cents"),
]


@pytest.mark.parametrize("build", MONEY_FIELDS)
@pytest.mark.parametrize("bad", [True, False, 1.0, 1.5, "100", None])
def test_money_fields_reject_non_integer_cents(build, bad: object) -> None:
    with pytest.raises(ValueError, match="integer cents"):
        build(bad)


@pytest.mark.parametrize("build", MONEY_FIELDS)
@pytest.mark.parametrize("bad", [0, -1, MAX_CENTS + 1])
def test_money_fields_reject_out_of_range(build, bad: int) -> None:
    with pytest.raises(ValueError, match="out of range"):
        build(bad)


@pytest.mark.parametrize("build", MONEY_FIELDS)
@pytest.mark.parametrize("limit", [1, MAX_CENTS])
def test_money_fields_accept_the_limits(build, limit: int) -> None:
    build(limit)


@pytest.mark.parametrize("bad", [str(OTHER), 1, None])
def test_user_ids_must_be_uuid(bad: object) -> None:
    with pytest.raises(ValueError, match="leader_id must be a UUID"):
        CurrentBid(amount_cents=1, leader_id=bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bidder_id must be a UUID"):
        BidAttempt(bidder_id=bad, amount_cents=1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"starts_at": NAIVE}, id="starts_at-naive"),
        pytest.param({"ends_at": NAIVE}, id="ends_at-naive"),
        pytest.param({"starts_at": "2026-10-25"}, id="starts_at-not-datetime"),
        pytest.param({"ends_at": None}, id="ends_at-not-datetime"),
        pytest.param({"ends_at": START}, id="equal"),
        pytest.param({"starts_at": END, "ends_at": START}, id="reversed"),
    ],
)
def test_lot_times_are_validated_on_construction(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        lot_state(**kwargs)


@pytest.mark.parametrize("bad", [(20_000, OTHER), {"amount_cents": 20_000}])
def test_current_must_be_a_current_bid_or_none(bad: object) -> None:
    with pytest.raises(ValueError, match="current must be a CurrentBid or None"):
        lot_state(current=bad)  # type: ignore[arg-type]


def test_current_bid_below_starting_bid_is_corruption() -> None:
    with pytest.raises(ValueError, match="current bid below starting bid"):
        lot_state(current=leader(OTHER, STARTING - 1))
    lot_state(current=leader(OTHER, STARTING))


@pytest.mark.parametrize("bad", [1, "yes", None])
def test_bid_accepted_requires_aware_end_and_bool_flag(bad: object) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        BidAccepted(ends_at=NAIVE, anti_sniping_applied=False)
    with pytest.raises(ValueError, match="anti_sniping_applied must be a bool"):
        BidAccepted(ends_at=END, anti_sniping_applied=bad)  # type: ignore[arg-type]


def test_eligible_bid_cannot_be_forged() -> None:
    with pytest.raises(ValueError, match="issued only by evaluate_pre_wallet"):
        EligibleBid(amount_cents=1, ends_at=END, now=LIVE)
    with pytest.raises(ValueError, match="issued only by evaluate_pre_wallet"):
        dataclasses.replace(eligible_bid(), amount_cents=2)


BAD_BALANCES = [-1, MAX_CENTS + 1, True, 1.0, "1", None]


@pytest.mark.parametrize("bad", BAD_BALANCES)
def test_available_balance_is_validated_by_evaluate_bid(bad: object) -> None:
    with pytest.raises(ValueError, match="available_balance_cents"):
        evaluate_bid(lot_state(), attempt(STARTING), bad, LIVE)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", BAD_BALANCES)
def test_available_balance_is_validated_by_evaluate_post_wallet(bad: object) -> None:
    with pytest.raises(ValueError, match="available_balance_cents"):
        evaluate_post_wallet(eligible_bid(), bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("balance", [0, MAX_CENTS])
def test_available_balance_limits_are_valid(balance: int) -> None:
    evaluate_bid(lot_state(), attempt(STARTING), balance, LIVE)
    evaluate_post_wallet(eligible_bid(), balance)


@pytest.mark.parametrize("now", [END, BEFORE], ids=["ended", "scheduled"])
def test_corrupt_balance_is_never_hidden_behind_a_refusal(now: datetime) -> None:
    with pytest.raises(ValueError, match="available_balance_cents"):
        evaluate_bid(lot_state(), attempt(STARTING), -1, now)


def test_functions_reject_foreign_objects() -> None:
    with pytest.raises(ValueError, match="lot must be a LotBidState"):
        minimum_bid_cents(SimpleNamespace(current=None))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="lot must be a LotBidState"):
        evaluate_pre_wallet(SimpleNamespace(), attempt(1), LIVE)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="attempt must be a BidAttempt"):
        evaluate_pre_wallet(lot_state(), SimpleNamespace(), LIVE)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="eligible must be an EligibleBid"):
        evaluate_post_wallet(BidRefusal.LOT_ENDED, 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="eligible must be an EligibleBid"):
        evaluate_post_wallet(None, 0)  # type: ignore[arg-type]


def test_naive_now_is_refused_by_both_entry_points() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        evaluate_pre_wallet(lot_state(), attempt(STARTING), NAIVE)
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        evaluate_bid(lot_state(), attempt(STARTING), STARTING, NAIVE)


def test_exact_fields() -> None:
    def names(cls: type) -> set[str]:
        return {f.name for f in dataclasses.fields(cls)}

    assert names(CurrentBid) == {"amount_cents", "leader_id"}
    assert names(LotBidState) == {
        "starts_at",
        "ends_at",
        "starting_bid_cents",
        "min_increment_cents",
        "current",
    }
    assert names(BidAttempt) == {"bidder_id", "amount_cents"}
    assert names(BidAccepted) == {"ends_at", "anti_sniping_applied"}
    assert names(EligibleBid) == {"amount_cents", "ends_at", "now"}


def test_attempt_has_no_balance_parameter() -> None:
    with pytest.raises(TypeError):
        BidAttempt(  # type: ignore[call-arg]
            bidder_id=BIDDER, amount_cents=1, available_balance_cents=1
        )


def test_construction_is_keyword_only() -> None:
    with pytest.raises(TypeError):
        BidAttempt(BIDDER, 1)  # type: ignore[misc]
    with pytest.raises(TypeError):
        CurrentBid(1, BIDDER)  # type: ignore[misc]
    with pytest.raises(TypeError):
        BidAccepted(END, False)  # type: ignore[misc]


@pytest.mark.parametrize(
    ("build", "field", "value"),
    [
        (lambda: leader(OTHER), "amount_cents", 1),
        (lambda: lot_state(), "ends_at", START + timedelta(days=1)),
        (lambda: attempt(1), "amount_cents", 2),
        (lambda: accepted(), "anti_sniping_applied", True),
        (lambda: eligible_bid(), "amount_cents", 2),
    ],
    ids=["CurrentBid", "LotBidState", "BidAttempt", "BidAccepted", "EligibleBid"],
)
def test_domain_objects_are_frozen(build, field: str, value: object) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(build(), field, value)


def test_scheduled_lot_with_a_current_bid_is_not_corruption() -> None:
    result = evaluate_bid(
        lot_state(current=leader(OTHER)), attempt(21_000), MAX_CENTS, BEFORE
    )
    assert result is BidRefusal.LOT_NOT_STARTED


def test_refusal_codes_are_exactly_the_five_rules_plus_lot_cancelled() -> None:
    # Story 3.6, D4: `lot_cancelled` é devolvido por `place_bid` depois do gate; as
    # regras puras continuam produzindo só os cinco anteriores.
    assert {r.value for r in BidRefusal} == {
        "lot_not_started",
        "lot_ended",
        "below_minimum",
        "already_winning",
        "insufficient_balance",
        "lot_cancelled",
    }


def test_refusal_codes_are_http_catalog_codes() -> None:
    # Story 3.4: "o contrato HTTP nasce com o endpoint". Cada recusa tem mensagem.
    assert {r.value for r in BidRefusal} <= set(MESSAGES)


# --- período, primeiro lance, lance seguinte, líder, saldo (CAP-3 a CAP-6) ---

# `now` e o esperado digitados à mão; sem lance, `attempt(10_000)`, saldo suficiente.
PERIOD_GRID = [
    pytest.param(START - MICRO, BidRefusal.LOT_NOT_STARTED, id="start-1us"),
    pytest.param(START, accepted(), id="start"),
    pytest.param(START + timedelta(hours=3), accepted(), id="middle"),
    pytest.param(END - MICRO, accepted(END + TWO_MIN, True), id="end-1us"),
    pytest.param(END, BidRefusal.LOT_ENDED, id="end"),
    pytest.param(END + MICRO, BidRefusal.LOT_ENDED, id="end+1us"),
    pytest.param(
        START - timedelta(days=30), BidRefusal.LOT_NOT_STARTED, id="far-before"
    ),
    pytest.param(END + timedelta(days=30), BidRefusal.LOT_ENDED, id="far-after"),
]


@pytest.mark.parametrize(("now", "expected"), PERIOD_GRID)
def test_period_boundaries(now: datetime, expected: object) -> None:
    result = evaluate_bid(lot_state(), attempt(STARTING), MAX_CENTS, now)
    assert result == expected


@pytest.mark.parametrize(("now", "expected"), PERIOD_GRID)
def test_period_refusal_matches_lot_phase(now: datetime, expected: object) -> None:
    phase = lot_phase(START, END, now)
    result = evaluate_bid(lot_state(), attempt(STARTING), MAX_CENTS, now)
    if phase is LotPhase.SCHEDULED:
        assert result is BidRefusal.LOT_NOT_STARTED
    elif phase is LotPhase.ENDED:
        assert result is BidRefusal.LOT_ENDED
    else:
        assert not isinstance(result, BidRefusal)


@pytest.mark.parametrize(("now", "expected"), PERIOD_GRID)
def test_period_compares_instants_across_offsets(
    now: datetime, expected: object
) -> None:
    lot = lot_state(
        starts_at=START.astimezone(MINUS_THREE), ends_at=END.astimezone(MINUS_THREE)
    )
    result = evaluate_bid(lot, attempt(STARTING), MAX_CENTS, now.astimezone(PLUS_NINE))
    assert result == expected


def test_period_with_same_tzinfo_in_an_ambiguous_hour() -> None:
    tz = FoldOffset()
    lot = lot_state(
        starts_at=datetime(2026, 11, 1, 0, 0, tzinfo=tz),  # 03:00Z
        ends_at=datetime(2026, 11, 1, 1, 10, fold=1, tzinfo=tz),  # 05:10Z
    )
    # 01:30 com fold=0 é 04:30Z: ao vivo e fora da janela. Pelo relógio de parede,
    # 01:30 > 01:10 daria "encerrado".
    result = evaluate_bid(
        lot, attempt(STARTING), MAX_CENTS, datetime(2026, 11, 1, 1, 30, tzinfo=tz)
    )
    assert result == accepted(datetime(2026, 11, 1, 5, 10, tzinfo=UTC), False)
    # 02:09 com fold=0 é 05:09Z: dentro da janela; o fim vigente
    # 05:10Z recebe mais 2 min.
    result = evaluate_bid(
        lot, attempt(STARTING), MAX_CENTS, datetime(2026, 11, 1, 2, 9, tzinfo=tz)
    )
    assert result == accepted(datetime(2026, 11, 1, 5, 12, tzinfo=UTC), True)


@pytest.mark.parametrize(
    ("starting", "amount", "expected"),
    [
        (STARTING, 9_999, BidRefusal.BELOW_MINIMUM),
        (STARTING, 10_000, accepted()),
        (STARTING, 10_001, accepted()),
        (1, 1, accepted()),
    ],
)
def test_first_bid_minimum(starting: int, amount: int, expected: object) -> None:
    result = evaluate_bid(
        lot_state(starting=starting), attempt(amount), MAX_CENTS, LIVE
    )
    assert result == expected


@pytest.mark.parametrize(
    ("increment", "amount", "expected"),
    [
        (1_000, 20_999, BidRefusal.BELOW_MINIMUM),
        (1_000, 20_000, BidRefusal.BELOW_MINIMUM),
        (1_000, 15_000, BidRefusal.BELOW_MINIMUM),
        (1_000, 21_000, accepted()),
        (1_000, 21_001, accepted()),
        (1, 20_000, BidRefusal.BELOW_MINIMUM),
        (1, 20_001, accepted()),
    ],
)
def test_next_bid_minimum(increment: int, amount: int, expected: object) -> None:
    lot = lot_state(increment=increment, current=leader(OTHER, 20_000))
    assert evaluate_bid(lot, attempt(amount), MAX_CENTS, LIVE) == expected


@pytest.mark.parametrize(
    ("lot", "expected"),
    [
        (lot_state(), STARTING),
        (lot_state(starting=1), 1),
        (lot_state(current=leader(OTHER, 20_000), increment=1_000), 21_000),
        (lot_state(current=leader(OTHER, 20_000), increment=1), 20_001),
        (lot_state(starting=MAX_CENTS), MAX_CENTS),
        (lot_state(current=leader(OTHER, MAX_CENTS - 1_000)), MAX_CENTS),
        (lot_state(current=leader(OTHER, MAX_CENTS - 999)), None),
    ],
)
def test_minimum_bid_cents(lot: LotBidState, expected: int | None) -> None:
    assert minimum_bid_cents(lot) == expected


def test_leader_cannot_outbid_itself() -> None:
    lot = lot_state(current=leader(BIDDER))
    result = evaluate_bid(lot, attempt(21_000), MAX_CENTS, LIVE)
    assert result is BidRefusal.ALREADY_WINNING


def test_another_bidder_with_the_same_input_is_accepted() -> None:
    lot = lot_state(current=leader(OTHER))
    assert evaluate_bid(lot, attempt(21_000), MAX_CENTS, LIVE) == accepted()


def test_no_current_bid_means_no_leader() -> None:
    result = evaluate_bid(lot_state(), attempt(10_000, BIDDER), MAX_CENTS, LIVE)
    assert result == accepted()


@pytest.mark.parametrize(
    ("balance", "expected"),
    [
        (20_999, BidRefusal.INSUFFICIENT_BALANCE),
        (21_000, accepted()),
        (21_001, accepted()),
        (MAX_CENTS, accepted()),
        (0, BidRefusal.INSUFFICIENT_BALANCE),
    ],
)
def test_balance_boundaries(balance: int, expected: object) -> None:
    lot = lot_state(current=leader(OTHER))
    assert evaluate_bid(lot, attempt(21_000), balance, LIVE) == expected


def test_same_input_same_result_and_inputs_unchanged() -> None:
    lot = lot_state(current=leader(OTHER))
    bid = attempt(21_000)
    first = evaluate_bid(lot, bid, 50_000, LIVE)
    second = evaluate_bid(lot, bid, 50_000, LIVE)
    assert first == second == accepted()
    assert lot == lot_state(current=leader(OTHER))
    assert bid == attempt(21_000)


# --- precedência (P3, D11): contrato, nunca derivado do código ---


def test_not_started_beats_below_minimum() -> None:
    result = evaluate_bid(lot_state(), attempt(9_999), MAX_CENTS, BEFORE)
    assert result is BidRefusal.LOT_NOT_STARTED


def test_ended_beats_below_minimum() -> None:
    result = evaluate_bid(lot_state(), attempt(9_999), MAX_CENTS, END)
    assert result is BidRefusal.LOT_ENDED


def test_ended_beats_already_winning() -> None:
    lot = lot_state(current=leader(BIDDER))
    assert evaluate_bid(lot, attempt(21_000), MAX_CENTS, END) is BidRefusal.LOT_ENDED


def test_below_minimum_beats_already_winning() -> None:
    lot = lot_state(current=leader(BIDDER))
    result = evaluate_bid(lot, attempt(20_500), MAX_CENTS, LIVE)
    assert result is BidRefusal.BELOW_MINIMUM


def test_below_minimum_beats_insufficient_balance() -> None:
    result = evaluate_bid(lot_state(), attempt(9_999), 0, LIVE)
    assert result is BidRefusal.BELOW_MINIMUM


def test_already_winning_beats_insufficient_balance() -> None:
    lot = lot_state(current=leader(BIDDER))
    result = evaluate_bid(lot, attempt(21_000), 20_999, LIVE)
    assert result is BidRefusal.ALREADY_WINNING


def test_already_winning_uses_uuid_equality_not_identity() -> None:
    leader_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    bidder_id = uuid.UUID(str(leader_id))
    assert leader_id == bidder_id
    assert leader_id is not bidder_id

    lot = lot_state(current=leader(leader_id))
    bid = attempt(21_000, bidder=bidder_id)
    assert evaluate_pre_wallet(lot, bid, LIVE) is BidRefusal.ALREADY_WINNING
    assert evaluate_bid(lot, bid, MAX_CENTS, LIVE) is BidRefusal.ALREADY_WINNING


def test_only_insufficient_balance() -> None:
    lot = lot_state(current=leader(OTHER))
    result = evaluate_bid(lot, attempt(21_000), 20_999, LIVE)
    assert result is BidRefusal.INSUFFICIENT_BALANCE


def test_ended_beats_everything() -> None:
    lot = lot_state(current=leader(BIDDER))
    assert evaluate_bid(lot, attempt(20_500), 0, END) is BidRefusal.LOT_ENDED


def test_not_started_beats_leader_and_balance() -> None:
    lot = lot_state(current=leader(BIDDER))
    result = evaluate_bid(lot, attempt(21_000), 0, BEFORE)
    assert result is BidRefusal.LOT_NOT_STARTED


NS = BidRefusal.LOT_NOT_STARTED
EN = BidRefusal.LOT_ENDED
BM = BidRefusal.BELOW_MINIMUM
AW = BidRefusal.ALREADY_WINNING
IB = BidRefusal.INSUFFICIENT_BALANCE
ACC = "ACCEPT"  # no teste vira `accepted()` (fim em END, sem extensão)

# Entradas: o `now` de cada fase, o lance atual, o valor e o saldo. Tentativa sempre de
# BIDDER. OK = 50_000 e LOW = 9_999 (abaixo do mínimo em todos os casos); SUFF = 50_000
# e INSUF = 9_998. O esperado de cada linha é digitado, nunca calculado.
PHASE_NOW = {"SCHEDULED": BEFORE, "LIVE": LIVE, "ENDED": END}
CURRENT_BY_NAME = {
    "NONE": None,
    "OTHER": leader(OTHER),
    "SELF": leader(BIDDER),
}
AMOUNT_BY_NAME = {"OK": 50_000, "LOW": 9_999}
BALANCE_BY_NAME = {"SUFF": 50_000, "INSUF": 9_998}

# fmt: off
PRECEDENCE_TABLE = [
    ("SCHEDULED", "NONE", "OK", "SUFF", NS),    # 1
    ("SCHEDULED", "NONE", "OK", "INSUF", NS),   # 2
    ("SCHEDULED", "NONE", "LOW", "SUFF", NS),   # 3
    ("SCHEDULED", "NONE", "LOW", "INSUF", NS),  # 4
    ("SCHEDULED", "OTHER", "OK", "SUFF", NS),   # 5
    ("SCHEDULED", "OTHER", "OK", "INSUF", NS),  # 6
    ("SCHEDULED", "OTHER", "LOW", "SUFF", NS),  # 7
    ("SCHEDULED", "OTHER", "LOW", "INSUF", NS), # 8
    ("SCHEDULED", "SELF", "OK", "SUFF", NS),    # 9
    ("SCHEDULED", "SELF", "OK", "INSUF", NS),   # 10
    ("SCHEDULED", "SELF", "LOW", "SUFF", NS),   # 11
    ("SCHEDULED", "SELF", "LOW", "INSUF", NS),  # 12
    ("LIVE", "NONE", "OK", "SUFF", ACC),        # 13
    ("LIVE", "NONE", "OK", "INSUF", IB),        # 14
    ("LIVE", "NONE", "LOW", "SUFF", BM),        # 15
    ("LIVE", "NONE", "LOW", "INSUF", BM),       # 16
    ("LIVE", "OTHER", "OK", "SUFF", ACC),       # 17
    ("LIVE", "OTHER", "OK", "INSUF", IB),       # 18
    ("LIVE", "OTHER", "LOW", "SUFF", BM),       # 19
    ("LIVE", "OTHER", "LOW", "INSUF", BM),      # 20
    ("LIVE", "SELF", "OK", "SUFF", AW),         # 21
    ("LIVE", "SELF", "OK", "INSUF", AW),        # 22
    ("LIVE", "SELF", "LOW", "SUFF", BM),        # 23
    ("LIVE", "SELF", "LOW", "INSUF", BM),       # 24
    ("ENDED", "NONE", "OK", "SUFF", EN),        # 25
    ("ENDED", "NONE", "OK", "INSUF", EN),       # 26
    ("ENDED", "NONE", "LOW", "SUFF", EN),       # 27
    ("ENDED", "NONE", "LOW", "INSUF", EN),      # 28
    ("ENDED", "OTHER", "OK", "SUFF", EN),       # 29
    ("ENDED", "OTHER", "OK", "INSUF", EN),      # 30
    ("ENDED", "OTHER", "LOW", "SUFF", EN),      # 31
    ("ENDED", "OTHER", "LOW", "INSUF", EN),     # 32
    ("ENDED", "SELF", "OK", "SUFF", EN),        # 33
    ("ENDED", "SELF", "OK", "INSUF", EN),       # 34
    ("ENDED", "SELF", "LOW", "SUFF", EN),       # 35
    ("ENDED", "SELF", "LOW", "INSUF", EN),      # 36
]
# fmt: on
ROW_IDS = [f"row-{n}" for n in range(1, len(PRECEDENCE_TABLE) + 1)]
PRE_WALLET_REFUSALS = {NS, EN, BM, AW}


def row_inputs(phase: str, current: str, amount: str, balance: str):
    lot = lot_state(current=CURRENT_BY_NAME[current])
    return (
        lot,
        attempt(AMOUNT_BY_NAME[amount]),
        BALANCE_BY_NAME[balance],
        (PHASE_NOW[phase]),
    )


def row_expected(expected: object) -> object:
    return accepted() if expected == ACC else expected


def test_precedence_table_has_36_rows() -> None:
    assert len(PRECEDENCE_TABLE) == 36


@pytest.mark.parametrize(
    ("phase", "current", "amount", "balance", "expected"),
    PRECEDENCE_TABLE,
    ids=ROW_IDS,
)
def test_precedence_table(phase, current, amount, balance, expected) -> None:
    lot, bid, available, now = row_inputs(phase, current, amount, balance)
    assert evaluate_bid(lot, bid, available, now) == row_expected(expected)


# --- MAX_CENTS (P6) ---

MAX_LOTS = [
    lot_state(starting=1),
    lot_state(starting=MAX_CENTS),
    lot_state(current=leader(OTHER, MAX_CENTS - 1_000)),
    lot_state(current=leader(OTHER, MAX_CENTS - 999)),
    lot_state(starting=1, increment=MAX_CENTS, current=leader(OTHER, MAX_CENTS)),
    lot_state(starting=1, increment=MAX_CENTS, current=leader(OTHER, 1)),
]


def test_max_amount_is_accepted() -> None:
    result = evaluate_bid(lot_state(starting=1), attempt(MAX_CENTS), MAX_CENTS, LIVE)
    assert result == accepted()


def test_starting_at_max() -> None:
    lot = lot_state(starting=MAX_CENTS)
    assert minimum_bid_cents(lot) == MAX_CENTS
    assert evaluate_bid(lot, attempt(MAX_CENTS), MAX_CENTS, LIVE) == accepted()
    below = evaluate_bid(lot, attempt(MAX_CENTS - 1), MAX_CENTS, LIVE)
    assert below is BidRefusal.BELOW_MINIMUM


def test_next_minimum_exactly_max() -> None:
    lot = lot_state(current=leader(OTHER, MAX_CENTS - 1_000))
    assert minimum_bid_cents(lot) == MAX_CENTS
    assert evaluate_bid(lot, attempt(MAX_CENTS), MAX_CENTS, LIVE) == accepted()
    below = evaluate_bid(lot, attempt(MAX_CENTS - 1), MAX_CENTS, LIVE)
    assert below is BidRefusal.BELOW_MINIMUM


def test_next_minimum_one_above_max_is_unreachable() -> None:
    lot = lot_state(current=leader(OTHER, MAX_CENTS - 999))
    assert minimum_bid_cents(lot) is None
    result = evaluate_bid(lot, attempt(MAX_CENTS), MAX_CENTS, LIVE)
    assert result is BidRefusal.BELOW_MINIMUM


def test_current_and_increment_at_max() -> None:
    lot = lot_state(starting=1, increment=MAX_CENTS, current=leader(OTHER, MAX_CENTS))
    assert minimum_bid_cents(lot) is None
    result = evaluate_bid(lot, attempt(MAX_CENTS), MAX_CENTS, LIVE)
    assert result is BidRefusal.BELOW_MINIMUM


def test_increment_max_after_first_bid() -> None:
    lot = lot_state(starting=1, increment=MAX_CENTS, current=leader(OTHER, 1))
    assert minimum_bid_cents(lot) is None
    result = evaluate_bid(lot, attempt(MAX_CENTS), MAX_CENTS, LIVE)
    assert result is BidRefusal.BELOW_MINIMUM


@pytest.mark.parametrize("lot", MAX_LOTS)
def test_minimum_never_exceeds_max(lot: LotBidState) -> None:
    minimum = minimum_bid_cents(lot)
    assert minimum is None or (type(minimum) is int and minimum <= MAX_CENTS)


# --- composição pré/pós-carteira (P11, C1, D2, D12) ---


def test_pre_wallet_signature_has_no_balance() -> None:
    def params(fn) -> list[str]:
        return list(inspect.signature(fn).parameters)

    assert params(evaluate_pre_wallet) == ["lot", "attempt", "now"]
    assert params(evaluate_post_wallet) == ["eligible", "available_balance_cents"]
    assert params(evaluate_bid) == ["lot", "attempt", "available_balance_cents", "now"]


@pytest.mark.parametrize(
    ("phase", "current", "amount", "balance", "expected"),
    PRECEDENCE_TABLE,
    ids=ROW_IDS,
)
def test_pre_wallet_matches_the_table(
    phase, current, amount, balance, expected
) -> None:
    lot, bid, _, now = row_inputs(phase, current, amount, balance)
    result = evaluate_pre_wallet(lot, bid, now)
    if expected in PRE_WALLET_REFUSALS:
        assert result is expected
    else:
        assert isinstance(result, EligibleBid)


@pytest.mark.parametrize(
    ("phase", "current", "amount", "balance", "expected"),
    PRECEDENCE_TABLE,
    ids=ROW_IDS,
)
def test_composition_equals_evaluate_bid(
    phase, current, amount, balance, expected
) -> None:
    lot, bid, available, now = row_inputs(phase, current, amount, balance)
    pre = evaluate_pre_wallet(lot, bid, now)
    composed = (
        pre if isinstance(pre, BidRefusal) else evaluate_post_wallet(pre, available)
    )
    assert composed == evaluate_bid(lot, bid, available, now) == row_expected(expected)


def test_post_wallet_only_decides_balance_and_extension() -> None:
    eligible_rows = [row for row in PRECEDENCE_TABLE if row[4] == ACC or row[4] is IB]
    assert len(eligible_rows) == 4
    for phase, current, amount, _, _ in eligible_rows:
        lot, bid, _, now = row_inputs(phase, current, amount, "SUFF")
        eligible = evaluate_pre_wallet(lot, bid, now)
        assert isinstance(eligible, EligibleBid)
        for balance in (0, 9_998, 50_000, MAX_CENTS):
            result = evaluate_post_wallet(eligible, balance)
            assert isinstance(result, BidAccepted) or result is IB


def test_post_wallet_does_not_rerun_pre_wallet_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eligible = eligible_bid()
    phase_calls = count_calls(monkeypatch, "lot_phase")
    minimum_calls = count_calls(monkeypatch, "minimum_bid_cents")
    evaluate_post_wallet(eligible, MAX_CENTS)
    evaluate_post_wallet(eligible, 0)
    assert phase_calls == []
    assert minimum_calls == []


@pytest.mark.parametrize(
    ("row", "phase_calls", "minimum_calls"),
    [(13, 1, 1), (15, 1, 1), (1, 1, 0)],
    ids=["accepted", "below_minimum", "lot_not_started"],
)
def test_evaluate_bid_runs_each_rule_once(
    monkeypatch: pytest.MonkeyPatch, row: int, phase_calls: int, minimum_calls: int
) -> None:
    phase, current, amount, balance, _ = PRECEDENCE_TABLE[row - 1]
    lot, bid, available, now = row_inputs(phase, current, amount, balance)
    phase_spy = count_calls(monkeypatch, "lot_phase")
    minimum_spy = count_calls(monkeypatch, "minimum_bid_cents")
    evaluate_bid(lot, bid, available, now)
    assert len(phase_spy) == phase_calls
    assert len(minimum_spy) == minimum_calls


@pytest.mark.parametrize(
    ("phase", "current", "amount", "balance", "expected"),
    PRECEDENCE_TABLE,
    ids=ROW_IDS,
)
def test_pre_wallet_refusal_never_reaches_the_balance(
    monkeypatch: pytest.MonkeyPatch, phase, current, amount, balance, expected
) -> None:
    lot, bid, available, now = row_inputs(phase, current, amount, balance)
    post_calls = count_calls(monkeypatch, "evaluate_post_wallet")
    evaluate_bid(lot, bid, available, now)
    assert len(post_calls) == (0 if expected in PRE_WALLET_REFUSALS else 1)


def test_eligible_bid_is_utc_and_carries_only_what_is_needed() -> None:
    lot = lot_state(
        starts_at=START.astimezone(MINUS_THREE), ends_at=END.astimezone(MINUS_THREE)
    )
    now = LIVE.astimezone(MINUS_THREE)
    eligible = evaluate_pre_wallet(lot, attempt(STARTING), now)
    assert isinstance(eligible, EligibleBid)
    assert eligible.ends_at.utcoffset() == timedelta(0)
    assert eligible.now.utcoffset() == timedelta(0)
    assert eligible.ends_at == END
    assert eligible.now == LIVE
    assert {f.name for f in dataclasses.fields(eligible)} == {
        "amount_cents",
        "ends_at",
        "now",
    }


# --- anti-sniping (AD-5, P5, P13) ---


def snipe(remaining: timedelta, **lot_kwargs: object) -> BidAccepted | BidRefusal:
    """Lance de 10_000 no lote START–END, com `now = END - restante`."""
    return evaluate_bid(
        lot_state(**lot_kwargs),
        attempt(10_000),
        10_000,
        END - remaining,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("remaining", "expected"),
    [
        pytest.param(timedelta(hours=1), accepted(END, False), id="1h"),
        pytest.param(TWO_MIN + MICRO, accepted(END, False), id="2min+1us"),
        # Janela inclusiva: exatamente 2 min também somam ao término vigente.
        pytest.param(TWO_MIN, accepted(END + TWO_MIN, True), id="2min"),
        pytest.param(TWO_MIN - MICRO, accepted(END + TWO_MIN, True), id="2min-1us"),
        pytest.param(
            timedelta(minutes=1),
            accepted(END + TWO_MIN, True),
            id="1min",
        ),
        pytest.param(MICRO, accepted(END + TWO_MIN, True), id="1us"),
    ],
)
def test_anti_sniping_window(remaining: timedelta, expected: BidAccepted) -> None:
    assert snipe(remaining) == expected


def test_outside_the_window_the_end_does_not_change() -> None:
    for remaining in (timedelta(hours=1), TWO_MIN + MICRO, timedelta(hours=5)):
        result = snipe(remaining)
        assert isinstance(result, BidAccepted)
        assert result.ends_at == END
        assert result.anti_sniping_applied is False


def test_exactly_two_minutes_remaining_extends_and_flags() -> None:
    assert snipe(TWO_MIN) == accepted(END + TWO_MIN, True)


def test_extension_is_from_current_end_not_from_now() -> None:
    now = END - timedelta(minutes=1)
    result = snipe(timedelta(minutes=1))
    assert result == accepted(END + TWO_MIN, True)
    assert result.ends_at != now + TWO_MIN


def test_one_microsecond_remaining_extends_current_end() -> None:
    assert snipe(MICRO) == accepted(END + TWO_MIN, True)


@pytest.mark.parametrize("now", [END, END + MICRO])
def test_end_instant_and_after_are_ended(now: datetime) -> None:
    result = evaluate_bid(lot_state(), attempt(10_000), 10_000, now)
    assert result is BidRefusal.LOT_ENDED


@pytest.mark.parametrize(
    ("now_text", "expected_text", "applied"),
    [
        ("14:57:59", "15:00:00", False),
        ("14:58:00", "15:02:00", True),
        ("14:59:20", "15:02:00", True),
    ],
)
def test_human_decision_examples(now_text, expected_text, applied) -> None:
    end = datetime.fromisoformat("2026-10-27T15:00:00+00:00")
    now = datetime.fromisoformat(f"2026-10-27T{now_text}+00:00")
    expected = datetime.fromisoformat(f"2026-10-27T{expected_text}+00:00")
    result = evaluate_bid(lot_state(ends_at=end), attempt(10_000), 10_000, now)
    assert result == accepted(expected, applied)


def test_extension_is_cumulative_across_three_valid_bids() -> None:
    end = datetime.fromisoformat("2026-10-27T15:00:00+00:00")
    current = None
    for index, (at, expected) in enumerate(
        [("14:59:20", "15:02:00"), ("15:01:10", "15:04:00"), ("15:03:30", "15:06:00")]
    ):
        now = datetime.fromisoformat(f"2026-10-27T{at}+00:00")
        bidder = BIDDER if index % 2 == 0 else OTHER
        amount = 10_000 + index * 1_000
        result = evaluate_bid(
            lot_state(ends_at=end, current=current),
            attempt(amount, bidder),
            MAX_CENTS,
            now,
        )
        assert result == accepted(
            datetime.fromisoformat(f"2026-10-27T{expected}+00:00"), True
        )
        assert result.ends_at != now + TWO_MIN
        end = result.ends_at
        current = leader(bidder, amount)


def test_bid_near_extended_end_adds_to_current_end() -> None:
    end = datetime.fromisoformat("2026-10-27T15:02:00+00:00")
    result = evaluate_bid(
        lot_state(ends_at=end, current=leader(BIDDER, 10_000)),
        attempt(11_000, OTHER),
        11_000,
        end - timedelta(seconds=1),
    )
    assert result == accepted(datetime.fromisoformat("2026-10-27T15:04:00+00:00"), True)


def test_short_lot_accepted_at_start_is_extended() -> None:
    lot = lot_state(starts_at=START, ends_at=START + timedelta(seconds=90))
    result = evaluate_bid(lot, attempt(10_000), 10_000, START)
    assert result == accepted(lot.ends_at + TWO_MIN, True)


@pytest.mark.parametrize(
    ("lot_kwargs", "bid_amount", "bid_by", "balance", "expected"),
    [
        ({}, 9_999, BIDDER, 10_000, BidRefusal.BELOW_MINIMUM),
        (
            {"current": leader(BIDDER)},
            21_000,
            BIDDER,
            MAX_CENTS,
            BidRefusal.ALREADY_WINNING,
        ),
        ({}, 10_000, BIDDER, 9_999, BidRefusal.INSUFFICIENT_BALANCE),
    ],
    ids=["below_minimum", "already_winning", "insufficient_balance"],
)
def test_refusals_inside_the_window_never_extend(
    lot_kwargs: dict, bid_amount: int, bid_by: uuid.UUID, balance: int, expected: object
) -> None:
    now = END - timedelta(minutes=1)
    result = evaluate_bid(
        lot_state(**lot_kwargs), attempt(bid_amount, bid_by), balance, now
    )
    assert result is expected
    assert not isinstance(result, BidAccepted)


def test_accepted_end_is_utc() -> None:
    lot = lot_state(
        starts_at=START.astimezone(MINUS_THREE), ends_at=END.astimezone(MINUS_THREE)
    )
    inside = evaluate_bid(
        lot,
        attempt(10_000),
        10_000,
        (END - timedelta(minutes=1)).astimezone(PLUS_FIVE_THIRTY),
    )
    assert isinstance(inside, BidAccepted)
    assert inside.ends_at.utcoffset() == timedelta(0)
    assert inside.ends_at == END + TWO_MIN
    outside = evaluate_bid(
        lot,
        attempt(10_000),
        10_000,
        (END - timedelta(hours=1)).astimezone(PLUS_FIVE_THIRTY),
    )
    assert isinstance(outside, BidAccepted)
    assert outside.ends_at.utcoffset() == timedelta(0)
    assert outside.ends_at == END


def test_flag_matches_end_change() -> None:
    scenarios = [
        (lot_state(), attempt(10_000), MAX_CENTS, now)
        for now in (START, LIVE, END - TWO_MIN - MICRO, END - TWO_MIN, END - MICRO)
    ]
    scenarios += [
        (
            lot_state(current=leader(OTHER)),
            attempt(21_000),
            MAX_CENTS,
            END - timedelta(seconds=30),
        ),
        (lot_state(), attempt(10_000), MAX_CENTS, END - timedelta(minutes=1)),
    ]
    checked = 0
    for lot, bid, balance, now in scenarios:
        result = evaluate_bid(lot, bid, balance, now)
        assert isinstance(result, BidAccepted)
        assert result.anti_sniping_applied == (result.ends_at != lot.ends_at)
        checked += 1
    assert checked == len(scenarios)


# --- hora injetada (AD-6, AD-26) ---


def test_injected_now_drives_the_result() -> None:
    lot = lot_state()  # janela em 2026
    bid = attempt(STARTING)
    year_2000 = datetime(2000, 1, 1, tzinfo=UTC)
    year_2100 = datetime(2100, 1, 1, tzinfo=UTC)
    assert evaluate_bid(lot, bid, MAX_CENTS, year_2000) is BidRefusal.LOT_NOT_STARTED
    assert evaluate_bid(lot, bid, MAX_CENTS, year_2100) is BidRefusal.LOT_ENDED
    lot_2100 = lot_state(starts_at=year_2100, ends_at=year_2100 + timedelta(days=1))
    noon_2100 = year_2100 + timedelta(hours=12)
    assert evaluate_bid(lot_2100, bid, MAX_CENTS, noon_2100) == accepted(
        year_2100 + timedelta(days=1), False
    )
    lot_2000 = lot_state(starts_at=year_2000, ends_at=year_2000 + timedelta(days=1))
    noon_2000 = year_2000 + timedelta(hours=12)
    assert evaluate_bid(lot_2000, bid, MAX_CENTS, noon_2000) == accepted(
        year_2000 + timedelta(days=1), False
    )
