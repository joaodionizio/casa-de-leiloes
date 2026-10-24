import logging
from pathlib import Path

from fastapi import FastAPI

from app import infra_check
from app.config import get_spa_settings
from app.spa import register_spa_routes, validate_spa_dist_dir

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")


def create_app(spa_dist_dir: Path | None = None) -> FastAPI:
    """Monta a aplicação. Sem argumento, lê `SPA_DIST_DIR` da configuração."""
    app = FastAPI(
        title="Casa de Leilões",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(infra_check.router)

    if spa_dist_dir is None:
        spa_dist_dir = get_spa_settings().spa_dist_dir
    if spa_dist_dir is None:
        logger.info("SPA_DIST_DIR is not set; the SPA will not be served")
    else:
        # Registrada por último, para nunca sombrear rotas da API.
        register_spa_routes(app, validate_spa_dist_dir(spa_dist_dir))

    return app


app = create_app()
