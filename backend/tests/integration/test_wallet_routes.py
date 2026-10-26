"""`GET /api/wallet` e `POST /api/wallet/deposit` sobre PostgreSQL real (Story 3.1,
CAP-4 a CAP-9, CAP-11). Dinheiro sempre como inteiro, nunca `float`."""

import json
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.errors import MESSAGES
from app.money import MAX_CENTS
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    cookie_name_of,
    forge_token,
    json_headers,
    login,
    seeded_id,
)
from tests.lot_support import statement_recorder
from tests.wallet_support import (
    delete_wallet,
    seed_users_with_wallets,
    set_wallet,
    wallet_row,
    wallet_rows,
)

READ = "/api/wallet"
DEPOSIT = "/api/wallet/deposit"
KEYS = ["available_balance_cents", "committed_balance_cents", "total_balance_cents"]
LIMIT_MESSAGE = "O depósito ultrapassaria o limite de saldo da carteira."


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    return db_session_factory


def client_for(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    email: str | None = BIDDER_EMAIL,
    **kwargs: Any,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded, **kwargs)
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


@pytest.fixture
def bidder(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    return client_for(monkeypatch, seeded)


@pytest.fixture
def auctioneer(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    return client_for(monkeypatch, seeded, AUCTIONEER_EMAIL)


def post(client: TestClient, amount: Any) -> Any:
    return client.post(
        DEPOSIT, json={"amount_cents": amount}, headers=json_headers(HTTPS_ORIGIN)
    )


def error_of(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    body = response.json()
    assert body["status"] == status
    assert body["code"] == code
    assert body["message"] == MESSAGES[code]
    return body


# --- leitura ---


def test_bidder_reads_the_three_balances(bidder: TestClient) -> None:
    response = bidder.get(READ)

    assert response.status_code == 200
    assert response.json() == {
        "total_balance_cents": 0,
        "committed_balance_cents": 0,
        "available_balance_cents": 0,
    }
    assert sorted(response.json()) == KEYS
    assert response.headers["cache-control"] == "no-store"


def test_available_is_derived_as_total_minus_committed(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    set_wallet(seeded, seeded_id(BIDDER_EMAIL), 1000, 400)

    assert bidder.get(READ).json() == {
        "total_balance_cents": 1000,
        "committed_balance_cents": 400,
        "available_balance_cents": 600,
    }


def test_reading_only_selects_and_never_locks(
    bidder: TestClient, db_engine: Engine
) -> None:
    with statement_recorder(db_engine) as recorder:
        assert bidder.get(READ).status_code == 200

    wallet_statements = [s for s in recorder.statements if "wallets" in s]
    assert wallet_statements, "a leitura não consultou a carteira"
    for statement in recorder.statements:
        normalized = statement.lstrip().upper()
        assert normalized.startswith(("SELECT", "BEGIN", "ROLLBACK")), statement
        assert "FOR UPDATE" not in normalized


def test_reading_does_not_change_the_wallet(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    before = wallet_rows(seeded)
    bidder.get(READ)
    assert wallet_rows(seeded) == before


def test_anonymous_tampered_and_expired_sessions_get_401(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    anonymous = client_for(monkeypatch, seeded, None)
    error_of(anonymous.get(READ), 401, "unauthorized")

    tampered = client_for(monkeypatch, seeded)
    tampered.cookies.set(
        cookie_name_of(tampered), "x" + tampered.cookies[cookie_name_of(tampered)]
    )
    response = tampered.get(READ)
    error_of(response, 401, "unauthorized")
    assert response.headers["cache-control"] == "no-store"

    expired = client_for(monkeypatch, seeded, None)
    expired.cookies.set(
        cookie_name_of(expired),
        forge_token(
            expired,
            sub=seeded_id(BIDDER_EMAIL),
            issued_ago=timedelta(hours=9),
        ),
    )
    error_of(expired.get(READ), 401, "unauthorized")


def test_auctioneer_gets_403_on_read_and_deposit(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    before = wallet_rows(seeded)

    read = auctioneer.get(READ)
    error_of(read, 403, "forbidden")
    assert read.headers["cache-control"] == "no-store"
    error_of(post(auctioneer, 1000), 403, "forbidden")

    assert wallet_rows(seeded) == before


# --- depósito ---


def test_deposit_returns_the_new_snapshot_and_stores_it(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    response = post(bidder, 50000)

    assert response.status_code == 200
    assert response.json() == {
        "total_balance_cents": 50000,
        "committed_balance_cents": 0,
        "available_balance_cents": 50000,
    }
    assert response.headers["cache-control"] == "no-store"
    assert wallet_row(seeded, seeded_id(BIDDER_EMAIL)) == (50000, 0)

    second = post(bidder, 25000)
    assert second.json()["total_balance_cents"] == 75000
    assert wallet_row(seeded, seeded_id(BIDDER_EMAIL)) == (75000, 0)
    assert bidder.get(READ).json() == second.json()


def test_deposit_keeps_committed_and_leaves_other_wallets_alone(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    set_wallet(seeded, seeded_id(BIDDER_EMAIL), 1000, 400)
    other_before = wallet_row(seeded, seeded_id(OTHER_BIDDER_EMAIL))

    assert post(bidder, 500).json() == {
        "total_balance_cents": 1500,
        "committed_balance_cents": 400,
        "available_balance_cents": 1100,
    }
    assert wallet_row(seeded, seeded_id(OTHER_BIDDER_EMAIL)) == other_before


def test_the_owner_is_always_the_session_user(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    other = seeded_id(OTHER_BIDDER_EMAIL)
    before = wallet_rows(seeded)

    response = bidder.post(
        DEPOSIT,
        json={"amount_cents": 100, "user_id": str(other)},
        headers=json_headers(HTTPS_ORIGIN),
    )

    body = error_of(response, 422, "validation_error")
    assert body["details"] == [{"loc": ["body", "user_id"], "type": "extra_forbidden"}]
    assert wallet_rows(seeded) == before


INVALID_AMOUNTS = [
    (0, "greater_than"),
    (-1, "greater_than"),
    (100.5, "int_type"),
    ("100", "int_type"),
    (True, "int_type"),
    (None, "int_type"),
    (MAX_CENTS + 1, "less_than_equal"),
]


@pytest.mark.parametrize(("amount", "kind"), INVALID_AMOUNTS)
def test_invalid_amounts_are_422_validation_errors_and_write_nothing(
    bidder: TestClient, seeded: sessionmaker[Session], amount: Any, kind: str
) -> None:
    before = wallet_rows(seeded)

    body = error_of(post(bidder, amount), 422, "validation_error")

    assert body["details"] == [{"loc": ["body", "amount_cents"], "type": kind}]
    assert wallet_rows(seeded) == before


def test_exponent_notation_is_rejected_without_float_parsing(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    before = wallet_rows(seeded)

    response = bidder.post(
        DEPOSIT, content=b'{"amount_cents": 1e2}', headers=json_headers(HTTPS_ORIGIN)
    )

    body = error_of(response, 422, "validation_error")
    assert body["details"] == [{"loc": ["body", "amount_cents"], "type": "int_type"}]
    assert wallet_rows(seeded) == before


def test_missing_field_empty_body_extra_fields_and_malformed_json(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    before = wallet_rows(seeded)
    headers = json_headers(HTTPS_ORIGIN)

    missing = bidder.post(DEPOSIT, json={}, headers=headers)
    body = error_of(missing, 422, "validation_error")
    assert body["details"] == [{"loc": ["body", "amount_cents"], "type": "missing"}]

    for extra in ("total_balance_cents", "committed_balance_cents"):
        response = bidder.post(
            DEPOSIT, json={"amount_cents": 1, extra: 1}, headers=headers
        )
        body = error_of(response, 422, "validation_error")
        assert body["details"] == [{"loc": ["body", extra], "type": "extra_forbidden"}]

    malformed = bidder.post(DEPOSIT, content=b'{"amount_cents": ', headers=headers)
    body = error_of(malformed, 422, "validation_error")
    assert body["details"][0]["type"] == "json_invalid"

    assert wallet_rows(seeded) == before


def test_a_deposit_over_the_ceiling_is_balance_limit_exceeded(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    user = seeded_id(BIDDER_EMAIL)
    set_wallet(seeded, user, MAX_CENTS - 10)

    response = post(bidder, 11)

    assert response.status_code == 422
    assert response.json() == {
        "status": 422,
        "code": "balance_limit_exceeded",
        "message": LIMIT_MESSAGE,
    }
    assert MESSAGES["balance_limit_exceeded"] == LIMIT_MESSAGE
    assert response.headers["cache-control"] == "no-store"
    assert wallet_row(seeded, user) == (MAX_CENTS - 10, 0)


def test_a_deposit_that_lands_exactly_on_the_ceiling_is_accepted(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    user = seeded_id(BIDDER_EMAIL)
    set_wallet(seeded, user, MAX_CENTS - 10)

    response = post(bidder, 10)

    assert response.status_code == 200
    assert response.json() == {
        "total_balance_cents": MAX_CENTS,
        "committed_balance_cents": 0,
        "available_balance_cents": MAX_CENTS,
    }
    assert wallet_row(seeded, user) == (MAX_CENTS, 0)


def test_the_largest_single_deposit_into_an_empty_wallet_fits(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    assert post(bidder, MAX_CENTS).json()["total_balance_cents"] == MAX_CENTS
    # E nada mais cabe.
    error_of(post(bidder, 1), 422, "balance_limit_exceeded")


# --- proteção das escritas (2.1) ---


def test_foreign_origin_missing_origin_and_non_json_never_reach_the_handler(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    before = wallet_rows(seeded)
    body = json.dumps({"amount_cents": 100})

    foreign = bidder.post(
        DEPOSIT,
        content=body,
        headers={"Origin": "https://evil.example", "Content-Type": "application/json"},
    )
    error_of(foreign, 403, "csrf_origin_mismatch")

    no_origin = bidder.post(
        DEPOSIT, content=body, headers={"Content-Type": "application/json"}
    )
    error_of(no_origin, 403, "csrf_origin_missing")

    not_json = bidder.post(
        DEPOSIT,
        content=body,
        headers={"Origin": HTTPS_ORIGIN, "Content-Type": "text/plain"},
    )
    error_of(not_json, 415, "unsupported_media_type")

    assert wallet_rows(seeded) == before
    for response in (foreign, no_origin, not_json):
        assert "access-control-allow-origin" not in response.headers


def test_other_methods_are_405(bidder: TestClient) -> None:
    headers = json_headers(HTTPS_ORIGIN)
    for method in ("GET", "PUT", "DELETE"):
        error_of(
            bidder.request(method, DEPOSIT, headers=headers), 405, "method_not_allowed"
        )
    for method in ("POST", "PUT", "DELETE"):
        error_of(
            bidder.request(method, READ, headers=headers), 405, "method_not_allowed"
        )


def test_the_policy_runs_before_the_body_is_validated(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    auctioneer: TestClient,
) -> None:
    """2.2 P8: a política decide antes do corpo. Corpo inválido de quem não pode
    depositar recebe 401/403, nunca o 422 que revelaria a validação. (JSON ilegível é
    outra história: o FastAPI o decodifica antes das dependências, como fixa a 2.4.)"""
    anonymous = client_for(monkeypatch, seeded, None)
    before = wallet_rows(seeded)
    headers = json_headers(HTTPS_ORIGIN)

    for body in ({"amount_cents": 0}, {"amount_cents": "100"}, {}):
        response = anonymous.post(DEPOSIT, json=body, headers=headers)
        error_of(response, 401, "unauthorized")
    for body in ({"amount_cents": 0}, {"amount_cents": 100, "user_id": "x"}, {}):
        response = auctioneer.post(DEPOSIT, json=body, headers=headers)
        error_of(response, 403, "forbidden")

    assert wallet_rows(seeded) == before


def test_anonymous_deposit_is_401_and_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    anonymous = client_for(monkeypatch, seeded, None)
    before = wallet_rows(seeded)

    error_of(post(anonymous, 100), 401, "unauthorized")

    assert wallet_rows(seeded) == before


# --- carteira ausente (P2, CAP-9) ---


def test_a_bidder_without_a_wallet_gets_a_generic_500_and_no_wallet_is_created(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
) -> None:
    user = seeded_id(BIDDER_EMAIL)
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    assert login(client, HTTPS_ORIGIN, BIDDER_EMAIL).status_code == 200
    crashing = TestClient(
        client.app, base_url=HTTPS_ORIGIN, raise_server_exceptions=False
    )
    crashing.cookies.update(client.cookies)
    delete_wallet(seeded, user)

    for response in (crashing.get(READ), post(crashing, 100)):
        assert response.status_code == 500
        assert response.json() == {
            "status": 500,
            "code": "internal_error",
            "message": MESSAGES["internal_error"],
        }
        for secret in (BIDDER_EMAIL, str(user), "wallet missing", "Traceback"):
            assert secret not in response.text

    assert wallet_row(seeded, user) is None
