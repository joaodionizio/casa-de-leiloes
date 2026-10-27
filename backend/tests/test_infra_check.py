"""The technical transport is replaced by the real public room."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app


@pytest.mark.parametrize(
    "path",
    [
        "/api/infra-check/ws",
        "/api/infra-check/cookie",
        "/ws",
        "/ws/lots/5f3a1c52-9d2e-4b7a-8c31-0a6d4e9b7f10",
    ],
)
def test_removed_echo_and_reserved_ws_never_serve_spa(tmp_path: Path, path: str):
    (tmp_path / "index.html").write_text("<!doctype html><title>SPA</title>")
    client = TestClient(create_app(tmp_path, app_origin="https://testserver"))
    response = client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "SPA" not in response.text


def test_removed_echo_rejects_upgrade():
    client = TestClient(create_app(app_origin="https://testserver"))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/infra-check/ws"):
            pass
