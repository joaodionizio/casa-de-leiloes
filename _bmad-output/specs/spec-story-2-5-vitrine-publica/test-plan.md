# Plano de testes — Story 2.5

> **Atualização R6.4-01 — 29/10/2026:** o contrato público vigente está em
> [public-lot-dtos.md](public-lot-dtos.md). A decisão humana substitui neste
> documento a proibição histórica de `settlement_status`, as contagens 9/17 e
> o rótulo incondicional de `ended`: resumo/detalhe têm 10/18 campos, incluindo
> `settlement_status` obrigatório (`pending|settled`), derivado exclusivamente
> do settlement persistido. Vitrine: `ended+pending` → “Encerrado, apurando
> resultado”; `ended+settled` → “Encerrado”. Os demais trechos registram o
> escopo original da 2.5.


Toda contagem vem do `verify` desta story; a regressão é a suíte inteira (último
registro: 985 do back-end e 39 do front, 2.4). Banco: PostgreSQL `_test` real; AIC pelo
`ArticClient` com `MockTransport` (`catalog_support.py`); a guarda de rede continua
ativa. Nada de SQLite.

## 1. Apoio

Reuso: `build_client`, `login`, `seed_demo_users`, `seeded_id`, `json_headers`
(`auth_support.py`); `db_now`, `insert_lot`, `lot_rows`, `count_lots`,
`statement_recorder` (`lot_support.py`); `FakeArtic`, `install`, `FAILURES_BOTH`
(`catalog_support.py`); `clean_users`/`clean_lots` (`conftest.py`). Novos helpers em
`lot_support.py` (só acréscimo):

- `fixed_as_of(monkeypatch, moment)`: envolve `app.lots.read_public_snapshot` e
  `app.lots.read_public_lot_snapshot` reais e troca só o `as_of` devolvido; as linhas
  continuam vindo do banco pelo statement real.
- `before_public_read(engine, action)`: listener `before_cursor_execute` que roda
  `action()` (numa conexão própria) uma única vez, imediatamente antes do statement
  público (`WITH clock AS MATERIALIZED`), e se remove. Ponto de injeção determinístico,
  sem `sleep` nem corrida.

## 2. Regra pura — `tests/test_lot_phase.py` (sem banco)

| Caso | Esperado |
| --- | --- |
| `now = starts_at − 1 µs` | `SCHEDULED` |
| `now = starts_at` | `LIVE` |
| `starts_at < now < ends_at` | `LIVE` |
| `now = ends_at − 1 µs` | `LIVE` |
| `now = ends_at` | `ENDED` |
| `now = ends_at + 1 µs` | `ENDED` |
| Offsets diferentes (`-03:00` × UTC) no mesmo instante | comparados como instantes |
| `now` ingênuo | `ValueError` |
| Valores do enum | `{"scheduled", "live", "ended"}` exatos |
| `public_lot_summary`/`public_lot_detail` com `Lot` em memória | chaves exatas; `image_url` derivada; timestamps em UTC; `phase` do `as_of` dado |
| `build_public_lots` com `Lot`s em memória e `as_of` fixo | um lote por fase, mais um com `ends_at == as_of` (vai a `ended`) e um com `starts_at == as_of` (vai a `live`): todos classificados pelo mesmo `as_of`; `as_of` devolvido igual ao recebido |

## 3. Integração — `tests/integration/test_public_lots.py`

### 3.1 Vitrine — acesso e forma

| Caso | Esperado |
| --- | --- |
| Anônimo, `BIDDER`, `AUCTIONEER`, cookie adulterado, cookie expirado | 200 em todos; com `fixed_as_of`, corpos idênticos byte a byte |
| Banco vazio | 200 `{"as_of": "<…Z>", "live": [], "scheduled": [], "ended": []}`: `as_of` presente, string terminando em `Z`, entre `db_now` antes e depois da chamada |
| Só agendados / só ao vivo / só encerrados / mistura | cada lote em exatamente um grupo; total = `count_lots` |
| Lotes de dois leiloeiros | todos aparecem |
| Chaves | item = 9 chaves de `PublicLotSummary`; raiz = 4 chaves |
| Valores | iguais às colunas da linha; centavos exatos, inclusive `MAX_CENTS`; `image_url == f"/api/catalog/images/{image_id}"`; timestamps e `as_of` terminam em `Z` |
| Cabeçalho | `Cache-Control: no-store` |
| Nada exposto | nenhuma chave `auctioneer_id`, `is_demo`, `created_at`, `image_id`, `email`, `password_hash`, `role`, `status`, `settlement_status` em nenhum nível |
| Demo | depois de `run_seed`, o demo está em `live` com as mesmas chaves de um lote manual; um demo vencido inserido por SQL está em `ended`, intocado |

