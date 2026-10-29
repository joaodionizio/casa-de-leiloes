"""Login, logout e usuário atual (Story 2.2, AD-11, AD-29).

O JWT vive só no cookie HttpOnly: nunca no corpo, na URL nem no cabeçalho
`Authorization`. Login e logout são `POST` e passam pela proteção de escrita de
`app/csrf.py` como qualquer outra escrita. GET nunca cria nem remove sessão.
"""

import logging
import unicodedata
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import security
from app.access import NO_STORE, AccessPolicy, api_route, require_user
from app.config import SessionConfig
from app.db import get_session
from app.errors import (
    EMAIL_ALREADY_REGISTERED,
    INVALID_CREDENTIALS,
    error_response,
    error_responses,
)
from app.users import User, UserRole
from app.wallet import create_wallet

logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=8, max_length=1024)
    # Deliberately closed: a future internal role must never become public.
    role: Literal["BIDDER", "AUCTIONEER"]

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if value.count("@") != 1 or any(char.isspace() for char in value):
            raise ValueError("invalid email")
        local, domain = value.split("@")
        if not local or not domain:
            raise ValueError("invalid email")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        # Same categories as the UI: Ll/Lu/Nd and P/S. Whitespace counts in
        # Python's code-point length but is not a composition group.
        categories = {unicodedata.category(char) for char in value}
        groups = sum(
            (
                "Ll" in categories,
                "Lu" in categories,
                "Nd" in categories,
                any(category.startswith(("P", "S")) for category in categories),
            )
        )
        if groups < 3:
            raise ValueError("password composition requirements not met")
        return value


def is_email_conflict(exc: IntegrityError) -> bool:
    original = exc.orig
    return (
        getattr(original, "sqlstate", None) == "23505"
        and getattr(getattr(original, "diag", None), "constraint_name", None)
        == "uq_users_email"
    )


class LoginRequest(BaseModel):
    # Formato do e-mail não é validado: um valor inválido cai no mesmo 401.
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class CurrentUser(BaseModel):
    email: str
    role: UserRole


def invalid_credentials() -> Response:
    """O mesmo corpo, byte a byte, para e-mail inexistente e senha errada."""
    return error_response(401, INVALID_CREDENTIALS, headers=NO_STORE)


def register_auth_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/auth/register",
        methods=["POST"],
        policy=AccessPolicy.PUBLIC,
        status_code=201,
        response_model=CurrentUser,
        responses=error_responses(403, 409, 415, 422, 500),
    )
    def register(
        payload: RegisterRequest,
        session: Session = Depends(get_session),
    ) -> Response:
        password_hash = security.hash_password(payload.password)
        user = User(
            id=uuid.uuid4(),
            email=payload.email,
            password_hash=password_hash,
            role=payload.role,
        )
        try:
            session.add(user)
            session.flush()
            create_wallet(session, user.id)
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            if isinstance(exc, IntegrityError) and is_email_conflict(exc):
                return error_response(409, EMAIL_ALREADY_REGISTERED, headers=NO_STORE)
            # Never format the exception: PostgreSQL DETAIL may contain input
            # even when the engine hides SQL parameters.
            logger.error(
                "registration persistence failure",
                extra={"error_type": type(exc).__name__},
            )
            return error_response(500, "internal_error", headers=NO_STORE)
        return JSONResponse(
            {"email": payload.email, "role": payload.role},
            status_code=201,
            headers=NO_STORE,
        )

    @api_route(
        app,
        "/api/auth/login",
        methods=["POST"],
        policy=AccessPolicy.PUBLIC,
        response_model=CurrentUser,
        responses=error_responses(401, 422),
    )
    def login(
        payload: LoginRequest,
        request: Request,
        session: Session = Depends(get_session),
    ) -> Response:
        config: SessionConfig = request.app.state.session_config
        user = session.scalar(select(User).where(User.email == payload.email))
        if user is None:
            security.verify_reference_password(payload.password)
            return invalid_credentials()
        if not security.verify_password(user.password_hash, payload.password):
            return invalid_credentials()

        token = security.issue_token(
            user.id, user.role, config.jwt_secret.get_secret_value()
        )
        response = JSONResponse(
            CurrentUser(email=user.email, role=UserRole(user.role)).model_dump(
                mode="json"
            ),
            headers=NO_STORE,
        )
        response.set_cookie(
            config.cookie_name,
            token,
            max_age=security.SESSION_MAX_AGE_SECONDS,
            path="/",
            domain=None,
            secure=config.cookie_secure,
            httponly=True,
            samesite="lax",
        )
        return response

    @api_route(
        app,
        "/api/auth/logout",
        methods=["POST"],
        policy=AccessPolicy.PUBLIC,
        status_code=204,
        response_class=Response,
        response_model=None,
    )
    def logout(request: Request) -> Response:
        """Idempotente: apaga o cookie com ou sem sessão válida. O token copiado
        antes continua válido até o `exp` (AD-29)."""
        config: SessionConfig = request.app.state.session_config
        response = Response(status_code=204, headers=NO_STORE)
        response.delete_cookie(
            config.cookie_name,
            path="/",
            domain=None,
            secure=config.cookie_secure,
            httponly=True,
            samesite="lax",
        )
        return response

    @api_route(
        app,
        "/api/me",
        methods=["GET"],
        policy=AccessPolicy.AUTHENTICATED,
        response_model=CurrentUser,
        responses=error_responses(401),
    )
    def me(response: Response, user: User = Depends(require_user)) -> CurrentUser:
        response.headers["Cache-Control"] = "no-store"
        return CurrentUser(email=user.email, role=UserRole(user.role))
