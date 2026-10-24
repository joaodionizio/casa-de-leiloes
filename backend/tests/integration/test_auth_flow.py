"""Login, `/api/me` e logout sobre PostgreSQL real (Story 2.2, CAP-2 a CAP-5)."""

import re
from datetime import timedelta
from unittest.mock import call, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app import security
from app.seed import DEMO_PASSWORD
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTP_ORIGIN,
    HTTPS_ORIGIN,
    build_client,
    cookie_name_of,
    forge_token,
    json_headers,
    login,
    secret_of,
    seed_demo_users,
    seeded_id,
)

MODES = {
    "https": (HTTPS_ORIGIN, "__Host-auction_session", True),
    "http": (HTTP_ORIGIN, "auction_session", False),
}


@pytest.fixture(params=list(MODES))
def mode(request: pytest.FixtureRequest) -> tuple[str, str, bool]:
    return MODES[request.param]


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_demo_users(db_session_factory)
    return db_session_factory


def make_client(
    monkeypatch: pytest.MonkeyPatch,
    factory: sessionmaker[Session],
    origin: str,
) -> TestClient:
    return build_client(monkeypatch, origin, session_factory=factory)


def set_cookie_attributes(header: str) -> tuple[str, dict[str, str]]:
    first, *rest = [part.strip() for part in header.split(";")]
    name = first.partition("=")[0]
    attributes = {}
    for attribute in rest:
        key, _, value = attribute.partition("=")
        attributes[key.lower()] = value
    return name, attributes


# --- login válido ---


def test_valid_login_returns_the_user_and_the_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    mode: tuple[str, str, bool],
) -> None:
    origin, cookie_name, secure = mode
    client = make_client(monkeypatch, seeded, origin)

    response = login(client, origin, BIDDER_EMAIL)

    assert response.status_code == 200
    assert response.json() == {"email": BIDDER_EMAIL, "role": "BIDDER"}
    assert response.headers["cache-control"] == "no-store"
    headers = response.headers.get_list("set-cookie")
    assert len(headers) == 1
    name, attributes = set_cookie_attributes(headers[0])
    assert name == cookie_name
    assert "httponly" in attributes
    assert ("secure" in attributes) is secure
    assert attributes["samesite"].lower() == "lax"
    assert attributes["path"] == "/"
    assert attributes["max-age"] == "28800"
    assert "domain" not in attributes


def test_token_is_in_the_cookie_only_never_in_the_body(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    mode: tuple[str, str, bool],
) -> None:
    origin, cookie_name, _ = mode
    client = make_client(monkeypatch, seeded, origin)

    response = login(client, origin, AUCTIONEER_EMAIL)

    token = client.cookies.get(cookie_name)
    assert token
    assert token not in response.text
    assert "token" not in response.text.lower()
    claims = jwt.decode(token, secret_of(client), algorithms=["HS256"])
    assert sorted(claims) == ["exp", "iat", "role", "sub"]
    assert claims["sub"] == str(seeded_id(AUCTIONEER_EMAIL))
    assert claims["role"] == "AUCTIONEER"
    assert AUCTIONEER_EMAIL not in token


def test_email_is_trimmed_and_lowercased(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)

    response = login(client, HTTPS_ORIGIN, "  Bidder1@Example.COM ")

    assert response.status_code == 200
    assert response.json()["email"] == BIDDER_EMAIL


# --- login inválido ---


def test_unknown_email_and_wrong_password_are_byte_identical(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)

    unknown = login(client, HTTPS_ORIGIN, "ninguem@example.com", "qualquer-1!")
    wrong = login(client, HTTPS_ORIGIN, BIDDER_EMAIL, "senha-errada-1!")

    for response in (unknown, wrong):
        assert response.status_code == 401
        assert response.json() == {
            "status": 401,
            "code": "invalid_credentials",
            "message": "E-mail ou senha inválidos.",
        }
        assert "set-cookie" not in response.headers
        assert response.headers["cache-control"] == "no-store"
        assert "example.com" not in response.text
    assert unknown.content == wrong.content
    assert client.cookies.get("__Host-auction_session") is None


