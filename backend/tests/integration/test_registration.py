"""Cadastro real: constraints, atomicidade e concorrência em PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app import auth, security
from app.auth import is_email_conflict
from app.seed import SEED_USERS, seed_users
from app.users import User
from app.wallet import Wallet
from tests.auth_support import HTTPS_ORIGIN, build_client, login

PATH = "/api/auth/register"
# Only a transient test value; never persist request bodies in test evidence.
PASSWORD = " registration test "
PAYLOAD = {"email": "new@example.com", "password": PASSWORD, "role": "BIDDER"}
DUPLICATE = {
    "status": 409,
    "code": "email_already_registered",
    "message": "Este e-mail já está cadastrado. Entre para continuar.",
}
INTERNAL = {
    "status": 500,
    "code": "internal_error",
    "message": "Erro interno. Tente novamente mais tarde.",
}


@pytest.fixture
def client(monkeypatch, db_session_factory, clean_users):
    return build_client(monkeypatch, HTTPS_ORIGIN, session_factory=db_session_factory)


def register(client, **changes):
    return client.post(
        PATH, json={**PAYLOAD, **changes}, headers={"Origin": HTTPS_ORIGIN}
    )


def counts(factory):
    with factory() as session:
        return (
            session.scalar(select(func.count()).select_from(User)),
            session.scalar(select(func.count()).select_from(Wallet)),
        )


def snapshot(factory):
    with factory() as session:
        return (
            session.execute(
                select(User.id, User.email, User.password_hash, User.role).order_by(
                    User.id
                )
            ).all(),
            session.execute(
                select(
                    Wallet.user_id,
                    Wallet.total_balance_cents,
                    Wallet.committed_balance_cents,
                ).order_by(Wallet.user_id)
            ).all(),
        )


@pytest.mark.parametrize("role", ["BIDDER", "AUCTIONEER"])
def test_register_commits_user_and_zero_wallet_then_normal_login(
    client, db_session_factory, role, caplog
):
    response = register(client, role=role)
    assert response.status_code == 201
    assert response.json() == {"email": PAYLOAD["email"], "role": role}
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert counts(db_session_factory) == (1, 1)
    assert client.get("/api/me").status_code == 401
    with db_session_factory() as session:
        user = session.scalar(select(User))
        assert user.role == role
        wallet = session.get(Wallet, user.id)
        assert (wallet.total_balance_cents, wallet.committed_balance_cents) == (0, 0)
        assert user.password_hash.startswith("$argon2id$")
        assert security.verify_password(user.password_hash, PASSWORD)
        assert not security.verify_password(user.password_hash, PASSWORD.strip())
        assert not security.verify_password(user.password_hash, "incorrect")
        assert user.password_hash not in response.text + caplog.text
    assert PASSWORD not in response.text + caplog.text
    assert login(client, HTTPS_ORIGIN, PAYLOAD["email"], PASSWORD).status_code == 200
    assert client.get("/api/me").json() == response.json()
    wallet_response = client.get("/api/wallet")
    assert wallet_response.status_code == (200 if role == "BIDDER" else 403)
    if role == "BIDDER":
        assert wallet_response.json() == {
            "total_balance_cents": 0,
            "committed_balance_cents": 0,
            "available_balance_cents": 0,
        }
        assert client.get("/api/lots/mine").status_code == 403
    else:
        assert client.get("/api/lots/mine").status_code == 200
        assert (
            client.post(
                "/api/wallet/deposit",
                json={"amount_cents": 100},
                headers={"Origin": HTTPS_ORIGIN},
            ).status_code
            == 403
        )


def test_same_password_has_different_salts(client, db_session_factory):
    assert register(client).status_code == 201
    assert register(client, email="other@example.com").status_code == 201
    with db_session_factory() as session:
        hashes = list(session.scalars(select(User.password_hash)))
    assert len(set(hashes)) == 2
    assert all(security.verify_password(h, PASSWORD) for h in hashes)


@pytest.mark.parametrize(
    "email,normalized",
    [
        ("  New+TAG@Example.COM  ", "new+tag@example.com"),
        ("a.b+c@domain", "a.b+c@domain"),
        (" a@" + "d" * 252 + " ", "a@" + "d" * 252),
    ],
)
def test_email_normalization_and_254_boundary(
    client, db_session_factory, email, normalized
):
    response = register(client, email=email)
    assert response.status_code == 201
    assert response.json()["email"] == normalized
    with db_session_factory() as session:
        assert session.scalar(select(User.email)) == normalized


@pytest.mark.parametrize(
    "email",
    [
        "",
        "  ",
        "no-at",
        "@domain",
        "local@",
        "a@@domain",
        "a b@domain",
        "a@do\tmain",
        "a@do\nmain",
        "a@do\u00a0main",
        "a@" + "d" * 253,
    ],
)
def test_invalid_email_is_422_without_persistence(client, db_session_factory, email):
    response = register(client, email=email)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert counts(db_session_factory) == (0, 0)


@pytest.mark.parametrize(
    "password_length,status", [(7, 422), (8, 201), (1024, 201), (1025, 422)]
)
def test_password_boundaries(client, db_session_factory, password_length, status):
    response = register(client, password="x" * password_length)
    assert response.status_code == status
    expected = (1, 1) if status == 201 else (0, 0)
    assert counts(db_session_factory) == expected


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "a@b"},
        {**PAYLOAD, "role": "ADMIN"},
        {**PAYLOAD, "role": "bidder"},
        {**PAYLOAD, "role": "LICITANTE"},
        {**PAYLOAD, "role": ["BIDDER"]},
        {**PAYLOAD, "role": None},
        {**PAYLOAD, "email": 123},
        {**PAYLOAD, "password": 12345678},
        {**PAYLOAD, "name": "not-collected"},
        {**PAYLOAD, "id": "client-id"},
        {**PAYLOAD, "password_hash": "client-hash"},
        {**PAYLOAD, "balance_cents": 1},
        {**PAYLOAD, "claims": {}},
        {**PAYLOAD, "is_admin": True},
        {**PAYLOAD, "password": None},
    ],
)
def test_invalid_payload_has_sanitized_error(client, db_session_factory, payload):
    response = client.post(PATH, json=payload, headers={"Origin": HTTPS_ORIGIN})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert all(set(detail) == {"loc", "type"} for detail in body["details"])
    assert PASSWORD not in response.text
    assert "set-cookie" not in response.headers
    assert counts(db_session_factory) == (0, 0)


def test_malformed_json_is_safe_422(client, db_session_factory):
    response = client.post(
        PATH,
        content=b'{"email":',
        headers={"Origin": HTTPS_ORIGIN, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["details"][0]["type"] == "json_invalid"
    assert counts(db_session_factory) == (0, 0)


def test_duplicate_normalized_email_never_updates_account(client, db_session_factory):
    assert register(client).status_code == 201
    before = snapshot(db_session_factory)
    response = register(
        client,
        email=" NEW@EXAMPLE.COM ",
        role="AUCTIONEER",
        password="different-account-input",
    )
    assert response.status_code == 409
    assert response.json() == DUPLICATE
    assert "set-cookie" not in response.headers
    assert response.headers["cache-control"] == "no-store"
    assert snapshot(db_session_factory) == before
    assert client.get("/api/me").status_code == 401


def test_demo_duplicate_and_other_wallets_are_untouched(client, db_session_factory):
    with db_session_factory() as session:
        seed_users(session)
        session.commit()
    # No wallets for demos: a scoped registration must not repair these users.
    before = snapshot(db_session_factory)
    for demo in SEED_USERS:
        response = register(client, email=demo.email)
        assert response.status_code == 409
        assert response.json() == DUPLICATE
        assert snapshot(db_session_factory) == before
    assert register(client).status_code == 201
    after_users, after_wallets = snapshot(db_session_factory)
    assert all(row in after_users for row in before[0])
    assert len(after_wallets) == 1
    assert after_wallets[0][0] not in {demo.id for demo in SEED_USERS}


def test_two_real_requests_race_on_postgresql_unique_constraint(
    client, db_session_factory, db_engine
):
    barrier = Barrier(2, timeout=15)

    def synchronize(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO users"):
            barrier.wait()

    def attempt(email):
        with TestClient(client.app, base_url=HTTPS_ORIGIN) as contender:
            return register(contender, email=email)

    event.listen(db_engine, "before_cursor_execute", synchronize)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(attempt, email)
                for email in (" NEW@example.com ", "new@EXAMPLE.COM")
            ]
            responses = [future.result(timeout=30) for future in futures]
    finally:
        event.remove(db_engine, "before_cursor_execute", synchronize)
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert next(r for r in responses if r.status_code == 409).json() == DUPLICATE
    assert all("set-cookie" not in r.headers for r in responses)
    assert counts(db_session_factory) == (1, 1)


@pytest.mark.parametrize("phase", ["flush", "wallet-before", "wallet-after", "commit"])
def test_failure_rolls_back_user_and_wallet(
    monkeypatch, db_session_factory, clean_users, phase, caplog
):
    class FailingSession(Session):
        def flush(self, *args, **kwargs):
            super().flush(*args, **kwargs)
            if phase == "flush":
                raise SQLAlchemyError("private persistence sentinel")

        def commit(self):
            if phase == "commit":
                raise SQLAlchemyError("private persistence sentinel")
            return super().commit()

    original = auth.create_wallet

    def fail_wallet(session, user_id):
        if phase == "wallet-after":
            original(session, user_id)
        raise SQLAlchemyError("private persistence sentinel")

    if phase.startswith("wallet"):
        monkeypatch.setattr(auth, "create_wallet", fail_wallet)
    factory = sessionmaker(
        bind=db_session_factory.kw["bind"],
        class_=FailingSession,
        expire_on_commit=False,
    )
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=factory)
    response = register(client)
    assert response.status_code == 500
    assert response.json() == INTERNAL
    assert "set-cookie" not in response.headers
    assert counts(db_session_factory) == (0, 0)
    assert PASSWORD not in response.text + caplog.text
    assert "private persistence sentinel" not in response.text + caplog.text
    assert "registration persistence failure" in caplog.text


def test_only_structural_email_unique_violation_is_duplicate():
    for sqlstate, constraint, expected in [
        ("23505", "uq_users_email", True),
        ("23505", "pk_users", False),
        ("23514", "uq_users_email", False),
        (None, None, False),
    ]:
        exc = IntegrityError(
            "not parsed",
            {},
            SimpleNamespace(
                sqlstate=sqlstate, diag=SimpleNamespace(constraint_name=constraint)
            ),
        )
        assert is_email_conflict(exc) is expected


@pytest.mark.parametrize("with_spa", [False, True])
@pytest.mark.parametrize(
    "origin,content_type,status,code",
    [
        ("https://foreign.example", "application/json", 403, "csrf_origin_mismatch"),
        (HTTPS_ORIGIN, None, 415, "unsupported_media_type"),
        (HTTPS_ORIGIN, "text/plain", 415, "unsupported_media_type"),
    ],
)
def test_ca1_blocks_before_handler_and_creates_nothing(
    monkeypatch,
    db_session_factory,
    clean_users,
    tmp_path,
    with_spa,
    origin,
    content_type,
    status,
    code,
):
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=db_session_factory)
    if with_spa:
        from app.spa import register_spa_routes

        (tmp_path / "index.html").write_text("<!doctype html>")
        register_spa_routes(client.app, tmp_path)
    called = []
    original = security.hash_password

    def record_hash(value):
        called.append(True)
        return original(value)

    monkeypatch.setattr(security, "hash_password", record_hash)
    headers = {"Origin": origin}
    if content_type:
        headers["Content-Type"] = content_type
    import json

    response = client.post(PATH, content=json.dumps(PAYLOAD), headers=headers)
    assert response.request.headers.get("content-type") == content_type
    assert response.status_code == status
    assert response.json()["code"] == code
    assert not called
    assert counts(db_session_factory) == (0, 0)
    assert "set-cookie" not in response.headers
    assert not any(h.startswith("access-control-") for h in response.headers)
    # Same app/path/body with allowed headers really executes the handler.
    assert register(client).status_code == 201
    assert called == [True]
    assert counts(db_session_factory) == (1, 1)


@pytest.mark.parametrize("method", ["get", "head", "options"])
def test_safe_methods_never_create_accounts(client, db_session_factory, method):
    response = getattr(client, method)(PATH)
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    if method == "head":
        assert response.content == b""
    assert "set-cookie" not in response.headers
    assert counts(db_session_factory) == (0, 0)


def test_other_real_integrity_violation_is_500_not_email_conflict(
    client, db_session_factory, monkeypatch, caplog
):
    def violate_primary_key(session, user_id):
        # The user was already flushed; this deliberately violates pk_users,
        # not uq_users_email. The database must still roll back the first row.
        from sqlalchemy.dialects.postgresql import insert

        session.execute(
            insert(User).values(
                id=user_id,
                email="different@example.com",
                password_hash="private-hash",
                role="BIDDER",
            )
        )

    monkeypatch.setattr(auth, "create_wallet", violate_primary_key)
    response = register(client)
    assert response.status_code == 500
    assert response.json() == INTERNAL
    assert counts(db_session_factory) == (0, 0)
    for sensitive in (PASSWORD, "private-hash", "INSERT INTO", "DETAIL:"):
        assert sensitive not in response.text + caplog.text