### 3.2 Instante, snapshot e fase (P2 refinada, D1)

Nenhum caso depende de tempo de espera ou de corrida: o instante é fixado por
`fixed_as_of` ou o ponto de concorrência é injetado por `before_public_read`.

| # | Caso | Esperado |
| --- | --- | --- |
| 1 | **Mesmo `as_of` para todos.** `fixed_as_of(T)`; lotes com `starts_at`/`ends_at` em `T`, `T ± 1 µs`, um por fase | fases da §2 pelo caminho HTTP; `as_of == T`; toda `phase` coerente com um só `T` |
| 1b | **Mesmo valor por linha no SQL real.** Com 20 lotes, o teste executa o mesmo `select` que `read_public_snapshot` monta (exposto como `public_snapshot_statement()`) e lê as linhas cruas | as 20 linhas trazem um único valor distinto de `as_of`, igual ao que `read_public_snapshot` devolveria |
| 2 | **`clock_timestamp()` uma vez por request.** `statement_recorder` em `GET /api/lots` e em `GET /api/lots/{id}` | **exatamente 1 statement** por request; o texto contém `clock_timestamp` **uma** vez, `MATERIALIZED` e `LEFT OUTER JOIN lots`; nenhum outro statement |
| 3 | **Vazio tem `as_of`.** Banco vazio: `GET /api/lots`; e `read_public_snapshot` direto | 200 com `as_of`; a função devolve `(as_of, [])` a partir da única linha do `LEFT JOIN` |
| 3b | Detalhe de UUID inexistente | 404; o recorder mostra 1 statement (o `as_of` foi lido sem lote) |
| 4 | **Mesmo snapshot (injeção antes da leitura).** `before_public_read` insere e **confirma** um lote L com `starts_at = created_at = clock_timestamp()` da outra conexão; depois `GET /api/lots` | L está na resposta, em `live` (`starts_at <= as_of`); para todo lote devolvido, `created_at` da linha (lido por SQL) `<= as_of`; idem no detalhe de L |
| 4b | **Não confirmado não entra.** `before_public_read` insere L sem commit (conexão segura aberta); `GET /api/lots`; depois rollback | L não aparece; nenhum bloqueio |
| 4c | **Controle negativo (só no teste).** Uma leitura em duas consultas escrita no próprio teste (`clock_timestamp()`, depois `SELECT lots`), com a mesma injeção **entre** as duas | L aparece com `created_at > as_of`: prova que o teste 4 detectaria a versão de duas consultas; nenhuma função de produção é usada aqui |
| 5 | Caminho real (sem patch) | `as_of` entre `db_now` antes e depois; lotes com margens de ±1 h na fase esperada |

### 3.3 Ordenação (P4, D3)

| Caso | Esperado |
| --- | --- |
| `live` com `ends_at` diferentes | `ends_at ASC` |
| `scheduled` com `starts_at` diferentes | `starts_at ASC` |
| `ended` com `ends_at` diferentes | `ends_at DESC` |
| Empates de horário em cada grupo (3 lotes, `id`s escolhidos) | `id ASC` nos três grupos |
| Destaque | `live[0]` é o de `ends_at` mais próximo; sem ao vivo, `scheduled[0]` é o próximo a começar |

### 3.4 Detalhe

| Caso | Esperado |
| --- | --- |
| Anônimo, `BIDDER`, `AUCTIONEER` | 200 iguais com `fixed_as_of` |
| Existente | `{as_of, lot}`; `lot` com as 17 chaves de `PublicLotDetail`, valores = linha; `no-store` |
| Fase | um lote por fase, `phase` correta com `T` fixo |
| UUID válido inexistente | 404, corpo exato `{status: 404, code: "not_found", message}`, `no-store` |
| `abc`, `mine-x`, `123`, UUID truncado | 422 `validation_error`, `details == [{"loc": ["path","lot_id"], "type": <real>}]` (tipo observado fixado e registrado na story); zero statements no banco |
| Nada exposto | como §3.1 |

### 3.5 Leitura pura e sem trava (AD-19, CA4)

