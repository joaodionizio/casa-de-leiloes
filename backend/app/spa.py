import posixpath
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.access import AccessPolicy, api_route

INDEX_FILE = "index.html"
SPA_FALLBACK_PATH = "/{full_path:path}"


class SpaConfigError(RuntimeError):
    """SPA_DIST_DIR está definido, mas não aponta para um build utilizável."""


def validate_spa_dist_dir(path: Path) -> Path:
    """Devolve o diretório resolvido ou levanta `SpaConfigError` com o motivo."""
    resolved = path.resolve()
    if not resolved.exists():
        raise SpaConfigError(f"SPA_DIST_DIR does not exist: {path}")
    if not resolved.is_dir():
        raise SpaConfigError(f"SPA_DIST_DIR is not a directory: {path}")
    if not (resolved / INDEX_FILE).is_file():
        raise SpaConfigError(f"SPA_DIST_DIR has no {INDEX_FILE}: {path}")
    return resolved


def normalize_route_path(path: str) -> str:
    """Caminho lógico da rota HTTP, sem barras repetidas, `.`, `..` nem barra final.

    Usado só para decidir se o pedido pertence a `/api` ou a `/health`; o arquivo
    é sempre procurado pelo caminho original, dentro de `resolve_inside`.
    """
    return posixpath.normpath("/" + path.lstrip("/")).lstrip("/")


def resolve_inside(dist_dir: Path, relative_path: str) -> Path | None:
    """Resolve `relative_path` dentro de `dist_dir` (já resolvido).

    Devolve `None` se o caminho final, depois de seguir `..` e symlinks, sair do
    diretório. Compara caminhos resolvidos, não strings.
    """
    try:
        candidate = (dist_dir / relative_path).resolve()
    except (OSError, ValueError):
        return None
    if candidate == dist_dir or candidate.is_relative_to(dist_dir):
        return candidate
    return None


def register_spa_routes(app: FastAPI, dist_dir: Path) -> None:
    """Serve o build do Vite na mesma origem. Registrar por último (D4).

    Só GET e HEAD. Outros métodos caem no 405 JSON do roteador.
    """

    @api_route(
        app,
        SPA_FALLBACK_PATH,
        methods=["GET", "HEAD"],
        policy=AccessPolicy.PUBLIC,
        include_in_schema=False,
        response_model=None,
    )
    def serve_spa(full_path: str) -> FileResponse:
        # `/api` é da API e `/health` é rota explícita: nunca viram SPA, nem por
        # caminhos equivalentes (`/health/`, `/lots/../api/x`).
        logical_path = normalize_route_path(full_path)
        if logical_path == "api" or logical_path.startswith("api/"):
            raise HTTPException(status_code=404)
        if logical_path == "health":
            if full_path == "health":
                raise HTTPException(status_code=405, headers={"Allow": "GET"})
            raise HTTPException(status_code=404)

        target = resolve_inside(dist_dir, full_path)
        if target is None:
            raise HTTPException(status_code=404)
        if target.is_file():
            return FileResponse(target)
        # Último segmento com extensão e arquivo ausente: 404 real, não HTML.
        if PurePosixPath(full_path).suffix:
            raise HTTPException(status_code=404)
        return FileResponse(dist_dir / INDEX_FILE)
