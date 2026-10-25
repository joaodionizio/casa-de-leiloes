# Mapa de implementação — Story 2.5

## 1. Requisito → arquivo/função

| Requisito | Arquivo | Função/elemento |
| --- | --- | --- |
| CAP-3 regra | `backend/app/lots.py` | `LotPhase`, `lot_phase(starts_at, ends_at, now)` |
| CAP-5 DTOs | `backend/app/lots.py` | `PublicLotSummary`, `PublicLotDetail`, `PublicLotsResponse`, `PublicLotDetailResponse` |
| CAP-1, CAP-2 serviço puro | `backend/app/lots.py` | `public_lot_summary`, `public_lot_detail`, `build_public_lots(lots, as_of)` |
| CAP-1, CAP-2, CAP-4, CAP-7 rotas | `backend/app/lots.py` | `register_lot_routes`: `public_lots` (`GET /api/lots`) e `public_lot` (`GET /api/lots/{lot_id}`), **depois** de `my_lots`; um único statement por request; `session.rollback()` antes de devolver |
| CAP-3 snapshot | `backend/app/lots.py` | `_clock_cte`, `public_snapshot_statement`, `read_public_snapshot`, `read_public_lot_snapshot` (CTE `MATERIALIZED` + `LEFT OUTER JOIN`, `backend-contract.md` §3) |
| CAP-13 política (teste) | `backend/tests/access_policy.py` | `policy_by_route` com chave `(path, method, kind)`, uma entrada por método, chave repetida → `ValueError` (D20) |
| CAP-9 rotas | `frontend/src/route.ts` | `parseRoute`, `routePath`, `isAuctioneerRoute`, `safeReturnPath`, `shouldHandleClick`, `readNavState` |
| CAP-9 efeitos | `frontend/src/navigation.ts` | `navigate`, `replaceRoute`, `patchCurrentState`, `NAVIGATION_EVENT` |
| CAP-9 link | `frontend/src/AppLink.tsx` | `<a href>` com clique interceptado |
| CAP-10 rótulos | `frontend/src/lotPhase.ts` | `phaseLabel`, `phaseStatusText` |
| D16 indicador | `frontend/src/asOf.ts` | `asOfText(asOf, today, timeZone?)` |
| CAP-10 regras de tela | `frontend/src/vitrine.ts` | `ENDED_STEP`, `selectFeatured`, `railItems`, `initialEndedVisible`, `nextEndedVisible`, `railScrollState` |
| CAP-1, CAP-2 cliente | `frontend/src/api/publicLots.ts` | tipos, `isPublicLotsResponse`, `isPublicLotDetailResponse`, `fetchPublicLots`, `fetchPublicLot` |
| CAP-10 vitrine | `frontend/src/Vitrine.tsx`, `FeaturedLot.tsx`, `LotRail.tsx`, `LiveLotItem.tsx`, `UpcomingLotItem.tsx`, `ClosedLotRow.tsx`, `LotState.tsx` | `frontend-vitrine.md` §3, §4 |
| CAP-11 página | `frontend/src/LotPage.tsx` | `frontend-vitrine.md` §5 |
| CAP-8 login | `frontend/src/LoginPage.tsx` | `frontend-navigation.md` §4 (usa `LoginForm` da 2.2 sem mudança) |
| CAP-9 não encontrada | `frontend/src/NotFoundPage.tsx` | `frontend-navigation.md` §8 |
| CAP-8 header | `frontend/src/SiteHeader.tsx` | §5 da navegação: `AppLink`s, `aria-current` pela rota, "Entrar" |
| CAP-8, CAP-9 app | `frontend/src/App.tsx` | rota + `navState` + `navigated`; sessão; vistas por rota; áreas do leiloeiro (§6); logout → `/` |
| CAP-10 imagem | `frontend/src/ArtworkImage.tsx` | variante `card` (D17) |
| CAP-12 estilo | `frontend/src/App.css` | seções "Vitrine", "Destaque", "Rail", "Encerrados", "Página do lote", "Estado do lote"; header com links |
| testes back-end | `backend/tests/...` | `test-plan.md` §2–§6 |
| testes front | `frontend/src/*.test.ts` (inclui `asOf.test.ts`), `src/api/publicLots.test.ts` | `test-plan.md` §7 |

**Alterados só no necessário:** `LotCreation.tsx` e `MyLots.tsx` (nenhuma mudança de
interface prevista: os callbacks `onShowMyLots`/`onCreateLot`/`onSessionExpired` passam
a navegar, no `App`). `LoginForm.tsx` sem mudança.

