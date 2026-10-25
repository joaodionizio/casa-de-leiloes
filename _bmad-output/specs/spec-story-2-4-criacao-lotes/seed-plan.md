# Seed do lote demo (P8, D8, D9; Q4 parcial)

## 1. Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `backend/app/seed_data/demo_artwork.json` | Os 11 campos de `ArtworkSnapshot`, exatamente, obra 27992 |
| `backend/app/seed.py` | `seed_users` (intocada), novas `acquire_seed_lock`, `seed_demo_lot`, `run_seed`; `main()` passa a chamar `run_seed` |

Não é pacote Python: `seed_data/` só guarda dados, sem `__init__.py`. Carregado por
`Path(__file__).resolve().parent / "seed_data" / "demo_artwork.json"`, lido como bytes
e validado por `ArtworkSnapshot.model_validate_json(...)` (`extra="forbid"`: campo a
mais ou a menos reprova o boot com erro claro, sem rede).

Conteúdo (valores da AIC real, já conferidos pelo smoke da 2.3 e iguais à fixture de
teste `artwork_27992.json`):

```json
{
  "external_id": 27992,
  "title": "A Sunday on La Grande Jatte — 1884",
  "artist_display": "Georges Seurat (French, 1859–1891)",
  "date_display": "1884–86, border added 1888–89",
  "medium_display": "Oil on canvas",
  "dimensions": "207.5 × 308.1 cm (81 3/4 × 121 1/4 in.)",
  "department_title": "Painting and Sculpture of Europe",
  "artwork_type_title": "Painting",
  "image_id": "2d484387-2509-5e8e-2c43-22f9981972eb",
  "credit_line": "Helen Birch Bartlett Memorial Collection",
  "source_url": "https://www.artic.edu/artworks/27992"
}
```

Sem dado pessoal; dados do acervo CC0. A imagem continua pelo proxy da 2.3 (AD-22): o
seed não toca no IIIF.

**Chega à produção:** o `Dockerfile` copia `backend/app` inteiro (`COPY backend/app ./app`)
e o `.dockerignore` exclui só `backend/tests`, `**/.env*`, caches, `node_modules`,
`.venv`, `dist`. Nenhuma mudança no `Dockerfile` nem no `.dockerignore`.

## 2. Constantes em `seed.py`

```python
SEED_ADVISORY_LOCK_KEY = 0x6361736173656564   # ASCII "casaseed" = 7161131744880846180 (bigint)
DEMO_AUCTIONEER_ID = SEED_USERS[0].id          # 219e37a5-0def-4b26-87d4-b08668f7c112
DEMO_LOT_DURATION = timedelta(hours=72)
DEMO_STARTING_BID_CENTS = 10_000               # R$ 100,00
DEMO_MIN_INCREMENT_CENTS = 1_000               # R$ 10,00
DEMO_ARTWORK_PATH = Path(__file__).resolve().parent / "seed_data" / "demo_artwork.json"
```

`DEMO_AUCTIONEER_ID` é derivado de `SEED_USERS` filtrando `UserRole.AUCTIONEER` (não pelo
índice), e o teste confere o UUID fixo.

## 3. Algoritmo

Fluxo (A3): fixture local versionada → `ArtworkSnapshot` → trava consultiva → hora do
banco → `create_lot(snapshot, terms_demo, auctioneer_id, now)` → commit. A criação
manual chega ao mesmo `create_lot` por outro caminho: `resolve_artwork_for_lot` (AIC) →
snapshot (`backend-contract.md` §2.2). O seed compartilha a regra e a persistência,
nunca a integração externa.

