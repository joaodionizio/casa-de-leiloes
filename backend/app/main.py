import logging
from contextlib import asynccontextmanager
from pathlib import Path

from anyio import CancelScope, to_thread
from fastapi import FastAPI

from app.access import AccessPolicy, api_route
from app.artic import ArticClient
from app.auth import register_auth_routes
from app.bids import register_bid_routes
from app.catalog import register_catalog_routes
from app.config import (
    AuthSettings,
    IntegritySettings,
    OriginSettings,
    SessionConfig,
    get_auth_settings,
    get_integrity_settings,
    get_origin_settings,
    get_spa_settings,
    integrity_config,
    session_cookie_for_origin,
)
from app.csrf import ApiWriteGuardMiddleware
from app.db import create_session_factory, get_engine
from app.errors import register_error_handlers
from app.lot_audit import register_audit_routes
from app.lot_cancellation import register_lot_cancellation_routes
from app.lot_room import register_room_routes
from app.lots import register_lot_routes
from app.settlement_scheduler import SettlementScheduler
from app.spa import register_spa_routes, validate_spa_dist_dir
from app.wallet import register_wallet_routes

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")


def create_app(
    spa_dist_dir: Path | None = None,
    app_origin: str | None = None,
    jwt_secret: str | None = None,
    audit_hmac_secret: str | None = None,
    pseudonym_secret: str | None = None,
) -> FastAPI:
    """Monta a aplicação. Sem argumentos, lê `SPA_DIST_DIR`, `APP_ORIGIN`,
    `JWT_SECRET`, `AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET` da configuração; sem
    `APP_ORIGIN` ou sem um `JWT_SECRET` de pelo menos 32 caracteres a criação falha,
    sem ecoar o valor (Story 2.1 D2, 2.2 P1). Os dois segredos de integridade
    precisam ter 32 bytes em UTF-8 e ser diferentes entre si e do `JWT_SECRET`
    (Story 3.4, P5). Uma `APP_ORIGIN` `http` fora de localhost também impede a
    criação (2.2 P4)."""
    if app_origin is None:
        app_origin = get_origin_settings().app_origin
    else:
        app_origin = OriginSettings(_env_file=None, app_origin=app_origin).app_origin

    if jwt_secret is None:
        auth_settings = get_auth_settings()
    else:
        auth_settings = AuthSettings(_env_file=None, jwt_secret=jwt_secret)
    cookie_name, cookie_secure = session_cookie_for_origin(app_origin)

    if audit_hmac_secret is None and pseudonym_secret is None:
        integrity_settings = get_integrity_settings()
    else:
        integrity_settings = IntegritySettings(
            _env_file=None,
            audit_hmac_secret=audit_hmac_secret,
            pseudonym_secret=pseudonym_secret,
        )  # type: ignore[arg-type]  # str do chamador; o Pydantic converte
    integrity = integrity_config(integrity_settings, auth_settings.jwt_secret)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        factory = await to_thread.run_sync(lambda: create_session_factory(get_engine()))
        scheduler = SettlementScheduler(factory, integrity, app.state.room_manager)
        app.state.settlement_scheduler = scheduler
        try:
            await scheduler.catch_up()
            scheduler.start()
            yield
        finally:
            with CancelScope(shield=True):
                await scheduler.stop()

    app = FastAPI(
        title="ÁTRIO",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        lifespan=lifespan,
    )
    # Segredo, nome e `Secure` do cookie ficam na app, para que apps de teste com
    # origens diferentes convivam no mesmo processo.
    app.state.session_config = SessionConfig(
        jwt_secret=auth_settings.jwt_secret,
        cookie_name=cookie_name,
        cookie_secure=cookie_secure,
    )
    # Segredos de integridade em `bytes`, convertidos uma vez (Story 3.4).
    app.state.integrity_config = integrity
    # Cliente da AIC (Story 2.3): sem rede na criação; os testes o substituem.
    app.state.artic_client = ArticClient()

    register_error_handlers(app)
    app.add_middleware(ApiWriteGuardMiddleware, allowed_origin=app_origin)

    @api_route(app, "/health", methods=["GET"], policy=AccessPolicy.PUBLIC)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    register_auth_routes(app)
    register_catalog_routes(app)
    register_lot_routes(app)
    register_wallet_routes(app)
    register_bid_routes(app)
    register_audit_routes(app)
    register_lot_cancellation_routes(app)
    register_room_routes(app, app_origin)

    if spa_dist_dir is None:
        spa_dist_dir = get_spa_settings().spa_dist_dir
    if spa_dist_dir is None:
        logger.info("SPA_DIST_DIR is not set; the SPA will not be served")
    else:
        # Registrada por último, para nunca sombrear rotas da API.
        register_spa_routes(app, validate_spa_dist_dir(spa_dist_dir))

    return app


app = create_app()
