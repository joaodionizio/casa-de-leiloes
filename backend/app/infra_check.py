"""Verificação técnica de infraestrutura do primeiro deploy (Story 1.4).

Prova, atrás do proxy real do Render, que um WebSocket `wss://` funciona na mesma
origem. Não lê nem grava nada, não usa o banco, não autentica e não identifica
ninguém. Fica fora do OpenAPI.

O cookie técnico da 1.4 saiu na Story 2.2 (o cookie real do JWT o substitui). O
WebSocket sai na Story 4.1 (sala ao vivo); até lá é uma rota pública na política
de acesso. A checagem de `Origin` daqui vale só para esta verificação; a política
da sala (Q2) continua em aberto para a 4.1.
"""

import asyncio
from urllib.parse import urlsplit

from fastapi import FastAPI, WebSocket

from app.access import AccessPolicy, websocket_route

WEBSOCKET_PATH = "/api/infra-check/ws"

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


def register_infra_check_routes(app: FastAPI) -> None:
    websocket_route(app, WEBSOCKET_PATH, policy=AccessPolicy.PUBLIC)(websocket_check)
