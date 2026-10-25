"""Rotas do catálogo da AIC, sobre PostgreSQL real (Story 2.3, test-plan §4)."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.artic import CatalogUnavailable
from app.catalog import LookupStatus, get_artwork
from app.errors import MESSAGES
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
    seed_demo_users,
)
from tests.catalog_support import (
    FAILURES_BOTH,
    FakeArtic,
    artic_client,
    install,
    raising,
    search_params,
    standard_handler,
)

SEARCH = "/api/catalog/artworks"
DETAIL = "/api/catalog/artworks/{}"

SUMMARY_KEYS = [
    "artist_display",
    "date_display",
    "external_id",
    "image_id",
    "image_url",
    "title",
]
DETAIL_KEYS = sorted(
    SUMMARY_KEYS
    + [
        "credit_line",
        "department_title",
        "dimensions",
        "medium_display",
        "source_url",
        "artwork_type_title",
    ]
)
IMAGE_PREFIX = "/api/catalog/images/"
UNAVAILABLE_BODY = {
    "status": 503,
    "code": "catalog_unavailable",
    "message": MESSAGES["catalog_unavailable"],
}
NOT_FOUND_BODY = {
    "status": 404,
    "code": "not_found",
    "message": "Recurso não encontrado.",
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
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    install(client.app, fake)  # type: ignore[arg-type]
    return client


@pytest.fixture
def auctioneer(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], fake: FakeArtic
) -> TestClient:
    client = make_client(monkeypatch, seeded, fake)
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    return client


@pytest.fixture
def bidder(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], fake: FakeArtic
) -> TestClient:
    client = make_client(monkeypatch, seeded, fake)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    return client


@pytest.fixture
def anonymous(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], fake: FakeArtic
) -> TestClient:
    return make_client(monkeypatch, seeded, fake)


# --- busca ---


def test_search_returns_only_eligible_items_in_the_aic_order(
    auctioneer: TestClient,
) -> None:
    response = auctioneer.get(SEARCH, params={"q": "monet"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    items = response.json()["items"]
    assert [item["external_id"] for item in items] == [16568, 16571, 16572]
    for item in items:
        assert sorted(item) == SUMMARY_KEYS
        # Same-origin: o navegador nunca pede o IIIF direto (revisão do AD-22).
        assert item["image_url"] == f"{IMAGE_PREFIX}{item['image_id']}"
        assert "artic.edu" not in item["image_url"]
    assert items[0]["title"] == "Water Lilies"
    assert items[2]["date_display"] is None
    assert items[2]["artist_display"] == "Atelier Monet\nFrench, 19th century"


def test_search_never_returns_ineligible_items(auctioneer: TestClient) -> None:
    ids = {
        item["external_id"]
        for item in auctioneer.get(SEARCH, params={"q": "monet"}).json()["items"]
    }

    # is_public_domain falso, ausente; sem image_id; image_id inválido; id string.
    assert ids.isdisjoint({100001, 100002, 100003, 100004})
    assert len(ids) == 3


def test_search_trims_the_term_before_calling_the_aic(
    auctioneer: TestClient, fake: FakeArtic
) -> None:
    auctioneer.get(SEARCH, params={"q": "  monet  "})

    (request,) = fake.requests
    assert search_params(request)["q"] == "monet"


def test_search_without_match_is_a_real_empty_list(auctioneer: TestClient) -> None:
    response = auctioneer.get(SEARCH, params={"q": "qxzvkwjq"})

    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert response.headers["cache-control"] == "no-store"


# --- detalhe ---


def test_detail_returns_the_full_snapshot(auctioneer: TestClient) -> None:
    response = auctioneer.get(DETAIL.format(27992))

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert sorted(body) == DETAIL_KEYS
    assert len(body) == 12
    assert body["external_id"] == 27992
    assert body["source_url"] == "https://www.artic.edu/artworks/27992"
    assert body["dimensions"] == "207.5 × 308.1 cm (81 3/4 × 121 1/4 in.)"
    assert body["image_url"] == (f"{IMAGE_PREFIX}2d484387-2509-5e8e-2c43-22f9981972eb")


def test_detail_missing_fields_are_null_never_invented(auctioneer: TestClient) -> None:
    body = auctioneer.get(DETAIL.format(555001)).json()

    assert body["title"] == "Study"
    assert body["medium_display"] is None
    assert body["dimensions"] is None
    assert body["department_title"] is None
    assert body["credit_line"] is None
    assert body["date_display"] is None
    assert body["artwork_type_title"] == "Drawing and Watercolor"


@pytest.mark.parametrize("external_id", [999999999, 129884, 555002])
def test_detail_not_found_not_public_domain_and_no_image_look_the_same(
    auctioneer: TestClient, external_id: int
) -> None:
    response = auctioneer.get(DETAIL.format(external_id))

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == NOT_FOUND_BODY


def test_service_keeps_the_internal_reason(fake: FakeArtic) -> None:
    client = artic_client(fake)

    assert get_artwork(client, 27992).status == LookupStatus.FOUND
    assert get_artwork(client, 27992).artwork is not None
    assert get_artwork(client, 999999999).status == LookupStatus.NOT_FOUND
    assert get_artwork(client, 129884).status == LookupStatus.NOT_PUBLIC_DOMAIN
    assert get_artwork(client, 555002).status == LookupStatus.NO_IMAGE
    assert get_artwork(client, 555002).artwork is None


def test_service_lets_catalog_unavailable_through() -> None:
    fake = FakeArtic(lambda request: httpx.Response(500))
    with pytest.raises(CatalogUnavailable):
        get_artwork(artic_client(fake), 27992)


# --- falhas da AIC ---


def assert_unavailable(response: httpx.Response) -> None:
    assert response.status_code == 503
    assert response.json() == UNAVAILABLE_BODY
    assert response.headers["cache-control"] == "no-store"
    lowered = response.text.lower()
    for forbidden in ("artic", "cloudflare", "<html", "detail"):
        assert forbidden not in lowered


@pytest.mark.parametrize(("reason", "handler"), FAILURES_BOTH)
def test_search_failures_are_503_catalog_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
    reason: str,
    handler: Any,
) -> None:
    client = make_client(monkeypatch, seeded, FakeArtic(handler))
    login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL)

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        response = client.get(SEARCH, params={"q": "termo-secreto"})

    assert_unavailable(response)
    assert f"operation=search reason={reason}" in caplog.text
    assert "termo-secreto" not in caplog.text


@pytest.mark.parametrize(("reason", "handler"), FAILURES_BOTH)
def test_detail_failures_are_503_catalog_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
    reason: str,
    handler: Any,
) -> None:
    client = make_client(monkeypatch, seeded, FakeArtic(handler))
    login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL)

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        response = client.get(DETAIL.format(27992))

    assert_unavailable(response)
    assert f"operation=detail reason={reason}" in caplog.text


def test_redirect_from_the_aic_is_503_after_a_single_request(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    fake = FakeArtic(
        lambda request: httpx.Response(301, headers={"Location": "https://x.example/"})
    )
    client = make_client(monkeypatch, seeded, fake)
    login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL)

    assert_unavailable(client.get(SEARCH, params={"q": "monet"}))
    assert len(fake.requests) == 1


# --- entrada ---


@pytest.mark.parametrize(
    "params",
    [None, {"q": ""}, {"q": "   "}, {"q": "a" * 101}, {"q": "  " + "a" * 101 + "  "}],
)
def test_invalid_term_is_422_without_calling_the_aic(
    auctioneer: TestClient, fake: FakeArtic, params: dict[str, str] | None
) -> None:
    response = auctioneer.get(SEARCH, params=params)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"][0]["loc"] == ["query", "q"]
    if params and params["q"].strip():
        assert params["q"].strip() not in response.text
    assert fake.requests == []


def test_term_of_exactly_100_characters_is_accepted(auctioneer: TestClient) -> None:
    assert auctioneer.get(SEARCH, params={"q": "a" * 100}).status_code == 200


@pytest.mark.parametrize("external_id", ["abc", "0", "-1", "1.5", "2147483648"])
def test_invalid_external_id_is_422_without_calling_the_aic(
    auctioneer: TestClient, fake: FakeArtic, external_id: str
) -> None:
    response = auctioneer.get(f"{SEARCH}/{external_id}")

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert fake.requests == []


def test_largest_valid_external_id_reaches_the_aic(
    auctioneer: TestClient, fake: FakeArtic
) -> None:
    assert auctioneer.get(DETAIL.format(2147483647)).status_code == 404
    assert [r.url.path for r in fake.requests] == ["/api/v1/artworks/2147483647"]


@pytest.mark.parametrize("path", ["1%2F2", "%2e%2e%2f1"])
def test_encoded_path_tricks_are_404_without_calling_the_aic(
    auctioneer: TestClient, fake: FakeArtic, path: str
) -> None:
    response = auctioneer.get(f"{SEARCH}/{path}")

    assert response.status_code == 404
    assert fake.requests == []


# --- política de acesso ---


@pytest.mark.parametrize("url", [SEARCH + "?q=monet", DETAIL.format(27992)])
def test_visitor_gets_401_without_calling_the_aic(
    anonymous: TestClient, fake: FakeArtic, url: str
) -> None:
    response = anonymous.get(url)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert fake.requests == []


@pytest.mark.parametrize("url", [SEARCH + "?q=monet", DETAIL.format(27992)])
def test_bidder_gets_403_without_calling_the_aic(
    bidder: TestClient, fake: FakeArtic, url: str
) -> None:
    response = bidder.get(url)

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert fake.requests == []


def test_visitor_with_an_invalid_term_still_gets_401(
    anonymous: TestClient, fake: FakeArtic
) -> None:
    assert anonymous.get(SEARCH, params={"q": ""}).status_code == 401
    assert anonymous.get(SEARCH).status_code == 401
    assert fake.requests == []


# --- sem efeito colateral ---


@contextmanager
def recorded_statements(engine: Engine) -> Iterator[list[str]]:
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany) -> None:  # type: ignore[no-untyped-def]
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_catalog_calls_only_select_from_the_database(
    auctioneer: TestClient, db_engine: Engine
) -> None:
    with recorded_statements(db_engine) as statements:
        assert auctioneer.get(SEARCH, params={"q": "monet"}).status_code == 200
        assert auctioneer.get(DETAIL.format(27992)).status_code == 200
        assert auctioneer.get(DETAIL.format(999999999)).status_code == 404

    assert statements
    assert all(s.lstrip().upper().startswith("SELECT") for s in statements)


@pytest.mark.parametrize("url", [SEARCH + "?q=monet", DETAIL.format(27992)])
@pytest.mark.parametrize("method", ["head", "options"])
def test_head_and_options_are_405_without_calling_the_aic(
    auctioneer: TestClient, fake: FakeArtic, method: str, url: str
) -> None:
    assert getattr(auctioneer, method)(url).status_code == 405
    assert fake.requests == []


def test_creating_the_app_and_health_do_not_call_the_aic(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], fake: FakeArtic
) -> None:
    client = make_client(monkeypatch, seeded, fake)

    assert client.get("/health").status_code == 200
    assert fake.requests == []


# --- isolamento ---


def test_the_rest_of_the_app_works_while_the_aic_fails(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    fake = FakeArtic(raising(lambda r: httpx.ConnectError("down", request=r)))
    client = make_client(monkeypatch, seeded, fake)

    assert client.get("/health").status_code == 200
    assert login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL).status_code == 200
    assert client.get("/api/me").status_code == 200
    assert_unavailable(client.get(SEARCH, params={"q": "monet"}))
    assert client.get("/api/me").status_code == 200
    logout = client.post("/api/auth/logout", headers=json_headers(HTTPS_ORIGIN))
    assert logout.status_code == 204