**Intocados (D19, lista original; a D21 de 25/10/2026 acrescentou depois o Playwright e passou a tocar `package.json`, `package-lock.json`, `verify.sh`, `.dockerignore` e `.gitignore`):** `app/main.py`, `app/spa.py`, `app/catalog.py`, `app/artic.py`,
`app/access.py`, `app/csrf.py`, `app/auth.py`, `app/security.py`, `app/config.py`,
`app/db.py`, `app/users.py`, `app/seed.py`, `app/errors.py`, migrations, `Dockerfile`,
`.dockerignore`, `compose.yaml`, `scripts/start.sh`, `pyproject.toml`, `uv.lock`,
`package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json`,
`eslint.config.js`, `verify.sh`, `money.ts`, `lotTime.ts`, `lotDraft.ts`, `api/lots.ts`,
`api/auth.ts`, `api/catalog.ts`, `CatalogSearch.tsx`.

## 2. Ordem (com dependências)

1. **Regra pura e DTOs** (`LotPhase`, `lot_phase`, os quatro DTOs, `public_lot_*`) +
   `test_lot_phase.py`.
2. **Leitura em um statement** (`public_snapshot_statement`, `read_public_snapshot`, `read_public_lot_snapshot`) e `build_public_lots`. Conferir o SQL emitido (`MATERIALIZED`, `LEFT OUTER JOIN`, um `clock_timestamp`) antes de seguir. Depende de 1.
3. **Rotas** em `register_lot_routes` depois de `my_lots`. Depende de 2.
4. **Contrato fixado**: `policy_by_route` (D20) e `EXPECTED_POLICIES`; `test_openapi.py`
   (§4 e §5 do plano); `test_lot_creation.py:787`; `test_spa.py` (§6). Rodar a suíte
   inteira aqui.
5. **Integração** `test_public_lots.py` (§3 do plano), incluindo o snapshot por
   injeção (`before_public_read`) com o controle negativo, row lock e statement único.
   Depende de 3.
6. **Front, lógica pura**: `route.ts`, `lotPhase.ts`, `vitrine.ts`, `asOf.ts`,
   `api/publicLots.ts` + testes; `npm test` e `npm run typecheck`.
7. **Front, navegação**: `navigation.ts`, `AppLink.tsx`, `App.tsx`, `SiteHeader.tsx`,
   `LoginPage.tsx`, `NotFoundPage.tsx`; áreas do leiloeiro da 2.4 em
   `/auctioneer/lots[/new]`. Depende de 6.
8. **Front, telas públicas**: `ArtworkImage` `card`, `LotState`, `FeaturedLot`,
   `LotRail`, itens, `ClosedLotRow`, `Vitrine`, `LotPage`, CSS. Depende de 3 (contrato) e 7.
9. **Docs** (§4) e `./verify.sh` completo.
10. Parar; o roteiro manual (`test-plan.md` §9) é do Joaodionizio; depois
    `bmad-code-review` em sessão nova.

## 3. Plano em até 8 linhas (para o `bmad-build` mostrar antes de editar)

`app/lots.py`: `lot_phase` pura, DTOs públicos e `GET /api/lots` + `GET /api/lots/{lot_id}`
`PUBLIC` depois de `/mine`, um statement só (CTE `MATERIALIZED` com `clock_timestamp()` +
`LEFT JOIN lots`: `as_of` e linhas no mesmo snapshot), rollback antes de responder, sem
AIC, sem escrita; `policy_by_route` por `(path, method, kind)` (D20); front com
`route.ts`/`navigation.ts`/`AppLink` (History API), header por papel, `/login` com
`returnTo` em `history.state`, áreas do leiloeiro em `/auctioneer/lots[/new]`, vitrine
(destaque, rails, encerrados com "Mostrar mais" local) e página do lote; estados de
carregando/erro/vazio; testes `pytest` (PostgreSQL real) e `node --test` de lógica pura;
`verify`. (Testes de navegador com Playwright, opt-in: acrescentados depois, D21.)

## 4. Documentação (na implementação)

- **Story 2.5:** P1–P9 (aprovadas) e D1–D20 em primeira pessoa, com a alternativa
  descartada; tarefas marcadas; tipo real do 422 de UUID; desvios; saídas reais; status
  `review` (nunca `done` antes do roteiro manual, do code review e da conferência
  documental).
- **`sprint-status.yaml`:** `in-progress` no início do build, `review` no fim.
- **README:** seção "Vitrine e página do lote" (rotas públicas, `as_of`, fase do
  servidor, ordem, sem paginação, URLs do front, login explícito e retorno); "Lotes" deixa
  de dizer que a fase "vem na Story 2.5"; "Comportamentos que podem surpreender":
  - a fase é um retrato do `as_of` e só muda num novo carregamento (P3);
  - todo lote encerrado aparece como "Encerrado, apurando resultado" até a liquidação
    existir (4.3) (P8);
  - a vitrine traz todos os lotes, sem paginação, e os demos encerrados se acumulam;
    "Mostrar mais encerrados" não busca nada novo (P7);
  - cada imagem visível é uma chamada à AIC, sem cache (P9, D1 da 2.3);
  - caminho desconhecido responde 200 com a SPA e a tela "Página não encontrada";
  - a API aceita o UUID do lote também em maiúsculas; o front usa só minúsculas;
  - depois do login, o Back passa pela página de origem.
  "Como validar": `curl` de `/api/lots`, `/api/lots/<uuid>`, `/api/lots/abc` e
  `/lots/<uuid>`.
