"""Política de acesso das rotas (Story 2.2, AD-11, P8, P9).

Toda rota da aplicação real é registrada por `api_route` ou `websocket_route`,
que são o único lugar onde a política é declarada: gravam `access_policy` no
endpoint e aplicam a dependência correspondente. Não use `@app.get`,
`include_router` nem `APIRouter` na aplicação real: `tests/access_policy.py`
reprova rota sem política e tipo de rota que não sabe inspecionar.

A autenticação existe num só lugar, `resolve_session_user`. As dependências são
`def` síncronas (threadpool), nunca no event loop (AD-25).
"""

import inspect
import uuid
from collections.abc import Callable
from enum import StrEnum
from typing import Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.params import Depends as DependsMarker
from sqlalchemy.orm import Session

from app import security
from app.config import SessionConfig
from app.db import get_session
from app.users import User, UserRole

# Um 401/403 de autenticação nunca deve ficar em cache.
NO_STORE = {"Cache-Control": "no-store"}


class AccessPolicy(StrEnum):
    PUBLIC = "PUBLIC"
    OPTIONAL = "OPTIONAL"
    AUTHENTICATED = "AUTHENTICATED"
    AUCTIONEER = "AUCTIONEER"
    BIDDER = "BIDDER"


def resolve_session_user(request: Request, session: Session) -> User | None:
    """O usuário da sessão, ou `None` em qualquer falha (Story 2.2, §8).

    O banco é a autoridade: usuário ausente ou papel do token diferente do papel
    atual do banco invalidam a sessão. Nunca lê `Authorization`.
    """
    config: SessionConfig = request.app.state.session_config
    token = request.cookies.get(config.cookie_name)
    if not token:
        return None
    try:
        claims = security.decode_token(token, config.jwt_secret.get_secret_value())
    except jwt.InvalidTokenError:
        return None
    try:
        user_id = uuid.UUID(claims["sub"])
        role = UserRole(claims["role"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    user = session.get(User, user_id)
    if user is None or user.role != role:
        return None
    return user


def public() -> None:
    """`PUBLIC`: não exige nada."""


def optional_user(
    request: Request, session: Session = Depends(get_session)
) -> User | None:
    """`OPTIONAL`: sessão válida expõe o usuário; qualquer outra situação é
    visitante anônimo, sem 401. Nunca concede dado protegido sem sessão válida."""
    return resolve_session_user(request, session)


def require_user(request: Request, session: Session = Depends(get_session)) -> User:
    """`AUTHENTICATED`: sem sessão válida, 401. Não apaga o cookie."""
    user = resolve_session_user(request, session)
    if user is None:
        raise HTTPException(status_code=401, headers=NO_STORE)
    return user


def require_auctioneer(user: User = Depends(require_user)) -> User:
    if user.role != UserRole.AUCTIONEER:
        raise HTTPException(status_code=403, headers=NO_STORE)
    return user


def require_bidder(user: User = Depends(require_user)) -> User:
    if user.role != UserRole.BIDDER:
        raise HTTPException(status_code=403, headers=NO_STORE)
    return user


POLICY_DEPENDENCIES: dict[AccessPolicy, Callable[..., Any]] = {
    AccessPolicy.PUBLIC: public,
    AccessPolicy.OPTIONAL: optional_user,
    AccessPolicy.AUTHENTICATED: require_user,
    AccessPolicy.AUCTIONEER: require_auctioneer,
    AccessPolicy.BIDDER: require_bidder,
}


def _declare_policy(endpoint: Callable[..., Any], policy: AccessPolicy) -> None:
    """Grava a política no endpoint, recusando contradições silenciosas."""
    existing = getattr(endpoint, "access_policy", None)
    if existing is not None and existing != policy:
        raise ValueError(
            f"endpoint {endpoint.__name__!r} already declares policy {existing}"
        )
    expected = POLICY_DEPENDENCIES[policy]
    policy_dependencies = set(POLICY_DEPENDENCIES.values())
    for parameter in inspect.signature(endpoint).parameters.values():
        default = parameter.default
        if (
            isinstance(default, DependsMarker)
            and default.dependency in policy_dependencies
            and default.dependency is not expected
        ):
            raise ValueError(
                f"endpoint {endpoint.__name__!r} uses a dependency that does not "
                f"match its declared policy {policy}"
            )
    endpoint.access_policy = policy  # type: ignore[attr-defined]


def api_route(
    app: FastAPI,
    path: str,
    *,
    methods: list[str],
    policy: AccessPolicy,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorador que registra uma rota HTTP declarando a sua política."""

    def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        _declare_policy(endpoint, policy)
        app.add_api_route(
            path,
            endpoint,
            methods=methods,
            dependencies=[Depends(POLICY_DEPENDENCIES[policy])],
            **kwargs,
        )
        return endpoint

    return decorator


def websocket_route(
    app: FastAPI, path: str, *, policy: AccessPolicy
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorador que registra uma rota WebSocket declarando a sua política."""

    def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        _declare_policy(endpoint, policy)
        app.add_api_websocket_route(
            path,
            endpoint,
            dependencies=[Depends(POLICY_DEPENDENCIES[policy])],
        )
        return endpoint

    return decorator
