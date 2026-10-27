"""Toda rota declara exatamente uma política (Story 2.2, CAP-6, P9)."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route, WebSocketRoute
from starlette.staticfiles import StaticFiles

from app import access, main
from app.access import (
    POLICY_DEPENDENCIES,
    AccessPolicy,
    api_route,
    require_user,
)
from app.config import SpaSettings
from app.db import get_session
from app.main import create_app
from tests.access_policy import FRAMEWORK_ROUTES, policy_by_route, policy_problems
from tests.auth_support import HTTPS_ORIGIN

BACKEND_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = "<!doctype html><title>SPA de teste</title>"

EXPECTED_POLICIES = {
    ("/health", "GET", "http"): AccessPolicy.PUBLIC,
    ("/api/auth/login", "POST", "http"): AccessPolicy.PUBLIC,
    ("/api/auth/logout", "POST", "http"): AccessPolicy.PUBLIC,
    ("/api/me", "GET", "http"): AccessPolicy.AUTHENTICATED,
    ("/api/catalog/artworks", "GET", "http"): AccessPolicy.AUCTIONEER,
    ("/api/catalog/artworks/{external_id}", "GET", "http"): AccessPolicy.AUCTIONEER,
    # Mídia de obras em domínio público; a vitrine pública da 2.5 a usa também.
    ("/api/catalog/images/{image_id}", "GET", "http"): AccessPolicy.PUBLIC,
    # Story 2.4: criar lote e listar os próprios lotes são do leiloeiro.
    ("/api/lots", "POST", "http"): AccessPolicy.AUCTIONEER,
    ("/api/lots/mine", "GET", "http"): AccessPolicy.AUCTIONEER,
    # Story 2.5: a vitrine e a página do lote são públicas. `GET /api/lots` e
    # `POST /api/lots` dividem o caminho: o mapa precisa guardar os dois (D20).
    ("/api/lots", "GET", "http"): AccessPolicy.PUBLIC,
    ("/api/lots/{lot_id}", "GET", "http"): AccessPolicy.PUBLIC,
    # Story 3.1: a carteira é só do licitante (leitura e depósito).
    ("/api/wallet", "GET", "http"): AccessPolicy.BIDDER,
    ("/api/wallet/deposit", "POST", "http"): AccessPolicy.BIDDER,
    # Story 3.4: só o licitante dá lance; o leiloeiro não.
    ("/api/lots/{lot_id}/bids", "POST", "http"): AccessPolicy.BIDDER,
    ("/api/lots/{lot_id}/cancel", "POST", "http"): AccessPolicy.AUCTIONEER,
    # Story 3.5: a sala lê o histórico em público e a participação própria como BIDDER.
    ("/api/lots/{lot_id}/bids", "GET", "http"): AccessPolicy.PUBLIC,
    ("/api/lots/{lot_id}/bids/mine", "GET", "http"): AccessPolicy.BIDDER,
    ("/ws/lots/{lot_id}", None, "websocket"): AccessPolicy.PUBLIC,
}
SPA_POLICY = {
    ("/{full_path:path}", "GET", "http"): AccessPolicy.PUBLIC,
    ("/{full_path:path}", "HEAD", "http"): AccessPolicy.PUBLIC,
}


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(INDEX_HTML)
    return dist_dir


@pytest.fixture
def api_only_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.delenv("SPA_DIST_DIR", raising=False)
    monkeypatch.setattr(main, "get_spa_settings", lambda: SpaSettings(_env_file=None))
    return create_app(app_origin=HTTPS_ORIGIN)


def paths_of(app: FastAPI) -> list[str]:
    return [getattr(route, "path", "") for route in app.routes]


# --- a aplicação real ---


def test_real_app_without_spa_has_no_policy_problems(api_only_app: FastAPI) -> None:
    assert policy_problems(api_only_app.routes) == []
    assert policy_by_route(api_only_app.routes) == EXPECTED_POLICIES


def test_real_app_with_spa_has_no_policy_problems(dist: Path) -> None:
    app = create_app(dist, app_origin=HTTPS_ORIGIN)
    assert policy_problems(app.routes) == []
    assert policy_by_route(app.routes) == {**EXPECTED_POLICIES, **SPA_POLICY}


def test_only_the_framework_documentation_routes_are_allowlisted(
    api_only_app: FastAPI,
) -> None:
    assert FRAMEWORK_ROUTES == {"/api/docs", "/api/openapi.json"}
    assert FRAMEWORK_ROUTES <= set(paths_of(api_only_app))


def test_the_imported_module_app_main_is_clean_too() -> None:
    assert policy_problems(main.app.routes) == []


def test_there_is_no_signup_route(api_only_app: FastAPI) -> None:
    client = TestClient(api_only_app, base_url=HTTPS_ORIGIN)
    headers = {"Origin": HTTPS_ORIGIN, "Content-Type": "application/json"}
    for method, path in [
        ("post", "/api/auth/register"),
        ("post", "/api/users"),
        ("get", "/api/users"),
    ]:
        response = getattr(client, method)(path, headers=headers)
        assert response.status_code in (404, 405)
        assert response.headers["content-type"].startswith("application/json")
    assert not any(
        word in path.lower()
        for path in paths_of(api_only_app)
        for word in ("register", "signup", "users")
    )


# --- o meta-teste: o verificador reprova de verdade ---


def test_route_added_with_plain_decorator_is_reported(api_only_app: FastAPI) -> None:
    @api_only_app.get("/api/esquecida")
    def forgotten() -> dict[str, bool]:
        return {"ok": True}

    assert policy_problems(api_only_app.routes) == ["sem política: /api/esquecida"]


def test_websocket_added_with_plain_decorator_is_reported(
    api_only_app: FastAPI,
) -> None:
    @api_only_app.websocket("/api/ws-esquecido")
    async def forgotten_ws(websocket) -> None:
        await websocket.close()

    assert policy_problems(api_only_app.routes) == ["sem política: /api/ws-esquecido"]


def test_included_router_is_reported_as_unsupported(api_only_app: FastAPI) -> None:
    router = APIRouter()

    @router.get("/api/via-router")
    def via_router() -> dict[str, bool]:
        return {"ok": True}

    api_only_app.include_router(router)

    problems = policy_problems(api_only_app.routes)
    assert len(problems) == 1
    assert problems[0].startswith("tipo de rota não suportado: ")


def test_route_inside_a_mount_without_policy_is_reported_with_its_prefix(
    api_only_app: FastAPI,
) -> None:
    sub_app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @sub_app.get("/dentro")
    def inside() -> dict[str, bool]:
        return {"ok": True}

    api_only_app.mount("/sub", sub_app)

    assert policy_problems(api_only_app.routes) == ["sem política: /sub/dentro"]


def test_route_inside_a_mount_with_policy_passes(api_only_app: FastAPI) -> None:
    sub_app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @api_route(sub_app, "/dentro", methods=["GET"], policy=AccessPolicy.PUBLIC)
    def inside() -> dict[str, bool]:
        return {"ok": True}

    api_only_app.mount("/sub", sub_app)

    assert policy_problems(api_only_app.routes) == []
    assert policy_by_route(api_only_app.routes)[("/sub/dentro", "GET", "http")] == (
        AccessPolicy.PUBLIC
    )


def test_mount_without_inspectable_routes_is_reported(
    api_only_app: FastAPI, tmp_path: Path
) -> None:
    api_only_app.mount("/static", StaticFiles(directory=tmp_path))

    assert policy_problems(api_only_app.routes) == [
        "mount sem rotas inspecionáveis: /static"
    ]


def test_endpoint_whose_policy_is_not_an_access_policy_is_reported(
    api_only_app: FastAPI,
) -> None:
    def fake() -> dict[str, bool]:
        return {"ok": True}

    fake.access_policy = "PUBLIC"  # type: ignore[attr-defined]
    api_only_app.add_api_route("/api/fake", fake, methods=["GET"])

    assert policy_problems(api_only_app.routes) == ["sem política: /api/fake"]


# --- metadata reaproveitada sem a dependência da política (achado M1 do review) ---


def test_helper_routes_carry_their_policy_dependency(api_only_app: FastAPI) -> None:
    @api_route(
        api_only_app, "/api/admin", methods=["GET"], policy=AccessPolicy.AUCTIONEER
    )
    def admin() -> dict[str, bool]:
        return {"ok": True}

    assert policy_problems(api_only_app.routes) == []
    assert policy_by_route(api_only_app.routes)[("/api/admin", "GET", "http")] == (
        AccessPolicy.AUCTIONEER
    )


def test_room_websocket_passes_as_public(api_only_app: FastAPI) -> None:
    table = policy_by_route(api_only_app.routes)
    assert policy_problems(api_only_app.routes) == []
    assert table[("/ws/lots/{lot_id}", None, "websocket")] == AccessPolicy.PUBLIC


def test_stacked_plain_decorator_reusing_a_protected_endpoint_is_reported(
    api_only_app: FastAPI,
) -> None:
    @api_only_app.get("/api/leak")
    @api_route(
        api_only_app, "/api/admin", methods=["GET"], policy=AccessPolicy.AUCTIONEER
    )
    def admin() -> dict[str, bool]:
        return {"secret": True}

    assert policy_problems(api_only_app.routes) == [
        "política AUCTIONEER sem a dependência: /api/leak"
    ]
    table = policy_by_route(api_only_app.routes)
    assert table[("/api/admin", "GET", "http")] == AccessPolicy.AUCTIONEER
    assert ("/api/leak", "GET", "http") not in table
    # O verificador reprova a rota que de fato está aberta.
    api_only_app.dependency_overrides[get_session] = lambda: iter([object()])
    client = TestClient(api_only_app, base_url=HTTPS_ORIGIN)
    assert client.get("/api/admin").status_code == 401
    assert client.get("/api/leak").status_code == 200


def test_add_api_route_reusing_a_protected_endpoint_is_reported(
    api_only_app: FastAPI,
) -> None:
    @api_route(api_only_app, "/api/bids", methods=["GET"], policy=AccessPolicy.BIDDER)
    def bids() -> dict[str, bool]:
        return {"ok": True}

    api_only_app.add_api_route("/api/bids-copy", bids, methods=["GET"])

    assert policy_problems(api_only_app.routes) == [
        "política BIDDER sem a dependência: /api/bids-copy"
    ]
    assert ("/api/bids-copy", "GET", "http") not in policy_by_route(api_only_app.routes)


def test_reused_endpoint_with_a_different_dependency_is_reported(
    api_only_app: FastAPI,
) -> None:
    @api_route(
        api_only_app, "/api/admin", methods=["GET"], policy=AccessPolicy.AUCTIONEER
    )
    def admin() -> dict[str, bool]:
        return {"ok": True}

    # Autenticada, mas não por papel: não é a política declarada.
    api_only_app.add_api_route(
        "/api/admin-any-user",
        admin,
        methods=["GET"],
        dependencies=[Depends(require_user)],
    )

    assert policy_problems(api_only_app.routes) == [
        "política AUCTIONEER sem a dependência: /api/admin-any-user"
    ]


def test_plain_starlette_routes_with_policy_metadata_are_reported(
    api_only_app: FastAPI,
) -> None:
    async def page(request) -> None:
        return None

    async def socket(websocket) -> None:
        await websocket.close()

    page.access_policy = AccessPolicy.PUBLIC  # type: ignore[attr-defined]
    socket.access_policy = AccessPolicy.PUBLIC  # type: ignore[attr-defined]
    api_only_app.router.routes.append(Route("/api/pure", page))
    api_only_app.router.routes.append(WebSocketRoute("/api/pure-ws", socket))

    assert policy_problems(api_only_app.routes) == [
        "política PUBLIC sem a dependência: /api/pure",
        "política PUBLIC sem a dependência: /api/pure-ws",
    ]


# --- o mapa por (caminho, método, tipo) (Story 2.5, D20) ---


def test_same_path_with_two_methods_keeps_both_policies(api_only_app: FastAPI) -> None:
    @api_route(api_only_app, "/api/dual", methods=["GET"], policy=AccessPolicy.PUBLIC)
    def read_dual() -> dict[str, bool]:
        return {"ok": True}

    @api_route(
        api_only_app, "/api/dual", methods=["POST"], policy=AccessPolicy.AUCTIONEER
    )
    def write_dual() -> dict[str, bool]:
        return {"ok": True}

    table = policy_by_route(api_only_app.routes)
    assert table[("/api/dual", "GET", "http")] == AccessPolicy.PUBLIC
    assert table[("/api/dual", "POST", "http")] == AccessPolicy.AUCTIONEER
    assert policy_problems(api_only_app.routes) == []


def test_two_routes_with_the_same_path_and_method_fail_loudly(
    api_only_app: FastAPI,
) -> None:
    @api_route(api_only_app, "/api/twin", methods=["GET"], policy=AccessPolicy.PUBLIC)
    def first() -> dict[str, bool]:
        return {"ok": True}

    @api_route(
        api_only_app, "/api/twin", methods=["GET"], policy=AccessPolicy.AUCTIONEER
    )
    def second() -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(ValueError, match="rota duplicada"):
        policy_by_route(api_only_app.routes)


def test_a_route_with_two_methods_gets_one_entry_per_method(
    api_only_app: FastAPI,
) -> None:
    @api_route(
        api_only_app,
        "/api/both",
        methods=["GET", "HEAD"],
        policy=AccessPolicy.PUBLIC,
    )
    def both() -> dict[str, bool]:
        return {"ok": True}

    table = policy_by_route(api_only_app.routes)
    assert table[("/api/both", "GET", "http")] == AccessPolicy.PUBLIC
    assert table[("/api/both", "HEAD", "http")] == AccessPolicy.PUBLIC


def test_real_app_tells_apart_get_and_post_on_api_lots(api_only_app: FastAPI) -> None:
    table = policy_by_route(api_only_app.routes)
    assert table[("/api/lots", "GET", "http")] == AccessPolicy.PUBLIC
    assert table[("/api/lots", "POST", "http")] == AccessPolicy.AUCTIONEER
    assert table[("/api/lots/mine", "GET", "http")] == AccessPolicy.AUCTIONEER
    assert table[("/api/lots/{lot_id}", "GET", "http")] == AccessPolicy.PUBLIC


# --- o helper de registro ---


def test_endpoint_reused_with_another_policy_is_refused(api_only_app: FastAPI) -> None:
    def shared() -> dict[str, bool]:
        return {"ok": True}

    api_route(api_only_app, "/api/a", methods=["GET"], policy=AccessPolicy.PUBLIC)(
        shared
    )
    with pytest.raises(ValueError):
        api_route(
            api_only_app,
            "/api/b",
            methods=["GET"],
            policy=AccessPolicy.AUTHENTICATED,
        )(shared)


def test_public_route_with_a_protected_dependency_in_the_signature_is_refused(
    api_only_app: FastAPI,
) -> None:
    def mismatch(user=Depends(require_user)) -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(ValueError):
        api_route(api_only_app, "/api/x", methods=["GET"], policy=AccessPolicy.PUBLIC)(
            mismatch
        )
    assert "/api/x" not in paths_of(api_only_app)


def test_every_policy_has_exactly_one_dependency() -> None:
    assert set(POLICY_DEPENDENCIES) == set(AccessPolicy)
    assert len(set(POLICY_DEPENDENCIES.values())) == len(AccessPolicy)


def test_authentication_dependency_declared_twice_runs_once_per_request(
    api_only_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def counting_resolver(request, session):
        calls.append(1)
        return SimpleNamespace(role="BIDDER")

    monkeypatch.setattr(access, "resolve_session_user", counting_resolver)

    # `require_user` na política (pelo helper) e na assinatura do handler.
    @api_route(
        api_only_app, "/api/twice", methods=["GET"], policy=AccessPolicy.AUTHENTICATED
    )
    def twice(user=Depends(require_user)) -> dict[str, bool]:
        return {"ok": True}

    api_only_app.dependency_overrides[get_session] = lambda: iter([object()])
    response = TestClient(api_only_app, base_url=HTTPS_ORIGIN).get("/api/twice")

    assert response.status_code == 200
    assert len(calls) == 1


# --- nenhuma API interna ou não documentada ---


def _imports(path: Path) -> list[tuple[str, str]]:
    """(módulo, nome) de cada import do arquivo; `import x` vira (x, "")."""
    found: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.extend((node.module, alias.name) for alias in node.names)
        elif isinstance(node, ast.Import):
            found.extend((alias.name, "") for alias in node.names)
    return found


def test_no_private_or_undocumented_framework_import_in_app_or_tests() -> None:
    banned_names = {"iter_route_contexts", "_IncludedRouter"}
    offenders: list[str] = []
    for folder in ("app", "tests"):
        for path in (BACKEND_DIR / folder).rglob("*.py"):
            for module, name in _imports(path):
                segments = module.split(".")
                in_framework = segments[0] in ("fastapi", "starlette")
                private = any(s.startswith("_") for s in segments) or name.startswith(
                    "_"
                )
                if name in banned_names or (in_framework and private):
                    offenders.append(f"{path.name}: {module} {name}".strip())
    assert offenders == []
