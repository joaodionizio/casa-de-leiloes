import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import BACKEND_DIR, SpaSettings, get_spa_settings
from app.main import create_app
from app.spa import (
    SPA_FALLBACK_PATH,
    SpaConfigError,
    normalize_route_path,
    resolve_inside,
)

INDEX_HTML = "<!doctype html><title>SPA de teste</title>"
APP_ORIGIN = "https://casa.example"
JSON_HEADERS = {"Origin": APP_ORIGIN, "Content-Type": "application/json"}
SECRET = "conteudo-fora-do-dist"


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    """Um build falso do Vite; `secret.txt` fica fora dele."""
    dist_dir = tmp_path / "dist"
    (dist_dir / "assets").mkdir(parents=True)
    (dist_dir / "index.html").write_text(INDEX_HTML)
    (dist_dir / "assets" / "app.js").write_text("console.log('ok')")
    (dist_dir / "assets" / "app.css").write_text("body { margin: 0 }")
    (dist_dir / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (tmp_path / "secret.txt").write_text(SECRET)
    return dist_dir


@pytest.fixture
def client(dist: Path) -> TestClient:
    return TestClient(create_app(dist, app_origin=APP_ORIGIN))


@pytest.fixture
def no_spa_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    return TestClient(create_app(app_origin=APP_ORIGIN))


@pytest.fixture
def fresh_spa_settings() -> Iterator[None]:
    get_spa_settings.cache_clear()
    yield
    get_spa_settings.cache_clear()


def assert_spa_405(response) -> None:
    """Escrita que cai no fallback (só GET/HEAD): 405 do roteador no contrato único.

    O `Allow` vem de um `set` no Starlette, então a ordem não é garantida.
    """
    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert set(body) == {"status", "code", "message"}
    assert body["status"] == 405
    assert body["code"] == "method_not_allowed"
    allowed = {method.strip() for method in response.headers["allow"].split(",")}
    assert allowed == {"GET", "HEAD"}


# --- entrega da SPA (CA1, CA2) ---


def test_root_serves_index_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_HTML


@pytest.mark.parametrize("path", ["/lots/qualquer-coisa", "/lots/1/audit", "/assets"])
def test_client_routes_serve_index_html(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_HTML


def test_head_on_client_route_has_no_body(client: TestClient) -> None:
    response = client.head("/lots/qualquer-coisa")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == b""


# --- /api e /health (CA3) ---


@pytest.mark.parametrize("path", ["/api", "/api/nao-existe", "/api/lots/x/y"])
@pytest.mark.parametrize("method", ["get", "head"])
def test_unknown_api_path_is_json_404(
    client: TestClient, method: str, path: str
) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "<html" not in response.text.lower()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_valid_write_on_unknown_api_path_with_spa_is_405_json(
    client: TestClient, method: str
) -> None:
    # Com a SPA montada (produção), o fallback GET/HEAD casa parcialmente com
    # qualquer caminho: o roteador responde 405, não 404 (decisão da 1.3 mantida).
    response = client.request(
        method, "/api/nao-existe", headers=JSON_HEADERS, content=b"{}"
    )
    assert_spa_405(response)
    assert INDEX_HTML not in response.text


def test_post_on_unknown_api_path_without_origin_is_403_json(
    client: TestClient,
) -> None:
    response = client.post("/api/nao-existe")
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_origin_missing"
    assert INDEX_HTML not in response.text


def test_health_is_untouched_with_and_without_spa(
    client: TestClient, no_spa_client: TestClient
) -> None:
    for test_client in (client, no_spa_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("which", ["client", "no_spa_client"])
def test_head_health_is_405_json_with_allow_get(
    which: str, request: pytest.FixtureRequest
) -> None:
    response = request.getfixturevalue(which).head("/health")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    # HEAD não tem corpo: o Content-Type JSON é o que prova que não é a SPA.
    assert response.headers["content-type"].startswith("application/json")


# --- métodos de escrita (CA10) ---


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_write_methods_never_get_index_html(client: TestClient, method: str) -> None:
    response = getattr(client, method)("/lots/x", headers=JSON_HEADERS)
    assert_spa_405(response)
    assert INDEX_HTML not in response.text


# --- assets e Content-Type (CA9) ---


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/assets/app.js", "javascript"),
        ("/assets/app.css", "text/css"),
        ("/favicon.svg", "image/svg+xml"),
    ],
)
@pytest.mark.parametrize("method", ["get", "head"])
def test_assets_have_the_right_content_type(
    client: TestClient, method: str, path: str, content_type: str
) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


@pytest.mark.parametrize(
    "path", ["/assets/velho.js", "/robots.txt", "/openapi.json", "/docs.html"]
)
def test_missing_file_with_extension_is_404_not_html(
    client: TestClient, path: str
) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert INDEX_HTML not in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/..%2fsecret.txt",
        "/assets/..%2f..%2fsecret.txt",
    ],
)
def test_path_traversal_is_never_served(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert SECRET not in response.text


@pytest.mark.parametrize("method", ["get", "head"])
def test_health_with_trailing_slash_is_not_the_spa(
    client: TestClient, method: str
) -> None:
    response = getattr(client, method)("/health/")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert INDEX_HTML not in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/",
        "/lots/..%2fapi/x",  # decodificado: /lots/../api/x
        "/%2e/api/x",  # /./api/x
        "/api/%2e/x",
        "/api//x",
        "/lots/..%2fapi",
    ],
)
@pytest.mark.parametrize("method", ["get", "head"])
def test_normalized_api_paths_are_never_the_spa(
    client: TestClient, method: str, path: str
) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert INDEX_HTML not in response.text


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("api", "api"),
        ("api/", "api"),
        ("api//x", "api/x"),
        ("api/./x", "api/x"),
        ("lots/../api/x", "api/x"),
        ("../api/x", "api/x"),
        ("/api/x", "api/x"),
        ("health/", "health"),
        ("", ""),
        ("lots/1/audit", "lots/1/audit"),
    ],
)
def test_normalize_route_path(path: str, expected: str) -> None:
    assert normalize_route_path(path) == expected


