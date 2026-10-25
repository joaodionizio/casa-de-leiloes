# Back-end — Story 2.4

## 1. Base reutilizada (não reabrir, não editar)

| De | O quê |
| --- | --- |
| `app/catalog.py` | `get_artwork(client, external_id) -> ArtworkLookup`, `LookupStatus`, `ArtworkDetail`, `image_url_for`, `get_artic_client`, `MAX_EXTERNAL_ID` |
| `app/artic.py` | `ArticClient`, `CatalogUnavailable` (`reason` só para log), `IMAGE_ID_PATTERN` |
| `app/access.py` | `api_route`, `AccessPolicy.AUCTIONEER`, `require_auctioneer`, `NO_STORE` |
| `app/db.py` | `get_session` (Session curta, sem commit automático), `Base` |
| `app/errors.py` | `error_response`, `error_responses`, `MESSAGES` |
| `app/csrf.py` | `POST /api/*` exige `Origin`/`Referer` = `APP_ORIGIN` e `Content-Type: application/json` antes do roteamento |

`catalog.py` e `artic.py` ficam intocados.

## 2. Módulo `app/lots.py`

Um módulo, como `catalog.py`: modelo, schemas, regra pura, serviço e rotas. Importa
`app.catalog`, `app.access`, `app.db`, `app.errors`, `app.users`; **nunca** `app.main`
(o seed o importa).

```python
MAX_CENTS = 9_007_199_254_740_991          # Number.MAX_SAFE_INTEGER (D3); mesma faixa na CHECK (A4)
API_DATETIME_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})"
)                                           # fullmatch (D2)

def _api_datetime_input(value: object) -> object:
    """Aceita `datetime` (chamada Python, ex.: seed) ou string que casa o padrão;
    qualquer outra coisa → PydanticCustomError("datetime_format", ...)."""

ApiDatetime = Annotated[AwareDatetime, BeforeValidator(_api_datetime_input)]
Cents = Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]
ExternalId = Annotated[StrictInt, Field(gt=0, le=MAX_EXTERNAL_ID)]

class LotTerms(BaseModel):                  # termos do leiloeiro; o seed usa este
    model_config = ConfigDict(extra="forbid")
    starting_bid_cents: Cents
    min_increment_cents: Cents
    starts_at: ApiDatetime | None = None
    ends_at: ApiDatetime

class CreateLotRequest(LotTerms):           # corpo do POST
    external_id: ExternalId

class ArtworkSnapshot(BaseModel):           # os 11 campos de P2
    model_config = ConfigDict(extra="forbid", frozen=True)
    external_id: ExternalId
    title: str | None
    artist_display: str | None
    date_display: str | None
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    image_id: Annotated[str, StringConstraints(pattern=IMAGE_ID_PATTERN.pattern)]  # ancorado
    credit_line: str | None
    source_url: str

def snapshot_from_detail(detail: ArtworkDetail) -> ArtworkSnapshot   # model_dump(exclude={"image_url"})
```

`StrictInt` recusa `100.0`, `"100"`, `true` e `1e2`. O padrão de `image_id` precisa de
`^...$` (o regex da 2.3 é usado com `fullmatch`).

### 2.1 Regra pura (AD-26)

```python
class ScheduleViolation(StrEnum):
    ENDS_AT_NOT_AFTER_START = "ends_at_not_after_start"
    STARTS_AT_NOT_IN_FUTURE = "starts_at_not_in_future"

@dataclass(frozen=True)
class Schedule:
    starts_at: datetime      # UTC
    ends_at: datetime        # UTC

def ends_not_after_scheduled_start(starts_at: datetime | None, ends_at: datetime) -> bool
    # starts_at is not None and ends_at <= starts_at  (pré-checagem sem `now`, D5)

def resolve_schedule(starts_at: datetime | None, ends_at: datetime,
                     now: datetime) -> Schedule | ScheduleViolation:
    # start = now se starts_at is None; senão starts_at <= now → STARTS_AT_NOT_IN_FUTURE
    # ends_at <= start → ENDS_AT_NOT_AFTER_START
    # devolve tudo em UTC (`astimezone(UTC)`); `now` sem tzinfo → ValueError
```

