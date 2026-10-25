# Back-end — Story 2.5

## 1. Base reutilizada (não editar)

| De | O quê |
| --- | --- |
| `app/lots.py` (2.4) | `Lot`, `register_lot_routes`, `LotResponse`/`MyLotsResponse` (privados, inalterados) |
| `app/catalog.py` (2.3) | `image_url_for(image_id)` → `/api/catalog/images/{image_id}` |
| `app/access.py` | `api_route`, `AccessPolicy.PUBLIC` (dependência `public()`, não lê sessão), `NO_STORE` |
| `app/db.py` | `get_session` (Session curta, sem commit) |
| `app/errors.py` | `error_response`, `error_responses`; códigos `not_found`, `validation_error` já existem — **nenhum código novo** |
| `app/spa.py` | fallback `GET/HEAD /{full_path:path}`, registrado por último; `/api` e `/health` nunca viram SPA |

Tudo novo fica em `app/lots.py` (a 2.4 §7 pediu a fase "de uma função única em
`app/lots.py`"). Nenhum outro módulo de produção muda.

## 2. Regra pura (AD-26)

```python
class LotPhase(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"

def lot_phase(starts_at: datetime, ends_at: datetime, now: datetime) -> LotPhase:
    # now sem tzinfo → ValueError (como resolve_schedule)
    # now <  starts_at          → SCHEDULED
    # now <  ends_at            → LIVE        (starts_at <= now)
    # caso contrário            → ENDED       (now >= ends_at)
```

Comparação entre instantes `aware`: o offset de cada argumento não importa. Nenhum
relógio dentro da função. É a definição única da 2.4 §7; a 3.2/3.4 reutilizam.

## 3. Leitura em um statement (P2 refinada, D1)

**Invariante.** `as_of` e o conjunto de lotes da resposta pertencem ao mesmo snapshot
lógico do PostgreSQL. Por isso o instante e as linhas saem de **um único statement**: em
`READ COMMITTED`, cada statement tem um só snapshot, tirado no início dele, e o
`clock_timestamp()` é avaliado depois disso, então `snapshot <= as_of` e toda linha
devolvida foi confirmada antes do `as_of`. Duas consultas independentes teriam dois
snapshots, e um lote confirmado entre elas entraria numa resposta cujo `as_of` é
anterior à existência dele.

SQL emitido (vitrine):

```sql
WITH clock AS MATERIALIZED (SELECT clock_timestamp() AS as_of)
SELECT clock.as_of, lots.*
FROM clock LEFT OUTER JOIN lots ON true
```

SQL emitido (detalhe):

```sql
WITH clock AS MATERIALIZED (SELECT clock_timestamp() AS as_of)
SELECT clock.as_of, lots.*
FROM clock LEFT OUTER JOIN lots ON lots.id = :lot_id
```

- **Um relógio só.** O CTE `MATERIALIZED` é avaliado uma vez; o valor é repetido em cada
  linha do resultado, sem `clock_timestamp()` por linha (o PostgreSQL também nunca
  embute um CTE com função volátil; o `MATERIALIZED` deixa isso explícito).
- **Caso vazio.** O `LEFT OUTER JOIN` parte do CTE, que tem exatamente uma linha: sem
  lotes (ou sem o lote pedido), o resultado é uma linha com `as_of` e as colunas de
  `lots` nulas. Nunca depende de existir lote para obter o `as_of`.
- **Sem trava.** Sem `FOR UPDATE`/`FOR SHARE`, sem `LOCK TABLE`, sem `WHERE` além do id,
  sem `ORDER BY` (a ordem é em Python), sem `LIMIT`.

SQLAlchemy 2.x (forma esperada; o teste confere o SQL emitido, não esta sintaxe):

```python
def _clock_cte():
    return select(func.clock_timestamp().label("as_of")).cte("clock").prefix_with("MATERIALIZED")

def public_snapshot_statement() -> Select:     # exposto para o teste 1b
    clock = _clock_cte()
    return select(clock.c.as_of, Lot).select_from(clock).outerjoin(Lot, true())

def read_public_snapshot(session: Session) -> tuple[datetime, list[Lot]]:
    rows = session.execute(public_snapshot_statement()).all()   # sempre >= 1 linha
    as_of = rows[0].as_of.astimezone(UTC)
    return as_of, [row.Lot for row in rows if row.Lot is not None]

def read_public_lot_snapshot(session: Session,
                             lot_id: uuid.UUID) -> tuple[datetime, Lot | None]:
    clock = _clock_cte()
    row = session.execute(
        select(clock.c.as_of, Lot).select_from(clock).outerjoin(Lot, Lot.id == lot_id)
    ).one()                                   # exatamente 1 linha
    return row.as_of.astimezone(UTC), row.Lot
```

## 4. Serviço puro (sem banco, sem rede)

```python
def public_lot_summary(lot: Lot, as_of: datetime) -> PublicLotSummary
def public_lot_detail(lot: Lot, as_of: datetime) -> PublicLotDetail
    # image_url = image_url_for(lot.image_id); timestamps .astimezone(UTC);
    # phase = lot_phase(lot.starts_at, lot.ends_at, as_of)

def build_public_lots(lots: list[Lot], as_of: datetime) -> PublicLotsResponse:
    # classifica cada lote com o MESMO as_of e ordena:
    #   live:      key=(ends_at,   id)
    #   scheduled: key=(starts_at, id)
    #   ended:     ends_at DESC, id ASC  → sort por id ASC e depois sort estável
    #              por ends_at com reverse=True (ou chave equivalente)
```

O instante entra por parâmetro: os testes passam um `as_of` fixo contra linhas reais.
Nenhuma chamada a `get_artic_client`, `catalog.get_artwork`, `ArticClient` ou seed.
`database_now` (2.4) continua existindo para a criação de lote e o seed, mas **não** é
usada pelas rotas públicas.

**Cancelados:** hoje não existem. A 3.6 acrescenta `AND lots.cancelled_at IS NULL` à
condição do `LEFT JOIN` das duas leituras, nunca num `WHERE` (que tiraria a linha do
`as_of` quando não sobra lote) (`deferred-work.md`).

## 5. Rotas

Registradas em `register_lot_routes`, nesta ordem (D4):

```text
POST /api/lots              (2.4, AUCTIONEER)
GET  /api/lots/mine         (2.4, AUCTIONEER)
GET  /api/lots              (2.5, PUBLIC)
GET  /api/lots/{lot_id}     (2.5, PUBLIC)   ← sempre depois de /mine
```

| Rota | Política | Entrada | Sucesso | Erros |
| --- | --- | --- | --- | --- |
| `GET /api/lots` | `PUBLIC` | nenhuma (query extra ignorada) | 200 `PublicLotsResponse`, `no-store` | 500 genérico |
| `GET /api/lots/{lot_id}` | `PUBLIC` | `lot_id: uuid.UUID` (caminho) | 200 `PublicLotDetailResponse`, `no-store` | 404 `not_found` (`no-store`); 422 `validation_error`; 500 |

Handlers `def` (threadpool), com `response: Response` e
`session: Session = Depends(get_session)`; **sem** `User`, `require_*` nem
`get_artic_client`.

```text
1. dependência public()                        não lê cookie nem banco
2. as_of, lots = read_public_snapshot(session)  o único statement (§3)
   (detalhe: as_of, lot = read_public_lot_snapshot(session, lot_id))
3. DTOs montados (build_public_lots / public_lot_detail; Pydantic, sem lazy load)
4. session.rollback()                          encerra a leitura (D2)
5. lot is None → error_response(404, "not_found", headers=NO_STORE)
   senão      → response.headers["Cache-Control"] = "no-store"; devolve o DTO
```

O handler chama `read_public_snapshot`/`read_public_lot_snapshot` pelo nome global do
módulo (`app.lots`): para fixar o instante num teste HTTP, o teste envolve a função real
e troca só o `as_of` devolvido (as linhas continuam vindo do banco).

**Por que assim.** Sem trava não há "depois da trava" (AD-6): o instante é lido uma vez,
dentro da própria leitura. Em `READ COMMITTED`, o `SELECT` comum não espera row lock de
outra transação (MVCC): vê a última versão confirmada. A transação de leitura tem um
statement curto e termina antes da resposta sair; nenhuma conexão fica
`idle in transaction`. No 404, o `as_of` foi lido mas não sai: o corpo é o envelope de
erro da 2.1.

**OpenAPI.**
- `GET /api/lots`: `response_model=PublicLotsResponse`; sem `responses=` (nenhum erro
  previsto além do 500; sem parâmetros, o FastAPI não gera 422).
- `GET /api/lots/{lot_id}`: `response_model=PublicLotDetailResponse`,
  `responses=error_responses(404, 422)` (tira o `HTTPValidationError`).

## 6. Erros

| Situação | Status | `code` | `details` | `Cache-Control` |
| --- | --- | --- | --- | --- |
| `lot_id` não é UUID (`abc`, `mine-x`, UUID truncado, `123`) | 422 | `validation_error` | `[{"loc": ["path","lot_id"], "type": "<tipo real>"}]` (proposto `uuid_parsing`; o teste fixa o observado) | ausente (handler global, C4 da 2.3) |
| UUID válido inexistente | 404 | `not_found` | — | `no-store` |
| Exceção inesperada (banco fora etc.) | 500 | `internal_error` | — | — |
| Vitrine vazia | 200 | — | três listas vazias | `no-store` |

Sem código específico para imagem ausente, lote encerrado ou lista vazia. Imagem que
falha é só visual.

## 7. Métodos e rotas vizinhas

| Pedido | Resposta |
| --- | --- |
| `GET /api/lots` | 200 (antes 405; troca prevista pela 2.4) |
| `POST /api/lots` | igual à 2.4 |
| `PUT`/`DELETE /api/lots` | 405 |
| `GET /api/lots/mine` | 401 anônimo, 403 `BIDDER`, 200 `AUCTIONEER` (nunca 422) |
| `HEAD`/`OPTIONS` nas rotas novas | 405, sem efeito |
| `PUT`/`DELETE /api/lots/{uuid}` | 405 (com origem e JSON válidos; senão 403/415 da 2.1) |
| `GET /api/lots/x/y` | 404 JSON (já testado na 1.3) |

## 8. Deep-link e fallback da SPA (sem mudança de código)

`spa.py` já cobre o que a 2.5 precisa: o fallback, registrado por último, só atende
`GET`/`HEAD`, recusa `/api` e `/api/*` (404 JSON, inclusive por caminhos equivalentes
como `/lots/../api/x`), devolve 404 a arquivo ausente com extensão e serve `index.html` a
todo o resto.

| Pedido (SPA montada) | Resposta |
| --- | --- |
| `GET /` | `index.html` |
| `GET /lots/<uuid>` | `index.html` (o front pede `/api/lots/<uuid>`) |
| `GET /login`, `/auctioneer/lots`, `/auctioneer/lots/new` | `index.html` |
| `GET /qualquer-rota-invalida` | `index.html` 200; o front mostra "Página não encontrada" (soft 404 consciente) |
| `GET /api/lots`, `/api/lots/<uuid>` | JSON da API |
| `GET /api/nao-existe` | 404 JSON |

Em desenvolvimento, o Vite serve `index.html` aos caminhos do cliente e faz proxy de
`/api` e `/health` (sem mudança em `vite.config.ts`).
