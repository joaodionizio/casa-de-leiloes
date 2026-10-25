# Plano de testes — Story 2.4

Toda contagem vem do `verify` desta story; a regressão é a suíte inteira (último
registro: 763 passed, 2.3). Testes de banco no PostgreSQL `_test` real; AIC sempre pelo
`ArticClient` real com `httpx.MockTransport` (`tests/catalog_support.py`); a guarda de
rede do `conftest.py` continua ativa.

## 1. Apoio

- `tests/conftest.py`: `clean_users` passa a `TRUNCATE lots, users` (D11, mesma guarda de
  banco `_test`); novo `clean_lots` (`TRUNCATE lots`). Adaptação ao FK; nenhuma asserção
  da 2.2 muda.
- `tests/lot_support.py` (novo): `valid_body(**overrides)` (27992, 125000, 5000,
  `starts_at: None`, `ends_at` = agora do banco + 1 dia em ISO com `Z`); `count_lots(factory)`;
  `lot_rows(factory)` (todas as colunas, ordenadas por `id`); `insert_lot(factory, **cols)`
  por SQL direto, para estados que a API não cria (demo vencido, lote de outro leiloeiro);
  `db_now(factory)`; `statement_recorder(engine)` (listener `before_cursor_execute`).
- Reuso: `build_client`, `login`, `seed_demo_users`, `seeded_id`, `json_headers`
  (`auth_support.py`); `FakeArtic`, `install`, `load_fixture`, `FAILURES_BOTH`
  (`catalog_support.py`). Um segundo `AUCTIONEER` só existe no teste, inserido por SQL.

## 2. Migration e esquema — `tests/integration/test_lots_migration.py`

| Caso | Esperado |
| --- | --- |
| Colunas | `list(columns)` na ordem de `database-schema.md` §1; nulabilidade exata; `BIGINT` em `*_cents`; `TIMESTAMP WITH TIME ZONE` em `starts_at`, `ends_at`, `created_at`; `UUID` em `id`/`auctioneer_id`; `INTEGER` em `external_id`; `VARCHAR(36)` em `image_id`; `TEXT` nos demais textos; `BOOLEAN` em `is_demo`. |
| Defaults | `is_demo` default `false`; `id` e `created_at` sem default. |
| Nomes | `pk_lots`, `fk_lots_auctioneer_id_users`, `ix_lots_auctioneer_id`; CHECKs exatamente os 5 de §3. |
| FK | `auctioneer_id` inexistente → `IntegrityError`; `DELETE FROM users` do dono de um lote → `IntegrityError` (`ondelete` = `RESTRICT`, conferido também no inspector). |
| CHECK dinheiro (A4) | Em cada `*_cents`, por SQL direto com parâmetro inteiro (nunca `float`): `1` e `9007199254740991` aceitos; `0`, `-1` e `9007199254740992` → `IntegrityError` com o nome da CHECK (`ck_lots_starting_bid_range` / `ck_lots_min_increment_range`). A definição lida do banco (`pg_get_constraintdef`) contém `9007199254740991`, igual a `str(MAX_CENTS)`. |
| CHECK tempo | `ends_at = starts_at` e `ends_at < starts_at` → `IntegrityError`. |
| CHECK snapshot | `external_id = 0`; `image_id` `"../evil"`, maiúsculas, vazio → `IntegrityError`. |
| Sem UNIQUE | Dois lotes com o mesmo `external_id` → aceitos (P7). |
| Snapshot | Linha com textos `NULL` aceita; `source_url`/`image_id` `NULL` recusados. |
| Downgrade | `downgrade 0002` remove `lots` e mantém `users`; `upgrade head` recria (fixture `back_at_head`, como a 2.2). |
| Lista de tabelas | `test_database.py`: `["alembic_version", "lots", "users"]` (acréscimo). |

## 3. Regra pura — `tests/test_lot_rules.py` (sem banco, `now` fixo)

