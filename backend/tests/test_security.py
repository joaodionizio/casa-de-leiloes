"""Senha e token da Story 2.2, sem banco."""

import uuid
from collections.abc import Iterator
from datetime import timedelta

import jwt
import pytest
from argon2.exceptions import InvalidHashError
from fastapi.testclient import TestClient

from app import security
from tests.auth_support import (
    HTTPS_ORIGIN,
    build_client,
    cookie_name_of,
    forge_token,
    secret_of,
)

PASSWORD = "uma-senha-qualquer-1!"


class NoDatabase:
    """Falha se a dependência tocar o banco: tokens inválidos nunca chegam lá."""

    def get(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("o banco não deveria ser consultado")


def no_database_session() -> Iterator[NoDatabase]:
    yield NoDatabase()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    return build_client(
        monkeypatch, HTTPS_ORIGIN, session_dependency=no_database_session
    )


# --- senha ---


def test_hash_is_argon2id_and_differs_from_the_plain_text() -> None:
    hashed = security.hash_password(PASSWORD)
    assert hashed.startswith("$argon2id$")
    assert PASSWORD not in hashed


def test_verify_password_right_and_wrong() -> None:
    hashed = security.hash_password(PASSWORD)
    assert security.verify_password(hashed, PASSWORD) is True
    assert security.verify_password(hashed, PASSWORD + "x") is False


def test_each_hash_has_its_own_salt() -> None:
    assert security.hash_password(PASSWORD) != security.hash_password(PASSWORD)


def test_a_corrupted_hash_propagates_instead_of_becoming_a_wrong_password() -> None:
    with pytest.raises(InvalidHashError):
        security.verify_password("isto-nao-e-um-hash", PASSWORD)


def test_reference_password_check_never_raises_and_returns_nothing() -> None:
    assert security.verify_reference_password(PASSWORD) is None


# --- token emitido ---


def test_issued_token_has_exactly_the_four_claims_and_8_hours(
    client: TestClient,
) -> None:
    user_id = uuid.uuid4()
    token = security.issue_token(user_id, "BIDDER", secret_of(client))

    claims = jwt.decode(token, secret_of(client), algorithms=["HS256"])
    assert sorted(claims) == ["exp", "iat", "role", "sub"]
    assert claims["sub"] == str(user_id)
    assert claims["role"] == "BIDDER"
    assert claims["exp"] - claims["iat"] == 28800 == security.SESSION_MAX_AGE_SECONDS
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_decode_token_round_trip(client: TestClient) -> None:
    user_id = uuid.uuid4()
    token = security.issue_token(user_id, "AUCTIONEER", secret_of(client))
    claims = security.decode_token(token, secret_of(client))
    assert claims["sub"] == str(user_id)
    assert claims["role"] == "AUCTIONEER"


# --- token recusado pela dependência (nunca chega ao banco) ---

INVALID_TOKENS = {
    "outro segredo": lambda c: forge_token(c, secret="x" * 40),
    "alg none": lambda c: forge_token(c, algorithm="none"),
    "HS384": lambda c: forge_token(c, algorithm="HS384"),
    "HS512": lambda c: forge_token(c, algorithm="HS512"),
    "sem exp": lambda c: forge_token(c, omit=("exp",)),
    "sem sub": lambda c: forge_token(c, omit=("sub",)),
    "sem role": lambda c: forge_token(c, omit=("role",)),
    "sem iat": lambda c: forge_token(c, omit=("iat",)),
    "expirado": lambda c: forge_token(
        c, issued_ago=timedelta(hours=9), lifetime=timedelta(hours=8)
    ),
    "iat no futuro": lambda c: forge_token(c, issued_ago=-timedelta(hours=1)),
    "sub não UUID": lambda c: forge_token(c, sub="não-é-uuid"),
    "role desconhecido": lambda c: forge_token(c, role="ADMIN"),
    "lixo": lambda c: "isto.nao.e-um-jwt",
    "vazio": lambda c: "",
}


@pytest.mark.parametrize("case", list(INVALID_TOKENS))
def test_invalid_tokens_are_401_without_touching_the_database(
    client: TestClient, case: str
) -> None:
    client.cookies.set(cookie_name_of(client), INVALID_TOKENS[case](client))

    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert "www-authenticate" not in response.headers


def test_authorization_header_is_never_accepted(client: TestClient) -> None:
    token = security.issue_token(uuid.uuid4(), "BIDDER", secret_of(client))
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_a_token_for_the_other_cookie_mode_is_not_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http_client = build_client(
        monkeypatch,
        "http://localhost:5173",
        session_dependency=no_database_session,
    )
    http_client.cookies.set(
        "__Host-auction_session", forge_token(http_client, sub=uuid.uuid4())
    )
    assert http_client.get("/api/me").status_code == 401
