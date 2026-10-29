from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute
from fastapi.testclient import TestClient
from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.websockets import WebSocketDisconnect

from app import lot_room, main
from app.access import AccessPolicy, require_user
from app.bids import PublicBidRoomResponse
from app.config import SpaSettings
from app.csrf import (
    ApiWriteGuardMiddleware,
    effective_path,
    format_origin,
    is_json_content_type,
    origin_problem,
    parse_origin,
)
from app.errors import MESSAGES
from app.main import create_app
from tests.access_policy import policy_by_route, policy_problems
from tests.synthetic_api import (
    ALLOWED_ORIGIN,
    JSON_HEADERS,
    WRITE_METHODS,
    build_app,
)

WRITE_URL = "/api/test/write"
ALLOWED = ("https", "casa.example", 443)

methods = pytest.mark.parametrize("method", WRITE_METHODS)


@pytest.fixture
def app_and_calls(monkeypatch: pytest.MonkeyPatch):
    return build_app(monkeypatch)


@pytest.fixture
def client(app_and_calls) -> TestClient:
    return TestClient(app_and_calls[0])


@pytest.fixture
def calls(app_and_calls):
    return app_and_calls[1]


def write(
    client: TestClient, method: str, headers: dict[str, str], url: str = WRITE_URL
):
    return client.request(method, url, headers=headers, content=b"{}")


def assert_refused(response, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.json() == {
        "status": status,
        "code": code,
        "message": MESSAGES[code],
    }


# --- parse_origin / origin_problem (CA6, CA7) ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://casa.example", ALLOWED),
        ("https://CASA.Example", ALLOWED),
        ("HTTPS://casa.example", ALLOWED),
        ("https://casa.example:443", ALLOWED),
        ("http://casa.example:80", ("http", "casa.example", 80)),
        ("http://localhost:5173", ("http", "localhost", 5173)),
        ("http://[::1]:5173", ("http", "::1", 5173)),
        ("https://casa.example:0", ("https", "casa.example", 0)),
    ],
)
def test_parse_origin_valid(value: str, expected: tuple[str, str, int]) -> None:
    assert parse_origin(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "null",
        "*",
        "casa.example",
        "ftp://casa.example",
        "https://",
        "https://[::1",
        "https://casa.example:abc",
        "https://casa.example:99999",
        "https://casa.example@evil.com",
        "https://user:pw@casa.example",
        "https://casa.example/",
        "https://casa.example/path",
        "https://casa.example?x=1",
        "https://casa.example?",
        "https://casa.example#frag",
        "https://casa.example, https://evil.example",
    ],
)
def test_parse_origin_invalid(value: str) -> None:
    assert parse_origin(value) is None


def test_parse_origin_ignores_path_query_and_fragment_for_referer() -> None:
    assert parse_origin("https://casa.example/a/b?x=1#f", allow_path=True) == ALLOWED
    assert parse_origin("https://casa.example@evil.com/a", allow_path=True) is None


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        (ALLOWED, "https://casa.example"),
        (("http", "localhost", 5173), "http://localhost:5173"),
        (("http", "::1", 80), "http://[::1]"),
        (("https", "casa.example", 8443), "https://casa.example:8443"),
    ],
)
def test_format_origin(origin: tuple[str, str, int], expected: str) -> None:
    assert format_origin(origin) == expected


def headers_of(*pairs: tuple[str, str]) -> Headers:
    return Headers(raw=[(k.lower().encode(), v.encode()) for k, v in pairs])


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "http://casa.example",  # outro esquema
        "https://casa.example:8443",  # outra porta
        "https://casa.example.evil.com",  # sufixo
        "https://evilcasa.example",  # prefixo
        "https://casa.example@evil.com",
        "null",
        "",
        "https://[::1",
        "https://casa.example/path",
    ],
)
def test_origin_problem_foreign_or_invalid_origin_is_a_mismatch(origin: str) -> None:
    assert origin_problem(headers_of(("origin", origin)), ALLOWED) == (
        "csrf_origin_mismatch"
    )


def test_origin_problem_same_origin_passes() -> None:
    assert (
        origin_problem(headers_of(("origin", "https://casa.example")), ALLOWED) is None
    )
    assert (
        origin_problem(headers_of(("origin", "https://CASA.example:443")), ALLOWED)
        is None
    )


