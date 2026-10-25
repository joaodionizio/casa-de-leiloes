# Back-end — Story 2.3

## 1. Base existente (não reabrir)

- `app/main.py`: `create_app()` guarda configuração em `app.state`
  (`session_config`); registra `/health`, auth, infra-check e, por último, a SPA.
- `app/access.py`: `api_route`, `AccessPolicy`, `NO_STORE`, `require_auctioneer`
  (depende de `require_user` → `get_session`). Política resolve antes dos
  parâmetros da rota.
- `app/errors.py`: `error_response`, `error_responses`, `MESSAGES`,
  `CODE_BY_STATUS` (sem 503). `code_for_status(503) == "internal_error"` é
  asserção da 2.1.
- `app/auth.py`: precedente de rota que devolve `Response` com `response_model`
  e de `no-store` no 200.

## 2. Módulos

Dois módulos novos, sem camada extra:

```text
app/artic.py    tudo o que é da AIC: constantes, ArticClient (HTTP, JSON e imagem), parsing → ArticArtwork
app/catalog.py  regra nossa: elegibilidade, URL IIIF, modelos da API, serviço, rotas
```

O endpoint não conhece a AIC; o front nunca recebe JSON da AIC; a 2.4 reusa
`catalog.get_artwork()` sem reimplementar parsing. `app/catalog.py` não importa
`app.main` (o smoke o importa sem `APP_ORIGIN`/`JWT_SECRET`).

### `app/artic.py`

```python
ARTIC_API_BASE_URL = "https://api.artic.edu/api/v1"
ARTIC_IIIF_BASE_URL = "https://www.artic.edu/iiif/2/"          # P6: com barra final
ARTIC_WEBSITE_BASE_URL = "https://www.artic.edu"
USER_AGENT = "casa-de-leiloes/1.0"                              # P8
AIC_USER_AGENT = "casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)"  # P8, P8.1
DEFAULT_TIMEOUT = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=3.0)
SEARCH_LIMIT = 20
IMAGE_ID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")  # fullmatch

class CatalogUnavailable(Exception):
    """Única exceção da integração. `reason` só para log: "timeout", "connect",
    "redirect", "http_<status>", "not_json", "bad_shape"."""
    def __init__(self, reason: str) -> None: ...

@dataclass(frozen=True)
class ArticArtwork:
    external_id: int
    title: str | None
    artist_display: str | None
    date_display: str | None
    image_id: str | None           # já validado pelo regex, senão None
    is_public_domain: bool | None  # só bool, senão None
    medium_display: str | None = None
    dimensions: str | None = None
    department_title: str | None = None
    artwork_type_title: str | None = None
    credit_line: str | None = None

class ArticClient:
    def __init__(self, *, api_base_url: str = ARTIC_API_BASE_URL,
                 transport: httpx.BaseTransport | None = None,
                 timeout: httpx.Timeout = DEFAULT_TIMEOUT) -> None: ...
    def search(self, term: str) -> list[ArticArtwork]: ...       # itens inválidos descartados
    def get_artwork(self, external_id: int) -> ArticArtwork | None: ...  # None só no 404
    def get_image(self, image_id: str) -> bytes | None: ...  # P6.1; None só no 404

def iiif_image_url(image_id: str, base_url: str = ARTIC_IIIF_BASE_URL) -> str
    # recusa (ValueError) image_id fora do regex; f"{base_url}{image_id}/full/843,/0/default.jpg"
```

`ArticClient.__init__` ganha `iiif_base_url` (só testes e smoke, como `api_base_url`).
`get_image` usa `client.stream` com teto de `MAX_IMAGE_BYTES` (5 MiB), confere
`Content-Type: image/jpeg` e a assinatura JPEG, mantém os bytes só em memória e usa os
mesmos cabeçalhos de identificação (com `Accept: */*`) e a mesma classificação de status.
Motivos novos do log: `not_image` (tipo ou assinatura) e `bad_shape` (corpo grande).

Regras do `ArticClient`:

