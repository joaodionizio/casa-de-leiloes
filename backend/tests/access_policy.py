"""Verificador da política de acesso (Story 2.2, P9).

Percorre `app.routes` recursivamente usando só estruturas públicas do FastAPI e do
Starlette: `APIRoute`, `APIWebSocketRoute`, `Route`, `WebSocketRoute`, `Mount`,
`.path`, `.endpoint`, `.dependencies` e `Mount.routes`. Nenhum tipo privado é
importado: um tipo de rota que o verificador não conhece (como o que
`include_router` deixa em `app.routes`) é reportado em vez de passar em silêncio.

A metadata do endpoint diz a política declarada; ela só vale se a própria rota
carregar a dependência dessa política. Um endpoint marcado e reaproveitado fora do
helper (`@app.get` empilhado, `app.add_api_route`) chega sem a dependência e
reprova, em vez de aparecer como protegido.
"""

from collections.abc import Sequence

from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.routing import Mount, Route, WebSocketRoute

from app.access import POLICY_DEPENDENCIES, AccessPolicy

# Rotas do próprio framework, sem endpoint nosso: a única exceção à regra.
FRAMEWORK_ROUTES = frozenset({"/api/docs", "/api/openapi.json"})

API_ROUTE_TYPES = (APIRoute, APIWebSocketRoute)
HTTP_ROUTE_TYPES = (APIRoute, Route)
WEBSOCKET_ROUTE_TYPES = (APIWebSocketRoute, WebSocketRoute)


def _declared_policy(route: object) -> AccessPolicy | None:
    policy = getattr(getattr(route, "endpoint", None), "access_policy", None)
    return policy if isinstance(policy, AccessPolicy) else None


def _applies_policy(route: object, policy: AccessPolicy) -> bool:
    """A rota carrega a dependência da política declarada. `Route` e
    `WebSocketRoute` puras não carregam dependências: nunca aplicam a política."""
    if not isinstance(route, API_ROUTE_TYPES):
        return False
    expected = POLICY_DEPENDENCIES[policy]
    return any(
        getattr(dependency, "dependency", None) is expected
        for dependency in route.dependencies
    )


def policy_problems(routes: Sequence[object], prefix: str = "") -> list[str]:
    """Problemas encontrados; lista vazia significa que toda rota tem política."""
    problems: list[str] = []
    for route in routes:
        if isinstance(route, Mount):
            inner = list(route.routes)
            if not inner:
                problems.append(f"mount sem rotas inspecionáveis: {prefix}{route.path}")
            else:
                problems.extend(policy_problems(inner, prefix + route.path))
        elif isinstance(route, HTTP_ROUTE_TYPES + WEBSOCKET_ROUTE_TYPES):
            full_path = prefix + route.path
            policy = _declared_policy(route)
            if policy is None:
                if full_path not in FRAMEWORK_ROUTES:
                    problems.append(f"sem política: {full_path}")
            elif not _applies_policy(route, policy):
                problems.append(f"política {policy} sem a dependência: {full_path}")
        else:
            problems.append(f"tipo de rota não suportado: {type(route).__name__}")
    return problems


def policy_by_route(
    routes: Sequence[object], prefix: str = ""
) -> dict[tuple[str, str], AccessPolicy]:
    """`(caminho, "http" | "websocket") -> política` das rotas que a declaram e
    de fato a aplicam; uma rota sem a dependência fica de fora."""
    table: dict[tuple[str, str], AccessPolicy] = {}
    for route in routes:
        if isinstance(route, Mount):
            table.update(policy_by_route(list(route.routes), prefix + route.path))
        elif isinstance(route, HTTP_ROUTE_TYPES + WEBSOCKET_ROUTE_TYPES):
            policy = _declared_policy(route)
            if policy is not None and _applies_policy(route, policy):
                kind = "http" if isinstance(route, HTTP_ROUTE_TYPES) else "websocket"
                table[(prefix + route.path, kind)] = policy
    return table
