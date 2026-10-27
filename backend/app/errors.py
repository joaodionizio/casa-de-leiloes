"""Contrato único de erro da API (Story 2.1, P1, P2, P6, D1, D3, D5).

Todo erro HTTP da API sai como JSON plano: `status` (igual ao status HTTP),
`code` (técnico, estável, em inglês) e `message` (em português). `details` só
existe quando há algo útil a dizer (hoje, só no 422) e é omitido, nunca `null`.

A mensagem vem sempre do catálogo abaixo: o `detail` de uma `HTTPException` e o
texto de qualquer exceção nunca chegam ao cliente.
"""

from collections.abc import Mapping, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

CODE_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    422: "validation_error",
    500: "internal_error",
}

# Códigos de causa específica, usados pela proteção HTTP (app/csrf.py).
CSRF_ORIGIN_MISSING = "csrf_origin_missing"
CSRF_ORIGIN_MISMATCH = "csrf_origin_mismatch"
# Login recusado (Story 2.2): sai só da rota de login, com 401.
INVALID_CREDENTIALS = "invalid_credentials"
# Catálogo do museu fora do ar (Story 2.3): sai só das rotas do catálogo, com 503.
CATALOG_UNAVAILABLE = "catalog_unavailable"
# Obra que não pode virar lote (Story 2.4, P6): inexistente, fora do domínio público
# ou sem imagem. Um código só: o motivo interno vai ao log, nunca ao cliente.
ARTWORK_NOT_ELIGIBLE = "artwork_not_eligible"
# Depósito que levaria o total da carteira acima do teto técnico (Story 3.1, P3).
BALANCE_LIMIT_EXCEEDED = "balance_limit_exceeded"
# Recusas de negócio do lance (Story 3.4, CA2): os valores são os de `BidRefusal`
# (`app/bid_rules.py`); `errors.py` não importa módulo do app e um teste prova a
# igualdade dos conjuntos. Saem só do `POST /api/lots/{lot_id}/bids`, com 422.
LOT_NOT_STARTED = "lot_not_started"
LOT_ENDED = "lot_ended"
BELOW_MINIMUM = "below_minimum"
ALREADY_WINNING = "already_winning"
INSUFFICIENT_BALANCE = "insufficient_balance"
LOT_CANCELLED = "lot_cancelled"
# Histórico do lote que não se autentica (Story 3.4, P7): um código e uma mensagem só,
# para toda categoria de falha; o detalhe técnico vai ao log interno.
LOT_INTEGRITY_CONFLICT = "lot_integrity_conflict"
# Cancelamento recusado porque o lote já recebeu lance (Story 3.6): sai só do
# `POST /api/lots/{lot_id}/cancel`, com 422.
LOT_HAS_BIDS = "lot_has_bids"

MESSAGES = {
    "bad_request": "Requisição inválida.",
    "unauthorized": "Autenticação necessária.",
    "forbidden": "Acesso negado.",
    "not_found": "Recurso não encontrado.",
    "method_not_allowed": "Método não permitido para este recurso.",
    "conflict": "Conflito com o estado atual do recurso.",
    "unsupported_media_type": (
        "O corpo da requisição deve ser JSON (Content-Type: application/json)."
    ),
    "validation_error": "Os dados enviados são inválidos.",
    "internal_error": "Erro interno. Tente novamente mais tarde.",
    CSRF_ORIGIN_MISSING: "Não foi possível verificar a origem da requisição.",
    CSRF_ORIGIN_MISMATCH: "Origem da requisição não permitida.",
    INVALID_CREDENTIALS: "E-mail ou senha inválidos.",
    CATALOG_UNAVAILABLE: (
        "O catálogo do museu está indisponível no momento. "
        "Tente novamente em instantes."
    ),
    ARTWORK_NOT_ELIGIBLE: (
        "Esta obra não pode virar lote. Só são aceitas obras de domínio "
        "público com imagem no acervo do museu."
    ),
    BALANCE_LIMIT_EXCEEDED: "O depósito ultrapassaria o limite de saldo da carteira.",
    LOT_NOT_STARTED: "Este lote ainda não começou.",
    LOT_ENDED: "Este lote já foi encerrado.",
    BELOW_MINIMUM: "Seu lance está abaixo do mínimo para este lote.",
    ALREADY_WINNING: "Você já está ganhando este lote.",
    INSUFFICIENT_BALANCE: "Saldo disponível insuficiente para este lance.",
    LOT_CANCELLED: "Este lote foi cancelado.",
    # Neutra e reutilizável (Story 3.6, D5): serve ao lance e ao cancelamento.
    LOT_INTEGRITY_CONFLICT: (
        "Não foi possível concluir a operação porque a integridade do lote "
        "não pôde ser confirmada."
    ),
    LOT_HAS_BIDS: "Este lote não pode ser cancelado porque já recebeu lances.",
}


class ErrorDetail(BaseModel):
    """Só documentação (OpenAPI): o item de `details` do 422."""

    loc: list[str | int]
    type: str


class ErrorResponse(BaseModel):
    """Só documentação (OpenAPI): o envelope real de erro. Não é `response_model`
    de nenhuma rota; `details` é omitido em runtime quando vazio."""

    status: int
    code: str
    message: str
    details: list[ErrorDetail] | None = None


def error_responses(*statuses: int) -> dict[int | str, dict[str, object]]:
    """`responses=` de uma rota: documenta o envelope real em vez do padrão do
    FastAPI. Declarar o 422 também tira `HTTPValidationError` do schema."""
    return {status: {"model": ErrorResponse} for status in statuses}


def code_for_status(status: int) -> str:
    """Código do catálogo; fora dele: `bad_request` (4xx) ou `internal_error`."""
    code = CODE_BY_STATUS.get(status)
    if code is not None:
        return code
    return "bad_request" if 400 <= status < 500 else "internal_error"


def error_response(
    status: int,
    code: str,
    *,
    details: list[dict[str, object]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> Response:
    """Monta a resposta de erro; usada pelos handlers e pela camada de proteção."""
    if status < 200 or status in (204, 304):
        # Sem corpo permitido, como no handler padrão do FastAPI.
        return Response(status_code=status, headers=dict(headers or {}))
    content: dict[str, object] = {
        "status": status,
        "code": code,
        "message": MESSAGES[code],
    }
    if details:
        content["details"] = details
    return JSONResponse(content, status_code=status, headers=dict(headers or {}))


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    """404/405 do roteador e `HTTPException` de rotas; preserva `Allow` etc. (D3)."""
    return error_response(
        exc.status_code, code_for_status(exc.status_code), headers=exc.headers
    )


def sanitize_validation_errors(
    errors: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Só `loc` e `type`: sem `input`, `ctx`, `url` nem `msg` (em inglês) (D1)."""
    sanitized: list[dict[str, object]] = []
    for error in errors:
        location = error.get("loc", ())
        parts = location if isinstance(location, (list, tuple)) else (location,)
        sanitized.append(
            {
                "loc": [
                    part if isinstance(part, (str, int)) else str(part)
                    for part in parts
                ],
                "type": str(error.get("type", "")),
            }
        )
    return sanitized


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    """422 de entrada inválida, inclusive JSON malformado (`json_invalid`)."""
    return error_response(
        422,
        code_for_status(422),
        details=sanitize_validation_errors(exc.errors()),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """500 genérico. Não loga aqui: o `ServerErrorMiddleware` relança a exceção e o
    uvicorn registra o traceback uma vez, só no servidor (D5)."""
    return error_response(500, code_for_status(500))


def register_error_handlers(app: FastAPI) -> None:
    """Registra os três handlers, separados (P6)."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