| # | Caso | Esperado |
| --- | --- | --- |
| 5 | **Somente leitura.** `statement_recorder` nas duas rotas, com lote vencido no banco | o único statement começa com `WITH clock AS MATERIALIZED` e contém só `SELECT`; nenhum `INSERT`, `UPDATE`, `DELETE`; `lot_rows` e `count_lots` idênticos antes e depois; `run_seed` (envolvido por `wraps`) não é chamado |
| 6 | **Sem `FOR UPDATE`.** Mesmo recorder | nenhum `FOR UPDATE`, `FOR SHARE`, `FOR NO KEY UPDATE`, `FOR KEY SHARE` nem `LOCK` |
| 7 | **Row lock não bloqueia.** Conexão A: `BEGIN; SELECT … FROM lots WHERE id = :x FOR UPDATE; UPDATE lots SET title = 'NAO CONFIRMADO' WHERE id = :x` sem commit; numa thread, `GET /api/lots` e `GET /api/lots/{x}`; `join(timeout=5)` | as duas terminam com 200 (o timeout só é rede de segurança: a asserção é "terminou", não "foi rápido"); o título é o confirmado (MVCC); `finally`: rollback de A |
| 7b | Sem `idle in transaction` | depois da resposta, `pg_stat_activity` (por outra conexão) não mostra conexão do banco `_test` em `idle in transaction` além da do próprio teste |

### 3.6 Sem AIC (CA7)

Transporte falso sempre levantando `ConnectError`: as duas rotas, com `fixed_as_of`,
devolvem o mesmo corpo de antes; `fake.requests == []`.

### 3.7 Rotas vizinhas e métodos

| Caso | Esperado |
| --- | --- |
| Ordem em `app.routes` | índice de `/api/lots/mine` < índice de `/api/lots/{lot_id}` |
| `GET /api/lots/mine` | anônimo 401, `BIDDER` 403, `AUCTIONEER` 200 com os próprios (nunca 422) |
| `PUT`/`DELETE /api/lots` | 405 |
| `PUT`/`DELETE /api/lots/{uuid}` com origem e JSON válidos | 405 |
| `HEAD`/`OPTIONS` nas rotas novas | 405, `lot_rows` iguais |
| `POST /api/lots` | testes da 2.4 verdes |

## 4. Ajustes conscientes em testes existentes (contrato novo, não afrouxamento)

| Arquivo | Antes | Depois |
| --- | --- | --- |
| `integration/test_lot_creation.py:787` | `GET /api/lots` → 405 | → 200 (a forma fica em `test_public_lots.py`); `PUT`/`DELETE` → 405 intactos |
| `test_openapi.py` (lista de `paths`) | termina em `/api/lots`, `/api/lots/mine` | ganha `/api/lots/{lot_id}` no fim |
| `test_openapi.py:199` | `paths[-2:] == [LOTS, MINE]` | `paths[-3:] == [LOTS, MINE, DETAIL]` |
| `test_openapi.py:228` | `set(paths[LOTS]) == {"post"}` | `== {"get", "post"}`; `MINE` segue `{"get"}`; `DETAIL` `{"get"}` |
| `tests/access_policy.py` (`policy_by_route`) e `test_access_policy.py` | chave `(path, kind)` | chave `(path, method, kind)` (D20); `EXPECTED_POLICIES` reescrito com o método em cada entrada |

**Nota de política (D20, aprovada).** Conferido no código: `policy_by_route` grava
`table[(path, kind)] = policy`, então duas rotas no mesmo caminho colapsam e a última
vence. Com `GET /api/lots` (`PUBLIC`) registrado depois de `POST /api/lots`
(`AUCTIONEER`), o mapa mostraria só `PUBLIC` e o teste de igualdade deixaria de enxergar
a política do POST, em silêncio.

- Chave nova `(path, method, kind)`: uma entrada por método em `sorted(route.methods)`
  para rotas HTTP; `method = None` para WebSocket.
- Chave repetida no mapa (duas rotas com o mesmo caminho e método) falha alto
  (`ValueError`), em vez de sobrescrever.
- `policy_problems` (o verificador) e os meta-testes não mudam.
- Esperado, entre outros: `("/api/lots", "POST", "http")` `AUCTIONEER`,
  `("/api/lots", "GET", "http")` `PUBLIC`, `("/api/lots/mine", "GET", "http")`
  `AUCTIONEER`, `("/api/lots/{lot_id}", "GET", "http")` `PUBLIC`,
  `("/api/infra-check/ws", None, "websocket")` `PUBLIC`; o fallback da SPA aparece duas
  vezes, `GET` e `HEAD`, ambas `PUBLIC`.
