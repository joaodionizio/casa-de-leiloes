"""Papéis nas rotas sintéticas, sobre PostgreSQL real (Story 2.2, CAP-7)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    cookie_name_of,
    forge_token,
    login,
    seed_demo_users,
    seeded_id,
)

AUCTIONEER_ONLY = "/api/test/auctioneer-only"
BIDDER_ONLY = "/api/test/bidder-only"
OPTIONAL = "/api/test/optional"


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_demo_users(db_session_factory)
    return db_session_factory


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    return build_client(
        monkeypatch, HTTPS_ORIGIN, session_factory=seeded, role_routes=True
    )


def test_auctioneer_passes_on_its_route_and_gets_403_on_the_bidders(
    client: TestClient,
) -> None:
    login(client, HTTPS_ORIGIN, AUCTIONEER_EMAIL)

    allowed = client.get(AUCTIONEER_ONLY)
    denied = client.get(BIDDER_ONLY)

    assert allowed.status_code == 200
    assert allowed.json() == {"email": AUCTIONEER_EMAIL}
    assert denied.status_code == 403
    assert denied.json() == {
        "status": 403,
        "code": "forbidden",
        "message": "Acesso negado.",
    }


def test_bidder_passes_on_its_route_and_gets_403_on_the_auctioneers(
    client: TestClient,
) -> None:
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)

    allowed = client.get(BIDDER_ONLY)
    denied = client.get(AUCTIONEER_ONLY)

    assert allowed.status_code == 200
    assert allowed.json() == {"email": BIDDER_EMAIL}
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"


@pytest.mark.parametrize("path", [AUCTIONEER_ONLY, BIDDER_ONLY])
def test_visitor_gets_401_on_role_routes(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_optional_route_without_cookie_is_anonymous(client: TestClient) -> None:
    response = client.get(OPTIONAL)
    assert response.status_code == 200
    assert response.json() == {"anonymous": True}


def test_optional_route_with_a_valid_session_exposes_the_user(
    client: TestClient,
) -> None:
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    assert client.get(OPTIONAL).json() == {"email": BIDDER_EMAIL}


def break_session(client: TestClient, seeded: sessionmaker[Session], how: str) -> None:
    """Deixa a sessão do cliente inválida de cinco jeitos diferentes."""
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    name = cookie_name_of(client)
    if how == "tampered":
        token = client.cookies.get(name)
        client.cookies.set(name, token[:-3] + ("abc" if token[-3:] != "abc" else "xyz"))
    elif how == "expired":
        client.cookies.set(
            name,
            forge_token(
                client, sub=seeded_id(BIDDER_EMAIL), issued_ago=timedelta(hours=9)
            ),
        )
    elif how == "deleted user":
        with seeded() as session:
            session.execute(
                text("DELETE FROM users WHERE email = :e"), {"e": BIDDER_EMAIL}
            )
            session.commit()
    elif how == "role changed":
        with seeded() as session:
            session.execute(
                text("UPDATE users SET role = 'AUCTIONEER' WHERE email = :e"),
                {"e": BIDDER_EMAIL},
            )
            session.commit()
    elif how == "garbage":
        client.cookies.set(name, "lixo")
    else:
        raise AssertionError(how)


INVALID_SESSIONS = ["tampered", "expired", "deleted user", "role changed", "garbage"]


@pytest.mark.parametrize("how", INVALID_SESSIONS)
def test_optional_route_treats_any_invalid_session_as_anonymous(
    client: TestClient, seeded: sessionmaker[Session], how: str
) -> None:
    break_session(client, seeded, how)

    response = client.get(OPTIONAL)

    assert response.status_code == 200
    assert response.json() == {"anonymous": True}
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("path", [AUCTIONEER_ONLY, BIDDER_ONLY])
@pytest.mark.parametrize("how", INVALID_SESSIONS)
def test_role_routes_answer_401_to_any_invalid_session(
    client: TestClient, seeded: sessionmaker[Session], how: str, path: str
) -> None:
    break_session(client, seeded, how)

    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert "set-cookie" not in response.headers


def test_a_401_does_not_clear_the_cookie_and_logout_after_it_still_works(
    client: TestClient,
) -> None:
    client.cookies.set(cookie_name_of(client), "lixo")
    assert client.get(AUCTIONEER_ONLY).status_code == 401
    assert client.cookies.get(cookie_name_of(client)) == "lixo"
