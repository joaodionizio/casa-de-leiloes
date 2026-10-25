"""`GET /api/lots/mine` sobre PostgreSQL real (Story 2.4, test-plan §5, A2)."""

import uuid
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.seed import DEMO_AUCTIONEER_ID
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
    seed_demo_users,
)
from tests.catalog_support import FakeArtic, install, standard_handler
from tests.lot_support import (
    count_lots,
    db_now,
    insert_lot,
    lot_rows,
    statement_recorder,
    valid_body,
)

URL = "/api/lots/mine"
KEYS = sorted(
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


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_demo_users(db_session_factory)
    return db_session_factory


@pytest.fixture
def fake() -> FakeArtic:
    return FakeArtic(standard_handler)


def client_for(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
    email: str | None = AUCTIONEER_EMAIL,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    install(client.app, fake)  # type: ignore[arg-type]
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


@pytest.fixture
def auctioneer(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session], fake: FakeArtic
) -> TestClient:
    return client_for(monkeypatch, seeded, fake)


def add_other_auctioneer(seeded: sessionmaker[Session]) -> uuid.UUID:
    other = uuid.uuid4()
    with seeded() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, 'segundo@example.com', 'h', 'AUCTIONEER')"
            ),
            {"id": other},
        )
        session.commit()
    return other


def ids_of(response: Any) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


def test_an_auctioneer_without_lots_gets_an_empty_list(
    auctioneer: TestClient,
) -> None:
    response = auctioneer.get(URL)

    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert response.headers["cache-control"] == "no-store"


def test_each_auctioneer_sees_only_their_own_lots(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    other = add_other_auctioneer(seeded)
    mine = insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID, title="Meu")
    theirs = insert_lot(seeded, auctioneer_id=other, title="Dele")
    client = client_for(monkeypatch, seeded, fake)

    response = client.get(URL)

    assert ids_of(response) == [str(mine)]
    assert response.json()["items"][0]["title"] == "Meu"
    assert str(theirs) not in response.text


def test_the_owner_never_comes_from_the_query_string(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    other = add_other_auctioneer(seeded)
    mine = insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID)
    insert_lot(seeded, auctioneer_id=other)
    client = client_for(monkeypatch, seeded, fake)

    for query in (f"?auctioneer_id={other}", f"?user_id={other}", "?limit=0&page=9"):
        assert ids_of(client.get(URL + query)) == [str(mine)]


def test_newest_first_and_id_descending_when_created_at_ties(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    now = db_now(seeded)
    oldest = insert_lot(
        seeded, auctioneer_id=DEMO_AUCTIONEER_ID, created_at=now - timedelta(days=2)
    )
    middle = insert_lot(
        seeded, auctioneer_id=DEMO_AUCTIONEER_ID, created_at=now - timedelta(days=1)
    )
    tie_a = insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID, created_at=now)
    tie_b = insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID, created_at=now)
    first, second = sorted([tie_a, tie_b], reverse=True)

    response = auctioneer.get(URL)

    assert ids_of(response) == [str(first), str(second), str(middle), str(oldest)]


def test_there_is_no_limit_and_no_pagination(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    now = db_now(seeded)
    created = [
        insert_lot(
            seeded,
            auctioneer_id=DEMO_AUCTIONEER_ID,
            created_at=now - timedelta(seconds=index),
        )
        for index in range(101)
    ]

    response = auctioneer.get(URL)

    assert response.status_code == 200
    assert len(response.json()["items"]) == 101
    assert ids_of(response) == [str(lot_id) for lot_id in created]


def test_items_have_the_exact_contract_keys_and_derived_image_url(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID)

    (item,) = auctioneer.get(URL).json()["items"]

    assert sorted(item) == KEYS
    assert "is_demo" not in item and "auctioneer_id" not in item
    assert item["image_url"] == f"/api/catalog/images/{item['image_id']}"
    for key in ("starts_at", "ends_at", "created_at"):
        assert item[key].endswith("Z")


def test_a_freshly_created_lot_is_the_first_item(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    insert_lot(
        seeded,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        created_at=db_now(seeded) - timedelta(days=1),
    )
    created = auctioneer.post(
        "/api/lots", json=valid_body(seeded), headers=json_headers(HTTPS_ORIGIN)
    )
    assert created.status_code == 201

    response = auctioneer.get(URL)

    assert ids_of(response)[0] == created.json()["id"]
    assert len(ids_of(response)) == 2


def test_the_list_does_not_depend_on_the_aic(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    def always_down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede", request=request)

    fake = FakeArtic(always_down)
    insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID, title="Persistido")
    client = client_for(monkeypatch, seeded, fake)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Persistido"
    assert fake.requests == []


def test_reading_only_selects_and_changes_nothing(
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID)
    before_rows = lot_rows(seeded)
    before_count = count_lots(seeded)

    with statement_recorder(db_engine) as recorder:
        response = auctioneer.get(URL)

    assert response.status_code == 200
    assert recorder.statements
    assert all(
        statement.lstrip().upper().startswith("SELECT")
        for statement in recorder.statements
    )
    assert count_lots(seeded) == before_count
    assert lot_rows(seeded) == before_rows


def test_anonymous_gets_401_and_bidder_gets_403(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    fake: FakeArtic,
) -> None:
    insert_lot(seeded, auctioneer_id=DEMO_AUCTIONEER_ID)

    anonymous = client_for(monkeypatch, seeded, fake, email=None).get(URL)
    bidder = client_for(monkeypatch, seeded, fake, email=BIDDER_EMAIL).get(URL)

    assert anonymous.status_code == 401
    assert anonymous.json()["code"] == "unauthorized"
    assert bidder.status_code == 403
    assert bidder.json()["code"] == "forbidden"
    assert fake.requests == []


def test_a_route_that_is_not_get_does_not_exist_for_the_list(
    auctioneer: TestClient,
) -> None:
    headers = json_headers(HTTPS_ORIGIN)

    assert auctioneer.post(URL, json={}, headers=headers).status_code == 405
    assert auctioneer.delete(URL, headers=headers).status_code == 405
