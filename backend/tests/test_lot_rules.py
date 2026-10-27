"""Regra pura de lotes, sem banco e com `now` fixo (Story 2.4, CAP-4, CAP-5, A3, A4)."""

import inspect
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.artic import ArticClient, CatalogUnavailable
from app.catalog import _detail
from app.lots import (
    MAX_CENTS,
    ArtworkRefusal,
    ArtworkSnapshot,
    CreateLotRequest,
    LotTerms,
    Schedule,
    ScheduleViolation,
    create_lot,
    ends_not_after_scheduled_start,
    resolve_artwork_for_lot,
    resolve_schedule,
    snapshot_from_detail,
)
from tests.catalog_support import (
    FAILURES_BOTH,
    FakeArtic,
    artic_client,
    json_response,
    load_fixture,
    standard_handler,
)

NOW = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)
MICRO = timedelta(microseconds=1)
FUTURE = NOW + timedelta(days=1)


def error_types(error: ValidationError) -> list[str]:
    return [item["type"] for item in error.errors()]


# --- resolve_schedule ---


def test_without_start_the_start_is_now_and_the_end_must_be_after_it() -> None:
    assert resolve_schedule(None, FUTURE, NOW) == Schedule(NOW, FUTURE)
    assert resolve_schedule(None, NOW, NOW) == ScheduleViolation.ENDS_AT_NOT_AFTER_START
    assert resolve_schedule(None, NOW + MICRO, NOW) == Schedule(NOW, NOW + MICRO)
    assert (
        resolve_schedule(None, NOW - MICRO, NOW)
        == ScheduleViolation.ENDS_AT_NOT_AFTER_START
    )


def test_a_scheduled_start_must_be_strictly_in_the_future() -> None:
    assert (
        resolve_schedule(NOW, FUTURE, NOW) == ScheduleViolation.STARTS_AT_NOT_IN_FUTURE
    )
    assert (
        resolve_schedule(NOW - MICRO, FUTURE, NOW)
        == ScheduleViolation.STARTS_AT_NOT_IN_FUTURE
    )
    start = NOW + MICRO
    assert resolve_schedule(start, FUTURE, NOW) == Schedule(start, FUTURE)


def test_the_end_must_be_strictly_after_a_scheduled_start() -> None:
    start = NOW + timedelta(hours=1)
    assert (
        resolve_schedule(start, start, NOW) == ScheduleViolation.ENDS_AT_NOT_AFTER_START
    )
    assert resolve_schedule(start, start + MICRO, NOW) == Schedule(start, start + MICRO)


def test_offsets_do_not_matter_and_the_output_is_always_utc() -> None:
    minus3 = timezone(timedelta(hours=-3))
    start = (NOW + timedelta(hours=1)).astimezone(minus3)
    end = (NOW + timedelta(hours=5)).astimezone(minus3)

    schedule = resolve_schedule(start, end, NOW.astimezone(minus3))

    assert isinstance(schedule, Schedule)
    assert schedule.starts_at == NOW + timedelta(hours=1)
    assert schedule.ends_at == NOW + timedelta(hours=5)
    assert schedule.starts_at.tzinfo == UTC
    assert schedule.ends_at.tzinfo == UTC


def test_a_naive_now_is_a_programming_error() -> None:
    with pytest.raises(ValueError):
        resolve_schedule(None, FUTURE, datetime(2026, 10, 24, 12, 0, 0))


def test_pre_check_only_compares_when_the_start_was_sent() -> None:
    assert ends_not_after_scheduled_start(None, NOW) is False
    assert ends_not_after_scheduled_start(NOW, NOW) is True
    assert ends_not_after_scheduled_start(NOW, NOW - MICRO) is True
    assert ends_not_after_scheduled_start(NOW, NOW + MICRO) is False


# --- dinheiro (A4) ---


def terms(**overrides: object) -> dict[str, object]:
    return {
        "starting_bid_cents": 10000,
        "min_increment_cents": 1000,
        "ends_at": "2026-10-25T12:00:00Z",
        **overrides,
    }