def test_resolve_inside_refuses_paths_that_escape(dist: Path, tmp_path: Path) -> None:
    root = dist.resolve()
    assert resolve_inside(root, "assets/app.js") == root / "assets" / "app.js"
    assert resolve_inside(root, "../secret.txt") is None
    assert resolve_inside(root, str(tmp_path / "secret.txt")) is None
    assert resolve_inside(root, "bad\x00name") is None


@pytest.mark.parametrize("link", ["leak.txt", "linked_dir/secret.txt"])
def test_symlink_pointing_outside_dist_is_not_served(
    client: TestClient, dist: Path, tmp_path: Path, link: str
) -> None:
    if link == "leak.txt":
        (dist / "leak.txt").symlink_to(tmp_path / "secret.txt")
    else:
        (dist / "linked_dir").symlink_to(tmp_path, target_is_directory=True)
    response = client.get(f"/{link}")
    assert response.status_code == 404
    assert SECRET not in response.text


# --- SPA_DIST_DIR (CA11) ---


def test_without_spa_dist_dir_only_the_spa_is_missing(
    no_spa_client: TestClient,
) -> None:
    assert no_spa_client.get("/health").status_code == 200
    assert no_spa_client.get("/").status_code == 404
    assert no_spa_client.get("/lots/x").status_code == 404


def test_spa_dist_dir_is_read_from_the_environment(
    dist: Path, monkeypatch: pytest.MonkeyPatch, fresh_spa_settings: None
) -> None:
    monkeypatch.setenv("SPA_DIST_DIR", str(dist))
    response = TestClient(create_app(app_origin=APP_ORIGIN)).get("/")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_relative_spa_dist_dir_is_resolved_against_backend_dir(
    dist: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_spa_settings: None,
) -> None:
    relative = os.path.relpath(dist, BACKEND_DIR)
    assert not Path(relative).is_absolute()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)  # o cwd não pode influenciar o resultado
    monkeypatch.setenv("SPA_DIST_DIR", relative)

    settings = SpaSettings(_env_file=None)
    assert settings.spa_dist_dir == BACKEND_DIR / relative

    response = TestClient(create_app(app_origin=APP_ORIGIN)).get("/")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_absolute_spa_dist_dir_is_kept_as_is() -> None:
    settings = SpaSettings(_env_file=None, spa_dist_dir=Path("/app/frontend-dist"))
    assert settings.spa_dist_dir == Path("/app/frontend-dist")


@pytest.mark.parametrize("case", ["missing", "file", "no_index"])
def test_invalid_spa_dist_dir_fails_on_creation(tmp_path: Path, case: str) -> None:
    path = tmp_path / "invalid"
    if case == "file":
        path.write_text("not a directory")
    elif case == "no_index":
        path.mkdir()
    with pytest.raises(SpaConfigError) as error:
        create_app(path, app_origin=APP_ORIGIN)
    assert "SPA_DIST_DIR" in str(error.value)


IMPORT_APP_MAIN = (
    "from app.config import OriginSettings, SpaSettings; "
    "SpaSettings.model_config['env_file'] = None; "
    "OriginSettings.model_config['env_file'] = None; "
    "import app.main"
)


def import_app_main(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in ("SPA_DIST_DIR", "DATABASE_URL", "TEST_DATABASE_URL", "APP_ORIGIN")
    }
    # Sem ler o .env do desenvolvedor: o objetivo é só o ambiente.
    return subprocess.run(
        [sys.executable, "-c", IMPORT_APP_MAIN],
        cwd=BACKEND_DIR,
        env={**env, **extra_env},
        capture_output=True,
        text=True,
    )


def test_importing_app_main_needs_neither_spa_nor_database() -> None:
    result = import_app_main({"APP_ORIGIN": APP_ORIGIN})
    assert result.returncode == 0, result.stderr


def test_importing_app_main_without_app_origin_fails_clearly() -> None:
    result = import_app_main({})
    assert result.returncode != 0
    assert "app_origin" in result.stderr.lower()


# --- o fallback é sempre a última rota (Story 1.3, T2.2) ---


def route_paths(test_client: TestClient) -> list[str | None]:
    return [getattr(route, "path", None) for route in test_client.app.routes]  # type: ignore[attr-defined]


def test_spa_fallback_is_the_last_route(client: TestClient) -> None:
    paths = route_paths(client)
    assert paths.count(SPA_FALLBACK_PATH) == 1
    assert paths[-1] == SPA_FALLBACK_PATH


def test_there_is_no_fallback_route_without_spa(no_spa_client: TestClient) -> None:
    assert SPA_FALLBACK_PATH not in route_paths(no_spa_client)


# --- OpenAPI com a SPA montada (CA12) ---


def test_api_docs_are_not_shadowed_by_the_spa(client: TestClient) -> None:
    docs = client.get("/api/docs")
    assert docs.status_code == 200
    assert INDEX_HTML not in docs.text
    assert client.get("/api/openapi.json").json()["info"]["title"]