@pytest.mark.parametrize("bad_origin", ["https://evil.example", "null", "", "lixo"])
def test_origin_has_precedence_over_a_valid_referer(bad_origin: str) -> None:
    headers = headers_of(("origin", bad_origin), ("referer", "https://casa.example/x"))
    assert origin_problem(headers, ALLOWED) == "csrf_origin_mismatch"


def test_referer_is_used_only_without_origin() -> None:
    assert (
        origin_problem(headers_of(("referer", "https://casa.example/a?b=1")), ALLOWED)
        is None
    )
    for referer in (
        "https://evil.example/a",
        "lixo",
        "",
        "https://casa.example.evil.com/",
    ):
        assert origin_problem(headers_of(("referer", referer)), ALLOWED) == (
            "csrf_origin_mismatch"
        )


def test_without_origin_and_referer_the_problem_is_missing() -> None:
    assert origin_problem(headers_of(), ALLOWED) == "csrf_origin_missing"


def test_duplicate_origin_or_referer_headers_are_ambiguous() -> None:
    two_origins = headers_of(
        ("origin", "https://casa.example"), ("origin", "https://casa.example")
    )
    assert origin_problem(two_origins, ALLOWED) == "csrf_origin_mismatch"
    two_referers = headers_of(
        ("referer", "https://casa.example/"), ("referer", "https://casa.example/")
    )
    assert origin_problem(two_referers, ALLOWED) == "csrf_origin_mismatch"


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["application/json"], True),
        (["application/json; charset=utf-8"], True),
        (["Application/JSON"], True),
        (["application/json;charset=UTF-8"], True),
        (["application/merge-patch+json"], False),
        (["application/vnd.api+json"], False),
        (["text/plain"], False),
        (["application/x-www-form-urlencoded"], False),
        (["multipart/form-data; boundary=x"], False),
        (["application/jsonx"], False),
        ([], False),
        (["application/json", "application/json"], False),
    ],
)
def test_is_json_content_type(values: list[str], expected: bool) -> None:
    headers = headers_of(*[("content-type", value) for value in values])
    assert is_json_content_type(headers) is expected


def test_middleware_rejects_an_invalid_allowed_origin() -> None:
    with pytest.raises(ValueError):
        ApiWriteGuardMiddleware(
            lambda *args: None, allowed_origin="https://casa.example/"
        )


# --- escritas por HTTP (CA5, CA8) ---


@methods
def test_valid_origin_and_json_reach_the_handler(
    client: TestClient, calls, method: str
) -> None:
    response = write(client, method, JSON_HEADERS)
    assert response.status_code == 200
    assert calls.count == 1


@methods
@pytest.mark.parametrize(
    "origin", ["https://evil.example", "http://casa.example", "null", "", "lixo"]
)
def test_foreign_origin_is_403_and_never_runs_the_handler(
    client: TestClient, calls, method: str, origin: str
) -> None:
    response = write(client, method, {**JSON_HEADERS, "Origin": origin})
    assert_refused(response, 403, "csrf_origin_mismatch")
    assert calls.count == 0


@methods
@pytest.mark.parametrize("origin", ["https://evil.example", "null", "lixo"])
def test_a_valid_referer_does_not_rescue_a_bad_origin(
    client: TestClient, calls, method: str, origin: str
) -> None:
    headers = {
        "Origin": origin,
        "Referer": f"{ALLOWED_ORIGIN}/pagina",
        "Content-Type": "application/json",
    }
    assert_refused(write(client, method, headers), 403, "csrf_origin_mismatch")
    assert calls.count == 0


@methods
def test_same_origin_referer_with_path_and_query_is_accepted(
    client: TestClient, calls, method: str
) -> None:
    headers = {
        "Referer": f"{ALLOWED_ORIGIN}/lots/1?tab=x",
        "Content-Type": "application/json",
    }
    assert write(client, method, headers).status_code == 200
    assert calls.count == 1


@methods
@pytest.mark.parametrize(
    "referer", ["https://evil.example/", "lixo", "https://casa.example.evil.com/x"]
)
def test_foreign_or_malformed_referer_without_origin_is_403(
    client: TestClient, calls, method: str, referer: str
) -> None:
    headers = {"Referer": referer, "Content-Type": "application/json"}
    assert_refused(write(client, method, headers), 403, "csrf_origin_mismatch")
    assert calls.count == 0