@pytest.mark.parametrize("field", ["starting_bid_cents", "min_increment_cents"])
def test_money_must_be_a_strict_integer(field: str) -> None:
    for value in (100.0, "100", True, 1e2, None):
        with pytest.raises(ValidationError) as error:
            LotTerms(**terms(**{field: value}))
        assert error_types(error.value) == ["int_type"], value


@pytest.mark.parametrize("field", ["starting_bid_cents", "min_increment_cents"])
def test_money_range_is_one_to_max_safe_integer(field: str) -> None:
    for value in (0, -1):
        with pytest.raises(ValidationError) as error:
            LotTerms(**terms(**{field: value}))
        assert error_types(error.value) == ["greater_than"]
    with pytest.raises(ValidationError) as error:
        LotTerms(**terms(**{field: MAX_CENTS + 1}))
    assert error_types(error.value) == ["less_than_equal"]
    assert getattr(LotTerms(**terms(**{field: 1})), field) == 1
    assert getattr(LotTerms(**terms(**{field: MAX_CENTS})), field) == MAX_CENTS


def test_the_money_range_is_one_for_api_service_and_database() -> None:
    assert MAX_CENTS == 2**53 - 1 == 9007199254740991


def test_unknown_fields_are_refused() -> None:
    with pytest.raises(ValidationError) as error:
        LotTerms(**terms(auctioneer_id="x"))
    assert error_types(error.value) == ["extra_forbidden"]


# --- horário na API (D2) ---


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-25T13:00:00Z",
        "2026-10-25T13:00:00-03:00",
        "2026-10-25T13:00Z",
        "2026-10-25T13:00:00.123456+00:00",
        "2026-10-25T13:00:00.5Z",
        datetime(2026, 10, 25, 13, 0, tzinfo=UTC),
    ],
)
def test_valid_aware_datetimes_are_accepted(value: object) -> None:
    parsed = LotTerms(**terms(ends_at=value)).ends_at
    assert parsed.tzinfo is not None


def test_a_datetime_without_offset_is_timezone_aware_error() -> None:
    for value in ("2026-10-25T13:00:00", "2026-10-25T13:00"):
        with pytest.raises(ValidationError) as error:
            LotTerms(**terms(ends_at=value))
        assert error_types(error.value) == ["timezone_aware"], value


@pytest.mark.parametrize(
    "value",
    [
        1730000000,
        1730000000.5,
        "1730000000",
        "2026-10-25",
        "2026-10-25 13:00:00Z",
        "2026-10-25T13:00:00z",
        "",
        True,
        ["2026-10-25T13:00:00Z"],
    ],
)
def test_other_shapes_are_datetime_format_errors(value: object) -> None:
    with pytest.raises(ValidationError) as error:
        LotTerms(**terms(ends_at=value))
    assert error_types(error.value) == ["datetime_format"]


@pytest.mark.parametrize(
    "value",
    [
        "9999-12-31T23:00:00-05:00",  # em UTC passaria de 9999-12-31
        "9999-12-31T19:00:00-05:00",  # 24:00 UTC: o primeiro que estoura
        "0001-01-01T00:00:00+05:00",  # em UTC seria antes de 0001-01-01
        "0001-01-01T00:00:00+00:01",
    ],
)
def test_datetimes_that_cannot_be_normalized_to_utc_are_refused(value: str) -> None:
    for field in ("starts_at", "ends_at"):
        with pytest.raises(ValidationError) as error:
            LotTerms(**terms(**{field: value}))
        assert error_types(error.value) == ["datetime_format"], (field, value)


@pytest.mark.parametrize(
    "value",
    [
        "9999-12-31T23:59:59.999999Z",  # o maior instante em UTC
        "9999-12-31T23:59:59+00:00",
        "9999-12-31T23:59:59-00:00",
        "0001-01-01T00:00:00Z",  # o menor
        "0001-01-01T05:00:00+05:00",  # mínimo exato em UTC
        "9999-12-31T18:59:59-05:00",  # 23:59:59 UTC: o último que cabe
        "9999-12-31T19:00:01-04:59",  # 23:59:01 UTC
    ],
)
def test_extreme_datetimes_that_fit_in_utc_are_still_accepted(value: str) -> None:
    parsed = LotTerms(**terms(ends_at=value)).ends_at
    assert parsed.astimezone(UTC).year in (1, 9999)


