"""Fase do lote e DTOs públicos, sem banco (Story 2.5, test-plan §2, AD-26)."""

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.lots import (
    Lot,
    LotPhase,
    build_public_lots,
    lot_phase,
    public_lot_detail,
    public_lot_summary,
)

START = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)
END = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)
MICRO = timedelta(microseconds=1)
IMAGE_ID = "2d484387-2509-5e8e-2c43-22f9981972eb"


def make_lot(
    starts_at: datetime = START,
    ends_at: datetime = END,
    *,
    lot_id: uuid.UUID | None = None,
) -> Lot:
    return Lot(
        id=lot_id or uuid.uuid4(),
        auctioneer_id=uuid.uuid4(),
        external_id=27992,
        title="Obra",
        artist_display="Artista",
        date_display="1884",
        medium_display="Oil on canvas",
        dimensions="10 × 10 cm",
        department_title="Painting",
        artwork_type_title="Painting",
        image_id=IMAGE_ID,
        credit_line="Crédito",
        source_url="https://www.artic.edu/artworks/27992",
        starting_bid_cents=10_000,
        min_increment_cents=1_000,
        starts_at=starts_at,
        ends_at=ends_at,
        is_demo=True,
        created_at=START - timedelta(days=1),
    )


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (START - MICRO, LotPhase.SCHEDULED),
        (START, LotPhase.LIVE),
        (START + timedelta(hours=1), LotPhase.LIVE),
        (END - MICRO, LotPhase.LIVE),
        (END, LotPhase.ENDED),
        (END + MICRO, LotPhase.ENDED),
        (START - timedelta(days=30), LotPhase.SCHEDULED),
        (END + timedelta(days=30), LotPhase.ENDED),
    ],
)
def test_phase_boundaries_are_exact_to_the_microsecond(
    now: datetime, expected: LotPhase
) -> None:
    assert lot_phase(START, END, now) == expected


def test_phase_compares_instants_not_offsets() -> None:
    brasilia = timezone(timedelta(hours=-3))
    # Mesmo instante que START, escrito em outro offset.
    same_as_start = START.astimezone(brasilia)
    same_as_end = END.astimezone(brasilia)

    assert same_as_start.utcoffset() != START.utcoffset()
    assert lot_phase(START, END, same_as_start) == LotPhase.LIVE
    assert lot_phase(same_as_start, same_as_end, START) == LotPhase.LIVE
    assert lot_phase(same_as_start, same_as_end, END) == LotPhase.ENDED
    assert lot_phase(same_as_start, same_as_end, START - MICRO) == LotPhase.SCHEDULED


def test_naive_now_is_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        lot_phase(START, END, datetime(2026, 10, 25, 13, 0, 0))


def test_phase_values_are_exactly_the_three_phases() -> None:
    assert {phase.value for phase in LotPhase} == {"scheduled", "live", "ended"}


def test_public_summary_has_exactly_the_contract_keys() -> None:
    summary = public_lot_summary(make_lot(), START + timedelta(hours=1))

    assert sorted(summary.model_dump()) == sorted(
        [
            "id",
            "title",
            "artist_display",
            "date_display",
            "image_url",
            "starting_bid_cents",
            "starts_at",
            "ends_at",
            "phase",
        ]
    )
    assert summary.image_url == f"/api/catalog/images/{IMAGE_ID}"
    assert summary.phase == LotPhase.LIVE
    assert summary.starts_at.utcoffset() == timedelta(0)


def test_public_summary_normalizes_timestamps_to_utc() -> None:
    brasilia = timezone(timedelta(hours=-3))
    lot = make_lot(START.astimezone(brasilia), END.astimezone(brasilia))

    summary = public_lot_summary(lot, START)

    assert summary.starts_at == START
    assert summary.starts_at.tzinfo == UTC
    assert summary.ends_at.tzinfo == UTC


def test_public_detail_has_exactly_the_contract_keys() -> None:
    detail = public_lot_detail(make_lot(), END)

    assert sorted(detail.model_dump()) == sorted(
        [
            "id",
            "title",
            "artist_display",
            "date_display",
            "image_url",
            "starting_bid_cents",
            "starts_at",
            "ends_at",
            "phase",
            "external_id",
            "medium_display",
            "dimensions",
            "department_title",
            "artwork_type_title",
            "credit_line",
            "source_url",
            "min_increment_cents",
        ]
    )
    assert detail.phase == LotPhase.ENDED
    assert detail.min_increment_cents == 1_000


