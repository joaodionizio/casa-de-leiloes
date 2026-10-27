"""`POST /api/lots/{lot_id}/bids` sobre PostgreSQL real (Story 3.4; CAP-1, CAP-2, CAP-5,
CAP-6, CAP-7). Dinheiro sempre como inteiro, nunca `float`."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import bids
from app.errors import MESSAGES
from app.money import MAX_CENTS
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import (
    assert_authenticated,
    assert_invariants,
    bid_rows,
    db_snapshot,
    live_lot,
    lot_state,
    statement_log,
    tamper,
)
from tests.lot_support import db_now, integrity_secrets
from tests.wallet_support import seed_users_with_wallets, set_wallet, wallet_row

ALICE = seeded_id(BIDDER_EMAIL)
BOB = seeded_id(OTHER_BIDDER_EMAIL)
BID_KEYS = ["amount_cents", "bidder_alias", "placed_at", "sequence"]
LOT_KEYS = ["anti_sniping_applied", "current_bid_cents", "ends_at"]
WALLET_KEYS = [
    "available_balance_cents",
    "committed_balance_cents",
    "total_balance_cents",
]
INTEGRITY_BODY = {
    "status": 409,
    "code": "lot_integrity_conflict",
    "message": "Não foi possível verificar a integridade deste lote. "
    "O lance não foi registrado.",
}
FORBIDDEN_NAMES = (
    "bidder_id",
    "user_id",
    "current_leader_id",
    "auctioneer_id",
    "email",
    "previous_hash",
    "current_hash",
    "final_hash",
    "anchor_hmac",
    "canonical_version",
    "is_demo",
)


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, 100_000)
    set_wallet(db_session_factory, BOB, 100_000)
    return db_session_factory


def client_for(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    email: str | None = BIDDER_EMAIL,
    *,
    raise_server_exceptions: bool = True,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    if not raise_server_exceptions:
        client = TestClient(
            client.app, base_url=HTTPS_ORIGIN, raise_server_exceptions=False
        )
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


@pytest.fixture
def alice(monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]) -> TestClient:
    return client_for(monkeypatch, seeded)


@pytest.fixture
def bob(monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]) -> TestClient:
    return client_for(monkeypatch, seeded, OTHER_BIDDER_EMAIL)


def url(lot_id: object) -> str:
    return f"/api/lots/{lot_id}/bids"


def bid(client: TestClient, lot_id: object, amount: Any) -> Any:
    return client.post(
        url(lot_id), json={"amount_cents": amount}, headers=json_headers(HTTPS_ORIGIN)
    )


def error_of(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body == {"status": status, "code": code, "message": MESSAGES[code]}
    return body


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value)


# --- 201: o contrato de resposta (CA3) ---


def test_an_accepted_bid_is_a_201_with_exactly_the_bid_the_lot_and_the_wallet(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000)

    response = bid(alice, lot_id, 10_000)

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert "location" not in response.headers
    body = response.json()
    assert sorted(body) == ["bid", "lot", "wallet"]
    assert sorted(body["bid"]) == BID_KEYS
    assert sorted(body["lot"]) == LOT_KEYS
    assert sorted(body["wallet"]) == WALLET_KEYS
    (row,) = bid_rows(seeded, lot_id)
    stored = lot_state(seeded, lot_id)
    assert body["bid"]["sequence"] == 1 == row["sequence"]
    assert body["bid"]["amount_cents"] == 10_000
    assert body["bid"]["bidder_alias"] == row["bidder_alias"]
    # O contrato HTTP é o instante, nunca a string (a fração zero pode sair sem casas).
    assert instant(body["bid"]["placed_at"]) == row["placed_at"]
    assert body["lot"]["current_bid_cents"] == 10_000
    assert instant(body["lot"]["ends_at"]) == stored["ends_at"]
    assert body["lot"]["anti_sniping_applied"] is False
    assert body["wallet"] == {
        "total_balance_cents": 100_000,
        "committed_balance_cents": 10_000,
        "available_balance_cents": 90_000,
    }
    assert_authenticated(seeded, lot_id)


def test_the_response_never_carries_ids_hashes_or_secrets(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)

    response = bid(alice, lot_id, 10_000)

    assert response.status_code == 201
    text = response.text
    for name in FORBIDDEN_NAMES:
        assert name not in text, name
    (row,) = bid_rows(seeded, lot_id)
    for hidden in (str(ALICE), str(BOB), row["current_hash"], row["previous_hash"]):
        assert hidden not in text
    for secret in integrity_secrets():
        assert secret.decode() not in text
    assert "alice" not in text.lower() and "@" not in text


def test_the_bidder_alias_is_the_public_pseudonym_of_this_lot(
    alice: TestClient, bob: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    other = live_lot(seeded)

    first = bid(alice, lot_id, 10_000).json()["bid"]["bidder_alias"]
    second = bid(bob, lot_id, 11_000).json()["bid"]["bidder_alias"]
    third = bid(alice, other, 10_000).json()["bid"]["bidder_alias"]

    assert len({first, second, third}) == 3
    assert all(
        a.startswith("Licitante-") and len(a) == 26 for a in (first, second, third)
    )


def test_an_outbid_over_http_returns_the_state_after_the_release(
    alice: TestClient, bob: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    assert bid(alice, lot_id, 10_000).status_code == 201

    response = bid(bob, lot_id, 12_000)

    assert response.status_code == 201
    body = response.json()
    assert body["bid"]["sequence"] == 2
    assert body["wallet"]["committed_balance_cents"] == 12_000  # a carteira de Bob
    assert wallet_row(seeded, ALICE) == (100_000, 0)
    assert wallet_row(seeded, BOB) == (100_000, 12_000)
    assert_invariants(seeded)


def test_an_accepted_bid_inside_the_window_reports_the_extended_end(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(seconds=60))
    stored_end = lot_state(seeded, lot_id)["ends_at"]

    body = bid(alice, lot_id, 10_000).json()

    assert body["lot"]["anti_sniping_applied"] is True
    assert instant(body["lot"]["ends_at"]) == stored_end + timedelta(minutes=2)


# --- recusas de negócio: 422 com o código de domínio (CA2) ---


@pytest.mark.parametrize(
    ("setup", "amount", "code"),
    [
        ("scheduled", 10_000, "lot_not_started"),
        ("ended", 10_000, "lot_ended"),
        ("live", 9_999, "below_minimum"),
        ("leading", 50_000, "already_winning"),
        ("poor", 10_000, "insufficient_balance"),
    ],
)
def test_each_business_refusal_is_a_422_with_its_code_and_changes_nothing(
    alice: TestClient,
    seeded: sessionmaker[Session],
    setup: str,
    amount: int,
    code: str,
) -> None:
    now = db_now(seeded)
    if setup == "scheduled":
        lot_id = live_lot(
            seeded, starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=2)
        )
    elif setup == "ended":
        lot_id = live_lot(
            seeded, starts_at=now - timedelta(hours=2), ends_at=now - timedelta(hours=1)
        )
    else:
        lot_id = live_lot(seeded)
    if setup == "leading":
        assert bid(alice, lot_id, 10_000).status_code == 201
    if setup == "poor":
        set_wallet(seeded, ALICE, 9_999)
    before = db_snapshot(seeded)

    response = bid(alice, lot_id, amount)

    error_of(response, 422, code)
    assert "details" not in response.json()
    assert db_snapshot(seeded) == before


def test_the_refusal_precedence_follows_the_domain_rules(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    now = db_now(seeded)
    lot_id = live_lot(
        seeded, starts_at=now - timedelta(hours=2), ends_at=now - timedelta(hours=1)
    )
    set_wallet(seeded, ALICE, 0)

    # Período vence mínimo e saldo.
    error_of(bid(alice, lot_id, 1), 422, "lot_ended")


# --- 404 / 405 / validação / CSRF / papéis (CA1) ---


def test_a_lot_that_does_not_exist_is_a_404(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    before = db_snapshot(seeded)

    response = bid(alice, uuid.uuid4(), 10_000)

    error_of(response, 404, "not_found")
    assert db_snapshot(seeded) == before


def test_other_methods_on_the_bid_path_are_not_allowed(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    headers = json_headers(HTTPS_ORIGIN)

    # Story 3.5: `GET` passou a ser a leitura pública da sala (test_bid_reads.py).
    for method in ("put", "patch"):
        response = getattr(alice, method)(url(lot_id), json={}, headers=headers)
        assert response.status_code == 405, method
    assert alice.delete(url(lot_id), headers=headers).status_code == 405
    assert bid_rows(seeded, lot_id) == []


def test_anonymous_gets_401_and_nothing_happens(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    before = db_snapshot(seeded)
    anonymous = client_for(monkeypatch, seeded, None)

    error_of(bid(anonymous, lot_id, 10_000), 401, "unauthorized")

    assert db_snapshot(seeded) == before


def test_anonymous_with_an_invalid_body_still_gets_401(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    anonymous = client_for(monkeypatch, seeded, None)

    error_of(bid(anonymous, lot_id, -1), 401, "unauthorized")


def test_the_auctioneer_gets_403_without_touching_the_lot(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    lot_id = live_lot(seeded)
    before = db_snapshot(seeded)
    auctioneer = client_for(monkeypatch, seeded, AUCTIONEER_EMAIL)

    with statement_log(db_engine) as log:
        response = bid(auctioneer, lot_id, 10_000)

    error_of(response, 403, "forbidden")
    assert not log.saw("FOR UPDATE")  # o handler nem rodou: nenhuma trava
    assert not log.saw("FROM lots")
    assert db_snapshot(seeded) == before


@pytest.mark.parametrize(
    "amount",
    [0, -1, 1.5, True, False, "100", None, MAX_CENTS + 1, [1], {"a": 1}],
    ids=repr,
)
def test_an_invalid_amount_is_a_422_validation_error(
    alice: TestClient, seeded: sessionmaker[Session], amount: Any
) -> None:
    lot_id = live_lot(seeded)
    before = db_snapshot(seeded)

    response = bid(alice, lot_id, amount)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"][0]["loc"] == ["body", "amount_cents"]
    assert db_snapshot(seeded) == before


def test_the_maximum_amount_is_accepted_by_the_contract(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    set_wallet(seeded, ALICE, MAX_CENTS)
    lot_id = live_lot(seeded, starting_bid_cents=MAX_CENTS)

    assert bid(alice, lot_id, MAX_CENTS).status_code == 201


def test_missing_extra_and_malformed_bodies_are_422(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    headers = json_headers(HTTPS_ORIGIN)

    for payload in ({}, {"amount_cents": 10_000, "bidder_id": str(ALICE)}, []):
        response = alice.post(url(lot_id), json=payload, headers=headers)
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"
    malformed = alice.post(url(lot_id), content=b'{"amount_cents": ', headers=headers)
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "validation_error"
    assert bid_rows(seeded, lot_id) == []


def test_a_lot_id_that_is_not_a_uuid_is_a_422(alice: TestClient) -> None:
    response = bid(alice, "nao-e-uuid", 10_000)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["details"][0]["loc"] == ["path", "lot_id"]


def test_csrf_protection_runs_before_the_handler(
    alice: TestClient, seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)
    before = db_snapshot(seeded)

    with statement_log(db_engine) as log:
        no_origin = alice.post(url(lot_id), json={"amount_cents": 10_000})
        foreign = alice.post(
            url(lot_id),
            json={"amount_cents": 10_000},
            headers={"Origin": "https://evil.example"},
        )
        not_json = alice.post(
            url(lot_id),
            content=b"amount_cents=10000",
            headers={
                "Origin": HTTPS_ORIGIN,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    assert (no_origin.status_code, foreign.status_code) == (403, 403)
    assert no_origin.json()["code"] == "csrf_origin_missing"
    assert foreign.json()["code"] == "csrf_origin_mismatch"
    assert not_json.status_code == 415
    assert not log.saw("FOR UPDATE")
    assert db_snapshot(seeded) == before


# --- 409: integridade (CA7) ---


def test_a_legacy_lot_without_anchor_answers_409_with_the_generic_body(
    alice: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded, anchored=False)
    before = db_snapshot(seeded)

    response = bid(alice, lot_id, 10_000)

    assert error_of(response, 409, "lot_integrity_conflict") == INTEGRITY_BODY
    assert response.json() == INTEGRITY_BODY
    assert db_snapshot(seeded) == before


def test_the_conflict_logs_only_the_category_and_the_lot_never_secrets_or_users(
    alice: TestClient,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded, anchored=False)

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        bid(alice, lot_id, 10_000)

    messages = [r.getMessage() for r in caplog.records if r.name == "uvicorn.error"]
    assert messages == [
        f"bid refused: integrity conflict lot_id={lot_id} reason=missing_anchor"
    ]
    logged = caplog.text
    for secret in integrity_secrets():
        assert secret.decode() not in logged
    for hidden in (str(ALICE), "Licitante-"):
        assert hidden not in logged


def test_an_accepted_bid_logs_the_lot_the_sequence_and_the_window_flag_only(
    alice: TestClient,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded)

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        bid(alice, lot_id, 10_000)

    messages = [r.getMessage() for r in caplog.records if r.name == "uvicorn.error"]
    assert messages == [f"bid accepted: lot_id={lot_id} sequence=1 anti_sniping=False"]
    (row,) = bid_rows(seeded, lot_id)
    for hidden in (str(ALICE), row["bidder_alias"], row["current_hash"], "10000"):
        assert hidden not in caplog.text


def test_a_business_refusal_writes_no_log(
    alice: TestClient,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded)

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert bid(alice, lot_id, 1).status_code == 422

    assert [r for r in caplog.records if r.name == "uvicorn.error"] == []


# --- T-ATOM: falha injetada, banco idêntico, 500 genérico (CA10) ---

SECRET_IN_ERROR = "SEGREDO-NA-FALHA /srv/app/bids.py"


def leading_lot(
    alice: TestClient, seeded: sessionmaker[Session]
) -> tuple[uuid.UUID, tuple[list, list, list]]:
    lot_id = live_lot(seeded)
    assert bid(alice, lot_id, 10_000).status_code == 201
    return lot_id, db_snapshot(seeded)


def assert_generic_500(response: Any) -> None:
    assert response.status_code == 500
    assert response.json() == {
        "status": 500,
        "code": "internal_error",
        "message": MESSAGES["internal_error"],
    }
    assert "SEGREDO" not in response.text and "ck_" not in response.text


def test_a_failure_after_the_wallet_update_rolls_everything_back(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    alice = client_for(monkeypatch, seeded)
    bob = client_for(
        monkeypatch, seeded, OTHER_BIDDER_EMAIL, raise_server_exceptions=False
    )
    lot_id, before = leading_lot(alice, seeded)
    real = bids.generate_bidder_alias

    def fail_after_update(**kwargs: Any) -> str:
        if log.saw("UPDATE wallets"):
            raise RuntimeError(SECRET_IN_ERROR)
        return real(**kwargs)  # o gate também chama a função, antes de qualquer UPDATE

    monkeypatch.setattr(bids, "generate_bidder_alias", fail_after_update)
    with statement_log(db_engine) as log:
        response = bid(bob, lot_id, 11_000)

    assert_generic_500(response)
    assert log.saw("UPDATE wallets") and not log.saw("INSERT INTO bids")
    assert db_snapshot(seeded) == before


def test_a_failure_between_the_insert_and_the_new_anchor_rolls_everything_back(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    alice = client_for(monkeypatch, seeded)
    bob = client_for(
        monkeypatch, seeded, OTHER_BIDDER_EMAIL, raise_server_exceptions=False
    )
    lot_id, before = leading_lot(alice, seeded)

    def fail(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError(SECRET_IN_ERROR)

    monkeypatch.setattr(bids, "compute_anchor_hmac", fail)  # o gate usa outro nome
    with statement_log(db_engine) as log:
        response = bid(bob, lot_id, 11_000)

    assert_generic_500(response)
    assert log.saw("INSERT INTO bids") and not log.saw("UPDATE lots")
    assert db_snapshot(seeded) == before


def test_a_failure_right_before_the_commit_rolls_everything_back(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    alice = client_for(monkeypatch, seeded)
    bob = client_for(
        monkeypatch, seeded, OTHER_BIDDER_EMAIL, raise_server_exceptions=False
    )
    lot_id, before = leading_lot(alice, seeded)

    def broken_commit(self: Session) -> None:
        raise RuntimeError(SECRET_IN_ERROR)

    monkeypatch.setattr(Session, "commit", broken_commit)
    with statement_log(db_engine) as log:
        response = bid(bob, lot_id, 11_000)
    monkeypatch.undo()

    assert_generic_500(response)
    assert log.saw("UPDATE lots")  # tudo já tinha sido executado, só faltou o COMMIT
    assert db_snapshot(seeded) == before


def test_a_database_check_failure_is_a_500_and_nothing_is_kept(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    alice = client_for(monkeypatch, seeded)
    bob = client_for(
        monkeypatch, seeded, OTHER_BIDDER_EMAIL, raise_server_exceptions=False
    )
    lot_id, _ = leading_lot(alice, seeded)
    # Carteira corrompida: o comprometido de Alice é menor que o lance atual dela.
    tamper(
        seeded,
        "UPDATE wallets SET committed_balance_cents = 1 WHERE user_id = :id",
        id=ALICE,
    )
    before = db_snapshot(seeded)

    with statement_log(db_engine) as log:
        response = bid(bob, lot_id, 11_000)

    assert_generic_500(response)
    assert log.saw("UPDATE wallets")
    assert db_snapshot(seeded) == before  # nada "consertado"


# --- T-SECRETS: nada de segredo em resposta ou log (CA12) ---


def test_a_full_flow_never_leaks_the_integrity_secrets(
    alice: TestClient,
    bob: TestClient,
    seeded: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded)
    legacy = live_lot(seeded, anchored=False)
    secrets = [secret.decode() for secret in integrity_secrets()]

    with caplog.at_level(logging.DEBUG):
        responses = [
            bid(alice, lot_id, 10_000),
            bid(bob, lot_id, 11_000),
            bid(bob, lot_id, 11_000),  # already_winning
            bid(alice, legacy, 10_000),  # 409
            bid(alice, uuid.uuid4(), 10_000),  # 404
            bid(alice, lot_id, 0),  # 422 de validação
        ]

    assert [r.status_code for r in responses] == [201, 201, 422, 409, 404, 422]
    for secret in secrets:
        assert all(secret not in r.text for r in responses)
        assert secret not in caplog.text
        assert all(secret not in str(vars(r)) for r in caplog.records)