| Caso | Esperado |
| --- | --- |
| `starts_at=None` | `Schedule(now, ends_at)`; `ends_at = now` → `ENDS_AT_NOT_AFTER_START`; `now + 1 µs` → ok. |
| Agendado | `starts_at = now` → `STARTS_AT_NOT_IN_FUTURE`; `now + 1 µs` → ok; `now − 1 µs` → violação. |
| Fim | `ends_at = starts_at` → violação; `starts_at + 1 µs` → ok. |
| Fusos | `starts_at` em `-03:00` e `now` em UTC comparados como instantes; saída sempre `tzinfo == UTC`. |
| `now` ingênuo | `ValueError`. |
| Pré-checagem | `ends_not_after_scheduled_start(None, x)` → `False`; igual/menor → `True`. |
| `LotTerms` | `StrictInt`: `100.0`, `"100"`, `True`, `1e2` → `int_type`; `0`/`-1` → `greater_than`; `MAX_CENTS + 1` → `less_than_equal`; `MAX_CENTS` ok. |
| `ApiDatetime` | `"2026-10-25T13:00:00Z"`, `"…-03:00"`, `"…T13:00Z"`, `"…13:00:00.123456+00:00"` ok; `"2026-10-25T13:00:00"` → `timezone_aware`; `1730000000`, `"1730000000"`, `"2026-10-25"`, `"2026-10-25 13:00Z"`, `"…z"` → `datetime_format`; `datetime` aware (chamada Python) ok. |
| `ArtworkSnapshot` | `extra` → recusado; `image_id` fora do regex → recusado; `snapshot_from_detail` sem `image_url` e com os 11 campos. |
| `resolve_artwork_for_lot` (A3) | Com `ArticClient` + `MockTransport`, sem banco: 27992 → `ArtworkSnapshot` igual a `snapshot_from_detail` do detalhe; 404 → `NOT_FOUND`; não PD → `NOT_PUBLIC_DOMAIN`; sem imagem → `NO_IMAGE`; cada falha de `FAILURES_BOTH` → `CatalogUnavailable` atravessa; exatamente 1 requisição por chamada. |
| `create_lot` sem rede (A3) | `inspect.signature(create_lot)` não tem parâmetro `client` nem anotação `ArticClient`; uma chamada real (§4) com `catalog.get_artwork` e `httpx.Client.__init__` trocados por funções que falham grava o lote normalmente. |
| Faixa única (A4) | `MAX_CENTS == 2**53 - 1`; `LotTerms` aceita `1` e `MAX_CENTS` e recusa `0` e `MAX_CENTS + 1` (o mesmo limite das CHECKs de §2). |

## 4. Criação — `tests/integration/test_lot_creation.py`

Cliente: `build_client(..., session_factory=…)` + `install(app, fake)` com o detalhe
`artwork_27992.json`; `seed_demo_users`; `clean_users`.

