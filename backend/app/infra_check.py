"""Verificações técnicas de infraestrutura para o primeiro deploy (Story 1.4).

Provam, atrás do proxy real do Render, que um WebSocket `wss://` e um cookie
`__Host-` funcionam na mesma origem. Não leem nem gravam nada, não usam o banco,
não autenticam e não identificam ninguém. Ficam fora do OpenAPI.

Destino: o cookie sai na Story 2.2 (cookie real do JWT) e o WebSocket sai na
Story 4.1 (sala ao vivo). Até lá, a 2.2 os classifica como rotas públicas na
política de acesso. A checagem de `Origin` daqui vale só para esta verificação;
a política da sala (Q2) continua em aberto para a 4.1.
"""

import asyncio
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response, WebSocket

router = APIRouter(prefix="/api/infra-check", include_in_schema=False)

COOKIE_NAME = "__Host-infra_check"
COOKIE_VALUE = "1"
COOKIE_MAX_AGE_SECONDS = 600

MAX_MESSAGE_BYTES = 64
RECEIVE_TIMEOUT_SECONDS = 10.0

NORMAL_CLOSURE = 1000
UNSUPPORTED_DATA = 1003
POLICY_VIOLATION = 1008
MESSAGE_TOO_BIG = 1009


def origin_host(origin: str) -> str | None:
    """Devolve o `host[:porta]` em minúsculas de um `Origin` válido, ou `None`.

    Válido é `http` ou `https` com host, sem caminho, query nem fragmento. Nunca
    levanta: qualquer valor inválido, inclusive `ValueError` do `urlsplit`, vira
    `None`.
    """
    try:
        parts = urlsplit(origin)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    if parts.path or parts.query or parts.fragment:
        return None
    return parts.netloc.lower()


def is_allowed_origin(origin: str | None, host: str | None) -> bool:
    """Sem `Origin` (cliente que não é navegador) aceita; com `Origin`, só o mesmo host.

    Compara apenas o host, não o esquema: atrás do proxy a aplicação pode ver
    `http` mesmo com o navegador em `https` (P8).
    """
    if origin is None:
        return True
    if host is None:
        return False
    return origin_host(origin) == host.lower()


@router.get("/cookie")
def cookie_check(request: Request, response: Response) -> dict[str, bool]:
    """Devolve se o cookie voltou e o emite de novo. Sem efeito no servidor."""
    received = request.cookies.get(COOKIE_NAME) == COOKIE_VALUE
    response.set_cookie(
        COOKIE_NAME,
        COOKIE_VALUE,
        max_age=COOKIE_MAX_AGE_SECONDS,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"cookie_received": received}


@router.websocket("/ws")
async def websocket_check(websocket: WebSocket) -> None:
    """Uma troca e fecha: recebe um texto curto e devolve `echo:<texto>`."""
    if not is_allowed_origin(
        websocket.headers.get("origin"), websocket.headers.get("host")
    ):
        await websocket.close(code=POLICY_VIOLATION)
        return
    await websocket.accept()

    try:
        message = await asyncio.wait_for(websocket.receive(), RECEIVE_TIMEOUT_SECONDS)
    except TimeoutError:
        await websocket.close(code=POLICY_VIOLATION)
        return
    if message["type"] == "websocket.disconnect":
        return

    text = message.get("text")
    if text is None:
        await websocket.close(code=UNSUPPORTED_DATA)
        return
    if len(text.encode()) > MAX_MESSAGE_BYTES:
        await websocket.close(code=MESSAGE_TOO_BIG)
        return

    await websocket.send_text(f"echo:{text}")
    await websocket.close(code=NORMAL_CLOSURE)