@methods
@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"Cookie": "__Host-infra_check=1"},
        {"User-Agent": "curl/8.0"},
    ],
)
def test_no_origin_and_no_referer_is_403_with_or_without_cookie(
    client: TestClient, calls, method: str, extra: dict[str, str]
) -> None:
    headers = {"Content-Type": "application/json", **extra}
    assert_refused(write(client, method, headers), 403, "csrf_origin_missing")
    assert calls.count == 0


@methods
@pytest.mark.parametrize(
    "forged",
    [
        {"Host": "evil.example"},
        {"Forwarded": "host=evil.example;proto=https"},
        {"X-Forwarded-Host": "evil.example", "X-Forwarded-Proto": "https"},
    ],
)
def test_host_and_forwarded_headers_do_not_choose_the_origin(
    client: TestClient, calls, method: str, forged: dict[str, str]
) -> None:
    headers = {
        "Origin": "https://evil.example",
        "Content-Type": "application/json",
        **forged,
    }
    assert_refused(write(client, method, headers), 403, "csrf_origin_mismatch")
    assert calls.count == 0


def test_external_https_origin_with_internal_http_request_is_accepted(
    client: TestClient, calls
) -> None:
    # O TestClient fala `http://testserver`; a origem configurada é `https://`.
    assert write(client, "POST", JSON_HEADERS).status_code == 200


@methods
@pytest.mark.parametrize(
    "content_type",
    [
        "text/plain",
        "application/x-www-form-urlencoded",
        "multipart/form-data; boundary=x",
        "application/merge-patch+json",
        "application/vnd.api+json",
        None,
    ],
)
def test_non_json_content_is_415_and_never_runs_the_handler(
    client: TestClient, calls, method: str, content_type: str | None
) -> None:
    headers = {"Origin": ALLOWED_ORIGIN}
    if content_type is not None:
        headers["Content-Type"] = content_type
    assert_refused(write(client, method, headers), 415, "unsupported_media_type")
    assert calls.count == 0


def test_two_content_type_headers_are_415(client: TestClient, calls) -> None:
    response = client.post(
        WRITE_URL,
        headers=[
            ("Origin", ALLOWED_ORIGIN),
            ("Content-Type", "application/json"),
            ("Content-Type", "application/json"),
        ],
        content=b"{}",
    )
    assert_refused(response, 415, "unsupported_media_type")
    assert calls.count == 0


@pytest.mark.parametrize(
    "content_type", ["application/json; charset=utf-8", "Application/JSON"]
)
def test_json_with_charset_or_other_case_is_accepted(
    client: TestClient, calls, content_type: str
) -> None:
    headers = {"Origin": ALLOWED_ORIGIN, "Content-Type": content_type}
    assert write(client, "POST", headers).status_code == 200
    assert calls.count == 1


def test_empty_body_with_json_content_type_reaches_the_handler(
    client: TestClient, calls
) -> None:
    response = client.post(WRITE_URL, headers=JSON_HEADERS, content=b"")
    assert response.status_code == 200
    assert calls.count == 1


@methods
def test_origin_is_checked_before_content(
    client: TestClient, calls, method: str
) -> None:
    headers = {"Origin": "https://evil.example", "Content-Type": "text/plain"}
    assert_refused(write(client, method, headers), 403, "csrf_origin_mismatch")
    assert calls.count == 0


@methods
def test_valid_write_on_unknown_api_path_without_spa_is_the_router_404(
    client: TestClient, method: str
) -> None:
    # Sem SPA (dev). Com a SPA montada é 405; ver test_spa.py.
    response = write(client, method, JSON_HEADERS, "/api/nao-existe")
    assert_refused(response, 404, "not_found")


@methods
def test_foreign_write_on_unknown_api_path_is_403_before_404(
    client: TestClient, method: str
) -> None:
    headers = {**JSON_HEADERS, "Origin": "https://evil.example"}
    response = write(client, method, headers, "/api/nao-existe")
    assert_refused(response, 403, "csrf_origin_mismatch")