Nenhum relógio dentro dessas funções. A comparação é entre instantes (`aware`), então
o offset de entrada não importa.

### 2.2 Serviço em dois níveis (D14, A3)

Compartilho a regra de criação, nunca a dependência externa.

```text
nível externo (só a criação manual)        nível de persistência (manual e seed)
resolve_artwork_for_lot(client, id)   ──►  create_lot(session, *, snapshot, terms,
   catalog.get_artwork → AIC                          auctioneer_id, now, is_demo)
   devolve ArtworkSnapshot ou recusa         regra pura + INSERT, sem rede
```

```python
class ArtworkRefusal(StrEnum):              # motivo interno, só para log e testes (P6)
    NOT_FOUND = "NOT_FOUND"
    NOT_PUBLIC_DOMAIN = "NOT_PUBLIC_DOMAIN"
    NO_IMAGE = "NO_IMAGE"

def resolve_artwork_for_lot(client: ArticClient,
                            external_id: int) -> ArtworkSnapshot | ArtworkRefusal:
    # Única ponte entre a criação de lote e a AIC: catalog.get_artwork(client, external_id)
    # (uma requisição); FOUND → snapshot_from_detail(lookup.artwork); outro status → o
    # ArtworkRefusal correspondente. CatalogUnavailable atravessa (a rota traduz em 503).
    # Não toca no banco.

def database_now(session: Session) -> datetime
    # session.execute(select(func.clock_timestamp())).scalar_one().astimezone(UTC)

def create_lot(session: Session, *, snapshot: ArtworkSnapshot, terms: LotTerms,
               auctioneer_id: uuid.UUID, now: datetime,
               is_demo: bool = False) -> Lot | ScheduleViolation:
    # Sem rede: nenhum ArticClient, httpx ou catalog.* na assinatura nem no corpo.
    # resolve_schedule(terms.starts_at, terms.ends_at, now) → violação, ou
    # Lot(id=uuid4(), **snapshot.model_dump(), termos, schedule, is_demo, created_at=now)
    # → session.add + flush; não faz commit (quem chama decide).

def lot_response(lot: Lot) -> LotResponse
    # image_url = image_url_for(lot.image_id); timestamps .astimezone(UTC)
```

`create_lot` é o único caminho de `INSERT` em `lots` e vale para o `POST` e o seed (CA11:
"mesmas regras de validação": `LotTerms` para dinheiro, `resolve_schedule` para horário,
`ArtworkSnapshot` para a obra). A diferença entre os dois chamadores é só a origem do
snapshot: AIC via `resolve_artwork_for_lot` na criação manual; fixture local no seed
(`seed-plan.md`). `is_demo` só é `True` quando o seed chama.

## 3. Contratos HTTP

```python
class LotResponse(BaseModel):
    id: uuid.UUID
    external_id: int
    title: str | None
    artist_display: str | None
    date_display: str | None
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    credit_line: str | None
    source_url: str
    image_id: str
    image_url: str                  # "/api/catalog/images/{image_id}"
    starting_bid_cents: int
    min_increment_cents: int
    starts_at: datetime             # UTC, serializado com "Z"
    ends_at: datetime
    created_at: datetime

class MyLotsResponse(BaseModel):
    items: list[LotResponse]
```

Sem `is_demo`, sem `auctioneer_id`, sem fase (D6, D10). Nenhum campo da AIC fora dos 11.

| Rota | Política | Entrada | Sucesso | Erros |
| --- | --- | --- | --- | --- |
| `POST /api/lots` | `AUCTIONEER` | `CreateLotRequest` (JSON) | 201 `LotResponse`, `no-store`, sem `Location` | 401, 403, 422, 503 (+ 403 `csrf_*` e 415 da 2.1) |
| `GET /api/lots/mine` | `AUCTIONEER` | nenhuma (query extra é ignorada pelo FastAPI e nunca lida) | 200 `MyLotsResponse`, `no-store` | 401, 403 |