def test_unknown_email_still_verifies_against_the_reference_hash(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    reference_hash = security._reference_hash()
    assert reference_hash.startswith("$argon2id$")

    # `wraps`: a verificação Argon2 real roda; o spy só registra os argumentos.
    with patch.object(
        security, "verify_password", wraps=security.verify_password
    ) as verify:
        login(client, HTTPS_ORIGIN, "ninguem@example.com", "qualquer-1!")
        assert verify.call_args_list == [call(reference_hash, "qualquer-1!")]

        verify.reset_mock()
        login(client, HTTPS_ORIGIN, BIDDER_EMAIL, "senha-errada-1!")
        # E-mail existente: verifica contra o hash do usuário, não o de referência.
        assert verify.call_count == 1
        user_hash, password = verify.call_args.args
        assert user_hash != reference_hash
        assert user_hash.startswith("$argon2id$")
        assert password == "senha-errada-1!"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "bidder1@example.com"},
        {"password": "x"},
        {"email": "", "password": "x"},
        {"email": "   ", "password": "x"},
        {"email": "a@example.com", "password": ""},
        {"email": "a" * 255, "password": "x"},
        {"email": "a@example.com", "password": "p" * 1025},
        {"email": 123, "password": "x"},
        {"email": "a@example.com", "password": None},
    ],
)
def test_invalid_payloads_are_422_without_input(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    payload: dict[str, object],
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)

    response = client.post(
        "/api/auth/login", json=payload, headers={"Origin": HTTPS_ORIGIN}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    for detail in body["details"]:
        assert set(detail) == {"loc", "type"}
    for value in ("x" * 5, "example.com", "p" * 10):
        assert value not in response.text
    assert "set-cookie" not in response.headers


def test_malformed_json_is_422(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    response = client.post(
        "/api/auth/login", content=b"{nao-e-json", headers=json_headers(HTTPS_ORIGIN)
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_a_malformed_email_is_just_invalid_credentials(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    response = login(client, HTTPS_ORIGIN, "isto não é e-mail", "x")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


# --- /api/me ---


def test_me_with_a_valid_session(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    mode: tuple[str, str, bool],
) -> None:
    origin, _, _ = mode
    client = make_client(monkeypatch, seeded, origin)
    login(client, origin, AUCTIONEER_EMAIL)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json() == {"email": AUCTIONEER_EMAIL, "role": "AUCTIONEER"}
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers


def test_me_without_cookie_is_401_in_the_single_format(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)

    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.json() == {
        "status": 401,
        "code": "unauthorized",
        "message": "Autenticação necessária.",
    }
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert "www-authenticate" not in response.headers


def test_me_with_a_tampered_cookie_is_401(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    name = cookie_name_of(client)
    token = client.cookies.get(name)
    client.cookies.set(
        name, token[:-3] + ("abc" if not token.endswith("abc") else "xyz")
    )

    assert client.get("/api/me").status_code == 401


def test_me_with_an_expired_forged_token_is_401(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    client.cookies.set(
        cookie_name_of(client),
        forge_token(
            client,
            sub=seeded_id(BIDDER_EMAIL),
            issued_ago=timedelta(hours=9),
        ),
    )
    assert client.get("/api/me").status_code == 401


def test_a_valid_forged_token_for_a_seeded_user_proves_the_control(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    # Controle: o mesmo token, não expirado, é aceito. Sem ele, os testes de
    # expirado e de papel incoerente poderiam passar por outro motivo.
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    client.cookies.set(
        cookie_name_of(client), forge_token(client, sub=seeded_id(BIDDER_EMAIL))
    )
    assert client.get("/api/me").json() == {"email": BIDDER_EMAIL, "role": "BIDDER"}


def test_me_after_the_user_is_deleted_is_401(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    with seeded() as session:
        session.execute(text("DELETE FROM users WHERE email = :e"), {"e": BIDDER_EMAIL})
        session.commit()

    assert client.get("/api/me").status_code == 401


def test_me_after_the_role_changed_in_the_database_is_401(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    with seeded() as session:
        session.execute(
            text("UPDATE users SET role = 'AUCTIONEER' WHERE email = :e"),
            {"e": BIDDER_EMAIL},
        )
        session.commit()

    assert client.get("/api/me").status_code == 401


def test_cookie_of_the_other_mode_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    https_client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    login(https_client, HTTPS_ORIGIN, BIDDER_EMAIL)
    token = https_client.cookies.get("__Host-auction_session")

    http_client = make_client(monkeypatch, seeded, HTTP_ORIGIN)
    http_client.cookies.set("__Host-auction_session", token)
    assert http_client.get("/api/me").status_code == 401

    other_https = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    other_https.cookies.set("auction_session", token)
    assert other_https.get("/api/me").status_code == 401


# --- logout ---


def test_logout_deletes_the_cookie_with_the_same_attributes_and_ends_the_session(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    mode: tuple[str, str, bool],
) -> None:
    origin, cookie_name, secure = mode
    client = make_client(monkeypatch, seeded, origin)
    login(client, origin, BIDDER_EMAIL)
    assert client.get("/api/me").status_code == 200

    response = client.post("/api/auth/logout", headers=json_headers(origin))

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    headers = response.headers.get_list("set-cookie")
    assert len(headers) == 1
    name, attributes = set_cookie_attributes(headers[0])
    assert name == cookie_name
    assert attributes["max-age"] == "0"
    assert attributes["path"] == "/"
    assert "httponly" in attributes
    assert ("secure" in attributes) is secure
    assert attributes["samesite"].lower() == "lax"
    assert "domain" not in attributes
    assert re.search(r"expires=", headers[0], re.IGNORECASE)
    assert client.get("/api/me").status_code == 401


def test_logout_without_session_or_with_an_invalid_cookie_is_still_204(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)

    without_cookie = client.post("/api/auth/logout", headers=json_headers(HTTPS_ORIGIN))
    client.cookies.set(cookie_name_of(client), "lixo")
    with_garbage = client.post("/api/auth/logout", headers=json_headers(HTTPS_ORIGIN))

    for response in (without_cookie, with_garbage):
        assert response.status_code == 204
        assert len(response.headers.get_list("set-cookie")) == 1


def test_a_token_copied_before_logout_keeps_working_until_exp(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    """Limitação declarada (AD-29, README): sem revogação no servidor."""
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    name = cookie_name_of(client)
    copied = client.cookies.get(name)

    client.post("/api/auth/logout", headers=json_headers(HTTPS_ORIGIN))
    assert client.get("/api/me").status_code == 401

    client.cookies.set(name, copied)
    assert client.get("/api/me").status_code == 200


def test_login_does_not_log_the_password_hash_or_token(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = make_client(monkeypatch, seeded, HTTPS_ORIGIN)
    with caplog.at_level("DEBUG"):
        login(client, HTTPS_ORIGIN, BIDDER_EMAIL)
    token = client.cookies.get("__Host-auction_session")
    assert DEMO_PASSWORD not in caplog.text
    assert token not in caplog.text
    assert "$argon2" not in caplog.text
