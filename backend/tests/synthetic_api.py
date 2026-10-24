"""Rotas sintéticas só para os testes (Stories 2.1 e 2.2). Nunca entram na
aplicação real."""

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app import main
from app.access import (
    AccessPolicy,
    api_route,
    optional_user,
    require_auctioneer,
    require_bidder,
)
from app.config import SpaSettings
from app.main import create_app
from app.users import User

ALLOWED_ORIGIN = "https://casa.example"
WRITE_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
JSON_HEADERS = {"Origin": ALLOWED_ORIGIN, "Content-Type": "application/json"}

SECRET_DETAIL = "detalhe-interno-secreto"
SECRET_EXCEPTION = "SELECT * FROM users WHERE token='abc'; /srv/app/secreto.py"


class Payload(BaseModel):
    name: str
    age: int


class Calls:
    """Conta quantas vezes o handler de escrita executou."""

    def __init__(self) -> None:
        self.count = 0


def build_router(calls: Calls) -> APIRouter:
    router = APIRouter(prefix="/api/test")

    @router.api_route("/write", methods=WRITE_METHODS, include_in_schema=False)
    def write() -> dict[str, bool]:
        calls.count += 1
        return {"ok": True}

    @router.get("/read")
    def read() -> dict[str, bool]:
        return {"ok": True}

    @router.get("/http-error/{status}")
    def http_error(status: int) -> None:
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        raise HTTPException(status_code=status, detail=SECRET_DETAIL, headers=headers)

    @router.post("/validate")
    def validate(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError(SECRET_EXCEPTION)

    @router.get("/bad-response", response_model=Payload)
    def bad_response() -> dict[str, object]:
        return {"name": 1, "age": "não é número"}

    return router


def build_app(
    monkeypatch, allowed_origin: str = ALLOWED_ORIGIN
) -> tuple[FastAPI, Calls]:
    """App sem SPA, com origem aceita `allowed_origin` e as rotas sintéticas."""
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    calls = Calls()
    app = create_app(app_origin=allowed_origin)
    app.include_router(build_router(calls))
    return app, calls


def register_role_routes(app: FastAPI) -> None:
    """Rotas só de teste, uma por papel (Story 2.2, P10), registradas pelo mesmo
    helper da aplicação real. O 403 real de cada rota de negócio é testado na
    story que a cria."""

    @api_route(
        app,
        "/api/test/auctioneer-only",
        methods=["GET"],
        policy=AccessPolicy.AUCTIONEER,
    )
    def auctioneer_only(user: User = Depends(require_auctioneer)) -> dict[str, str]:
        return {"email": user.email}

    @api_route(
        app, "/api/test/bidder-only", methods=["GET"], policy=AccessPolicy.BIDDER
    )
    def bidder_only(user: User = Depends(require_bidder)) -> dict[str, str]:
        return {"email": user.email}

    @api_route(app, "/api/test/optional", methods=["GET"], policy=AccessPolicy.OPTIONAL)
    def optional(user: User | None = Depends(optional_user)) -> dict[str, object]:
        if user is None:
            return {"anonymous": True}
        return {"email": user.email}