Exemplo:

```json
POST /api/lots
{"external_id": 27992, "starting_bid_cents": 125000, "min_increment_cents": 5000,
 "starts_at": null, "ends_at": "2026-10-26T18:00:00-03:00"}

201
{"id": "…", "external_id": 27992, "title": "A Sunday on La Grande Jatte — 1884", …,
 "image_id": "2d484387-2509-5e8e-2c43-22f9981972eb",
 "image_url": "/api/catalog/images/2d484387-2509-5e8e-2c43-22f9981972eb",
 "starting_bid_cents": 125000, "min_increment_cents": 5000,
 "starts_at": "2026-10-24T15:02:11.481203Z", "ends_at": "2026-10-26T21:00:00Z",
 "created_at": "2026-10-24T15:02:11.481203Z"}
```

`GET /api/lots/mine`: `WHERE auctioneer_id = :user_id ORDER BY created_at DESC, id DESC`,
**todos** os lotes do dono, sem `LIMIT`, sem paginação (A2). Vazio → `{"items": []}`.
Inclui os demos do leiloeiro semeado (são dele). Não depende de `get_artic_client`.

Registro: `register_lot_routes(app)` logo depois de `register_catalog_routes(app)` em
`create_app()`. `/api/lots/mine` fica registrada **antes** de qualquer
`/api/lots/{lot_id}` futura (2.5).

## 4. Erros

| Situação | Status | `code` | `details` |
| --- | --- | --- | --- |
| Sem sessão válida | 401 | `unauthorized` | — |
| `BIDDER` | 403 | `forbidden` | — |
| `Origin` estrangeiro/ausente | 403 | `csrf_origin_mismatch` / `csrf_origin_missing` | — |
| Sem `Content-Type: application/json` | 415 | `unsupported_media_type` | — |
| JSON malformado | 422 | `validation_error` | `[{"loc":["body",…],"type":"json_invalid"}]` |
| Campo ausente | 422 | `validation_error` | `type: "missing"` |
| Campo desconhecido (`auctioneer_id`, `title`, `is_demo`…) | 422 | `validation_error` | `loc ["body","<campo>"]`, `type: "extra_forbidden"` |
| Dinheiro não inteiro/string/booleano | 422 | `validation_error` | `type: "int_type"` |
| Dinheiro `<= 0` / `> MAX_CENTS` | 422 | `validation_error` | `greater_than` / `less_than_equal` (o banco recusa a mesma faixa por CHECK, A4) |
| `external_id` fora de 1..2147483647 ou não inteiro | 422 | `validation_error` | `greater_than` / `less_than_equal` / `int_type` |
| Horário não string ISO (número, data sem hora, espaço no lugar do `T`) | 422 | `validation_error` | `type: "datetime_format"` |
| Horário sem offset | 422 | `validation_error` | `type: "timezone_aware"` |
| Horário ISO impossível (`2026-02-30T…`) | 422 | `validation_error` | `type` do Pydantic (`datetime_from_date_parsing` ou similar; o teste fixa o real) |
| `ends_at <= starts_at` (ambos enviados) | 422 | `validation_error` | `[{"loc":["body","ends_at"],"type":"ends_at_not_after_start"}]` |
| `starts_at <= now` | 422 | `validation_error` | `[{"loc":["body","starts_at"],"type":"starts_at_not_in_future"}]` |
| `starts_at` nulo e `ends_at <= now` | 422 | `validation_error` | `[{"loc":["body","ends_at"],"type":"ends_at_not_after_start"}]` |
| Obra inexistente, não PD ou sem imagem | 422 | `artwork_not_eligible` | — |
| AIC indisponível (qualquer `CatalogUnavailable`) | 503 | `catalog_unavailable` | — |
| Exceção inesperada (inclui violação de CHECK) | 500 | `internal_error` | — |