- Cada método abre `with httpx.Client(base_url=..., transport=..., timeout=...,
  headers=..., follow_redirects=False)`; nunca reaproveita conexão entre
  requisições; sem rede no construtor.
- Requisições exatamente como `aic-contract.md` §2. A consulta da busca vem de
  uma função pura `build_search_query(term: str) -> dict`, que monta o objeto
  fixo e coloca `term` só em `q` e em `multi_match.query`; nunca interpreta,
  concatena nem faz parse do termo. O JSON resultante vai em `params`
  (codificado pelo httpx); o `external_id` só no caminho, como `str(int)`.
- Classificação das respostas: `aic-contract.md` §3. Mapeamento de falha →
  `CatalogUnavailable(reason)`: `httpx.TimeoutException` → `timeout`; outros
  `httpx.TransportError` (conexão, DNS) → `connect`; 3xx → `redirect`; qualquer
  outro status ≠ 200, exceto o 404 de `get_artwork` (que devolve `None`) →
  `http_<status>`; `Content-Type` não JSON ou corpo inválido → `not_json`;
  formato fora do esperado → `bad_shape`. Nada mais escapa (nenhum `KeyError`,
  `ValueError`, `TypeError`).
- `api_base_url` é parâmetro do construtor, só para testes e smoke;
  `create_app()` nunca o passa e nenhuma configuração/variável o lê.

### `app/catalog.py`

```python
class LookupStatus(StrEnum):
    FOUND = "FOUND"; NOT_FOUND = "NOT_FOUND"
    NOT_PUBLIC_DOMAIN = "NOT_PUBLIC_DOMAIN"; NO_IMAGE = "NO_IMAGE"

@dataclass(frozen=True)
class ArtworkLookup:
    status: LookupStatus
    artwork: ArtworkDetail | None   # só em FOUND

def image_url_for(image_id: str) -> str
    # URL same-origin (P6.1): f"/api/catalog/images/{image_id}"; recusa (ValueError) image_id fora do regex
def is_eligible(a: ArticArtwork) -> bool   # a.is_public_domain is True and a.image_id is not None
def search_artworks(client: ArticClient, term: str) -> ArtworkSearchResponse   # só elegíveis, ordem da AIC
def get_artwork(client: ArticClient, external_id: int) -> ArtworkLookup
    # None → NOT_FOUND; is_public_domain is not True → NOT_PUBLIC_DOMAIN; image_id None → NO_IMAGE
def get_artic_client(request: Request) -> ArticClient   # request.app.state.artic_client
def register_catalog_routes(app: FastAPI) -> None
```

`CatalogUnavailable` atravessa o serviço; só a rota a traduz. O motivo de
`ArtworkLookup` é interno: a rota colapsa todos os não-`FOUND` em 404
`not_found` (P4). Elegibilidade é só do dado da AIC; falha de carga da imagem no
navegador nunca chega ao servidor e não muda elegibilidade.

## 3. Registro na aplicação

Em `create_app()`, ao lado de `session_config`:
`app.state.artic_client = ArticClient()`; `register_catalog_routes(app)` logo
depois de `register_auth_routes(app)` (ordem do OpenAPI, CAP-11). Sem novo
argumento em `create_app`. Testes substituem `app.state.artic_client` por um
`ArticClient(transport=httpx.MockTransport(handler))`, exercitando o cliente real.

## 4. Contratos HTTP

```python
class ArtworkSummary(BaseModel):
    external_id: int
    title: str | None
    artist_display: str | None
    date_display: str | None
    image_id: str
    image_url: str

class ArtworkDetail(ArtworkSummary):
    medium_display: str | None
    dimensions: str | None          # P11
    department_title: str | None
    artwork_type_title: str | None
    credit_line: str | None
    source_url: str

class ArtworkSearchResponse(BaseModel):
    items: list[ArtworkSummary]
```

Campos `None` saem como `null` (sempre presentes). Nenhum campo da AIC fora
desta lista.

