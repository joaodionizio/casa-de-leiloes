"""`POST /api/lots` sobre PostgreSQL real, com a AIC falsa (Story 2.4, test-plan §4).

O `ArticClient` é o real, com `httpx.MockTransport`; a guarda de rede do
`conftest.py` continua ativa."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import lots
from app.bid_integrity import GENESIS_HASH, AnchorState, verify_anchor_hmac
from app.errors import MESSAGES
from app.lots import MAX_CENTS, Schedule
from app.seed import load_demo_artwork
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
    seed_demo_users,
    seeded_id,
)
from tests.catalog_support import (
    FAILURES_BOTH,
    FakeArtic,
    install,
    json_response,
    load_fixture,
    standard_handler,
)
from tests.lot_support import (
    LOT_COLUMNS,
    count_lots,
    db_now,
    empty_anchor,
    integrity_secrets,
    iso,
    lot_rows,
    valid_body,
)

URL = "/api/lots"
RESPONSE_KEYS = sorted(
    [
        "id",
        "external_id",
        "title",
        "artist_display",
        "date_display",
        "medium_display",
        "dimensions",
        "department_title",
        "artwork_type_title",
        "credit_line",
        "source_url",
        "image_id",
        "image_url",
        "starting_bid_cents",
        "min_increment_cents",
        "starts_at",
        "ends_at",
        "created_at",
    ]
)
DETAIL_FIELDS = (
    "id,title,artist_display,date_display,medium_display,dimensions,"
    "department_title,artwork_type_title,image_id,is_public_domain,credit_line"
)
NOT_ELIGIBLE_BODY = {
    "status": 422,
    "code": "artwork_not_eligible",
    "message": MESSAGES["artwork_not_eligible"],
}
UNAVAILABLE_BODY = {
    "status": 503,
    "code": "catalog_unavailable",
    "message": MESSAGES["catalog_unavailable"],
}


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_demo_users(db_session_factory)
    return db_session_factory


@pytest.fixture
def fake() -> FakeArtic:
    return FakeArtic(standard_handler)


def make_client(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    email: str | None = AUCTIONEER_EMAIL,
    **kwargs: Any,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    if kwargs.get("raise_server_exceptions") is False:
        client = TestClient(
            client.app, base_url=HTTPS_ORIGIN, raise_server_exceptions=False
        )
    install(client.app, fake)  # type: ignore[arg-type]
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


@pytest.fixture
def auctioneer(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], fake: FakeArtic
) -> TestClient:
    return make_client(monkeypatch, seeded, fake)


def post(client: TestClient, body: object) -> Any:
    return client.post(URL, json=body, headers=json_headers(HTTPS_ORIGIN))


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def validation_details(response: Any) -> list[dict[str, Any]]:
    body = response.json()
    assert body["status"] == 422
    assert body["code"] == "validation_error"
    return body["details"]


# --- sucesso ---


def test_auctioneer_creates_a_lot_and_the_row_equals_the_response(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    response = post(auctioneer, valid_body(seeded))

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert "location" not in response.headers
    body = response.json()
    assert sorted(body) == RESPONSE_KEYS
    assert body["image_url"] == f"/api/catalog/images/{body['image_id']}"
    assert body["title"] == "A Sunday on La Grande Jatte — 1884"
    assert body["source_url"] == "https://www.artic.edu/artworks/27992"
    assert body["starting_bid_cents"] == 125000
    assert body["min_increment_cents"] == 5000
    for key in ("starts_at", "ends_at", "created_at"):
        assert body[key].endswith("Z")

    (row,) = lot_rows(seeded)
    stored = dict(zip(LOT_COLUMNS, row, strict=True))
    assert str(stored["id"]) == body["id"]
    assert stored["auctioneer_id"] == seeded_id(AUCTIONEER_EMAIL)
    assert stored["is_demo"] is False
    for key in RESPONSE_KEYS:
        if key in ("image_url", "starts_at", "ends_at", "created_at", "id"):
            continue
        assert stored[key] == body[key], key
    for key in ("starts_at", "ends_at", "created_at"):
        assert stored[key] == parse(body[key]), key


def test_the_aic_receives_exactly_one_detail_request(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    assert post(auctioneer, valid_body(seeded)).status_code == 201

    assert len(fake.requests) == 1
    request = fake.requests[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v1/artworks/27992"
    assert request.url.params["fields"] == DETAIL_FIELDS


def test_the_snapshot_is_what_the_server_got_from_the_aic(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    def altered(request):  # type: ignore[no-untyped-def]
        artwork = load_fixture("artwork_27992.json")
        artwork["data"]["title"] = "Título da AIC"
        artwork["data"]["dimensions"] = None
        return json_response(artwork)

    client = make_client(monkeypatch, seeded, FakeArtic(altered))

    response = post(client, valid_body(seeded))

    assert response.status_code == 201
    assert response.json()["title"] == "Título da AIC"
    (row,) = lot_rows(seeded)
    stored = dict(zip(LOT_COLUMNS, row, strict=True))
    assert stored["title"] == "Título da AIC"
    assert stored["dimensions"] is None


@pytest.mark.parametrize(
    "field",
    [
        "auctioneer_id",
        "title",
        "artist_display",
        "image_id",
        "image_url",
        "source_url",
        "is_public_domain",
        "is_demo",
        "snapshot",
        "created_at",
        "id",
    ],
)
def test_fields_the_client_does_not_control_are_refused(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    field: str,
) -> None:
    response = post(auctioneer, {**valid_body(seeded), field: "adulterado"})

    assert response.status_code == 422
    assert validation_details(response) == [
        {"loc": ["body", field], "type": "extra_forbidden"}
    ]
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_the_owner_is_the_session_user_even_with_another_auctioneer_around(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    other = uuid.uuid4()
    with seeded() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, 'outro@example.com', 'h', 'AUCTIONEER')"
            ),
            {"id": other},
        )
        session.commit()
    client = make_client(monkeypatch, seeded, fake)

    assert post(client, valid_body(seeded)).status_code == 201

    (row,) = lot_rows(seeded)
    assert dict(zip(LOT_COLUMNS, row, strict=True))["auctioneer_id"] == seeded_id(
        AUCTIONEER_EMAIL
    )


def test_the_same_artwork_can_become_many_lots(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    assert post(auctioneer, valid_body(seeded)).status_code == 201
    assert post(auctioneer, valid_body(seeded)).status_code == 201

    assert count_lots(seeded) == 2


# --- dinheiro ---


def test_money_is_stored_exactly_including_the_maximum(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    body = valid_body(seeded, starting_bid_cents=MAX_CENTS, min_increment_cents=1)

    response = post(auctioneer, body)

    assert response.status_code == 201
    assert response.json()["starting_bid_cents"] == MAX_CENTS
    assert response.json()["min_increment_cents"] == 1
    (row,) = lot_rows(seeded)
    stored = dict(zip(LOT_COLUMNS, row, strict=True))
    assert stored["starting_bid_cents"] == MAX_CENTS
    assert stored["min_increment_cents"] == 1


@pytest.mark.parametrize("field", ["starting_bid_cents", "min_increment_cents"])
@pytest.mark.parametrize(
    ("value", "error_type"),
    [
        (100.0, "int_type"),
        ("100", "int_type"),
        (True, "int_type"),
        (None, "int_type"),
        (0, "greater_than"),
        (-1, "greater_than"),
        (MAX_CENTS + 1, "less_than_equal"),
        (..., "missing"),
    ],
)
def test_invalid_money_is_refused_before_the_aic(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    field: str,
    value: object,
    error_type: str,
) -> None:
    response = post(auctioneer, valid_body(seeded, **{field: value}))

    assert response.status_code == 422
    assert validation_details(response) == [
        {"loc": ["body", field], "type": error_type}
    ]
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_a_float_written_with_an_exponent_is_refused(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    body = valid_body(seeded)
    ends_at = body["ends_at"]
    raw = (
        '{"external_id": 27992, "starting_bid_cents": 1e2, '
        '"min_increment_cents": 5000, "starts_at": null, '
        f'"ends_at": "{ends_at}"}}'
    )

    response = auctioneer.post(URL, content=raw, headers=json_headers(HTTPS_ORIGIN))

    assert response.status_code == 422
    assert validation_details(response)[0]["loc"] == ["body", "starting_bid_cents"]
    assert count_lots(seeded) == 0


@pytest.mark.parametrize("external_id", [0, -5, 2_147_483_648, "27992", 27992.0, None])
def test_invalid_external_id_is_refused_before_the_aic(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    external_id: object,
) -> None:
    response = post(auctioneer, valid_body(seeded, external_id=external_id))

    assert response.status_code == 422
    assert validation_details(response)[0]["loc"] == ["body", "external_id"]
    assert fake.requests == []


# --- horário ---


@pytest.mark.parametrize("omit_start", [False, True])
def test_start_now_uses_the_database_clock_for_start_and_created_at(
    auctioneer: TestClient, seeded: sessionmaker[Session], omit_start: bool
) -> None:
    body = valid_body(seeded, **({"starts_at": ...} if omit_start else {}))
    before = db_now(seeded)

    response = post(auctioneer, body)

    after = db_now(seeded)
    assert response.status_code == 201
    created = response.json()
    assert created["starts_at"] == created["created_at"]
    assert before <= parse(created["created_at"]) <= after
    (row,) = lot_rows(seeded)
    stored = dict(zip(LOT_COLUMNS, row, strict=True))
    assert stored["starts_at"] == stored["created_at"]
    assert before <= stored["created_at"] <= after


def test_a_scheduled_start_is_stored_and_returned_in_utc(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    minus3 = timezone(timedelta(hours=-3))
    base = db_now(seeded)
    start = (base + timedelta(hours=1)).astimezone(minus3)
    end = (base + timedelta(hours=3)).astimezone(minus3)
    body = valid_body(seeded, starts_at=start.isoformat(), ends_at=end.isoformat())

    response = post(auctioneer, body)

    assert response.status_code == 201
    created = response.json()
    assert created["starts_at"].endswith("Z")
    assert created["ends_at"].endswith("Z")
    assert parse(created["starts_at"]) == start
    assert parse(created["ends_at"]) == end
    (row,) = lot_rows(seeded)
    stored = dict(zip(LOT_COLUMNS, row, strict=True))
    assert stored["starts_at"] == start and stored["ends_at"] == end
    assert stored["created_at"] < stored["starts_at"]


def test_a_start_in_the_past_is_refused_after_the_aic_and_nothing_is_stored(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    now = db_now(seeded)
    body = valid_body(seeded, starts_at=iso(now - timedelta(minutes=1)))

    response = post(auctioneer, body)

    assert response.status_code == 422
    assert validation_details(response) == [
        {"loc": ["body", "starts_at"], "type": "starts_at_not_in_future"}
    ]
    assert len(fake.requests) == 1  # D5: só a hora do banco decide, depois da AIC
    assert count_lots(seeded) == 0


def test_end_not_after_a_sent_start_is_refused_without_calling_the_aic(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    start = db_now(seeded) + timedelta(hours=2)
    for end in (start, start - timedelta(seconds=1)):
        response = post(
            auctioneer, valid_body(seeded, starts_at=iso(start), ends_at=iso(end))
        )
        assert response.status_code == 422
        assert validation_details(response) == [
            {"loc": ["body", "ends_at"], "type": "ends_at_not_after_start"}
        ]
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_start_now_with_an_end_in_the_past_is_refused_after_the_aic(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    body = valid_body(seeded, ends_at=iso(db_now(seeded) - timedelta(minutes=5)))

    response = post(auctioneer, body)

    assert response.status_code == 422
    assert validation_details(response) == [
        {"loc": ["body", "ends_at"], "type": "ends_at_not_after_start"}
    ]
    assert len(fake.requests) == 1
    assert count_lots(seeded) == 0


@pytest.mark.parametrize(
    ("value", "error_type"),
    [
        ("2030-01-01T10:00:00", "timezone_aware"),
        (1893492000, "datetime_format"),
        ("1893492000", "datetime_format"),
        ("2030-01-01", "datetime_format"),
        ("2030-01-01 10:00:00Z", "datetime_format"),
        ("amanhã", "datetime_format"),
    ],
)
@pytest.mark.parametrize("field", ["starts_at", "ends_at"])
def test_malformed_datetimes_are_refused_before_the_aic(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    field: str,
    value: object,
    error_type: str,
) -> None:
    response = post(auctioneer, valid_body(seeded, **{field: value}))

    assert response.status_code == 422
    assert validation_details(response) == [
        {"loc": ["body", field], "type": error_type}
    ]
    assert fake.requests == []
    assert count_lots(seeded) == 0


@pytest.mark.parametrize("field", ["starts_at", "ends_at"])
@pytest.mark.parametrize(
    "value", ["9999-12-31T23:00:00-05:00", "0001-01-01T00:00:00+05:00"]
)
def test_a_datetime_that_overflows_utc_is_a_422_and_never_reaches_the_aic(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    field: str,
    value: str,
) -> None:
    response = post(auctioneer, valid_body(seeded, **{field: value}))

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert validation_details(response) == [
        {"loc": ["body", field], "type": "datetime_format"}
    ]
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_the_latest_instant_that_fits_in_utc_is_still_created(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    response = post(
        auctioneer, valid_body(seeded, ends_at="9999-12-31T23:59:59.999999Z")
    )

    assert response.status_code == 201
    assert response.json()["ends_at"].startswith("9999-12-31T23:59:59.999999")
    assert count_lots(seeded) == 1


def test_an_impossible_calendar_date_is_a_validation_error(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    response = post(auctioneer, valid_body(seeded, ends_at="2030-02-30T10:00:00Z"))

    assert response.status_code == 422
    details = validation_details(response)
    assert details[0]["loc"] == ["body", "ends_at"]
    # O tipo real do Pydantic para a data impossível (R10): fixado aqui.
    assert details[0]["type"] == "datetime_from_date_parsing"
    assert fake.requests == []


def test_the_end_is_required(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    response = post(auctioneer, valid_body(seeded, ends_at=...))

    assert validation_details(response) == [
        {"loc": ["body", "ends_at"], "type": "missing"}
    ]


# --- obra inelegível e catálogo indisponível ---


@pytest.mark.parametrize(
    ("external_id", "reason"),
    [(999999, "NOT_FOUND"), (129884, "NOT_PUBLIC_DOMAIN"), (555002, "NO_IMAGE")],
)
def test_ineligible_artwork_has_one_code_and_nothing_is_stored(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    caplog: pytest.LogCaptureFixture,
    external_id: int,
    reason: str,
) -> None:
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = post(auctioneer, valid_body(seeded, external_id=external_id))

    assert response.status_code == 422
    assert response.json() == NOT_ELIGIBLE_BODY
    assert response.headers["cache-control"] == "no-store"
    assert f"lot creation refused: reason={reason}" in caplog.text
    assert len(fake.requests) == 1
    assert count_lots(seeded) == 0


@pytest.mark.parametrize(("reason", "handler"), FAILURES_BOTH)
def test_catalog_failures_are_a_503_and_nothing_is_stored(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
    reason: str,
    handler: Any,
) -> None:
    fake = FakeArtic(handler)
    client = make_client(monkeypatch, seeded, fake)

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = post(client, valid_body(seeded))

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE_BODY
    assert response.headers["cache-control"] == "no-store"
    lowered = response.text.lower()
    assert "artic" not in lowered
    assert "cloudflare" not in lowered
    assert "<html" not in lowered
    assert f"operation=create_lot reason={reason}" in caplog.text
    assert count_lots(seeded) == 0


# --- fronteira da transação (CA8, D1) ---


def test_no_connection_is_idle_in_a_transaction_while_the_aic_is_called(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    test_database_url: str,
) -> None:
    timeline: list[str] = []
    idle_in_transaction: list[int] = []

    def watching(request):  # type: ignore[no-untyped-def]
        # Dentro da "chamada externa": outra conexão olha o `pg_stat_activity`.
        with db_engine.connect() as connection:
            idle_in_transaction.append(
                connection.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() "
                        "AND pid <> pg_backend_pid() "
                        "AND state IN ('idle in transaction', "
                        "'idle in transaction (aborted)')"
                    )
                ).scalar_one()
            )
        timeline.append("AIC")
        return standard_handler(request)

    def tag(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        if "pg_stat_activity" not in statement:
            timeline.append(statement.lstrip().split(None, 1)[0].upper())

    client = make_client(monkeypatch, seeded, FakeArtic(watching))
    body = valid_body(seeded)  # lê o relógio do banco: antes de escutar
    event.listen(db_engine, "before_cursor_execute", tag)
    try:
        response = post(client, body)
    finally:
        event.remove(db_engine, "before_cursor_execute", tag)

    assert response.status_code == 201
    assert idle_in_transaction == [0]
    # Antes da AIC: só a leitura da autenticação (um SELECT). Depois: o relógio do
    # banco e o INSERT; a obra nunca é lida do banco.
    assert timeline[0] == "SELECT"
    position = timeline.index("AIC")
    assert timeline[:position] == ["SELECT"]
    assert timeline[position + 1 :] == ["SELECT", "INSERT"]


# --- Story 3.4: o lote novo nasce autenticado (CA11) ---


def test_a_new_lot_is_born_with_a_valid_empty_anchor_for_its_own_id(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    response = post(auctioneer, valid_body(seeded))

    assert response.status_code == 201
    (row,) = lot_rows(seeded)
    stored = dict(zip(LOT_COLUMNS, row, strict=True))
    assert (stored["current_bid_cents"], stored["current_leader_id"]) == (None, None)
    assert (stored["bid_count"], stored["final_hash"]) == (0, GENESIS_HASH)
    audit, pseudonym = integrity_secrets()
    state = AnchorState(v=1, lot_id=stored["id"], bid_count=0, final_hash=GENESIS_HASH)
    assert verify_anchor_hmac(state, stored["anchor_hmac"], audit_hmac_secret=audit)
    assert stored["anchor_hmac"] == empty_anchor(stored["id"])
    # A âncora é do próprio lote e do segredo de auditoria, não do de pseudônimo.
    assert not verify_anchor_hmac(
        state, stored["anchor_hmac"], audit_hmac_secret=pseudonym
    )
    other = AnchorState(v=1, lot_id=uuid.uuid4(), bid_count=0, final_hash=GENESIS_HASH)
    assert not verify_anchor_hmac(other, stored["anchor_hmac"], audit_hmac_secret=audit)
    # Nada do estado de lance vaza pela resposta de criação.
    for forbidden in ("anchor_hmac", "final_hash", "bid_count", "current_leader_id"):
        assert forbidden not in response.json()


def test_a_lot_whose_anchor_cannot_be_signed_is_never_created(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    client = make_client(monkeypatch, seeded, fake, raise_server_exceptions=False)

    def refuse(*args: object, **kwargs: object) -> str:
        raise ValueError("audit_hmac_secret must be non-empty bytes")

    monkeypatch.setattr(lots, "compute_anchor_hmac", refuse)
    response = post(client, valid_body(seeded))
    monkeypatch.undo()

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert count_lots(seeded) == 0


def test_create_lot_with_an_invalid_secret_adds_nothing_to_the_session(
    seeded: sessionmaker[Session],
) -> None:
    snapshot = load_demo_artwork()
    terms = lots.LotTerms(
        starting_bid_cents=10000,
        min_increment_cents=1000,
        starts_at=None,
        ends_at=db_now(seeded) + timedelta(days=1),
    )
    with seeded() as session:
        with pytest.raises(ValueError):
            lots.create_lot(
                session,
                snapshot=snapshot,
                terms=terms,
                auctioneer_id=seeded_id(AUCTIONEER_EMAIL),
                now=db_now(seeded),
                audit_hmac_secret=b"",
            )
        assert not session.new
    assert count_lots(seeded) == 0


# --- atomicidade ---


def test_a_failure_at_commit_leaves_no_row_and_a_generic_500(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    client = make_client(monkeypatch, seeded, fake, raise_server_exceptions=False)
    body = valid_body(seeded)

    def broken_commit(self: Session) -> None:
        raise RuntimeError("SEGREDO-NO-COMMIT /srv/app/lots.py")

    monkeypatch.setattr(Session, "commit", broken_commit)
    response = post(client, body)
    monkeypatch.undo()

    assert response.status_code == 500
    assert response.json() == {
        "status": 500,
        "code": "internal_error",
        "message": MESSAGES["internal_error"],
    }
    assert "SEGREDO" not in response.text
    assert count_lots(seeded) == 0


def test_a_database_check_violation_is_a_500_and_leaves_no_row(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    client = make_client(monkeypatch, seeded, fake, raise_server_exceptions=False)
    # A regra de domínio "deixa passar" um intervalo vazio; a CHECK do banco barra.
    monkeypatch.setattr(
        lots, "resolve_schedule", lambda starts_at, ends_at, now: Schedule(now, now)
    )

    response = post(client, valid_body(seeded))

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "ck_lots" not in response.text
    assert count_lots(seeded) == 0


# --- política de acesso ---


def test_anonymous_gets_401_and_nothing_happens(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    client = make_client(monkeypatch, seeded, fake, email=None)

    response = post(client, valid_body(seeded))

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_bidder_gets_403_and_nothing_happens(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    client = make_client(monkeypatch, seeded, fake, email=BIDDER_EMAIL)

    response = post(client, valid_body(seeded))

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_anonymous_with_invalid_fields_still_gets_401(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    client = make_client(monkeypatch, seeded, fake, email=None)

    response = post(client, {"external_id": "x"})

    assert response.status_code == 401
    assert fake.requests == []


def test_malformed_json_without_a_session_is_decoded_before_the_policy(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    """Comportamento real do FastAPI, fixado aqui: ele decodifica o JSON antes de
    resolver as dependências, então o corpo ilegível vence o 401. Nada é gravado e a
    AIC não é chamada."""
    client = make_client(monkeypatch, seeded, fake, email=None)

    response = client.post(URL, content=b"{", headers=json_headers(HTTPS_ORIGIN))

    assert response.status_code == 422
    assert validation_details(response)[0]["type"] == "json_invalid"
    assert fake.requests == []
    assert count_lots(seeded) == 0


# --- proteção da 2.1 ---


def test_foreign_origin_missing_origin_and_non_json_never_reach_the_handler(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    body = valid_body(seeded)

    foreign = auctioneer.post(
        URL, json=body, headers=json_headers("https://evil.example")
    )
    missing = auctioneer.post(URL, json=body)
    not_json = auctioneer.post(
        URL,
        content="x",
        headers={"Origin": HTTPS_ORIGIN, "Content-Type": "text/plain"},
    )

    assert (foreign.status_code, foreign.json()["code"]) == (
        403,
        "csrf_origin_mismatch",
    )
    assert (missing.status_code, missing.json()["code"]) == (
        403,
        "csrf_origin_missing",
    )
    assert not_json.status_code == 415
    assert fake.requests == []
    assert count_lots(seeded) == 0


def test_other_methods_on_the_collection_are_not_allowed(
    auctioneer: TestClient, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    headers = json_headers(HTTPS_ORIGIN)

    assert auctioneer.put(URL, json={}, headers=headers).status_code == 405
    assert auctioneer.delete(URL, headers=headers).status_code == 405
    # Story 2.5: `GET /api/lots` virou a vitrine pública. Era 405 na 2.4, que
    # previa a troca; a forma da resposta é testada em `test_public_lots.py`.
    assert auctioneer.get(URL).status_code == 200
    assert fake.requests == []