@methods
def test_write_outside_api_is_not_guarded_and_gets_the_router_404(
    client: TestClient, method: str
) -> None:
    # Sem SPA não há rota em /lots/x: o roteador responde 404, nunca o 403/415.
    response = write(client, method, {"Origin": "https://evil.example"}, "/lots/x")
    assert_refused(response, 404, "not_found")


# --- root_path: a proteção usa o mesmo caminho que o roteador ---


@pytest.fixture
def root_path_client(app_and_calls) -> TestClient:
    return TestClient(app_and_calls[0], root_path="/prefix")


@methods
def test_foreign_write_under_root_path_is_403_and_never_runs_the_handler(
    root_path_client: TestClient, calls, method: str
) -> None:
    headers = {**JSON_HEADERS, "Origin": "https://evil.example"}
    response = write(root_path_client, method, headers, f"/prefix{WRITE_URL}")
    assert_refused(response, 403, "csrf_origin_mismatch")
    assert calls.count == 0


@methods
def test_non_json_write_under_root_path_is_415(
    root_path_client: TestClient, calls, method: str
) -> None:
    headers = {"Origin": ALLOWED_ORIGIN, "Content-Type": "text/plain"}
    response = write(root_path_client, method, headers, f"/prefix{WRITE_URL}")
    assert_refused(response, 415, "unsupported_media_type")
    assert calls.count == 0


def test_valid_write_under_root_path_reaches_the_handler(
    root_path_client: TestClient, calls
) -> None:
    response = write(root_path_client, "POST", JSON_HEADERS, f"/prefix{WRITE_URL}")
    assert response.status_code == 200
    assert calls.count == 1


# --- métodos seguros (CA9) ---


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"Origin": "lixo", "Content-Type": "text/plain"},
        {"Referer": "https://evil.example/"},
    ],
)
def test_safe_methods_are_never_refused_by_the_guard(
    client: TestClient, method: str, headers: dict[str, str]
) -> None:
    response = client.request(method, "/api/test/read", headers=headers)
    if method == "GET":
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    else:
        # 405 do roteador (sem CORS), com o Allow preservado.
        assert response.status_code == 405
        assert response.headers["allow"] == "GET"
        if method == "HEAD":
            assert response.content == b""
        else:
            assert_refused(response, 405, "method_not_allowed")
    assert not any(name.startswith("access-control-") for name in response.headers)