def test_build_public_lots_classifies_every_lot_with_the_same_as_of() -> None:
    as_of = START + timedelta(hours=1)
    scheduled = make_lot(as_of + timedelta(hours=1), as_of + timedelta(hours=5))
    live = make_lot(as_of - timedelta(hours=1), as_of + timedelta(hours=1))
    ended = make_lot(as_of - timedelta(hours=5), as_of - timedelta(hours=1))
    # No limite: começa exatamente em `as_of` (ao vivo) e termina exatamente em
    # `as_of` (encerrado).
    starts_now = make_lot(as_of, as_of + timedelta(hours=2))
    ends_now = make_lot(as_of - timedelta(hours=2), as_of)

    response = build_public_lots([scheduled, live, ended, starts_now, ends_now], as_of)

    assert response.as_of == as_of
    assert {lot.id for lot in response.live} == {live.id, starts_now.id}
    assert [lot.id for lot in response.scheduled] == [scheduled.id]
    assert {lot.id for lot in response.ended} == {ended.id, ends_now.id}
    assert all(lot.phase == LotPhase.LIVE for lot in response.live)
    assert all(lot.phase == LotPhase.SCHEDULED for lot in response.scheduled)
    assert all(lot.phase == LotPhase.ENDED for lot in response.ended)


def test_build_public_lots_with_no_lots_keeps_as_of_and_three_empty_groups() -> None:
    response = build_public_lots([], START)

    assert response.model_dump() == {
        "as_of": START,
        "live": [],
        "scheduled": [],
        "ended": [],
    }


def ids(n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=value) for value in range(1, n + 1)]


def test_groups_are_ordered_by_the_documented_keys() -> None:
    as_of = START
    a, b, c = ids(3)
    # Ao vivo: ends_at ASC. A termina por último, C primeiro.
    live = [
        make_lot(as_of - timedelta(hours=1), as_of + timedelta(hours=3), lot_id=a),
        make_lot(as_of - timedelta(hours=1), as_of + timedelta(hours=2), lot_id=b),
        make_lot(as_of - timedelta(hours=1), as_of + timedelta(hours=1), lot_id=c),
    ]
    # Agendados: starts_at ASC.
    scheduled = [
        make_lot(as_of + timedelta(hours=3), as_of + timedelta(hours=9), lot_id=a),
        make_lot(as_of + timedelta(hours=2), as_of + timedelta(hours=9), lot_id=b),
        make_lot(as_of + timedelta(hours=1), as_of + timedelta(hours=9), lot_id=c),
    ]
    live_response = build_public_lots(live, as_of)
    scheduled_response = build_public_lots(scheduled, as_of)

    assert [lot.id for lot in live_response.live] == [c, b, a]
    assert [lot.id for lot in scheduled_response.scheduled] == [c, b, a]


def test_ended_group_is_newest_first_and_ties_break_by_id_ascending() -> None:
    as_of = START
    a, b, c, d = ids(4)
    older = as_of - timedelta(hours=5)
    newer = as_of - timedelta(hours=1)
    lots = [
        make_lot(older - timedelta(days=1), older, lot_id=d),
        make_lot(newer - timedelta(days=1), newer, lot_id=c),
        make_lot(newer - timedelta(days=1), newer, lot_id=a),
        make_lot(newer - timedelta(days=1), newer, lot_id=b),
    ]

    response = build_public_lots(lots, as_of)

    # ends_at DESC (a/b/c primeiro); empate por id ASC; o mais antigo por último.
    assert [lot.id for lot in response.ended] == [a, b, c, d]


def test_ties_break_by_id_ascending_in_live_and_scheduled_too() -> None:
    as_of = START
    a, b, c = ids(3)
    live = [
        make_lot(as_of - timedelta(hours=1), as_of + timedelta(hours=1), lot_id=lot_id)
        for lot_id in (c, a, b)
    ]
    scheduled = [
        make_lot(as_of + timedelta(hours=1), as_of + timedelta(hours=2), lot_id=lot_id)
        for lot_id in (b, c, a)
    ]

    assert [lot.id for lot in build_public_lots(live, as_of).live] == [a, b, c]
    assert [lot.id for lot in build_public_lots(scheduled, as_of).scheduled] == [
        a,
        b,
        c,
    ]