- **`docs/uso_de_ia.md`:** seção "Story 2.5" (spec, build, review; o que eu decidi; o que
  revisei; números só de comando).
- **`docs/ARQUITETURA.md`** (questões e histórico, nenhuma AD alterada):
  - Questão 8: "**Resolvida na Story 2.5:** a leitura expõe só `phase`
    (`scheduled`/`live`/`ended`), calculada com um `clock_timestamp()` lido uma vez por
    leitura, sem trava e sem escrita; para `ended` a interface mostra 'Encerrado,
    apurando resultado'. Não criei `settlement_status`: a 4.3 acrescenta um segundo eixo
    real quando a liquidação existir. Descartei `settlement_status = pending` sempre e um
    campo único com `closing`/`closed`."
  - Histórico: linha da Story 2.5 (Q8 resolvida; nenhuma AD alterada; AD-22 intacto).
- **`CLAUDE.md`:** item 8 de "Questões para a implementação" ganha "(Resolvida na 2.5:
  só `phase`; 'Encerrado, apurando resultado' para `ended`.)". Nada mais.
- **`deferred-work.md`:**
  - vitrine sem paginação (P7): resposta cresce; demos encerrados acumulam; OPT1 (6.5)
    pode trazer paginação;
  - D1 da 2.3 (chamadas de mídia sem cache): atualizar com a evidência do teste manual
    da 2.5 (429/503 observado ou não), sem resolver;
  - para a 3.6: `cancelled_at IS NULL` também em `read_public_snapshot` e `read_public_lot_snapshot`, **na condição do `LEFT JOIN`** (não num `WHERE`, que apagaria a linha do `as_of` no caso vazio)
    (além do seed);
  - componentes do front sem teste automatizado: atualizar a linha existente com os
    componentes da 2.5.
  - A P3 (fase sem atualização automática) **não** entra: é comportamento deliberado,
    documentado no README, sem trabalho futuro previsto.
- **`epics.md`:** sem mudança (o critério "Encerrado, apurando resultado" é cumprido).

Antes de `done`, a conferência de coerência da seção "Fechamento" da story
(ARQUITETURA, spec, story, uso_de_ia, CLAUDE.md, epics, README, deferred-work),
preservando decisão → motivo → alternativa descartada → evidência → revisão →
limitação.

## 5. Riscos

| # | Risco | Mitigação |
| --- | --- | --- |
| R1 | `/api/lots/{lot_id}` registrada antes de `/mine` → "Meus lotes" vira 422 público. | Ordem D4; teste de índice em `app.routes` e de 401/403/200 do `/mine`. |
| R2 | `clock_timestamp()` por linha, ou `as_of` e linhas em snapshots diferentes. | Um statement com CTE `MATERIALIZED`; testes 1b (um só `as_of` em 20 linhas), 2 (um statement, um `clock_timestamp`) e 4/4c (injeção com controle negativo). |
| R3 | `FOR UPDATE` ou transação longa na leitura. | Teste de row lock com `join(timeout)`; rollback antes da resposta; `pg_stat_activity`. |
| R4 | `session.rollback()` antes de montar os DTOs expira os objetos e dispara nova leitura. | Montar os DTOs (Pydantic) primeiro; o teste 2 pega um 2º statement. |
| R13 | O SQLAlchemy emitir o CTE sem `MATERIALIZED` ou um `JOIN` interno (vazio sem `as_of`). | Teste 2 confere o texto; teste 3 confere o vazio pela função e pela rota. |
| R5 | Mapa de política colapsar POST e GET de `/api/lots`. | D20 e teste novo do mapa. |
| R6 | Front reclassificar ou usar relógio. | Guards recusam `phase` inválida; nenhuma função do front compara datas (review). |
| R7 | Navegação própria errar foco, Back ou clique com modificador. | `route.ts` testado; roteiro manual 4–7 e 14. |
| R8 | Fluxo da 2.4 regredir com as rotas novas (perder rascunho, sessão expirada). | `LotCreation` montado enquanto `AUCTIONEER` (D10); roteiro 8–10. |
| R9 | Rails causarem rolagem horizontal global no mobile. | `min-width: 0`, `max-width: 100%`; roteiro 15. |
| R10 | Muitas miniaturas → 429 da AIC → placeholders. | `lazy`, 6 encerrados iniciais; evidência registrada (P9). |
| R11 | Tipo do 422 de UUID diferente de `uuid_parsing`. | O teste fixa o observado e a story registra. |
| R12 | Módulo novo do front quebrar na importação (como o `Intl` da 2.4). | Todo módulo com lógica no nível do módulo é importado por um teste `node --test`; imports com `.ts`. |
