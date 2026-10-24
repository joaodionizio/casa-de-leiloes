"""Proteção HTTP das escritas da API: `Origin`/`Referer` e `Content-Type` (AD-29).

Um middleware ASGI puro (Story 2.1, P8): roda antes do roteamento, olha só os
cabeçalhos, nunca lê o corpo e não toca em WebSocket. Atua em POST, PUT, PATCH e
DELETE sob `/api`; GET, HEAD e OPTIONS passam sempre (AD-19). A origem aceita
vem da configuração (`APP_ORIGIN`), nunca de `Host`, `Forwarded` ou
`X-Forwarded-*`.
"""

from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.errors import (
    CSRF_ORIGIN_MISMATCH,
    CSRF_ORIGIN_MISSING,
    code_for_status,
    error_response,
)

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULT_PORTS = {"http": 80, "https": 443}

# (esquema, host, porta efetiva): o que se compara, nunca texto.
OriginTuple = tuple[str, str, int]


def parse_origin(value: str, *, allow_path: bool = False) -> OriginTuple | None:
    """Esquema, host e porta efetiva de uma origem, ou `None` se for inválida.

    Só `http`/`https`, com host e sem credenciais na URL. Para um `Origin`,
    caminho, query e fragmento têm de estar vazios; com `allow_path=True`
    (`Referer`) são ignorados. Nunca levanta.
    """
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in DEFAULT_PORTS or not hostname:
        return None
    if "@" in parts.netloc:
        return None
    if not allow_path and (parts.path or "?" in value or "#" in value):
        return None
    effective_port = port if port is not None else DEFAULT_PORTS[parts.scheme]
    return (parts.scheme, hostname.lower(), effective_port)


def format_origin(origin: OriginTuple) -> str:
    """Forma canônica `esquema://host[:porta]`, sem a porta padrão do esquema."""
    scheme, host, port = origin
    shown_host = f"[{host}]" if ":" in host else host
    if port == DEFAULT_PORTS[scheme]:
        return f"{scheme}://{shown_host}"
    return f"{scheme}://{shown_host}:{port}"


def origin_problem(headers: Headers, allowed: OriginTuple) -> str | None:
    """`None` se a origem é a esperada; senão o código do erro.

    `Origin` presente (mesmo vazio, `null` ou malformado) tem precedência e não
    é resgatado pelo `Referer`. Só sem `Origin` o `Referer` é considerado. Sem
    os dois, recusa. Mais de um valor do mesmo cabeçalho é ambíguo: recusa.
    """
    origins = headers.getlist("origin")
    if origins:
        if len(origins) == 1 and parse_origin(origins[0]) == allowed:
            return None
        return CSRF_ORIGIN_MISMATCH
    referers = headers.getlist("referer")
    if referers:
        if len(referers) == 1 and parse_origin(referers[0], allow_path=True) == allowed:
            return None
        return CSRF_ORIGIN_MISMATCH
    return CSRF_ORIGIN_MISSING


def is_json_content_type(headers: Headers) -> bool:
    """Exatamente um `Content-Type`, do tipo `application/json` (P7).

    Parâmetros como `charset` são aceitos; maiúsculas não importam; tipos
    `+json` não são aceitos.
    """
    values = headers.getlist("content-type")
    if len(values) != 1:
        return False
    return values[0].split(";", 1)[0].strip().lower() == "application/json"


def is_api_path(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


def effective_path(scope: Scope) -> str:
    """Caminho que o roteador enxerga, derivado só do `scope` ASGI.

    Se a proteção olhasse `scope["path"]` cru, `/<root_path>/api/...` chegaria à
    rota sem checagem. Usa `route_path` se já existir; senão `path` sem o
    `root_path`, e só quando ele é de fato um prefixo por segmento (`/pre` não é
    prefixo de `/prefix/api`). Sem `root_path`, devolve `path` como está.
    """
    route_path = scope.get("route_path")
    if isinstance(route_path, str):
        return route_path
    path: str = scope["path"]
    root_path: str = scope.get("root_path") or ""
    if not root_path or not path.startswith(root_path):
        return path
    rest = path[len(root_path) :]
    if rest == "" or rest.startswith("/"):
        return rest
    return path


class ApiWriteGuardMiddleware:
    """Recusa escritas em `/api` de outra origem (403) ou sem JSON (415).

    A origem vem antes do conteúdo e antes do roteamento: escrita estrangeira em
    rota inexistente recebe 403, não 404. Sem `try/except`: se esta camada falhar,
    a exceção segue para o handler de 500 do contrato.
    """

    def __init__(self, app: ASGIApp, allowed_origin: str) -> None:
        allowed = parse_origin(allowed_origin)
        if allowed is None:
            raise ValueError("allowed_origin must be scheme://host[:port]")
        self.app = app
        self.allowed = allowed

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] not in WRITE_METHODS
            or not is_api_path(effective_path(scope))
        ):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        problem = origin_problem(headers, self.allowed)
        if problem is not None:
            await error_response(403, problem)(scope, receive, send)
            return
        if not is_json_content_type(headers):
            response = error_response(415, code_for_status(415))
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