```python
def acquire_seed_lock(session) -> None:
    session.execute(select(func.pg_advisory_xact_lock(SEED_ADVISORY_LOCK_KEY)))

def seed_demo_lot(session, now: datetime) -> bool:
    """True se criou. Nunca UPDATE/DELETE em lots."""
    open_demo = session.scalar(
        select(exists().where(Lot.is_demo.is_(True), Lot.ends_at > now)))
    if open_demo:
        return False
    snapshot = load_demo_artwork()      # fixture local → ArtworkSnapshot; nunca a AIC
    terms = LotTerms(starting_bid_cents=DEMO_STARTING_BID_CENTS,
                     min_increment_cents=DEMO_MIN_INCREMENT_CENTS,
                     starts_at=None, ends_at=now + DEMO_LOT_DURATION)
    result = create_lot(session, snapshot=snapshot, terms=terms,
                        auctioneer_id=DEMO_AUCTIONEER_ID, now=now, is_demo=True)
    if isinstance(result, ScheduleViolation):
        raise RuntimeError(...)   # impossível com 72 h; falha alto em vez de silenciar
    return True

def run_seed(session) -> tuple[int, bool]:
    """Uma transação; não faz commit."""
    acquire_seed_lock(session)          # 1º statement da transação
    users = seed_users(session)         # o leiloeiro existe antes do lote (FK)
    now = database_now(session)         # depois da trava (análogo ao AD-6)
    created = seed_demo_lot(session, now)
    return users, created

def main() -> None:
    ... with factory() as session:
            users, created = run_seed(session)
            session.commit()            # libera a trava
    logger.info("seed: %d user(s) inserted; demo lot %s", users,
                "created" if created else "kept")
```

- **Uma única transação** para usuários e lote: falha em qualquer passo desfaz tudo
  e o `set -eu` do `start.sh` impede o servidor de subir.
- **Hora:** `clock_timestamp()` lido uma vez, **depois** da trava; o mesmo `now` decide
  "existe demo aberto", vira `starts_at`, `created_at` e base de `ends_at`.
- **Trava:** `pg_advisory_xact_lock(bigint)`, de transação: liberada sozinha no commit
  ou rollback (inclusive se o processo morrer). Um segundo seed bloqueia até o primeiro
  terminar e, ao seguir, lê `now` e consulta de novo.
- **Isolamento:** `READ COMMITTED` (padrão do PostgreSQL e do psycopg). Cada statement
  vê o que já foi confirmado, então o segundo seed enxerga o demo do primeiro. Em
  `REPEATABLE READ` o snapshot seria tirado no statement da trava e o segundo seed não
  veria o lote do primeiro: um teste fixa o nível padrão.
- **Demo aberto (Q4):** `is_demo = true AND ends_at > now`. Lote manual aberto não conta.
  Demo vencido e não liquidado conta como encerrado (não há liquidação ainda).
- **Nunca altera nem apaga:** o seed só faz `INSERT`; um teste compara as linhas antigas
  coluna a coluna antes e depois e escuta os statements (nenhum `UPDATE`/`DELETE` em
  `lots`).
- **Mesmas regras da criação manual:** `LotTerms` (Pydantic) valida os valores e
  `create_lot` → `resolve_schedule` valida os horários; `ArtworkSnapshot` valida a fixture.
- `seed_users` mantém assinatura e comportamento: os testes da 2.2 chamam a função
  direto.
- O log continua contendo `"3 user(s) inserted"` (o teste da 2.2 procura a substring).

## 4. Ordem na inicialização (Q4)

`start.sh` não muda: `alembic upgrade head` → `python -m app.seed` → `uvicorn`. Quando a
4.4 criar o catch-up de fechamento, ele entra **antes** do seed. A 3.6 acrescenta
`AND cancelled_at IS NULL` ao predicado. Registro em `docs/ARQUITETURA.md` (Questão 4 e
histórico), sem AD nova.

## 5. Independência

Sem `APP_ORIGIN`, `JWT_SECRET` nem `app.main`; só `DATABASE_URL`. O seed **não chama**
`resolve_artwork_for_lot`, `catalog.get_artwork`, `ArticClient` nem `httpx`: `seed.py`
importa de `app.lots` só `Lot`, `LotTerms`, `ArtworkSnapshot`, `ScheduleViolation`,
`create_lot` e `database_now`. Importar `app.lots` carrega `app.catalog` indiretamente (tipos e
`image_url_for`), o que não abre rede (como prova o smoke da 2.3); chamar é o que fica
proibido. Prova (`test-plan.md` §6): o seed roda com esses quatro pontos trocados por
funções que falham, e a guarda de rede não registra host.

## 6. Comportamento observável

| Banco antes | Resultado |
| --- | --- |
| vazio | 3 usuários, 1 demo aberto (`created`) |
| demo aberto | nada (`kept`) |
| só demos encerrados | 1 demo novo; antigos idênticos |
| demo aberto + encerrados | nada |
| só lote manual aberto | 1 demo novo |
| dois seeds ao mesmo tempo, vazio | exatamente 1 demo |

Consequência aceita: com o serviço acordado, um demo que vence não é recriado até o
próximo boot (P8, 72 h).
