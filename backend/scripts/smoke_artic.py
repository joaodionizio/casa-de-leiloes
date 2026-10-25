"""Smoke test manual da integração real com a AIC (Story 2.3, AD-23, Q7).

    cd backend && uv run python -m scripts.smoke_artic

Fora do `verify` e do `pytest`: fala com a internet. Sem banco, login, segredo nem
escrita; importa só `app.artic` e `app.catalog`. Cobre os seis itens do AD-23 e
imprime `PASS|FAIL <n> <item> — <detalhe>`. Sai com 0 só se todos passarem; uma
falha não interrompe os itens seguintes. São cerca de 8 requisições (limite da AIC:
60 por minuto por IP), cada uma com o timeout padrão do cliente.
"""

import sys
from collections.abc import Callable
from typing import Any

import httpx

from app.artic import (
    AIC_USER_AGENT,
    ARTIC_API_BASE_URL,
    ARTIC_IIIF_BASE_URL,
    ARTIC_WEBSITE_BASE_URL,
    DEFAULT_TIMEOUT,
    DETAIL_FIELDS,
    JPEG_MAGIC,
    USER_AGENT,
    ArticClient,
    CatalogUnavailable,
    iiif_image_url,
)
from app.catalog import LookupStatus, get_artwork, search_artworks

SEARCH_TERM = "monet"
NO_MATCH_TERM = "qxzvkwjq"
KNOWN_PUBLIC_DOMAIN_ID = 27992
KNOWN_NOT_PUBLIC_DOMAIN_ID = 129884
UNREACHABLE_BASE_URL = "http://127.0.0.1:9"  # porta "discard": conexão recusada

HEADERS = {
    "User-Agent": USER_AGENT,
    "AIC-User-Agent": AIC_USER_AGENT,
    "Accept": "application/json",
}


class Failed(Exception):
    """Item reprovado; a mensagem é o detalhe curto impresso."""


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise Failed(detail)


def raw_detail() -> dict[str, Any]:
    """`GET` cru do detalhe conhecido, para `config` e para os campos usados."""
    response = httpx.get(
        f"{ARTIC_API_BASE_URL}/artworks/{KNOWN_PUBLIC_DOMAIN_ID}",
        params={"fields": DETAIL_FIELDS},
        headers=HEADERS,
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=False,
    )
    require(
        response.status_code == 200, f"detalhe cru respondeu {response.status_code}"
    )
    body = response.json()
    require(isinstance(body, dict), "detalhe cru não é um objeto JSON")
    return body


def check_search(client: ArticClient, state: dict[str, Any]) -> str:
    found = search_artworks(client, SEARCH_TERM)
    require(len(found.items) >= 1, f"'{SEARCH_TERM}' devolveu 0 obras")
    empty = search_artworks(client, NO_MATCH_TERM)
    require(len(empty.items) == 0, f"'{NO_MATCH_TERM}' devolveu {len(empty.items)}")
    return f"'{SEARCH_TERM}' → {len(found.items)} obras; '{NO_MATCH_TERM}' → 0"


def check_detail(client: ArticClient, state: dict[str, Any]) -> str:
    lookup = get_artwork(client, KNOWN_PUBLIC_DOMAIN_ID)
    require(lookup.status == LookupStatus.FOUND, f"status {lookup.status}")
    artwork = lookup.artwork
    require(artwork is not None, "FOUND sem obra")
    assert artwork is not None
    require(bool(artwork.title), "título vazio")
    require(bool(artwork.artist_display), "artista vazio")
    state["image_id"] = artwork.image_id
    return f"{KNOWN_PUBLIC_DOMAIN_ID}: {artwork.title}"


def check_public_domain(client: ArticClient, state: dict[str, Any]) -> str:
    raw_items = client.search(SEARCH_TERM)
    require(len(raw_items) >= 1, "busca sem itens para conferir")
    not_pd = [a.external_id for a in raw_items if a.is_public_domain is not True]
    require(not not_pd, f"itens fora do domínio público na resposta: {not_pd}")
    negative = get_artwork(client, KNOWN_NOT_PUBLIC_DOMAIN_ID)
    require(
        negative.status == LookupStatus.NOT_PUBLIC_DOMAIN,
        f"controle negativo {KNOWN_NOT_PUBLIC_DOMAIN_ID} deu {negative.status}",
    )
    return (
        f"{len(raw_items)} itens com is_public_domain=true; "
        f"{KNOWN_NOT_PUBLIC_DOMAIN_ID} → NOT_PUBLIC_DOMAIN"
    )


