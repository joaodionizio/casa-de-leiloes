"""Apoio dos testes do catálogo (Story 2.3): fixtures JSON da AIC e um transporte
falso que conta e inspeciona as chamadas. O `ArticClient` usado é o real."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from app.artic import ArticClient

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "artic"

Handler = Callable[[httpx.Request], httpx.Response]


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def json_response(body: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=body)


class FakeArtic:
    """Transporte falso: `handler` decide a resposta e `requests` registra cada
    chamada que chegou ao transporte."""

    def __init__(self, handler: Handler) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def artic_client(fake: FakeArtic) -> ArticClient:
    return ArticClient(transport=httpx.MockTransport(fake.handler))


def install(app: FastAPI, fake: FakeArtic) -> None:
    app.state.artic_client = artic_client(fake)


def search_params(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.url.params["params"])


def standard_handler(request: httpx.Request) -> httpx.Response:
    """Respostas das fixtures: busca por 'monet' ou vazia, e alguns detalhes."""
    path = request.url.path
    if path.endswith("/artworks/search"):
        term = search_params(request)["q"]
        name = "search_empty.json" if term == "qxzvkwjq" else "search_monet.json"
        return json_response(load_fixture(name))
    detail = {
        "/api/v1/artworks/27992": "artwork_27992.json",
        "/api/v1/artworks/555001": "artwork_missing_fields.json",
        "/api/v1/artworks/129884": "artwork_not_public_domain.json",
        "/api/v1/artworks/555002": "artwork_no_image.json",
    }.get(path)
    if detail is None:
        return json_response(load_fixture("not_found.json"), 404)
    return json_response(load_fixture(detail))


# Falhas comuns à busca e ao detalhe: (motivo interno, handler que as simula).
def raising(error: Callable[[httpx.Request], Exception]):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error(request)

    return handler


def status_handler(status: int) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(
        status, text="<html>cloudflare</html>", headers={"content-type": "text/html"}
    )


def body_handler(
    content: bytes, content_type: str = "application/json"
) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(
        200, content=content, headers={"content-type": content_type}
    )


FAILURES_BOTH = [
    ("timeout", raising(lambda r: httpx.ConnectTimeout("t", request=r))),
    ("timeout", raising(lambda r: httpx.ReadTimeout("t", request=r))),
    ("connect", raising(lambda r: httpx.ConnectError("c", request=r))),
    ("http_403", status_handler(403)),
    ("http_429", status_handler(429)),
    ("http_500", status_handler(500)),
    ("http_502", status_handler(502)),
    ("http_503", status_handler(503)),
    ("http_400", status_handler(400)),
    ("not_json", body_handler(b"<html>")),
    ("not_json", body_handler(b'{"data": []}', "text/html")),
    ("bad_shape", body_handler(b"[]")),
    ("bad_shape", body_handler(b'{"data": "x"}')),
    ("bad_shape", body_handler(b'{"pagination": {}}')),
]


# Proxy de imagem (revisão do AD-22).
IMAGE_ID = "2d484387-2509-5e8e-2c43-22f9981972eb"
UPSTREAM_IMAGE_URL = f"https://www.artic.edu/iiif/2/{IMAGE_ID}/full/843,/0/default.jpg"


def image_bytes() -> bytes:
    """JPEG minúsculo versionado (`image_sample.jpg`)."""
    return (FIXTURES / "image_sample.jpg").read_bytes()


def jpeg_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, content=image_bytes(), headers={"content-type": "image/jpeg"}
    )


def image_response(
    content: bytes, content_type: str = "image/jpeg"
) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(
        200, content=content, headers={"content-type": content_type}
    )


# Falhas do IIIF: (motivo interno, handler). O 404 não está aqui: é "inexistente".
IMAGE_FAILURES = [
    ("timeout", raising(lambda r: httpx.ConnectTimeout("t", request=r))),
    ("timeout", raising(lambda r: httpx.ReadTimeout("t", request=r))),
    ("connect", raising(lambda r: httpx.ConnectError("c", request=r))),
    (
        "redirect",
        lambda r: httpx.Response(301, headers={"Location": "https://x.example/"}),
    ),
    ("http_403", status_handler(403)),
    ("http_429", status_handler(429)),
    ("http_500", status_handler(500)),
    ("http_502", status_handler(502)),
    ("http_503", status_handler(503)),
    ("http_400", status_handler(400)),
    ("not_image", image_response(b"<html>cloudflare</html>", "text/html")),
    ("not_image", image_response(b"<html>cloudflare</html>")),
    ("not_image", image_response(b"")),
    ("not_image", image_response(b"GIF89a not a jpeg", "image/jpeg")),
]
