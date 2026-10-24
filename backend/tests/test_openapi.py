import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import SpaSettings
from app.main import create_app


@pytest.fixture
def api_only(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    return TestClient(create_app(app_origin="https://casa.example"))


def test_docs_and_schema_live_under_api(api_only: TestClient) -> None:
    docs = api_only.get("/api/docs")
    assert docs.status_code == 200
    assert docs.headers["content-type"].startswith("text/html")

    schema = api_only.get("/api/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"]["title"] == "Casa de Leilões"
    assert list(schema.json()["paths"]) == ["/health"]


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/api/redoc"])
def test_old_documentation_routes_are_gone(api_only: TestClient, path: str) -> None:
    assert api_only.get(path).status_code == 404


def test_oauth2_redirect_is_disabled(api_only: TestClient) -> None:
    paths = [getattr(route, "path", "") for route in api_only.app.routes]  # type: ignore[attr-defined]
    assert not any("oauth2-redirect" in path for path in paths)
    assert "oauth2RedirectUrl" not in api_only.get("/api/docs").text
    assert api_only.get("/api/docs/oauth2-redirect").status_code == 404