Novo em `app/errors.py`: `ARTWORK_NOT_ELIGIBLE = "artwork_not_eligible"` e
`MESSAGES[ARTWORK_NOT_ELIGIBLE] = "Esta obra não pode virar lote. Só são aceitas obras
de domínio público com imagem no acervo do museu."` `CODE_BY_STATUS` não muda. As
respostas montadas no handler (422 próprios, 503) levam `NO_STORE`; o 422 do handler
global continua sem `no-store` (precedente C4 da 2.3). O `loc` de `extra_forbidden`
contém o nome da chave enviada (item já em `deferred-work.md`, 2.1).

## 5. Fluxo do `POST /api/lots` (D1, D5)

```text
1. ApiWriteGuardMiddleware (2.1)          → 403 csrf_* / 415, handler não roda
2. require_auctioneer (rota)              → 401 / 403; lê o User (SELECT, abre transação implícita)
3. corpo → CreateLotRequest               → 422 (Pydantic); política vem antes (2.2 P8)
4. handler:
   a. auctioneer_id = user.id             (antes do rollback: o rollback expira o User)
   b. session.rollback()                  encerra a leitura; conexão volta ao pool
   c. ends_not_after_scheduled_start?     → 422 ends_at_not_after_start, zero AIC
   d. resolve_artwork_for_lot(client, external_id)
                                          SEM transação aberta; CatalogUnavailable → 503
   e. ArtworkRefusal                      → 422 artwork_not_eligible (log do motivo)
   f. snapshot = o ArtworkSnapshot devolvido (autoritativo)
   g. now = database_now(session)         abre a transação de persistência (1º statement)
   h. create_lot(session, snapshot=..., terms=body, auctioneer_id=..., now=now)
                                          ScheduleViolation → session.rollback(); 422
   i. session.commit()                    IntegrityError/qualquer erro → 500, nada gravado
   j. 201 lot_response(lot), no-store
```

**Por que esta ordem.** A chamada à AIC leva até ~8 s; segurar uma transação (e uma
conexão do pool) durante ela não protege nada, porque a linha é nova e não há trava. A
validação que não depende de `now` sai antes da AIC (não gasta cota). As comparações
com `now` ficam na transação de escrita, com um único `clock_timestamp()` que também
vira `created_at` e, sem `starts_at`, o próprio `starts_at` (AD-6, AD-26). A transação
só insere e confirma: qualquer falha antes do commit desfaz tudo, e falha antes do
passo g nem chega a escrever.

O handler declara `user: User = Depends(require_auctioneer)`,
`session: Session = Depends(get_session)` e `client: ArticClient =
Depends(get_artic_client)`; o FastAPI reaproveita a mesma `Session` da dependência de
política (cache por requisição). Handler `def` (threadpool, AD-25).

## 6. Log

`logging.getLogger("uvicorn.error")`, como a 2.3:

- 503: `logger.warning("artic request failed: operation=create_lot reason=%s", exc.reason)`.
- Obra inelegível: `logger.info("lot creation refused: reason=%s", refusal)`
  (`ArtworkRefusal`: `NOT_FOUND`, `NOT_PUBLIC_DOMAIN`, `NO_IMAGE`).

Nunca o corpo, o usuário, o e-mail nem a resposta da AIC.

## 7. Fase temporal (conceito único, não exposto — D10)

```text
agendado    now <  starts_at
ao vivo     starts_at <= now < ends_at
encerrado   now >= ends_at
```

Coerente com AD-5 ("lance depois do fim nunca reabre") e com a 3.2 (`now >= ends_at` →
encerrado). Nesta story nenhuma resposta e nenhuma tela calculam a fase; o único uso é o
predicado do seed "demo aberto" = `ends_at > now` (= não encerrado). Quando a 2.5 expuser
a fase, ela sai do back-end com a hora do banco, de uma função única em `app/lots.py`,
e a Q8 decide o nome de "Encerrado, apurando resultado".

## 8. OpenAPI

- `POST /api/lots`: `status_code=201`, `response_model=LotResponse`,
  `responses=error_responses(401, 403, 422, 503)`; corpo `CreateLotRequest`.
- `GET /api/lots/mine`: `response_model=MyLotsResponse`,
  `responses=error_responses(401, 403)`.
- `HTTPValidationError` continua ausente do schema.