| Grupo | Casos |
| --- | --- |
| Sucesso | `AUCTIONEER` → 201, `Cache-Control: no-store`, sem `Location`; chaves exatas de `LotResponse`; `image_url == "/api/catalog/images/{image_id}"`; a linha gravada == resposta (todas as colunas); `auctioneer_id == seeded_id(AUCTIONEER_EMAIL)`; `is_demo is False`; uma linha nova. |
| AIC | `fake.requests` tem exatamente 1 requisição, `GET /api/v1/artworks/27992` com o `fields` da 2.3; nenhuma busca nem imagem. |
| Snapshot autoritativo | A fixture da AIC é alterada no teste (título "Título da AIC"): o gravado é "Título da AIC". Corpo com `title`, `artist_display`, `image_id`, `is_public_domain`, `snapshot`, `auctioneer_id`, `is_demo`, `image_url`, `source_url` (um por caso) → 422 `extra_forbidden` com `loc ["body","<campo>"]`, zero requisições à AIC, zero linhas. |
| Dono | Login como `AUCTIONEER`; `auctioneer_id` gravado é o da sessão mesmo com outro `AUCTIONEER` no banco. |
| Dinheiro | Valores gravados exatos (`125000`, `5000`); `MAX_CENTS` aceito e devolvido exato; `100.0`, `"100"`, `true`, `0`, `-1`, `MAX_CENTS + 1`, `null`, ausente → 422 com o `type` de `backend-contract.md` §4; zero AIC, zero linhas. |
| Horário real | `starts_at: null` e campo ausente: `starts_at == created_at`, ambos entre `db_now` antes e depois da chamada (caminho real com margem); `starts_at` futuro (agora do banco + 1 h, em `-03:00`) gravado e devolvido em UTC com `Z`; `starts_at` = agora do banco − 1 min → 422 `starts_at_not_in_future` **depois** de 1 requisição à AIC (D5), zero linhas; `ends_at <= starts_at` (ambos enviados) → 422 `ends_at_not_after_start` com **zero** requisições à AIC; `starts_at: null` e `ends_at` no passado → 422 `ends_at_not_after_start` depois da AIC; sem offset → `timezone_aware`; número → `datetime_format`. |
| Obra inelegível | AIC 404, `artwork_not_public_domain.json`, `artwork_no_image.json` → 422 `artwork_not_eligible`, corpo exatamente `{status, code, message}` e idêntico nos três, `no-store`; `caplog` tem `reason=NOT_FOUND|NOT_PUBLIC_DOMAIN|NO_IMAGE`; zero linhas. |
| AIC indisponível | Cada item de `FAILURES_BOTH` → 503 `catalog_unavailable` com corpo exato, `no-store`, sem `artic`, `cloudflare`, `<html` no texto; `caplog` com `operation=create_lot reason=`; zero linhas. |
| Fronteira (CA8) | Dentro do handler falso da AIC: nenhuma conexão do banco `_test` em `idle in transaction` (consulta a `pg_stat_activity` por outra conexão) e o `statement_recorder` não registra statement entre o início e o fim da chamada. |
| Atomicidade | `monkeypatch` em `Session.commit` (só nessa app) levantando erro depois do `flush` → 500 `internal_error` genérico (`raise_server_exceptions=False`), zero linhas; `create_lot` forçado a violar a CHECK (patch do `resolve_schedule` devolvendo `ends_at == starts_at`) → 500 e zero linhas. |
| Vários lotes | Duas criações com a mesma obra → 2 linhas (P7). |
| Política | Sem cookie → 401; `BIDDER` → 403; ambos no formato único, `fake.requests == []`, zero linhas; anônimo com corpo inválido (campos) → 401. JSON malformado sem sessão: o teste fixa o comportamento real do FastAPI (ele decodifica o JSON antes das dependências) e registra na story. |
| Proteção 2.1 | `Origin` estrangeiro, sem `Origin`/`Referer`, `Content-Type: text/plain` → 403 `csrf_origin_mismatch` / `csrf_origin_missing` / 415; handler não roda (`fake.requests == []`), zero linhas. |
| Métodos | `PUT`/`DELETE /api/lots` com origem e JSON válidos → 405; `GET /api/lots` → 405 nesta story (a 2.5 cria o GET público). |

## 5. Meus lotes — `tests/integration/test_my_lots.py`

| Caso | Esperado |
| --- | --- |
| Vazio | 200 `{"items": []}`, `no-store`. |
| Próprios | Lotes do leiloeiro semeado e de um segundo `AUCTIONEER` (SQL): cada um vê só os seus. |
| Ordem | `created_at` diferentes → mais recente primeiro; `created_at` iguais → `id DESC`. |
| Sem limite (A2) | 101 lotes do mesmo dono → 101 itens, todos na ordem `created_at DESC, id DESC`; nenhum parâmetro de página é lido. |
| Forma | Cada item com as chaves exatas de `LotResponse`; `image_url` derivada; timestamps com `Z`. |
| Recém-criado | `POST` seguido de `GET` → o novo é o primeiro item. |
| Sem dono por query | `?auctioneer_id=<outro>` → continua só os da sessão. |
| Sem AIC | Com o transporte falso sempre levantando `ConnectError`: resposta idêntica e `fake.requests == []`. |
| Leitura pura | `statement_recorder` durante a chamada: todo statement começa com `SELECT`; contagem de `lots` igual. |
| Política | 401 sem cookie; 403 `BIDDER`. |

## 6. Seed — `tests/integration/test_seed.py` (ampliado) e `tests/test_seed_fixture.py`

Testes existentes da 2.2 continuam iguais (chamam `seed_users` direto).

