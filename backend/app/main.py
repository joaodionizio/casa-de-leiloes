import logging
from pathlib import Path

from fastapi import FastAPI

from app.access import AccessPolicy, api_route
from app.artic import ArticClient
from app.auth import register_auth_routes
from app.catalog import register_catalog_routes
from app.config import (
    AuthSettings,
    OriginSettings,
    SessionConfig,
    get_auth_settings,
    get_origin_settings,
    get_spa_settings,
    session_cookie_for_origin,
)
from app.csrf import ApiWriteGuardMiddleware
from app.errors import register_error_handlers
from app.infra_check import register_infra_check_routes
from app.lots import register_lot_routes
from app.spa import register_spa_routes, validate_spa_dist_dir

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")


def create_app(
    spa_dist_dir: Path | None = None,
    app_origin: str | None = None,
    jwt_secret: str | None = None,
) -> FastAPI:
    """Monta a aplicação. Sem argumentos, lê `SPA_DIST_DIR`, `APP_ORIGIN` e
    `JWT_SECRET` da configuração; sem `APP_ORIGIN` ou sem um `JWT_SECRET` de pelo
    menos 32 caracteres a criação falha, sem ecoar o valor (Story 2.1 D2, 2.2 P1).
    Uma `APP_ORIGIN` `http` fora de localhost também impede a criação (2.2 P4)."""
    if app_origin is None:
        app_origin = get_origin_settings().app_origin
    else:
        app_origin = OriginSettings(_env_file=None, app_origin=app_origin).app_origin

    if jwt_secret is None:
        auth_settings = get_auth_settings()
    else:
        auth_settings = AuthSettings(_env_file=None, jwt_secret=jwt_secret)
    cookie_name, cookie_secure = session_cookie_for_origin(app_origin)

    app = FastAPI(
        title="ÁTRIO",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    # Segredo, nome e `Secure` do cookie ficam na app, para que apps de teste com
    # origens diferentes convivam no mesmo processo.
    app.state.session_config = SessionConfig(
        jwt_secret=auth_settings.jwt_secret,
        cookie_name=cookie_name,
        cookie_secure=cookie_secure,
    )
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
    register_infra_check_routes(app)

    if spa_dist_dir is None:
        spa_dist_dir = get_spa_settings().spa_dist_dir
    if spa_dist_dir is None:
        logger.info("SPA_DIST_DIR is not set; the SPA will not be served")
    else:
        # Registrada por último, para nunca sombrear rotas da API.
        register_spa_routes(app, validate_spa_dist_dir(spa_dist_dir))

    return app


app = create_app()