def test_the_start_is_optional_and_null_means_now() -> None:
    assert LotTerms(**terms()).starts_at is None
    assert LotTerms(**terms(starts_at=None)).starts_at is None
    with pytest.raises(ValidationError) as error:
        LotTerms(**terms(starts_at=1730000000))
    assert error_types(error.value) == ["datetime_format"]


def test_the_end_is_required() -> None:
    body = terms()
    del body["ends_at"]
    with pytest.raises(ValidationError) as error:
        LotTerms(**body)
    assert error_types(error.value) == ["missing"]


@pytest.mark.parametrize("external_id", [0, -1, 2_147_483_648, 1.0, "1", True])
def test_external_id_must_be_a_positive_int4(external_id: object) -> None:
    with pytest.raises(ValidationError):
        CreateLotRequest(**terms(external_id=external_id))
    assert CreateLotRequest(**terms(external_id=2_147_483_647)).external_id


# --- snapshot ---


def detail_of(name: str = "artwork_27992.json"):
    fake = FakeArtic(lambda request: json_response(load_fixture(name)))
    artwork = artic_client(fake).get_artwork(27992)
    assert artwork is not None and artwork.image_id is not None
    return _detail(artwork, artwork.image_id)


def test_snapshot_has_the_eleven_fields_and_no_image_url() -> None:
    snapshot = snapshot_from_detail(detail_of())

    assert sorted(snapshot.model_dump()) == sorted(
        [
            "external_id",
            "title",
            "artist_display",
            "date_display",
            "medium_display",
            "dimensions",
            "department_title",
            "artwork_type_title",
            "image_id",
            "credit_line",
            "source_url",
        ]
    )
    assert "image_url" not in snapshot.model_dump()


def test_snapshot_refuses_extras_and_a_malformed_image_id() -> None:
    data = snapshot_from_detail(detail_of()).model_dump()
    with pytest.raises(ValidationError):
        ArtworkSnapshot(**data, image_url="/api/catalog/images/x")
    for image_id in ("../evil", data["image_id"].upper(), data["image_id"] + "0", ""):
        with pytest.raises(ValidationError):
            ArtworkSnapshot(**{**data, "image_id": image_id})


# --- nível externo (A3) ---


def make_client(handler) -> tuple[ArticClient, FakeArtic]:
    fake = FakeArtic(handler)
    return artic_client(fake), fake


def test_resolve_returns_the_snapshot_of_the_artwork_with_one_request() -> None:
    client, fake = make_client(standard_handler)

    resolved = resolve_artwork_for_lot(client, 27992)

    assert resolved == snapshot_from_detail(detail_of())
    assert len(fake.requests) == 1
    assert fake.requests[0].url.path == "/api/v1/artworks/27992"


@pytest.mark.parametrize(
    ("external_id", "refusal"),
    [
        (999999, ArtworkRefusal.NOT_FOUND),
        (129884, ArtworkRefusal.NOT_PUBLIC_DOMAIN),
        (555002, ArtworkRefusal.NO_IMAGE),
    ],
)
def test_resolve_names_the_internal_refusal(
    external_id: int, refusal: ArtworkRefusal
) -> None:
    client, fake = make_client(standard_handler)

    assert resolve_artwork_for_lot(client, external_id) == refusal
    assert len(fake.requests) == 1


@pytest.mark.parametrize(("reason", "handler"), FAILURES_BOTH)
def test_resolve_lets_catalog_unavailable_through(reason: str, handler) -> None:
    client, fake = make_client(handler)

    with pytest.raises(CatalogUnavailable) as error:
        resolve_artwork_for_lot(client, 27992)

    assert error.value.reason == reason
    assert len(fake.requests) <= 1


def test_the_persistence_level_knows_nothing_about_the_network() -> None:
    parameters = inspect.signature(create_lot).parameters

    assert sorted(parameters) == [
        "auctioneer_id",
        "audit_hmac_secret",
        "is_demo",
        "now",
        "session",
        "snapshot",
        "terms",
    ]
    for parameter in parameters.values():
        assert "client" not in parameter.name
        assert "ArticClient" not in str(parameter.annotation)
        assert "httpx" not in str(parameter.annotation)
