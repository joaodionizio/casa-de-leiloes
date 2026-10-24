"""Apoio dos testes de autenticação (Story 2.2): app sem SPA, banco _test e
credenciais de demonstração."""

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.config import SpaSettings
from app.db import get_session
from app.main import create_app
from app.seed import DEMO_PASSWORD, SEED_USERS, seed_users
from tests.synthetic_api import register_role_routes

HTTPS_ORIGIN = "https://testserver"
HTTP_ORIGIN = "http://localhost:5173"

AUCTIONEER_EMAIL = "auctioneer@example.com"
BIDDER_EMAIL = "bidder1@example.com"
OTHER_BIDDER_EMAIL = "bidder2@example.com"


def json_headers(origin: str) -> dict[str, str]:
    return {"Origin": origin, "Content-Type": "application/json"}


def build_client(
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
    *,
    session_factory: sessionmaker[Session] | None = None,
    session_dependency: Callable[[], Iterator[Any]] | None = None,
    role_routes: bool = False,
) -> TestClient:
    """App real sem SPA, com `get_session` apontando para o banco _test (ou para
    uma dependência de teste) e, opcionalmente, as rotas sintéticas por papel."""
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    app = create_app(app_origin=origin)
    if role_routes:
        register_role_routes(app)

    if session_factory is not None:

        def override_session() -> Iterator[Session]:
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_session
    elif session_dependency is not None:
        app.dependency_overrides[get_session] = session_dependency
    return TestClient(app, base_url=origin)


def login(client: TestClient, origin: str, email: str, password: str = DEMO_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"Origin": origin},
    )


def secret_of(client: TestClient) -> str:
    return client.app.state.session_config.jwt_secret.get_secret_value()  # type: ignore[attr-defined]


def cookie_name_of(client: TestClient) -> str:
    return client.app.state.session_config.cookie_name  # type: ignore[attr-defined]


def forge_token(
    client: TestClient,
    *,
    sub: object = None,
    role: object = "BIDDER",
    issued_ago: timedelta = timedelta(minutes=1),
    lifetime: timedelta = timedelta(hours=8),
    secret: str | None = None,
    algorithm: str = "HS256",
    omit: tuple[str, ...] = (),
) -> str:
    """Token assinado com o segredo de teste (ou outro), para casos de borda."""
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(sub if sub is not None else uuid.uuid4()),
        "role": role,
        "iat": now - issued_ago,
        "exp": now - issued_ago + lifetime,
    }
    for name in omit:
        del claims[name]
    key = secret if secret is not None else secret_of(client)
    if algorithm == "none":
        return jwt.encode(claims, None, algorithm="none")
    return jwt.encode(claims, key, algorithm=algorithm)


def seed_demo_users(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        seed_users(session)
        session.commit()


def seeded_id(email: str) -> uuid.UUID:
    return next(seed.id for seed in SEED_USERS if seed.email == email)