def check_iiif(client: ArticClient, state: dict[str, Any]) -> str:
    image_id = state.get("image_id")
    require(image_id is not None, "sem image_id (o item 2 falhou)")
    # O IIIF direto, como o servidor o chama: com a identificação e sem Referer.
    image_url = iiif_image_url(image_id)
    with httpx.stream(
        "GET",
        image_url,
        headers={"User-Agent": USER_AGENT, "AIC-User-Agent": AIC_USER_AGENT},
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=False,
    ) as response:
        content_type = response.headers.get("content-type", "")
        first_chunk = next(response.iter_bytes(), b"")  # bytes descartados
        require(response.status_code == 200, f"IIIF respondeu {response.status_code}")
        require(content_type.startswith("image/jpeg"), f"content-type {content_type!r}")
        require(len(first_chunk) > 0, "IIIF sem corpo")
    # O mesmo caminho do proxy same-origin (`GET /api/catalog/images/{image_id}`).
    data = client.get_image(image_id)
    require(data is not None, "get_image devolveu None (404) para uma obra válida")
    assert data is not None
    require(data.startswith(JPEG_MAGIC), "get_image não devolveu um JPEG")
    config = state["raw_detail"].get("config", {})
    iiif = str(config.get("iiif_url", ""))
    website = str(config.get("website_url", ""))
    require(
        iiif.rstrip("/") == ARTIC_IIIF_BASE_URL.rstrip("/"),
        f"config.iiif_url mudou: {iiif!r}",
    )
    require(website == ARTIC_WEBSITE_BASE_URL, f"config.website_url mudou: {website!r}")
    return (
        f"200 {content_type}; get_image → {len(data)} bytes JPEG; "
        "config.iiif_url e website_url iguais às constantes"
    )


def check_fields(client: ArticClient, state: dict[str, Any]) -> str:
    data = state["raw_detail"].get("data")
    require(isinstance(data, dict), "detalhe cru sem 'data'")
    names = DETAIL_FIELDS.split(",")
    missing = [name for name in names if name not in data]
    require(not missing, f"campos ausentes na resposta: {missing}")
    nulls = [name for name in names if data[name] is None]
    return f"{len(names)} campos presentes; null neste detalhe: {nulls or 'nenhum'}"


def check_unavailable(client: ArticClient, state: dict[str, Any]) -> str:
    # Falha local e determinística: nada tenta derrubar a AIC.
    down = ArticClient(api_base_url=UNREACHABLE_BASE_URL)
    try:
        down.search(SEARCH_TERM)
    except CatalogUnavailable as error:
        require(error.reason == "connect", f"motivo {error.reason!r}, esperado connect")
        return f"{UNREACHABLE_BASE_URL} → CatalogUnavailable(connect)"
    raise Failed("não levantou CatalogUnavailable")


CHECKS: list[tuple[str, Callable[[ArticClient, dict[str, Any]], str]]] = [
    ("Busca real", check_search),
    ("Detalhe real", check_detail),
    ("is_public_domain=true", check_public_domain),
    ("Imagem IIIF", check_iiif),
    ("Campos usados", check_fields),
    ("API indisponível (simulada)", check_unavailable),
]


def main() -> int:
    client = ArticClient()
    state: dict[str, Any] = {}
    try:
        state["raw_detail"] = raw_detail()
    except Exception as error:
        state["raw_detail"] = {}
        state["raw_detail_error"] = f"{type(error).__name__}: {error}"

    passed = 0
    for number, (name, check) in enumerate(CHECKS, start=1):
        try:
            if not state["raw_detail"] and name in ("Imagem IIIF", "Campos usados"):
                raise Failed(state.get("raw_detail_error", "detalhe cru indisponível"))
            detail = check(client, state)
            print(f"PASS {number} {name} — {detail}")
            passed += 1
        except Failed as error:
            print(f"FAIL {number} {name} — {error}")
        except Exception as error:
            print(f"FAIL {number} {name} — {type(error).__name__}: {error}")

    print(f"{passed}/{len(CHECKS)} PASS")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