def test_get_does_not_need_origin_or_json(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/openapi.json").status_code == 200
    assert client.get("/api/docs").status_code == 200


# --- escopo e estrutura ---


def unguarded_write_surfaces(app: FastAPI) -> list[str]:
    """Rotas de qualquer tipo que aceitam escrita fora de `/api`, e `Mount` fora de
    `/api` (um app montado pode aceitar escrita sem declarar métodos)."""
    escaped: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        under_api = path == "/api" or path.startswith("/api/")
        if isinstance(route, Mount):
            if not under_api:
                escaped.append(path)
            continue
        methods = getattr(route, "methods", None) or set()
        if methods & set(WRITE_METHODS) and not under_api:
            escaped.append(path)
    return escaped


def test_every_http_write_route_lives_under_api(client: TestClient) -> None:
    # Escrita fora de /api escaparia da proteção (que só cobre /api).
    assert unguarded_write_surfaces(client.app) == []  # type: ignore[arg-type]


def test_real_app_has_no_write_route_outside_api(tmp_path: Path) -> None:
    # Com a SPA montada, como em produção: o fallback é só GET/HEAD.
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>")
    app = create_app(dist, app_origin=ALLOWED_ORIGIN)
    assert unguarded_write_surfaces(app) == []


# Story 6.1: o próprio mapa executado é confrontado com todas as escritas reais.
REAL_WRITES = [
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/lots"),
    ("POST", "/api/wallet/deposit"),
    ("POST", "/api/lots/{lot_id}/bids"),
    ("POST", "/api/lots/{lot_id}/cancel"),
]


def http_write_inventory(
    routes: Sequence[object], prefix: str = ""
) -> set[tuple[str, str]]:
    """Descobre escritas pela estrutura HTTP pública, sem consultar políticas.

    Uma superfície que não posso inspecionar reprova em vez de desaparecer do
    inventário. Mounts preservam o prefixo; nenhuma exceção documental se aplica.
    """
    inventory: set[tuple[str, str]] = set()
    for route in routes:
        if isinstance(route, Mount):
            if not route.routes:
                raise ValueError(
                    f"mount sem rotas inspecionáveis: {prefix}{route.path}"
                )
            entries = http_write_inventory(route.routes, prefix + route.path)
        elif isinstance(route, (APIRoute, Route)):
            path = prefix + route.path
            if not route.methods:
                raise ValueError(f"rota HTTP sem métodos inspecionáveis: {path}")
            entries = set()
            for method in route.methods:
                if method in WRITE_METHODS:
                    entries.add((method, path))
                elif method not in {"GET", "HEAD", "OPTIONS", "TRACE"}:
                    raise ValueError(f"método HTTP não suportado: {method} {path}")
        elif isinstance(route, (APIWebSocketRoute, WebSocketRoute)):
            continue
        else:
            raise ValueError(f"tipo de rota não suportado: {type(route).__name__}")
        duplicates = inventory & entries
        if duplicates:
            raise ValueError(f"escrita duplicada no inventário: {sorted(duplicates)}")
        inventory.update(entries)
    return inventory


def assert_real_write_inventory(app: FastAPI) -> set[tuple[str, str]]:
    registered = http_write_inventory(app.routes)
    assert registered == set(REAL_WRITES), "inventário CA1 diverge das escritas W1–W7"
    return registered


@pytest.fixture
def real_write_app(tmp_path, monkeypatch, with_spa) -> FastAPI:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>")
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    return create_app(dist if with_spa else None, app_origin=ALLOWED_ORIGIN)


@pytest.mark.parametrize("with_spa", [False, True])
@pytest.mark.parametrize("route_type", [Route, APIRoute])
@pytest.mark.parametrize("path", ["/api/docs", "/api/openapi.json", "/api/unexpected"])
def test_write_inventory_rejects_unprotected_real_app_mutations(
    real_write_app, route_type, path
) -> None:
    async def unprotected(request):
        return PlainTextResponse("mutation only")

    assert assert_real_write_inventory(real_write_app) == set(REAL_WRITES)
    real_write_app.routes.append(route_type(path, unprotected, methods=["POST"]))

    assert http_write_inventory(real_write_app.routes) == {
        *REAL_WRITES,
        ("POST", path),
    }
    # Estes caminhos documentais são tolerados pelo verificador de política;
    # ainda assim a mesma validação CA1 da matriz deve reprovar a oitava escrita.
    expected_problems = [] if path != "/api/unexpected" else [f"sem política: {path}"]
    assert policy_problems(real_write_app.routes) == expected_problems
    assert (path, "POST", "http") not in policy_by_route(real_write_app.routes)
    with pytest.raises(AssertionError, match="inventário CA1"):
        assert_real_write_inventory(real_write_app)


@pytest.mark.parametrize("with_spa", [False, True])
@pytest.mark.parametrize("invalid_policy", ["metadata", "dependency"])
def test_write_inventory_includes_routes_with_invalid_policy(
    real_write_app, invalid_policy
) -> None:
    def misconfigured():
        return {"ok": True}

    misconfigured.access_policy = (  # type: ignore[attr-defined]
        "PUBLIC" if invalid_policy == "metadata" else AccessPolicy.AUCTIONEER
    )
    real_write_app.add_api_route(
        "/api/misconfigured",
        misconfigured,
        methods=["POST"],
        dependencies=[Depends(require_user)],
    )

    assert http_write_inventory(real_write_app.routes) == {
        *REAL_WRITES,
        ("POST", "/api/misconfigured"),
    }
    problem = (
        "sem política"
        if invalid_policy == "metadata"
        else "política AUCTIONEER sem a dependência"
    )
    assert policy_problems(real_write_app.routes) == [f"{problem}: /api/misconfigured"]
    assert ("/api/misconfigured", "POST", "http") not in policy_by_route(
        real_write_app.routes
    )
    with pytest.raises(AssertionError, match="inventário CA1"):
        assert_real_write_inventory(real_write_app)


@pytest.mark.parametrize("route_type", [Route, APIRoute])
def test_write_inventory_keeps_all_declared_write_methods(route_type) -> None:
    async def handler(request):
        return PlainTextResponse("ok")

    route = route_type(
        "/api/multiple", handler, methods=[*WRITE_METHODS, "GET", "HEAD", "OPTIONS"]
    )
    assert http_write_inventory([route]) == {
        (method, "/api/multiple") for method in WRITE_METHODS
    }


@pytest.mark.parametrize("route_type", [Route, APIRoute])
def test_write_inventory_ignores_only_safe_http_methods(route_type) -> None:
    async def handler(request):
        return PlainTextResponse("ok")

    assert (
        http_write_inventory(
            [route_type("/safe", handler, methods=["GET", "HEAD", "OPTIONS", "TRACE"])]
        )
        == set()
    )
    with pytest.raises(ValueError, match="método HTTP não suportado: CONNECT"):
        http_write_inventory([route_type("/tunnel", handler, methods=["CONNECT"])])


@pytest.mark.parametrize("route_type", [WebSocketRoute, APIWebSocketRoute])
def test_write_inventory_ignores_known_websockets(route_type) -> None:
    async def socket(websocket):
        await websocket.close()

    assert http_write_inventory([route_type("/ws/room", socket)]) == set()


def test_write_inventory_recurses_through_mounts_with_their_prefixes() -> None:
    async def handler(request):
        return PlainTextResponse("ok")

    routes = [
        Mount(
            "/api",
            routes=[
                Mount("/nested", routes=[Route("/write", handler, methods=["PATCH"])])
            ],
        )
    ]
    assert http_write_inventory(routes) == {("PATCH", "/api/nested/write")}


def test_write_inventory_rejects_uninspectable_mounts() -> None:
    with pytest.raises(ValueError, match="mount sem rotas inspecionáveis: /api/opaque"):
        http_write_inventory([Mount("/api/opaque", app=PlainTextResponse("ok"))])


@pytest.mark.parametrize("declared_methods", [None, []])
def test_write_inventory_rejects_http_routes_without_declared_methods(
    declared_methods,
) -> None:
    class OpaqueApp:
        async def __call__(self, scope, receive, send):
            await PlainTextResponse("ok")(scope, receive, send)

    with pytest.raises(ValueError, match="rota HTTP sem métodos inspecionáveis"):
        http_write_inventory(
            [Route("/api/opaque", OpaqueApp(), methods=declared_methods)]
        )


def test_write_inventory_rejects_unknown_route_types() -> None:
    unknown = SimpleNamespace(path="/api/unknown", methods={"POST"})
    with pytest.raises(ValueError, match="tipo de rota não suportado: SimpleNamespace"):
        http_write_inventory([unknown])


@pytest.mark.parametrize("mounted", [False, True])
def test_write_inventory_rejects_duplicate_method_and_path(mounted) -> None:
    async def handler(request):
        return PlainTextResponse("ok")

    first = Route("/api/twin", handler, methods=["POST"])
    second = (
        Mount("/api", routes=[APIRoute("/twin", handler, methods=["POST"])])
        if mounted
        else APIRoute("/api/twin", handler, methods=["POST"])
    )
    with pytest.raises(ValueError, match="escrita duplicada no inventário"):
        http_write_inventory([first, second])


@pytest.mark.parametrize("with_spa", [False, True])
@pytest.mark.parametrize("method,path", REAL_WRITES)
@pytest.mark.parametrize(
    "origin,content_type,status,code",
    [
        ("https://evil.example", "application/json", 403, "csrf_origin_mismatch"),
        (ALLOWED_ORIGIN, None, 415, "unsupported_media_type"),
        (ALLOWED_ORIGIN, "text/plain", 415, "unsupported_media_type"),
    ],
    ids=["foreign-origin", "missing-content-type", "non-json-content-type"],
)
def test_every_real_write_is_refused_before_route_dispatch(
    real_write_app, monkeypatch, method, path, origin, content_type, status, code
) -> None:
    app = real_write_app
    registered = assert_real_write_inventory(app)
    assert policy_problems(app.routes) == []
    policy_writes = {
        (verb, route_path)
        for route_path, verb, kind in policy_by_route(app.routes)
        if kind == "http" and verb in WRITE_METHODS
    }
    assert policy_writes == registered

    reached = []

    async def dispatch_probe(scope, receive, send):
        reached.append(scope["path"])
        raise AssertionError("real route dispatch reached")

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == path
        and method in (getattr(route, "methods", None) or ())
    )
    # Antes de dependências/handler: se não há despacho, não há banco, AIC ou
    # alteração de sessão. Os controles transacionais existentes são preservados.
    monkeypatch.setattr(route, "app", dispatch_probe)
    url = path.replace("{lot_id}", "00000000-0000-4000-8000-000000000001")
    client = TestClient(app, base_url=ALLOWED_ORIGIN)
    headers = {"Origin": origin}
    if content_type is not None:
        headers["Content-Type"] = content_type
    response = client.request(method, url, headers=headers, content=b"{}")
    assert response.request.headers.get("content-type") == content_type
    assert_refused(response, status, code)
    assert reached == []
    assert "set-cookie" not in response.headers
    assert not any(h.startswith("access-control-") for h in response.headers)

    # Controle positivo: o mesmo caminho/método realmente alcança a sentinela
    # com headers válidos; uma rota inexistente não pode produzir essa prova.
    with pytest.raises(AssertionError, match="real route dispatch reached"):
        client.request(method, url, headers=JSON_HEADERS, content=b"{}")
    assert reached == [url]


