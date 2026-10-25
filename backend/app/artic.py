"""Cliente da API do Art Institute of Chicago (Story 2.3, AD-12, AD-22, AD-23).

Tudo o que é da AIC mora aqui: constantes de rede, o `ArticClient` (HTTP) e o
adaptador da resposta externa para `ArticArtwork`. A regra nossa (elegibilidade,
URL da imagem, modelos da API) fica em `app/catalog.py`.

O destino de rede é fixo no código. O termo do usuário entra na consulta só como
valor de string; nada da requisição vira host, esquema, caminho ou estrutura de
consulta, e nada da resposta vira URL requisitada pelo servidor. Redirecionamento
não é seguido. Síncrono, para rodar em handler `def` (threadpool, AD-25).

Também busca os bytes da imagem no IIIF, para o proxy same-origin da rota de mídia
(revisão do AD-22, 24/10/2026): só `image_id` validado, host/caminho/tamanho fixos,
em memória, sem gravar nada.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

ARTIC_API_BASE_URL = "https://api.artic.edu/api/v1"
# Base fixa, com barra final (P6). `config.iiif_url` da resposta é ignorado.
ARTIC_IIIF_BASE_URL = "https://www.artic.edu/iiif/2/"
ARTIC_WEBSITE_BASE_URL = "https://www.artic.edu"

# Identificação recomendada pela documentação da AIC; não é autenticação (P8).
USER_AGENT = "casa-de-leiloes/1.0"
AIC_USER_AGENT = "casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)"

DEFAULT_TIMEOUT = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=3.0)
SEARCH_LIMIT = 20
# Imagem de 843 px: um JPEG típico tem centenas de KB. O teto protege a memória.
MAX_IMAGE_BYTES = 5 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"

SEARCH_FIELDS = "id,title,artist_display,date_display,image_id,is_public_domain"
DETAIL_FIELDS = (
    "id,title,artist_display,date_display,medium_display,dimensions,"
    "department_title,artwork_type_title,image_id,is_public_domain,credit_line"
)

IMAGE_ID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


class CatalogUnavailable(Exception):
    """Única exceção da integração. `reason` serve só ao log: "timeout",
    "connect", "redirect", "http_<status>", "not_json", "not_image" ou "bad_shape"."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ArticArtwork:
    external_id: int
    title: str | None
    artist_display: str | None
    date_display: str | None
    image_id: str | None  # já validado pelo regex, senão None
    is_public_domain: bool | None  # só bool, senão None
    medium_display: str | None = None
    dimensions: str | None = None
    department_title: str | None = None
    artwork_type_title: str | None = None
    credit_line: str | None = None


def iiif_image_url(image_id: str, base_url: str = ARTIC_IIIF_BASE_URL) -> str:
    """URL da imagem no IIIF: base, caminho, tamanho e formato fixos. Recusa
    (`ValueError`) `image_id` fora do regex, antes de qualquer composição."""
    if not IMAGE_ID_PATTERN.fullmatch(image_id):
        raise ValueError("image_id is not a valid IIIF identifier")
    return f"{base_url}{image_id}/full/843,/0/default.jpg"


def build_search_query(term: str) -> dict[str, Any]:
    """Consulta fixa da busca. `term` entra só em `q` (relevância) e em
    `multi_match.query`, como valor; nunca é interpretado nem concatenado."""
    return {
        "q": term,
        "query": {
            "bool": {
                "must": [{"multi_match": {"query": term, "operator": "and"}}],
                "filter": [
                    {"term": {"is_public_domain": True}},
                    {"exists": {"field": "image_id"}},
                ],
            }
        },
        "limit": SEARCH_LIMIT,
        "fields": SEARCH_FIELDS,
    }


