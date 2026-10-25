"""Busca e detalhe de obras do Art Institute of Chicago (Story 2.3, AD-12, AD-23).

Leitura pura e ao vivo do catálogo externo: nada é gravado e o endpoint não conhece
o JSON da AIC, só os modelos abaixo. A elegibilidade (domínio público e imagem
válida, AD-23) é reconferida aqui em cada item, além do filtro da consulta. A 2.4
reusa `get_artwork()` sem reimplementar o parsing.

A imagem sai por um proxy same-origin (`GET /api/catalog/images/{image_id}`): o
navegador não consegue chamar o IIIF da AIC (403 do Cloudflare, teste manual de
24/10/2026). O proxy aceita só `image_id` validado, não guarda bytes e não é um proxy
genérico (revisão do AD-22).
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, FastAPI, Path, Query, Request, Response
from pydantic import BaseModel, StringConstraints

from app.access import NO_STORE, AccessPolicy, api_route
from app.artic import (
    ARTIC_WEBSITE_BASE_URL,
    IMAGE_ID_PATTERN,
    ArticArtwork,
    ArticClient,
    CatalogUnavailable,
)
from app.errors import CATALOG_UNAVAILABLE, error_response, error_responses

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")

MAX_EXTERNAL_ID = 2_147_483_647


class ArtworkSummary(BaseModel):
    external_id: int
    title: str | None
    artist_display: str | None
    date_display: str | None
    image_id: str
    image_url: str


class ArtworkDetail(ArtworkSummary):
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    credit_line: str | None
    source_url: str


class ArtworkSearchResponse(BaseModel):
    items: list[ArtworkSummary]


class LookupStatus(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    NOT_PUBLIC_DOMAIN = "NOT_PUBLIC_DOMAIN"
    NO_IMAGE = "NO_IMAGE"


@dataclass(frozen=True)
class ArtworkLookup:
    """O motivo é interno: a rota colapsa todo não-`FOUND` em 404 (P4)."""

    status: LookupStatus
    artwork: ArtworkDetail | None = None


IMAGE_PATH_PREFIX = "/api/catalog/images/"


def image_url_for(image_id: str) -> str:
    """URL same-origin da imagem (a que o navegador usa); recusa `image_id` fora do
    regex. O IIIF em si só é chamado pelo servidor (`ArticClient.get_image`)."""
    if not IMAGE_ID_PATTERN.fullmatch(image_id):
        raise ValueError("image_id is not a valid IIIF identifier")
    return f"{IMAGE_PATH_PREFIX}{image_id}"


def is_eligible(artwork: ArticArtwork) -> bool:
    """AD-23: domínio público confirmado (`True` exato) e `image_id` válido."""
    return artwork.is_public_domain is True and artwork.image_id is not None


def _summary(artwork: ArticArtwork, image_id: str) -> ArtworkSummary:
    return ArtworkSummary(
        external_id=artwork.external_id,
        title=artwork.title,
        artist_display=artwork.artist_display,
        date_display=artwork.date_display,
        image_id=image_id,
        image_url=image_url_for(image_id),
    )


def _detail(artwork: ArticArtwork, image_id: str) -> ArtworkDetail:
    return ArtworkDetail(
        **_summary(artwork, image_id).model_dump(),
        medium_display=artwork.medium_display,
        dimensions=artwork.dimensions,
        department_title=artwork.department_title,
        artwork_type_title=artwork.artwork_type_title,
        credit_line=artwork.credit_line,
        source_url=f"{ARTIC_WEBSITE_BASE_URL}/artworks/{artwork.external_id}",
    )


def search_artworks(client: ArticClient, term: str) -> ArtworkSearchResponse:
    """Só obras elegíveis, na ordem da AIC. `CatalogUnavailable` atravessa."""
    items: list[ArtworkSummary] = []
    for artwork in client.search(term):
        if artwork.image_id is not None and is_eligible(artwork):
            items.append(_summary(artwork, artwork.image_id))
    return ArtworkSearchResponse(items=items)


def get_artwork(client: ArticClient, external_id: int) -> ArtworkLookup:
    """`CatalogUnavailable` atravessa; o 404 real da AIC é `NOT_FOUND`."""
    artwork = client.get_artwork(external_id)
    if artwork is None:
        return ArtworkLookup(LookupStatus.NOT_FOUND)
    if artwork.is_public_domain is not True:
        return ArtworkLookup(LookupStatus.NOT_PUBLIC_DOMAIN)
    if artwork.image_id is None:
        return ArtworkLookup(LookupStatus.NO_IMAGE)
    return ArtworkLookup(LookupStatus.FOUND, _detail(artwork, artwork.image_id))


def get_artic_client(request: Request) -> ArticClient:
    client: ArticClient = request.app.state.artic_client
    return client


def _unavailable(operation: str, error: CatalogUnavailable) -> Response:
    # Só a categoria vai ao log: nunca o termo, a URL, o corpo nem o usuário.
    logger.warning(
        "artic request failed: operation=%s reason=%s", operation, error.reason
    )
    return error_response(503, CATALOG_UNAVAILABLE, headers=NO_STORE)


SearchTerm = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


def register_catalog_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/catalog/artworks",
        methods=["GET"],
        policy=AccessPolicy.AUCTIONEER,
        response_model=ArtworkSearchResponse,
        responses=error_responses(401, 403, 422, 503),
    )
    def search(
        response: Response,
        q: Annotated[SearchTerm, Query()],
        client: ArticClient = Depends(get_artic_client),
    ) -> ArtworkSearchResponse | Response:
        try:
            result = search_artworks(client, q)
        except CatalogUnavailable as error:
            return _unavailable("search", error)
        response.headers["Cache-Control"] = "no-store"
        return result

    @api_route(
        app,
        "/api/catalog/artworks/{external_id}",
        methods=["GET"],
        policy=AccessPolicy.AUCTIONEER,
        response_model=ArtworkDetail,
        responses=error_responses(401, 403, 404, 422, 503),
    )
    def artwork_detail(
        response: Response,
        external_id: Annotated[int, Path(gt=0, le=MAX_EXTERNAL_ID)],
        client: ArticClient = Depends(get_artic_client),
    ) -> ArtworkDetail | Response:
        try:
            lookup = get_artwork(client, external_id)
        except CatalogUnavailable as error:
            return _unavailable("detail", error)
        if lookup.status != LookupStatus.FOUND or lookup.artwork is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return lookup.artwork

    @api_route(
        app,
        "/api/catalog/images/{image_id}",
        methods=["GET"],
        # PUBLIC de propósito: obras de domínio público, nenhum dado de conta, e a
        # vitrine pública da 2.5 usará as mesmas imagens.
        policy=AccessPolicy.PUBLIC,
        response_class=Response,
        response_model=None,
        responses={
            200: {
                "description": "JPEG de 843 px da obra.",
                "content": {
                    "image/jpeg": {"schema": {"type": "string", "format": "binary"}}
                },
            },
            **error_responses(404, 422, 503),
        },
    )
    def artwork_image(
        image_id: str,
        client: ArticClient = Depends(get_artic_client),
    ) -> Response:
        # Único dado do usuário que chega ao IIIF, validado antes de qualquer
        # chamada; host, caminho, tamanho e formato são fixos no cliente.
        if not IMAGE_ID_PATTERN.fullmatch(image_id):
            return error_response(
                422,
                "validation_error",
                details=[{"loc": ["path", "image_id"], "type": "invalid_image_id"}],
                headers=NO_STORE,
            )
        try:
            data = client.get_image(image_id)
        except CatalogUnavailable as error:
            return _unavailable("image", error)
        if data is None:
            return error_response(404, "not_found", headers=NO_STORE)
        return Response(
            content=data,
            media_type="image/jpeg",
            headers={**NO_STORE, "X-Content-Type-Options": "nosniff"},
        )
