# DTOs públicos — Story 2.5 (P1, P6, P8)

Em `app/lots.py`, separados do `LotResponse` privado da 2.4 (que não muda).

```python
class PublicLotSummary(BaseModel):          # item da vitrine
    id: uuid.UUID
    title: str | None
    artist_display: str | None
    date_display: str | None
    image_url: str                          # "/api/catalog/images/{image_id}"
    starting_bid_cents: int
    starts_at: datetime                     # UTC, "Z"
    ends_at: datetime                       # UTC, "Z"
    phase: LotPhase                         # "scheduled" | "live" | "ended"

class PublicLotDetail(PublicLotSummary):    # página do lote
    external_id: int
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    credit_line: str | None
    source_url: str
    min_increment_cents: int

class PublicLotsResponse(BaseModel):        # GET /api/lots
    as_of: datetime                         # o instante usado na classificação
    live: list[PublicLotSummary]
    scheduled: list[PublicLotSummary]
    ended: list[PublicLotSummary]

class PublicLotDetailResponse(BaseModel):   # GET /api/lots/{lot_id}
    as_of: datetime
    lot: PublicLotDetail
```

## Chaves exatas (fixadas por teste)

| DTO | Chaves |
| --- | --- |
| `PublicLotSummary` | `id`, `title`, `artist_display`, `date_display`, `image_url`, `starting_bid_cents`, `starts_at`, `ends_at`, `phase` |
| `PublicLotDetail` | as 9 acima + `external_id`, `medium_display`, `dimensions`, `department_title`, `artwork_type_title`, `credit_line`, `source_url`, `min_increment_cents` |
| `PublicLotsResponse` | `as_of`, `live`, `scheduled`, `ended` |
| `PublicLotDetailResponse` | `as_of`, `lot` |

Campos `None` saem como `null` (sempre presentes).

## Fora de qualquer DTO público

`auctioneer_id`, `is_demo`, `created_at`, `image_id` cru (já está em `image_url`), e-mail,
nome, papel, qualquer dado de usuário, `status`, `settlement_status`, lance atual, líder,
quantidade de lances. Nada da AIC fora dos campos persistidos.

## Formatos

- `as_of` e timestamps: ISO 8601 em UTC com `Z`, como a 2.4 (D5). Ex.:
  `"2026-10-25T14:30:00.123456Z"`. O front pode exibir `as_of` (D16), nunca usá-lo para
  iniciar relógio de domínio.
- Dinheiro: inteiros de centavos (`1..9007199254740991`, faixa da 2.4); o front formata
  com `formatCents`. Não existe "lance atual" antes da 3.4.
- `phase`: string de `LotPhase`; o OpenAPI mostra o enum com os três valores. O front
  recebe e apresenta, nunca recalcula.

## Exemplo

```json
GET /api/lots → 200
{
  "as_of": "2026-10-25T14:30:00.123456Z",
  "live": [
    {"id": "…", "title": "A Sunday on La Grande Jatte — 1884",
     "artist_display": "Georges Seurat (French, 1859–1891)",
     "date_display": "1884–86, border added 1888–89",
     "image_url": "/api/catalog/images/2d484387-2509-5e8e-2c43-22f9981972eb",
     "starting_bid_cents": 10000,
     "starts_at": "2026-10-25T12:00:00.481203Z",
     "ends_at": "2026-10-28T12:00:00.481203Z",
     "phase": "live"}
  ],
  "scheduled": [],
  "ended": []
}

GET /api/lots/{id} → 200
{"as_of": "…Z", "lot": {…os 9 campos…, "external_id": 27992,
  "medium_display": "Oil on canvas", "dimensions": "207.5 × 308.1 cm (…)",
  "department_title": "Painting and Sculpture of Europe",
  "artwork_type_title": "Painting",
  "credit_line": "Helen Birch Bartlett Memorial Collection",
  "source_url": "https://www.artic.edu/artworks/27992",
  "min_increment_cents": 1000}}
```

## Tipos no front (`src/api/publicLots.ts`)

```ts
export type LotPhase = 'scheduled' | 'live' | 'ended'

export interface PublicLotSummary {
  id: string; title: string | null; artist_display: string | null
  date_display: string | null; image_url: string; starting_bid_cents: number
  starts_at: string; ends_at: string; phase: LotPhase
}
export interface PublicLotDetail extends PublicLotSummary {
  external_id: number; medium_display: string | null; dimensions: string | null
  department_title: string | null; artwork_type_title: string | null
  credit_line: string | null; source_url: string; min_increment_cents: number
}
export interface PublicLotsResponse {
  as_of: string; live: PublicLotSummary[]; scheduled: PublicLotSummary[]
  ended: PublicLotSummary[]
}
export interface PublicLotDetailResponse { as_of: string; lot: PublicLotDetail }
```

Type guards exportados (`isPublicLotsResponse`, `isPublicLotDetailResponse`) recusam
`phase` fora dos três valores, centavos que não sejam `Number.isSafeInteger` e `>= 1`, e
qualquer campo obrigatório ausente. Resposta fora do contrato = falha `server`.