def _text(value: object) -> str | None:
    """String com `strip`; vazia, ausente ou de outro tipo vira `None`."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _valid_id(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _artwork_from(item: object) -> ArticArtwork | None:
    """Adapta um item da AIC; `None` se não for objeto ou não tiver `id` válido."""
    if not isinstance(item, dict):
        return None
    external_id = _valid_id(item.get("id"))
    if external_id is None:
        return None
    image_id = item.get("image_id")
    public_domain = item.get("is_public_domain")
    return ArticArtwork(
        external_id=external_id,
        title=_text(item.get("title")),
        artist_display=_text(item.get("artist_display")),
        date_display=_text(item.get("date_display")),
        image_id=(
            image_id
            if isinstance(image_id, str) and IMAGE_ID_PATTERN.fullmatch(image_id)
            else None
        ),
        is_public_domain=public_domain if isinstance(public_domain, bool) else None,
        medium_display=_text(item.get("medium_display")),
        dimensions=_text(item.get("dimensions")),
        department_title=_text(item.get("department_title")),
        artwork_type_title=_text(item.get("artwork_type_title")),
        credit_line=_text(item.get("credit_line")),
    )


def _headers(accept: str) -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "AIC-User-Agent": AIC_USER_AGENT,
        "Accept": accept,
    }


def _is_expected_missing(status: int, *, allow_404: bool) -> bool:
    """`True` para o 404 que a chamada aceita como "inexistente"; qualquer outro
    status que não seja 200 levanta `CatalogUnavailable`."""
    if allow_404 and status == 404:
        return True
    if 300 <= status < 400:
        raise CatalogUnavailable("redirect")
    if status != 200:
        raise CatalogUnavailable(f"http_{status}")
    return False


class ArticClient:
    """Um `httpx.Client` curto por chamada, sem reaproveitar conexão. Sem rede no
    construtor. `api_base_url`, `iiif_base_url` e `transport` existem para testes e
    para o smoke; a aplicação nunca os passa e nenhuma configuração os lê."""

    def __init__(
        self,
        *,
        api_base_url: str = ARTIC_API_BASE_URL,
        iiif_base_url: str = ARTIC_IIIF_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self._api_base_url = api_base_url
        self._iiif_base_url = iiif_base_url
        self._transport = transport
        self._timeout = timeout

    def search(self, term: str) -> list[ArticArtwork]:
        """Itens com `id` válido, na ordem da AIC. Elegibilidade não é daqui."""
        query = json.dumps(
            build_search_query(term), separators=(",", ":"), ensure_ascii=False
        )
        response = self._get("/artworks/search", {"params": query})
        data = self._json_object(response).get("data")
        if not isinstance(data, list):
            raise CatalogUnavailable("bad_shape")
        found = (_artwork_from(item) for item in data)
        return [artwork for artwork in found if artwork is not None]

    def get_artwork(self, external_id: int) -> ArticArtwork | None:
        """`None` só para o 404 real da AIC (obra inexistente); o resto é falha."""
        response = self._get(
            f"/artworks/{external_id}", {"fields": DETAIL_FIELDS}, allow_404=True
        )
        if response is None:
            return None
        data = self._json_object(response).get("data")
        artwork = _artwork_from(data)
        if artwork is None or artwork.external_id != external_id:
            raise CatalogUnavailable("bad_shape")
        return artwork

    def get_image(self, image_id: str) -> bytes | None:
        """Bytes do JPEG de 843 px, só em memória. `None` só para o 404 real do
        IIIF. `image_id` fora do regex levanta `ValueError` sem tocar a rede (a
        rota valida antes). Status, tipo e corpo inesperados são falha."""
        url = iiif_image_url(image_id, self._iiif_base_url)
        try:
            with (
                self._client(base_url="", accept="*/*") as client,
                client.stream("GET", url) as response,
            ):
                if _is_expected_missing(response.status_code, allow_404=True):
                    return None
                content_type = response.headers.get("content-type", "")
                if not content_type.lower().startswith("image/jpeg"):
                    raise CatalogUnavailable("not_image")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_IMAGE_BYTES:
                        raise CatalogUnavailable("bad_shape")
        except httpx.TimeoutException:
            raise CatalogUnavailable("timeout") from None
        except httpx.TransportError:
            raise CatalogUnavailable("connect") from None
        except httpx.HTTPError:
            raise CatalogUnavailable("bad_shape") from None
        if not body.startswith(JPEG_MAGIC):
            raise CatalogUnavailable("not_image")
        return bytes(body)

    def _client(self, *, base_url: str, accept: str) -> httpx.Client:
        return httpx.Client(
            base_url=base_url,
            transport=self._transport,
            timeout=self._timeout,
            headers=_headers(accept),
            follow_redirects=False,
        )

    def _get(
        self, path: str, params: dict[str, str], *, allow_404: bool = False
    ) -> httpx.Response | None:
        try:
            with self._client(
                base_url=self._api_base_url, accept="application/json"
            ) as client:
                response = client.get(path, params=params)
        except httpx.TimeoutException:
            raise CatalogUnavailable("timeout") from None
        except httpx.TransportError:
            raise CatalogUnavailable("connect") from None
        except httpx.HTTPError:
            raise CatalogUnavailable("bad_shape") from None

        if _is_expected_missing(response.status_code, allow_404=allow_404):
            return None
        return response

    @staticmethod
    def _json_object(response: httpx.Response | None) -> dict[str, Any]:
        if response is None:
            raise CatalogUnavailable("bad_shape")
        if "json" not in response.headers.get("content-type", "").lower():
            raise CatalogUnavailable("not_json")
        try:
            body = response.json()
        except ValueError:
            raise CatalogUnavailable("not_json") from None
        if not isinstance(body, dict):
            raise CatalogUnavailable("bad_shape")
        return body