- Testes novos em `test_access_policy.py`: (a) app sintética com `GET` `PUBLIC` e `POST`
  `AUCTIONEER` no mesmo caminho → as duas entradas aparecem com as políticas certas;
  (b) duas rotas com o mesmo caminho e método → `policy_by_route` levanta `ValueError`;
  (c) `EXPECTED_POLICIES` da app real distingue `GET /api/lots` de `POST /api/lots`.

## 5. OpenAPI (acréscimos em `test_openapi.py`)

- `GET /api/lots`: 200 → `PublicLotsResponse`; sem 422.
- `GET /api/lots/{lot_id}`: 200 → `PublicLotDetailResponse`; 404 e 422 → `ErrorResponse`;
  parâmetro `lot_id` `format: uuid`.
- `sorted(properties)` exatos de `PublicLotSummary`, `PublicLotDetail`,
  `PublicLotsResponse`, `PublicLotDetailResponse`; `LotPhase` com `enum` `["scheduled",
  "live", "ended"]`.
- Nenhum schema público contém `is_demo`, `auctioneer_id`, `created_at`, `image_id`,
  `status`, `settlement_status`; `LotResponse` (privado) inalterado; `HTTPValidationError`
  ausente.

## 6. SPA e deep-link (acréscimos em `test_spa.py`)

Com `create_app(dist)`: `GET /lots/<uuid>`, `/login`, `/auctioneer/lots`,
`/auctioneer/lots/new` → 200 `text/html` (`index.html`); `GET /api/lots` e
`/api/lots/<uuid inexistente>` → JSON (200 e 404), nunca HTML; `GET /api/lots/abc` →
422 JSON. Sem SPA, `/lots/<uuid>` → 404 (comportamento atual).

## 7. Front automatizado (`node --test`, D18)

> Plano original. Depois do teste manual (25/10/2026), os testes de navegador com Playwright (`frontend/e2e/`, opt-in com `VERIFY_E2E=1`) foram acrescentados pela D21; este plano não os descreve.

| Arquivo | Casos |
| --- | --- |
| `src/route.test.ts` | `/` → vitrine; `/lots/<uuid>` → lot; `/lots/<UUID maiúsculo>`, `/lots/abc`, `/lots/`, `/lots/<uuid>/`, `/lots/<uuid>/x` → not-found; `/login`; `/auctioneer/lots`; `/auctioneer/lots/new`; `/login/`, `/x`, `''` → not-found; ida e volta `parseRoute(routePath(r))` para cada `AppRoute`; `safeReturnPath`: `/`, `/lots/<uuid>` aceitos; `https://evil.com`, `//evil.com`, `/login`, `/x`, `42`, `null`, `undefined` → `/`; `/auctioneer/lots` com `AUCTIONEER` → aceito, com `BIDDER` → `/`; `shouldHandleClick`: clique simples → true; meta, ctrl, shift, alt, botão 1, `defaultPrevented`, `target='_blank'` → false; `readNavState`: objeto válido mantido; `restoreLotId` não-uuid, `endedVisible` negativo ou não inteiro, `returnTo` não-string, `null`, string → campos ausentes |
| `src/lotPhase.test.ts` | `phaseLabel` das três fases exatas; `phaseStatusText('ended') === 'Encerrado, apurando resultado'`, demais iguais ao rótulo |
| `src/vitrine.test.ts` | `selectFeatured`: com ao vivo → `live[0]`; sem ao vivo → `scheduled[0]`; ambos vazios (com encerrados) → `none`; `railItems` remove só o destaque e preserva a ordem; `ENDED_STEP === 6`; `initialEndedVisible(0)=0`, `(4)=4`, `(50)=6`, `(50, 18)=18`, `(10, 18)=10`, `(50, 3)` e `(50, NaN)` → 6; `nextEndedVisible(6, 50)=12`, `(48, 50)=50`; `railScrollState`: sem overflow, início, meio, fim (tolerância de 1 px) |
| `src/asOf.test.ts` (D16) | `timeZone` fixo `America/Sao_Paulo`: `as_of` `2026-10-25T17:30:00Z` com `today` 25/10 → `Situação atualizada às 14:30`; com `today` 26/10 → `Situação atualizada em 25/10/2026 às 14:30`; `2026-10-26T02:30:00Z` com `today` 25/10 → mesmo dia em São Paulo (`às 23:30`), dia seguinte em `UTC`; 24 h (`09:05`, não `9:05 AM`); `as_of` ilegível → `null`; o módulo é importado pelo teste (lição do `Intl` da 2.4) |
| `src/api/publicLots.test.ts` | guards aceitam o exemplo de `public-lot-dtos.md`; recusam `phase: 'cancelled'`, centavos `100.5`/`0`/`'100'`, `title` numérico, `live` ausente, `as_of` ausente, `lot` ausente |