| Rota | Política | Entrada | 200 | Erros |
| --- | --- | --- | --- | --- |
| `GET /api/catalog/artworks` | `AUCTIONEER` | `q: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100), Query()]` | `ArtworkSearchResponse`, `no-store` | 401, 403, 422, 503 |
| `GET /api/catalog/artworks/{external_id}` | `AUCTIONEER` | `external_id: Annotated[int, Path(gt=0, le=2_147_483_647)]` | `ArtworkDetail`, `no-store` | 401, 403, 404, 422, 503 |
| `GET /api/catalog/images/{image_id}` (P6.1) | `PUBLIC` | `image_id: str`, validado no handler pelo `IMAGE_ID_PATTERN` | bytes `image/jpeg`, `no-store`, `X-Content-Type-Options: nosniff` | 404, 422, 503 |

A rota de imagem é `PUBLIC` de propósito: obras de domínio público, nenhum dado de
conta e a vitrine da 2.5 usa as mesmas imagens. Handler `def`, `response_class=Response`,
`response_model=None`. `image_id` fora do regex → 422 `validation_error` com
`details=[{"loc": ["path", "image_id"], "type": "invalid_image_id"}]`, sem chamar o
upstream. Upstream 404 → `error_response(404, "not_found", headers=NO_STORE)`; qualquer
`CatalogUnavailable` → o mesmo 503 das outras rotas (log `operation=image`). Nada vai ao
filesystem, ao banco nem a cache; o corpo e os cabeçalhos do upstream nunca chegam ao cliente.

Handlers `def`, com `client: ArticClient = Depends(get_artic_client)` e
`response: Response`; `responses=error_responses(...)` com os status da tabela;
`response_model` explícito. Na busca, o handler trata `CatalogUnavailable`; no
detalhe, também `LookupStatus != FOUND` → `error_response(404, "not_found",
headers=NO_STORE)`. `HEAD`/`OPTIONS` → 405 (comportamento atual do FastAPI).

## 5. Erros

- Novo em `app/errors.py`: `CATALOG_UNAVAILABLE = "catalog_unavailable"` e
  `MESSAGES[CATALOG_UNAVAILABLE] = "O catálogo do museu está indisponível no
  momento. Tente novamente em instantes."`. `CODE_BY_STATUS` não muda.
- 404 usa `not_found` existente. 422 usa o handler da 2.1 (`details` só com
  `loc` e `type`; sem eco do termo), sem `no-store` (C4: sem mecanismo especial).
- Nenhuma hierarquia de exceção: só `CatalogUnavailable`.

## 6. Log

Logger `logging.getLogger("uvicorn.error")` (padrão de `main.py`). Na tradução
para 503: `logger.warning("artic request failed: operation=%s reason=%s",
"search" | "detail" | "image", exc.reason)`. Nunca registra o termo, URL, corpo,
cabeçalhos nem usuário. Item descartado na busca não gera log.

## 7. SSRF e destino de rede

- Hosts e caminhos: só as três constantes do §2. O IIIF é chamado só pelo servidor, em
  `get_image`, com `image_id` validado; a rota de imagem não aceita URL, host,
  esquema, tamanho, região, rotação nem formato (não é proxy genérico).
- Nada da requisição do usuário vira host, esquema, caminho ou estrutura de
  consulta: o termo só entra como valor de string em `build_search_query`
  (JSON serializado por `json.dumps`, codificado pelo httpx); o
  `external_id` é `int` validado antes, e `/` codificado no caminho já dá 404 no
  roteador.
- Nada da resposta da AIC vira URL de requisição do servidor:
  `config.iiif_url`/`website_url` ignorados; `follow_redirects=False`; `image_id`
  só entra na URL (do proxy e do IIIF) depois do regex.
- Única base alternativa: argumento do construtor do `ArticClient`, nunca
  ligado a configuração, ambiente ou requisição.

## 8. Dependências

`backend/pyproject.toml`: mover `httpx` de `[dependency-groups].dev` para
`dependencies` (`"httpx>=0.28.1"`); `uv lock` atualiza o lock sem trocar versão.
O `TestClient` continua funcionando (mesmo pacote).
