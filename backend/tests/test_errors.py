import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import csrf
from app.errors import (
    CODE_BY_STATUS,
    MESSAGES,
    code_for_status,
    sanitize_validation_errors,
)
from app.main import create_app
from tests.synthetic_api import (
    JSON_HEADERS,
    SECRET_DETAIL,
    SECRET_EXCEPTION,
    build_app,
)

INDEX_HTML = "<!doctype html><title>SPA de teste</title>"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app, _ = build_app(monkeypatch)
    return TestClient(app)


@pytest.fixture
def crash_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app, _ = build_app(monkeypatch)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def spa_client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(INDEX_HTML)
    return TestClient(create_app(dist, app_origin="https://casa.example"))


def assert_contract(response, status: int, code: str) -> dict:
    body = response.json()
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")
    assert body["status"] == status
    assert body["code"] == code
    assert body["message"] == MESSAGES[code]
    assert "detail" not in body
    return body


# --- erros previstos (CA1, CA2) ---


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "bad_request"),
        (401, "unauthorized"),
        (403, "forbidden"),
        (404, "not_found"),
        (409, "conflict"),
    ],
)
def test_http_exceptions_use_the_single_contract(
    client: TestClient, status: int, code: str
) -> None:
    response = client.get(f"/api/test/http-error/{status}")
    body = assert_contract(response, status, code)
    assert set(body) == {"status", "code", "message"}  # sem `details` nem `null`
    assert SECRET_DETAIL not in response.text


def test_401_keeps_www_authenticate(client: TestClient) -> None:
    response = client.get("/api/test/http-error/401")
    assert response.headers["www-authenticate"] == "Bearer"


def test_status_outside_the_catalog_falls_back_by_class(client: TestClient) -> None:
    assert code_for_status(418) == "bad_request"
    assert code_for_status(503) == "internal_error"
    response = client.get("/api/test/http-error/418")
    assert_contract(response, 418, "bad_request")


def test_messages_are_the_fixed_portuguese_catalog() -> None:
    # Texto literal: o front exibe estas mensagens; mudar uma é mudar o contrato.
    assert MESSAGES == {
        "bad_request": "Requisição inválida.",
        "unauthorized": "Autenticação necessária.",
        "forbidden": "Acesso negado.",
        "not_found": "Recurso não encontrado.",
        "method_not_allowed": "Método não permitido para este recurso.",
        "conflict": "Conflito com o estado atual do recurso.",
        "unsupported_media_type": (
            "O corpo da requisição deve ser JSON (Content-Type: application/json)."
        ),
        "validation_error": "Os dados enviados são inválidos.",
        "internal_error": "Erro interno. Tente novamente mais tarde.",
        "csrf_origin_missing": "Não foi possível verificar a origem da requisição.",
        "csrf_origin_mismatch": "Origem da requisição não permitida.",
        # Story 2.2: código específico do login, emitido só pela rota de login.
        "invalid_credentials": "E-mail ou senha inválidos.",
        # Story 2.3: catálogo do museu fora do ar, emitido só pelas rotas do catálogo.
        "catalog_unavailable": (
            "O catálogo do museu está indisponível no momento. "
            "Tente novamente em instantes."
        ),
        # Story 2.4: obra que não pode virar lote, emitido só pela criação de lote.
        "artwork_not_eligible": (
            "Esta obra não pode virar lote. Só são aceitas obras de domínio "
            "público com imagem no acervo do museu."
        ),
        # Story 3.1: depósito que passaria do teto de saldo, emitido só pelo depósito.
        "balance_limit_exceeded": (
            "O depósito ultrapassaria o limite de saldo da carteira."
        ),
        # Story 3.4: recusas de negócio do lance (códigos de `BidRefusal`) e o
        # conflito de integridade, emitidos só pelo `POST /api/lots/{id}/bids`.
        "lot_not_started": "Este lote ainda não começou.",
        "lot_ended": "Este lote já foi encerrado.",
        "below_minimum": "Seu lance está abaixo do mínimo para este lote.",
        "already_winning": "Você já está ganhando este lote.",
        "insufficient_balance": "Saldo disponível insuficiente para este lance.",
        "lot_integrity_conflict": (
            "Não foi possível verificar a integridade deste lote. "
            "O lance não foi registrado."
        ),
    }