Sem teste de componente nem DOM (2.4 Q1). Componentes ficam para o roteiro manual e o
code review.

## 8. Regressões

Suíte inteira da 2.4; `/health` sem banco; login/logout/`/api/me`; criação de lote e
"Meus lotes"; catálogo e proxy de imagem (sem mudança de teste); fallback da SPA;
WebSocket técnico; `npm test` existente (`money`, `lotTime`, `lotDraft`); `docker build`.
Nenhuma asserção afrouxada além da §4.

## 9. Roteiro manual no navegador (do Joaodionizio, antes do review)

Pré: `docker compose up -d --wait postgres`, migrations, `python -m app.seed`, uvicorn,
`npm run dev`. Depois, repetir 1, 4, 6 e 7 com o build servido pelo FastAPI
(`SPA_DIST_DIR`).

1. Aba anônima em `/`: vitrine, não login; demo em destaque com "● Ao vivo", "Lance
   inicial R$ 100,00", "Termina …" com fuso; "Situação atualizada às HH:mm".
2. Header anônimo: marca, "Vitrine" (`aria-current`), "Entrar"; nada de leiloeiro.
3. Criar por SQL local: 5 ao vivo, 3 e depois 20 agendados, 8 e depois 50 encerrados,
   um título excessivo, valores R$ 850, R$ 18.450, R$ 1.250.000 e o máximo; conferir
   rails, "parte do próximo item", botões só no desktop com overflow, encerrados com 6 e
   "Mostrar mais encerrados" (aba Rede: nenhum `GET` novo).
4. Abrir um lote pelo clique: URL `/lots/<uuid>`, foco no título; Cmd+R mantém o lote;
   Back volta à vitrine com foco no lote clicado; Forward volta ao lote.
5. "← Vitrine" depois de chegar pela vitrine se comporta como Back; colado direto numa
   aba nova, leva à vitrine.
6. Colar `/lots/<uuid>` numa aba nova → abre; `/lots/<uuid inexistente>` → "Lote não
   encontrado"; `/lots/abc` e `/qualquer-coisa` → "Página não encontrada" (aba Rede: sem
   `GET /api/lots/abc`).
7. "Entrar" a partir de `/lots/<uuid>` como `bidder1@example.com` → volta ao lote;
   header com e-mail, "Licitante", "Sair", sem carteira; "Sair" → vitrine.
8. Abrir `/login` direto e entrar como `auctioneer@example.com` → vitrine; header com
   "Criar lote" e "Meus lotes"; criar um lote (fluxo da 2.4) e vê-lo na vitrine no grupo
   certo; "Meus lotes" continua listando.
9. Anônimo em `/auctioneer/lots` → login e, depois de entrar como leiloeiro, "Meus lotes";
   como `BIDDER` → "Área do leiloeiro".
10. Sessão expirada (apagar o cookie) em "Meus lotes" → login com "Sua sessão expirou." e
    volta a "Meus lotes".
11. Lote que vence com a página aberta: o rótulo não muda; Cmd+R mostra "Encerrado,
    apurando resultado" (P3).
12. Rede externa cortada: vitrine e lote completos, imagens no placeholder; anotar se
    houver 503/429 da rota de imagem (P9: evidência, sem mudança).
13. Servidor parado: "Não foi possível carregar a vitrine." + "Tentar novamente";
    idem na página do lote.
14. Teclado: Tab pelo header, destaque, rails (o rail rola), "Mostrar mais", lote, link
    externo ("abre em nova aba" no leitor de tela); foco sempre visível.
15. 320 px, 375 px e desktop largo: sem rolagem horizontal global no header, destaque,
    rails, encerrados, página do lote e login; títulos longos e o valor máximo quebram.
16. `npm test` aparece como etapa "Frontend: test" no `verify`.

Registro só o que eu observar; o que não for verificado fica marcado como não
verificado.
