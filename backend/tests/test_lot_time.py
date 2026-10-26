"""Fase temporal do lote como módulo puro (Story 3.2, test-plan §2; P8, D7, D9)."""

from datetime import UTC, date, datetime, timedelta, timezone, tzinfo

import pytest

import app.lot_time as lot_time
from app import lots
from app.lot_time import LotPhase, check_lot_window, lot_phase, require_aware

START = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
END = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
NAIVE = datetime(2026, 10, 25, 12, 0)
MINUS_THREE = timezone(timedelta(hours=-3))


class FoldOffset(tzinfo):
    """Offset −3 h com fold=0 e −4 h com fold=1: uma hora ambígua sem depender da base
    de fusos do sistema."""

    def utcoffset(self, dt):
        return timedelta(hours=-4 if dt.fold else -3)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return None


class NoOffset(tzinfo):
    """`tzinfo` presente, mas que não informa offset: não é um instante com fuso."""

    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None

    def tzname(self, dt):
        return None


def test_lots_reexports_the_same_objects() -> None:
    assert lots.LotPhase is lot_time.LotPhase
    assert lots.lot_phase is lot_time.lot_phase


def test_naive_starts_at_is_refused() -> None:
    with pytest.raises(ValueError, match="starts_at must be timezone-aware"):
        lot_phase(NAIVE, END, START)


def test_naive_ends_at_is_refused() -> None:
    with pytest.raises(ValueError, match="ends_at must be timezone-aware"):
        lot_phase(START, NAIVE, START)


def test_naive_now_is_refused_by_the_pure_module() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        lot_phase(START, END, NAIVE)


@pytest.mark.parametrize("position", ["starts_at", "ends_at", "now"])
@pytest.mark.parametrize("bad", ["2026-10-25T12:00:00Z", date(2026, 10, 25), None])
def test_non_datetime_is_refused(position: str, bad: object) -> None:
    args = {"starts_at": START, "ends_at": END, "now": START}
    args[position] = bad  # type: ignore[assignment]
    with pytest.raises(ValueError, match=f"{position} must be a datetime"):
        lot_phase(**args)  # type: ignore[arg-type]


def test_tzinfo_without_offset_is_refused() -> None:
    no_offset = datetime(2026, 10, 25, 12, 0, tzinfo=NoOffset())
    with pytest.raises(ValueError, match="timezone-aware"):
        lot_phase(no_offset, END, START)
    with pytest.raises(ValueError, match="timezone-aware"):
        lot_phase(START, END, no_offset)


@pytest.mark.parametrize(
    ("starts_at", "ends_at"),
    [
        (START, START),
        (END, START),
        (START, START.astimezone(MINUS_THREE)),
    ],
)
def test_window_must_be_increasing(starts_at: datetime, ends_at: datetime) -> None:
    with pytest.raises(ValueError, match="starts_at must be before ends_at"):
        lot_phase(starts_at, ends_at, START)


def test_window_is_checked_before_now() -> None:
    with pytest.raises(ValueError, match="starts_at must be timezone-aware"):
        lot_phase(NAIVE, END, NAIVE)


def test_same_tzinfo_in_an_ambiguous_hour_compares_instants() -> None:
    tz = FoldOffset()
    starts_at = datetime(2026, 11, 1, 0, 0, tzinfo=tz)  # 03:00Z
    ends_at = datetime(2026, 11, 1, 1, 10, fold=1, tzinfo=tz)  # 05:10Z
    # 01:30 com fold=0 é 04:30Z: ao vivo. Pelo relógio de parede, 01:30 > 01:10 daria
    # "encerrado".
    assert lot_phase(starts_at, ends_at, datetime(2026, 11, 1, 1, 30, tzinfo=tz)) is (
        LotPhase.LIVE
    )
    # 02:20 com fold=0 é 05:20Z: encerrado.
    assert lot_phase(starts_at, ends_at, datetime(2026, 11, 1, 2, 20, tzinfo=tz)) is (
        LotPhase.ENDED
    )


def test_require_aware_returns_the_value() -> None:
    assert require_aware("x", START) is START


def test_check_lot_window_accepts_a_valid_window() -> None:
    assert check_lot_window(START, END) is None
