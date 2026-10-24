from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import infra_check
from app.infra_check import (
    MAX_MESSAGE_BYTES,
    is_allowed_origin,
    origin_host,
)
from app.main import create_app

COOKIE_PATH = "/api/infra-check/cookie"
WS_PATH = "/api/infra-check/ws"
INDEX_HTML = "<!doctype html><title>SPA de teste</title>"
APP_ORIGIN = "https://testserver"
JSON_HEADERS = {"Origin": APP_ORIGIN, "Content-Type": "application/json"}

# Fecha o handshake antes do accept: o servidor responde 403 e o TestClient
# levanta WebSocketDisconnect com o código usado em `close()`.
POLICY_VIOLATION = 1008
UNSUPPORTED_DATA = 1003
MESSAGE_TOO_BIG = 1009
NORMAL_CLOSURE = 1000


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(INDEX_HTML)
    return dist_dir


@pytest.fixture
def client(dist: Path) -> TestClient:
    # A SPA montada prova que o fallback não sombreia as rotas técnicas.
    return TestClient(
        create_app(dist, app_origin=APP_ORIGIN), base_url="https://testserver"
    )


def test_technical_cookie_route_is_gone_and_answers_the_json_404(
    client: TestClient,
) -> None:
    response = client.get(COOKIE_PATH)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["code"] == "not_found"
    assert "set-cookie" not in response.headers
    assert "SPA de teste" not in response.text


def test_technical_cookie_route_is_gone_without_the_spa() -> None:
    response = TestClient(
        create_app(app_origin=APP_ORIGIN), base_url="https://testserver"
    ).get(COOKIE_PATH)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_infra_check_routes_stay_out_of_openapi(client: TestClient) -> None:
    paths = client.get("/api/openapi.json").json()["paths"]
    assert not any("infra-check" in path for path in paths)


@pytest.mark.parametrize(
    "origin, expected",
    [
        ("https://testserver", "testserver"),
        ("http://TestServer", "testserver"),
        ("http://127.0.0.1:8000", "127.0.0.1:8000"),
        ("https://evil.example", "evil.example"),
        ("", None),
        ("null", None),
        ("http://[::1", None),
        ("not-a-url", None),
        ("ftp://testserver", None),
        ("https://", None),
        ("https://testserver/path", None),
        ("https://testserver/", None),
        ("https://testserver?x=1", None),
        ("https://testserver#frag", None),
    ],
)
def test_origin_host(origin: str, expected: str | None) -> None:
    assert origin_host(origin) == expected


@pytest.mark.parametrize(
    "origin, host, expected",
    [
        (None, "testserver", True),
        (None, None, True),
        ("https://testserver", "testserver", True),
        ("https://TestServer", "TESTSERVER", True),
        ("http://127.0.0.1:8000", "127.0.0.1:8000", True),
        ("http://[::1]:8000", "[::1]:8000", True),
        ("https://evil.example", "testserver", False),
        ("https://testserver", None, False),
        # Política atual: compara `host[:porta]` literal, sem normalizar a porta padrão.
        ("https://testserver:443", "testserver", False),
        ("https://user@testserver", "testserver", False),
        ("https://testserver@evil.example", "testserver", False),
        ("null", "testserver", False),
        ("http://[::1", "testserver", False),
    ],
)
def test_is_allowed_origin(
    origin: str | None, host: str | None, expected: bool
) -> None:
    assert is_allowed_origin(origin, host) is expected


def test_websocket_echoes_once_and_closes_normally(client: TestClient) -> None:
    with client.websocket_connect(
        WS_PATH, headers={"origin": "https://testserver"}
    ) as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "echo:ping"
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_text()
    assert closed.value.code == NORMAL_CLOSURE


def test_websocket_accepts_message_at_the_size_limit(client: TestClient) -> None:
    message = "a" * MAX_MESSAGE_BYTES
    with client.websocket_connect(WS_PATH) as websocket:
        websocket.send_text(message)
        assert websocket.receive_text() == f"echo:{message}"


def test_websocket_without_origin_is_accepted(client: TestClient) -> None:
    with client.websocket_connect(WS_PATH) as websocket:
        websocket.send_text("ping")
        assert websocket.receive_text() == "echo:ping"


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "https://testserver.evil.example"]
)
def test_websocket_with_foreign_origin_is_rejected(
    client: TestClient, origin: str
) -> None:
    with pytest.raises(WebSocketDisconnect) as rejected:
        with client.websocket_connect(WS_PATH, headers={"origin": origin}):
            pass
    assert rejected.value.code == POLICY_VIOLATION


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "null",
        "http://[::1",
        "not-a-url",
        "ftp://testserver",
        "https://testserver/path",
    ],
)
def test_websocket_with_malformed_origin_is_rejected_without_error(
    client: TestClient, origin: str
) -> None:
    with pytest.raises(WebSocketDisconnect) as rejected:
        with client.websocket_connect(WS_PATH, headers={"origin": origin}):
            pass
    assert rejected.value.code == POLICY_VIOLATION


@pytest.mark.parametrize(
    "payload, expected_code",
    [
        ("a" * (MAX_MESSAGE_BYTES + 1), MESSAGE_TOO_BIG),
        # 33 caracteres de 2 bytes: passa em caracteres, estoura em bytes.
        ("é" * (MAX_MESSAGE_BYTES // 2 + 1), MESSAGE_TOO_BIG),
        (b"\x00\x01", UNSUPPORTED_DATA),
    ],
)
def test_websocket_rejects_unexpected_messages(
    client: TestClient, payload: str | bytes, expected_code: int
) -> None:
    with client.websocket_connect(WS_PATH) as websocket:
        if isinstance(payload, bytes):
            websocket.send_bytes(payload)
        else:
            websocket.send_text(payload)
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_text()
    assert closed.value.code == expected_code


def test_websocket_closes_when_no_message_arrives(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(infra_check, "RECEIVE_TIMEOUT_SECONDS", 0.05)
    with client.websocket_connect(WS_PATH) as websocket:
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_text()
    assert closed.value.code == POLICY_VIOLATION


def test_websocket_route_is_not_served_by_the_spa_fallback(
    client: TestClient,
) -> None:
    # Um GET HTTP comum no caminho do WebSocket cai no 404 JSON de `/api`, nunca
    # no index.html.
    response = client.get(WS_PATH)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "SPA de teste" not in response.text