| Caso | Esperado |
| --- | --- |
| Banco vazio | `run_seed` → `(3, True)`; 1 lote, `is_demo`, `auctioneer_id = 219e37a5-…`, `external_id 27992`, snapshot == fixture, `10000`/`1000`, `starts_at == created_at`, `ends_at − starts_at == 72 h` exatos, `starts_at` entre `db_now` antes e depois. |
| Idempotência | Segunda execução → `(0, False)`; `lot_rows` idênticas. |
| Demo antigo intocado | Demo encerrado inserido por SQL (horários no passado) → novo demo criado; a linha antiga idêntica coluna a coluna; o `statement_recorder` não vê `UPDATE` nem `DELETE` em `lots`. |
| Vários antigos + aberto | Nada muda. |
| Manual aberto | Lote `is_demo = false` aberto → demo criado mesmo assim. |
| Limite do "aberto" | Demo com `ends_at` = agora do banco + 1 s → mantido; − 1 s → novo criado. |
| Mesma regra | `seed_demo_lot` passa por `create_lot` (patch de `resolve_schedule` devolvendo violação → `RuntimeError` e nada gravado). |
| Concorrência determinística | Conexão A do teste abre transação e faz `pg_advisory_xact_lock(SEED_ADVISORY_LOCK_KEY)`; uma thread roda `run_seed` + commit com sessão própria; o teste espera (poll com timeout de 10 s) até `pg_locks` mostrar `locktype='advisory' AND NOT granted`; A insere um demo aberto e faz commit; a thread termina com `created is False`; total de demos = 1. |
| Concorrência sem demo | Mesmo arranjo, A faz rollback sem inserir; a thread cria exatamente 1. |
| Corrida livre | Duas threads com `threading.Barrier` rodando `main`-equivalente em banco vazio, 5 repetições → sempre exatamente 1 demo e 3 usuários. |
| Isolamento | `SHOW transaction_isolation` na sessão do seed → `read committed`. |
| Seed não passa pelo catálogo (A3) | `monkeypatch` de `app.lots.resolve_artwork_for_lot`, `app.catalog.get_artwork`, `ArticClient.search`/`get_artwork`/`get_image` e `httpx.Client.__init__` por funções que levantam `AssertionError` → `run_seed` cria o demo normalmente; a guarda de rede não registra host. Checagem estática: a AST de `app/seed.py` não referencia `resolve_artwork_for_lot`, `get_artwork`, `ArticClient`, `artic_client` nem `httpx`. |
| Mesma persistência (A3) | `create_lot` envolvido por `wraps` registra exatamente uma chamada no seed, com `is_demo=True` e o snapshot da fixture. |
| Subprocesso (2.2) | O teste existente passa; ganha asserção de 1 demo no banco e log com `demo lot created`. Continua sem `APP_ORIGIN`, `JWT_SECRET` e sem `app.main`. |
| `start.sh` | Teste existente da ordem continua passando sem mudança. |

`tests/test_seed_fixture.py` (sem banco): o arquivo existe em
`BACKEND_DIR / "app/seed_data/demo_artwork.json"`; valida em `ArtworkSnapshot`; tem
exatamente as 11 chaves; `image_id` casa o regex; igual a
`snapshot_from_detail(_detail(...))` montado da fixture de teste `artwork_27992.json`
(coerência com a 2.3); o `Dockerfile` contém `COPY backend/app ./app`; nenhuma linha do
`.dockerignore` casa `backend/app/seed_data/demo_artwork.json` nem um diretório-pai dele
(`fnmatch` por padrão); `DEMO_AUCTIONEER_ID` é o `AUCTIONEER` de `SEED_USERS`.

## 7. Contrato e regressão (sem banco)

- `test_openapi.py`: `paths` ganha `/api/lots` e `/api/lots/mine`, nessa ordem, depois de
  `/api/catalog/images/{image_id}`; `POST /api/lots` com 201 → `LotResponse` e
  401/403/422/503 → `ErrorResponse`; `GET /api/lots/mine` com 200 → `MyLotsResponse` e
  401/403 → `ErrorResponse`; `sorted(properties)` exatos de `CreateLotRequest`,
  `LotResponse`, `MyLotsResponse`; nenhum schema expõe `is_demo` ou `auctioneer_id`;
  `HTTPValidationError` ausente.
- `test_errors.py`: `MESSAGES ==` ganha `artwork_not_eligible` com o texto exato;
  `code_for_status` intacto.
- `test_access_policy.py`: `EXPECTED_POLICIES` ganha `("/api/lots", "http")` e
  `("/api/lots/mine", "http")` como `AUCTIONEER`; verificador e meta-testes inalterados.
- `test_csrf.py`: as checagens estruturais existentes já cobrem a nova rota de escrita sob
  `/api`; nada a mudar.
- `create_app()` continua sem banco e sem rede; `/health` 200.

## 8. Front automatizado — `frontend/src/money.test.ts` (Q1)

`npm test` (`node --test "src/**/*.test.ts"`), etapa "Frontend: test" do `verify.sh`,
entre "typecheck" e "build". Um `test()` por grupo, com `assert.deepEqual` por caso:

