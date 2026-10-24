import pytest
from fastapi import FastAPI
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
    assert list(schema.json()["paths"]) == [
        "/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/me",
    ]


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/api/redoc"])
def test_old_documentation_routes_are_gone(api_only: TestClient, path: str) -> None:
    assert api_only.get(path).status_code == 404


def test_oauth2_redirect_is_disabled(api_only: TestClient) -> None:
    paths = [getattr(route, "path", "") for route in api_only.app.routes]  # type: ignore[attr-defined]
    assert not any("oauth2-redirect" in path for path in paths)
    assert "oauth2RedirectUrl" not in api_only.get("/api/docs").text
    assert api_only.get("/api/docs/oauth2-redirect").status_code == 404


ERROR_REF = "#/components/schemas/ErrorResponse"


def response_ref(operation: dict, status: str) -> str:
    return operation["responses"][status]["content"]["application/json"]["schema"][
        "$ref"
    ]


def test_error_responses_of_the_new_routes_use_the_real_envelope(
    api_only: TestClient,
) -> None:
    schema = api_only.get("/api/openapi.json").json()
    login = schema["paths"]["/api/auth/login"]["post"]
    me = schema["paths"]["/api/me"]["get"]

    assert response_ref(login, "401") == ERROR_REF
    assert response_ref(login, "422") == ERROR_REF
    assert response_ref(me, "401") == ERROR_REF
    assert "204" in schema["paths"]["/api/auth/logout"]["post"]["responses"]


def test_default_validation_schema_is_gone(api_only: TestClient) -> None:
    # Se uma rota futura com corpo esquecer `error_responses(..., 422)`, o schema
    # padrão do FastAPI volta e este teste reprova.
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    assert {"ErrorResponse", "ErrorDetail", "CurrentUser", "LoginRequest"} <= set(
        schemas
    )


def test_openapi_has_no_secret_cookie_or_token_in_the_documented_bodies(
    api_only: TestClient,
) -> None:
    schemas = api_only.get("/api/openapi.json").json()["components"]["schemas"]
    assert sorted(schemas["CurrentUser"]["properties"]) == ["email", "role"]


def test_app_openapi_is_not_overridden(api_only: TestClient) -> None:
    # Sem override de `app.openapi()`: o método continua sendo o do FastAPI.
    assert type(api_only.app).openapi is FastAPI.openapi
    assert "openapi" not in vars(api_only.app)