def test_structural_check_catches_plain_routes_and_mounts(monkeypatch) -> None:
    app, _ = build_app(monkeypatch)

    def handler(request):
        return PlainTextResponse("ok")

    app.add_route("/fora", handler, methods=["POST"])
    app.mount("/montado", app=PlainTextResponse("ok"))
    assert unguarded_write_surfaces(app) == ["/fora", "/montado"]


# --- WebSocket técnico intacto ---


def test_websocket_policy_is_not_changed_by_the_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _ = build_app(monkeypatch)  # APP_ORIGIN https://casa.example, Host testserver
    client = TestClient(app)
    lot = "00000000-0000-4000-8000-000000000001"
    reads: list[object] = []

    def read(identifier: object) -> PublicBidRoomResponse:
        reads.append(identifier)
        return PublicBidRoomResponse(
            as_of=datetime.now(UTC),
            phase="live",
            ends_at=datetime.now(UTC),
            current_bid_cents=None,
            minimum_next_bid_cents=10000,
            bid_count=0,
            bids=[],
            settlement_status="pending",
            settlement=None,
        )

    # The lot exists for the read, so the refusal below can only come from Origin; the
    # HTTP write guard itself leaves the WebSocket to the public room policy.
    monkeypatch.setattr(lot_room, "read_room", read)
    with client.websocket_connect(
        f"/ws/lots/{lot}", headers={"origin": "https://casa.example"}
    ) as accepted:
        assert accepted.receive_json()["type"] == "room_snapshot"
    assert len(reads) == 1
    reads.clear()
    with pytest.raises(WebSocketDisconnect) as rejected:
        with client.websocket_connect(
            f"/ws/lots/{lot}", headers={"origin": "https://evil.example"}
        ):
            pass
    assert rejected.value.code == 1008
    assert reads == []


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        ({"path": "/api/x"}, "/api/x"),
        ({"path": "/api/x", "root_path": ""}, "/api/x"),
        ({"path": "/prefix/api/x", "root_path": "/prefix"}, "/api/x"),
        ({"path": "/prefix", "root_path": "/prefix"}, ""),
        # `/pre` não é prefixo por segmento de `/prefix/api`: nada é removido.
        ({"path": "/prefix/api/x", "root_path": "/pre"}, "/prefix/api/x"),
        # `root_path` que não é prefixo do caminho: nada é removido.
        ({"path": "/api/x", "root_path": "/prefix"}, "/api/x"),
        ({"path": "/api/x", "root_path": "/"}, "/api/x"),
        # `route_path` já presente vence `path` e `root_path`.
        (
            {"path": "/prefix/api/x", "root_path": "/prefix", "route_path": "/api/y"},
            "/api/y",
        ),
        ({"path": "/api/x", "route_path": "/outro"}, "/outro"),
    ],
)
def test_effective_path(scope: dict[str, str], expected: str) -> None:
    assert effective_path(scope) == expected  # type: ignore[arg-type]
