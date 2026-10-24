"""Login, logout e usuário atual (Story 2.2, AD-11, AD-29).

O JWT vive só no cookie HttpOnly: nunca no corpo, na URL nem no cabeçalho
`Authorization`. Login e logout são `POST` e passam pela proteção de escrita de
`app/csrf.py` como qualquer outra escrita. GET nunca cria nem remove sessão.
"""

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import security
from app.access import NO_STORE, AccessPolicy, api_route, require_user
from app.config import SessionConfig
from app.db import get_session
from app.errors import INVALID_CREDENTIALS, error_response, error_responses
from app.users import User, UserRole


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