| Grupo | Casos |
| --- | --- |
| Aceitos | `10` → 1000; `10,5` → 1050; `0,50` → 50; `0,01` → 1; `1.234,56` → 123456; `1234,56` → 123456; `  100,00  ` → 10000; `1.000.000` → 100000000; `90.071.992.547.409,91` → 9007199254740991. |
| `empty` | `""`, `"   "`. |
| `not_positive` | `0`, `0,00`, `000`, `0,0`. |
| `too_many_decimals` | `1,234`, `10,999`, `1.234,567`. |
| `dot_decimal` | `10.5`, `12.50`, `333.55`. |
| `format` | `abc`, `-5`, `R$ 10`, `1.23,45`, `1.2345`, `,50`, `10,`, `1 000`, `10.000.0`, `1e3`, `+10`, `１０` (dígitos de largura total). |
| `too_large` | `90.071.992.547.409,92`; `100000000000000`; `99999999999999999,99`. |
| Inteiro seguro | Todo resultado `ok` satisfaz `Number.isSafeInteger(cents)` e `cents >= 1`. |
| `formatCents` | 1 → `R$ 0,01`; 50 → `R$ 0,50`; 100 → `R$ 1,00`; 123456 → `R$ 1.234,56`; 100000000 → `R$ 1.000.000,00`; `MAX_CENTS` → `R$ 90.071.992.547.409,91`. |
| Ida e volta | Para 1, 99, 100, 123456, 100000000 e `MAX_CENTS`: `parseReaisToCents(formatCents(c).slice(3))` → `{ok: true, cents: c}`. |
| Limite igual ao back-end | `MAX_CENTS === Number.MAX_SAFE_INTEGER` e `=== 9007199254740991`. |
| Sem float | Checagem textual do fonte de `money.ts` (`readFileSync`): não contém `parseFloat`, `parseInt`, `* 100` nem `/ 100`. |

## 9. Roteiro manual no navegador (antes do review)

Pré: `docker compose up -d --wait postgres`, migrations, `python -m app.seed`, uvicorn e
`npm run dev`.

1. `bidder1@example.com`: nenhuma navegação de leiloeiro; `GET /api/lots/mine` na barra → 403.
2. `auctioneer@example.com`: header com "Criar lote" (ativo) e "Meus lotes"; nada de "Vitrine".
3. "Meus lotes": o lote demo da obra 27992 aparece, com R$ 100,00 e R$ 10,00 e término ~72 h depois.
4. "Criar lote": buscar "seurat", abrir 27992, "Criar lote com esta obra" → formulário com a obra em leitura e foco no título.
5. Dinheiro: `1.234,56`, `0,5`, `10`, `1,234`, `abc`, `0`, `10.5` (dot_decimal) → mensagens de §4 ao revisar; foco no primeiro inválido.
6. Início "Agendar" sem data → mensagem; término antes do início agendado → mensagem; corrigir.
7. "Revisar lote" → valores formatados a partir dos centavos e horários com fuso; "Editar" preserva tudo.
8. Duplo clique rápido em "Publicar lote" → uma só requisição `POST /api/lots` na aba Rede.
9. Confirmação "Lote criado" com o `starts_at` do servidor; "Ver meus lotes" → o lote novo no topo.
10. "Criar outro lote" → a busca anterior continua lá.
11. Agendar início 1 minuto no passado (editar o horário até ficar passado) → "O início agendado já passou…" no campo.
12. AIC indisponível: desligar a rede externa e publicar → mensagem do catálogo, dados mantidos, "Tentar novamente"; religar e repetir → criado. Com a rede desligada, "Meus lotes" continua listando (miniaturas no placeholder).
13. Erro desconhecido: parar o uvicorn e publicar → "Não foi possível confirmar se o lote foi criado…" com "Ver meus lotes".
14. Sessão expirada (apagar o cookie no DevTools) e publicar → login com "Sua sessão expirou."
15. Teclado: Tab/Enter/Espaço do detalhe à confirmação; foco visível; rádios por setas.
16. 320 px: sem rolagem horizontal no formulário, na revisão e em "Meus lotes"; desktop ≥ 64rem: obra e campos lado a lado.
17. Stress visual: com ~30 a 50 lotes (criados por script SQL local), "Meus lotes" mostra todos, continua legível, títulos longos truncados com `title`.
18. `npm test` passa sozinho e aparece como etapa "Frontend: test" na saída do `verify`.

Registro só o que eu observar; o que não for verificado fica marcado como não verificado.