def test_every_status_code_has_a_message_and_codes_are_snake_case_english() -> None:
    for code in CODE_BY_STATUS.values():
        assert code in MESSAGES
    for code in MESSAGES:
        assert code.isascii() and code == code.lower() and " " not in code


def test_unknown_api_path_is_the_contract_404(client: TestClient) -> None:
    assert_contract(client.get("/api/nao-existe"), 404, "not_found")


def test_head_on_unknown_api_path_has_no_body(client: TestClient) -> None:
    response = client.head("/api/nao-existe")
    assert response.status_code == 404
    assert response.content == b""


def test_405_keeps_allow_and_uses_the_contract(client: TestClient) -> None:
    response = client.request("POST", "/api/test/read", headers=JSON_HEADERS)
    assert_contract(response, 405, "method_not_allowed")
    assert response.headers["allow"] == "GET"


def test_unknown_api_path_with_spa_is_the_contract_404(spa_client: TestClient) -> None:
    response = spa_client.get("/api/nao-existe")
    assert_contract(response, 404, "not_found")
    assert INDEX_HTML not in response.text


def test_missing_asset_with_spa_follows_the_contract(spa_client: TestClient) -> None:
    assert_contract(spa_client.get("/assets/velho.js"), 404, "not_found")


# --- validação 422 (CA3) ---


def test_validation_error_lists_only_location_and_type(client: TestClient) -> None:
    response = client.post(
        "/api/test/validate",
        headers=JSON_HEADERS,
        content=json.dumps({"name": "senha-super-secreta", "age": "não é número"}),
    )
    body = assert_contract(response, 422, "validation_error")
    assert body["details"] == [{"loc": ["body", "age"], "type": "int_parsing"}]
    for forbidden in ("senha-super-secreta", "input", "ctx", "url", "msg"):
        assert forbidden not in response.text


def test_missing_field_is_reported_by_location(client: TestClient) -> None:
    response = client.post(
        "/api/test/validate", headers=JSON_HEADERS, content=json.dumps({"name": "x"})
    )
    body = assert_contract(response, 422, "validation_error")
    assert body["details"] == [{"loc": ["body", "age"], "type": "missing"}]


def test_malformed_json_is_a_422_without_the_input(client: TestClient) -> None:
    response = client.post(
        "/api/test/validate", headers=JSON_HEADERS, content='{"senha": "senha-vazada'
    )
    body = assert_contract(response, 422, "validation_error")
    assert body["details"][0]["type"] == "json_invalid"
    assert "senha-vazada" not in response.text


def test_sanitize_drops_everything_but_location_and_type() -> None:
    sanitized = sanitize_validation_errors(
        [
            {
                "loc": ("body", 0, "campo"),
                "type": "missing",
                "msg": "Field required",
                "input": "segredo",
                "ctx": {"error": "x"},
                "url": "https://errors.pydantic.dev",
            }
        ]
    )
    assert sanitized == [{"loc": ["body", 0, "campo"], "type": "missing"}]


# --- falha inesperada (CA4) ---


def test_unexpected_error_is_a_generic_500(crash_client: TestClient) -> None:
    response = crash_client.get("/api/test/boom")
    assert_contract(response, 500, "internal_error")
    for leaked in (
        "RuntimeError",
        SECRET_EXCEPTION,
        "Traceback",
        "secreto.py",
        "SELECT",
    ):
        assert leaked not in response.text


def test_unexpected_error_is_reraised_for_the_server_log(client: TestClient) -> None:
    # O ServerErrorMiddleware envia o 500 e relança: é isso que o uvicorn registra (D5).
    with pytest.raises(RuntimeError):
        client.get("/api/test/boom")


def test_invalid_response_is_a_500_not_a_422(crash_client: TestClient) -> None:
    response = crash_client.get("/api/test/bad-response")
    assert_contract(response, 500, "internal_error")
    assert "não é número" not in response.text


def test_failure_inside_the_guard_is_the_contract_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, calls = build_app(monkeypatch)

    def broken(headers, allowed):
        raise RuntimeError(SECRET_EXCEPTION)

    monkeypatch.setattr(csrf, "origin_problem", broken)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/test/write", headers=JSON_HEADERS, content="{}"
    )
    assert_contract(response, 500, "internal_error")
    assert SECRET_EXCEPTION not in response.text
    assert calls.count == 0
