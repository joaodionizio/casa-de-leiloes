"""Rota de mídia `GET /api/catalog/images/{image_id}` (revisão do AD-22).

Pública, sem banco: o proxy só aceita `image_id` validado e fala com um IIIF de host,
caminho, tamanho e formato fixos. O transporte é sempre falso; a guarda de rede do
`conftest.py` reprova qualquer acesso real.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.access import AccessPolicy
from app.config import SpaSettings
from app.main import create_app
from tests.access_policy import policy_by_route, policy_problems
from tests.catalog_support import (
    IMAGE_FAILURES,
    IMAGE_ID,
    UPSTREAM_IMAGE_URL,
    FakeArtic,
    image_bytes,
    image_response,
    install,
    jpeg_handler,
)

ORIGIN = "https://casa.example"
PATH = f"/api/catalog/images/{IMAGE_ID}"
UNAVAILABLE = {
    "status": 503,
    "code": "catalog_unavailable",
    "message": "O catálogo do museu está indisponível no momento. "
    "Tente novamente em instantes.",
}


def make_client(monkeypatch: pytest.MonkeyPatch, fake: FakeArtic) -> TestClient:
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    app = create_app(app_origin=ORIGIN)
    install(app, fake)
    return TestClient(app, base_url=ORIGIN)


def test_valid_image_id_returns_the_upstream_jpeg_without_a_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeArtic(jpeg_handler)
    client = make_client(monkeypatch, fake)

    response = client.get(PATH)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content == image_bytes()


def test_upstream_request_is_built_only_by_the_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeArtic(jpeg_handler)
    make_client(monkeypatch, fake).get(PATH, params={"url": "https://evil.example/"})

    (request,) = fake.requests
    assert str(request.url) == UPSTREAM_IMAGE_URL
    assert request.url.scheme == "https"
    assert request.url.host == "www.artic.edu"
    assert request.url.path == f"/iiif/2/{IMAGE_ID}/full/843,/0/default.jpg"
    assert request.url.query == b""
    assert request.headers["user-agent"] == "casa-de-leiloes/1.0"
    assert request.headers["aic-user-agent"] == (
        "casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)"
    )


def test_redirect_is_not_followed_and_becomes_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeArtic(
        lambda request: httpx.Response(301, headers={"Location": "https://x.example/"})
    )
    response = make_client(monkeypatch, fake).get(PATH)

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert [r.url.host for r in fake.requests] == ["www.artic.edu"]


def test_upstream_404_is_our_404(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeArtic(lambda request: httpx.Response(404, text="<html>missing</html>"))
    response = make_client(monkeypatch, fake).get(PATH)

    assert response.status_code == 404
    assert response.json() == {
        "status": 404,
        "code": "not_found",
        "message": "Recurso não encontrado.",
    }
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("reason", "handler"), IMAGE_FAILURES)
def test_upstream_failures_are_503_catalog_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    reason: str,
    handler: object,
) -> None:
    fake = FakeArtic(handler)  # type: ignore[arg-type]
    client = make_client(monkeypatch, fake)

    with caplog.at_level("WARNING", logger="uvicorn.error"):
        response = client.get(PATH)

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    # Nada do upstream (HTML do Cloudflare, bytes) chega ao cliente.
    lowered = response.text.lower()
    for forbidden in ("cloudflare", "<html", "gif89a", "artic"):
        assert forbidden not in lowered
    assert f"operation=image reason={reason}" in caplog.text


def test_oversized_body_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.artic.MAX_IMAGE_BYTES", 100)
    fake = FakeArtic(image_response(b"\xff\xd8\xff" + b"0" * 500))

    response = make_client(monkeypatch, fake).get(PATH)

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE


@pytest.mark.parametrize(
    "image_id",
    [
        "abc",
        "2D484387-2509-5E8E-2C43-22F9981972EB",
        "..",
        "%2e%2e",
        "2d484387-2509-5e8e-2c43-22f9981972eb%0A",
        "2d484387-2509-5e8e-2c43-22f9981972eb.jpg",
        "https:%2F%2Fevil.example%2Fx",
        "full",
    ],
)
def test_invalid_image_id_never_reaches_the_upstream(
    monkeypatch: pytest.MonkeyPatch, image_id: str
) -> None:
    fake = FakeArtic(jpeg_handler)
    response = make_client(monkeypatch, fake).get(f"/api/catalog/images/{image_id}")

    assert response.status_code in (404, 422)
    assert response.headers["content-type"].startswith("application/json")
    assert fake.requests == []


def test_invalid_image_id_is_a_422_in_the_single_error_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeArtic(jpeg_handler)
    response = make_client(monkeypatch, fake).get("/api/catalog/images/abc")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"] == [
        {"loc": ["path", "image_id"], "type": "invalid_image_id"}
    ]
    assert "abc" not in response.text
    assert fake.requests == []


def test_path_with_extra_segments_is_a_router_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeArtic(jpeg_handler)
    response = make_client(monkeypatch, fake).get(f"{PATH}/full/843,/0/default.jpg")

    assert response.status_code == 404
    assert fake.requests == []


@pytest.mark.parametrize("method", ["head", "options", "post"])
def test_only_get_is_allowed(monkeypatch: pytest.MonkeyPatch, method: str) -> None:
    fake = FakeArtic(jpeg_handler)
    client = make_client(monkeypatch, fake)

    response = getattr(client, method)(PATH, headers={"Origin": ORIGIN})

    assert response.status_code in (405, 415)
    assert fake.requests == []


def test_image_route_is_public_and_the_policy_check_still_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_client(monkeypatch, FakeArtic(jpeg_handler)).app

    assert policy_problems(app.routes) == []
    table = policy_by_route(app.routes)
    assert (
        table[("/api/catalog/images/{image_id}", "GET", "http")] == AccessPolicy.PUBLIC
    )
    # A busca e o detalhe continuam exclusivos do leiloeiro.
    assert table[("/api/catalog/artworks", "GET", "http")] == AccessPolicy.AUCTIONEER
    assert table[("/api/catalog/artworks/{external_id}", "GET", "http")] == (
        AccessPolicy.AUCTIONEER
    )
