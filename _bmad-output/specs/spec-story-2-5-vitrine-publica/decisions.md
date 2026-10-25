# Decisões — Story 2.5

P1 a P9 foram **aprovadas** pelo Joaodionizio antes desta spec e não são reabertas.
D1 a D20 detalham (a D21, de 25/10/2026, foi acrescentada depois do teste manual) essas aprovações e os pontos que a story deixou "para o `bmad-spec`"
(direção do desempate, N de "Mostrar mais", URL do login, nomes das rotas do leiloeiro),
sem criar regra de produto. Nenhuma questão aberta. Na implementação, cada item vai para
a story em primeira pessoa, com a alternativa descartada.

## 1. Decisões aprovadas (P1 a P9)

### P1 — Forma da resposta da vitrine — APROVADA
- **Decisão.** `GET /api/lots` → `{"as_of", "live", "scheduled", "ended"}`, cada item
  também com `phase`; detalhe → `{"as_of", "lot"}`. `as_of` é o instante autoritativo
  usado para classificar aquela resposta.
- **Motivo.** O front não agrupa nem classifica; a ordem e a exclusividade por grupo são
  garantidas e testadas no servidor; o destaque vira "o primeiro da lista".
- **Alternativa descartada.** Lista plana `{as_of, items}` agrupada no front; uma rota por
  grupo (três instantes diferentes para uma página).
- **Consequência.** O OPT1 (6.5) acrescenta parâmetros sem mudar a forma; a 3.5 tem um
  ponto de referência do servidor (`as_of`).

### P2 — Cálculo da fase — APROVADA (refinada em 25/10/2026)
- **Decisão.** Back-end classifica: `now < starts_at` → `scheduled`; `starts_at <= now <
  ends_at` → `live`; `now >= ends_at` → `ended`. Um único instante do PostgreSQL por
  request (`clock_timestamp()` avaliado uma vez) vira `as_of`, e uma função pura classifica
  todos os lotes com esse mesmo instante. Sem coluna `status`, sem `FOR UPDATE`, sem
  relógio do navegador.
- **Refinamento (invariante).** `as_of` e o conjunto de lotes da resposta pertencem ao
  **mesmo snapshot lógico** do PostgreSQL. A primeira versão desta spec lia o instante e os
  lotes em duas consultas; em `READ COMMITTED` cada statement tem o seu snapshot, então um
  lote confirmado entre as duas apareceria numa resposta cujo `as_of` é anterior à
  existência dele. A forma concreta é a D1: um statement só.
- **Motivo.** AD-6/AD-26 à letra; `as_of` passa a significar "o banco como ele era nesse
  instante"; regra testável com `now` fixo; uma definição única (2.4 §7) reaproveitável na
  3.2/3.4.
- **Alternativa descartada.** `CASE` no SQL (fácil errar o `clock_timestamp()` por linha;
  regra só testável pelo banco); classificação no navegador (dois relógios); duas
  consultas independentes em `READ COMMITTED` (snapshots diferentes; versão anterior desta
  spec).
- **Consequência.** Uma ida ao banco por leitura; nenhum `clock_timestamp()` por linha.

### P3 — Página aberta atravessando um limite — APROVADA
- **Decisão.** A fase não muda sozinha: só num novo `GET` (refresh, navegação,
  reabertura). Sem countdown, polling, `setInterval` nem `Date.now()` de domínio.
- **Motivo.** Uma autoridade só; não antecipar tempo real; simplicidade.
- **Alternativa descartada.** Um `GET` agendado para o próximo limite; polling periódico.
- **Consequência.** "Ao vivo" pode ficar velho até o próximo `GET`, sem efeito de domínio
  (o lance é validado no servidor, 3.4). README em "Comportamentos que podem surpreender".
  Comportamento deliberado, sem item em `deferred-work.md`.

### P4 — Ordenação — APROVADA
- **Decisão.** `live`: `ends_at ASC`; `scheduled`: `starts_at ASC`; `ended`: `ends_at DESC`;
  `id` como desempate determinístico (direção na D3).
- **Motivo.** Responde "o que termina primeiro / começa depois / acabou de terminar" e
  combina com a regra de destaque do blueprint.
- **Alternativa descartada.** `created_at DESC`; ranking adicional.
- **Consequência.** O destaque é `live[0]`, senão `scheduled[0]`.

### P5 — Navegação — APROVADA
- **Decisão.** Sem React Router; History API própria; URLs `/` e `/lots/{id}`; login por
  ação explícita, com volta à página pública de origem; clique, `pushState`, `popstate`,
  Back, Forward, refresh e deep-link em produção (FastAPI) e no Vite.
- **Motivo.** Página do lote compartilhável e recarregável; a 3.5 e a 5.2 apontam para ela.
- **Alternativa descartada.** Estado em memória (sem URL); React Router (dependência e API
  maiores que cinco rotas pedem, AD-4).
- **Consequência.** `App.tsx`, `SiteHeader.tsx` e a navegação do leiloeiro passam a usar
  rotas (`frontend-navigation.md`). A story P5 (a) já lista `/login` e "caminhos para Criar
  lote e Meus lotes (nomes no `bmad-spec`)": a D7 os nomeia.

### P6 — DTO público e erros — APROVADA
- **Decisão.** DTOs próprios de lista e detalhe (`public-lot-dtos.md`); sem
  `auctioneer_id`, `is_demo`, `created_at`, dado de usuário nem campo interno. UUID inválido
  → 422; UUID válido inexistente → 404.
- **Motivo.** Separar o público do privado: o que a 4.5 acrescentar a "Meus lotes" não
  vaza para a vitrine.
- **Alternativa descartada.** Reaproveitar `LotResponse` (expõe `created_at`, acopla);
  DTO único na lista e no detalhe; 404 para os dois casos.
- **Consequência.** 3.4/3.5 acrescentam campos (ex.: `current_bid_cents`) de forma aditiva.

### P7 — Paginação — APROVADA
- **Decisão.** `GET /api/lots` devolve todos os lotes; sem paginação, limite silencioso ou
  truncamento. No front, "Encerrados" pode mostrar parte e oferecer "Mostrar mais", só
  localmente (N na D13).
- **Motivo.** Nenhum lote fica inacessível; nenhum contrato novo.
- **Alternativa descartada.** Paginação ou limite de encerrados na API.
- **Consequência.** A resposta cresce com o tempo (demos encerrados se acumulam a cada
  72 h de boot): `deferred-work.md`.

### P8 — Encerrado vs liquidação — APROVADA
- **Decisão.** Sem `settlement_status`, coluna, campo, enum ou valor de liquidação. O
  único eixo real é `phase`. Para `ended`, a interface mostra "Encerrado, apurando
  resultado".
- **Motivo.** Fim temporal ≠ processo financeiro; a liquidação só existe na 4.3, que
  poderá acrescentar um segundo eixo **real**.
- **Alternativa descartada.** `settlement_status` sempre `"pending"` agora; um campo único
  com `closing`/`closed`.
- **Consequência.** Resolve a Q8 (registro em `ARQUITETURA.md`, questões e histórico, sem
  AD nova). Hoje todo encerrado mostra "apurando"; a 4.3 muda a regra da tela quando o
  eixo existir.

### P9 — Imagens e cache — APROVADA
- **Decisão.** Estratégia da 2.3 intacta: `GET /api/catalog/images/{image_id}`, proxy
  same-origin, 843 px, `no-store`, sem cache novo; AD-22 e P6.1 da 2.3 sem mudança.
- **Motivo.** Não mexer em decisão fechada nesta story.
- **Alternativa descartada.** Cache do navegador nos 200 da imagem; segunda largura para
  miniaturas.
- **Consequência.** O risco de 429 da AIC continua no `deferred-work.md` (D1 da 2.3); um
  429 real no teste manual vira evidência registrada, não mudança silenciosa. O front só
  reduz chamadas com `loading="lazy"` e a D13.

## 2. Decisões de detalhamento (D1 a D21)

D3, D7, D13, D16 e D20 foram aprovadas explicitamente em 25/10/2026, junto com o
refinamento da P2 (D1 revisada).

| ID | Decisão | Alternativa descartada | Origem |
| --- | --- | --- | --- |
| D1 | **Revisada (refinamento da P2).** Cada rota executa **um único statement**: `WITH clock AS MATERIALIZED (SELECT clock_timestamp() AS as_of) SELECT clock.as_of, lots.* FROM clock LEFT OUTER JOIN lots ON true` (no detalhe, `ON lots.id = :lot_id`). Um statement tem um só snapshot em `READ COMMITTED`; o CTE materializado avalia o relógio uma vez; o `LEFT JOIN` a partir do CTE devolve sempre ao menos uma linha, então há `as_of` mesmo sem lotes. Leitura em `read_public_snapshot(session)` / `read_public_lot_snapshot(session, lot_id)`; classificação e ordenação em funções puras com o `as_of` devolvido. `database_now` (2.4) não é usada nas rotas públicas. | Duas consultas (`database_now` + `SELECT`) em `READ COMMITTED` (versão anterior desta spec: snapshots diferentes); transação `REPEATABLE READ` (exige configurar o isolamento na `Session` antes do primeiro statement, sem ganho sobre um statement só); subconsulta escalar por linha (`clock_timestamp()` correria a cada linha sem o CTE materializado). | P2 refinada |
| D2 | Ciclo da sessão: a transação implícita do SQLAlchemy cobre a leitura; o handler monta os DTOs (objetos Pydantic, sem lazy load) e chama `session.rollback()` antes de devolver. Nada de `commit`, `FOR UPDATE` ou `FOR SHARE`. | Deixar a transação aberta até a saída da dependência `get_session` (depende do momento em que o FastAPI encerra a dependência); `commit` numa leitura. | P2, AD-19 |
| D3 | Desempate por `id ASC` nos três grupos, uma direção só. O `id` é UUID v4, sem significado temporal: espelhar a direção não diria nada. Comparação por `uuid.UUID` (inteiro de 128 bits). | `id DESC` nos encerrados, espelhando o `ends_at` (proposta da story P4 a). | P4 |
| D4 | Ordem de registro em `register_lot_routes`: `POST /api/lots`, `GET /api/lots/mine`, `GET /api/lots`, `GET /api/lots/{lot_id}`. Um teste fixa `índice(mine) < índice({lot_id})` em `app.routes`. | Outra estratégia (prefixo diferente, regex no parâmetro): mais complexa que a ordem já prevista pela 2.4. | 2.4 P9 |
| D5 | `as_of` e todos os timestamps saem em UTC com `Z` pela serialização Pydantic, como na 2.4 (a fração só some se os microssegundos forem 0). | Forçar 6 casas só no `as_of` (formato diferente dos outros campos). | P1 |
| D6 | `lot_id: uuid.UUID` no caminho; inválido → 422 do handler global (`loc ["path","lot_id"]`, tipo real fixado no teste), sem `no-store` (C4 da 2.3); inexistente → `error_response(404, "not_found", headers=NO_STORE)`. | 404 para formato inválido; validar por regex própria. | P6, 2.1 |
| D7 | Rotas do front: `/` (vitrine), `/lots/{uuid}` (UUID minúsculo com hífens), `/login`, `/auctioneer/lots/new` (Criar lote), `/auctioneer/lots` (Meus lotes). Qualquer outro caminho, inclusive barra final e `/lots/<não-uuid>`, → "Página não encontrada", sem chamar a API. | `/lots/new` e `/lots/mine` (colidem com `/lots/{id}`); `/painel/...` (português em identificador técnico); aceitar barra final. | P5, story P5 (a) |
| D8 | `returnTo` mora em `history.state` da entrada `/login`, nunca na URL; ao ler, passa por `parseRoute` e só vale se for rota interna conhecida (vitrine, lote, áreas do leiloeiro); senão `/`. "Entrar" faz `pushState`; o login bem-sucedido faz `replaceState` para o destino. Refresh em `/login` preserva o `state`; `/login` aberto direto → destino `/`. | `?next=` na URL (aceita destino arbitrário e exige validação de URL externa); só memória do React (perde no refresh). | P5 |
| D9 | Áreas do leiloeiro: anônimo → `replaceState` para `/login` com `returnTo`; `BIDDER` → vista "Área do leiloeiro" com link para a vitrine; `returnTo` de área do leiloeiro é ignorado (→ `/`) se quem entrou é `BIDDER`; 401 numa área do leiloeiro → `replaceState` para `/login` com `returnTo` e o aviso "Sua sessão expirou. Entre novamente." | Mandar o anônimo para a vitrine; 404 para o `BIDDER`. | 2.2, 2.4, P5 |
| D10 | "Sair" → `pushState('/')`. Enquanto a sessão for `AUCTIONEER`, `LotCreation` fica montado e oculto fora de `/auctioneer/lots/new` (preserva busca e rascunho, como na 2.4). | Ficar na página pública em que estava; desmontar `LotCreation` ao sair da rota. | P5, 2.4 D12 |
| D11 | Foco: cada vista tem um `h1` único com `tabIndex={-1}`, focado em navegação interna e em `popstate`, nunca no primeiro carregamento. Ao clicar num lote, a entrada da vitrine recebe `restoreLotId` (e `endedVisible`) por `replaceState`; no Back, depois do `GET`, o link desse lote recebe o foco (e entra na tela); sem ele, o `h1`. `history.scrollRestoration = 'manual'`; navegação nova rola ao topo. | Só rolar ao topo; restaurar rolagem do navegador (falha com conteúdo assíncrono). | CA12, P5 |
| D12 | Destaque = `live[0]`, senão `scheduled[0]`, senão vazio editorial. O lote em destaque não se repete no próprio rail; grupo que só tem o destaque mostra uma linha de contexto, sem imagem. | Repetir o destaque no rail (blueprint §6: não repetir imagem grande); omitir a seção. | Blueprint §5, §6 |
| D13 | "Encerrados": 6 itens iniciais; "Mostrar mais encerrados" revela mais 6, sem nova chamada; "Mostrando X de Y"; botão some quando tudo está visível. Uma constante `ENDED_STEP = 6`. | 12 (proposta da story P7 a): dobra as miniaturas iniciais contra o limite da AIC (P9). | P7, P9 |
| D14 | "Ao vivo" e "Próximos lotes" em rail horizontal sem limite, imagens `lazy`, `scroll-snap`, parte do próximo item visível. Botões "Anterior"/"Próximo" só ≥ 64rem e só quando há overflow, desabilitados nas pontas. | Grid que quebra linha (blueprint §7 pede rail com navegação lateral no desktop); botões sempre visíveis (controle sem função). | Blueprint §6, §7, §10 |
| D15 | Rótulos únicos: `scheduled` "Agendado", `live` "Ao vivo", `ended` "Encerrado"; status do encerrado "Encerrado, apurando resultado" (DESIGN §14, AD-19). Marcador "●" só no ao vivo, `aria-hidden`, sempre com o texto. Seção de agendados chama-se "Próximos lotes" (blueprint). | "Encerrado — apurando resultado" (travessão; o DESIGN e o AD-19 usam vírgula). | P8, CA2 |
| D16 | **Aprovada.** Vitrine e página do lote mostram uma linha discreta derivada de `as_of`: "Situação atualizada às HH:mm" quando o `as_of` cai no mesmo dia do navegador; senão "Situação atualizada em DD/MM/AAAA às HH:mm" (fuso do navegador, 24 h). Função pura `asOfText(asOf, today, timeZone?)` em `src/asOf.ts`; `today` só decide o formato do texto. Não inicia relógio, não se atualiza, não recalcula `phase`, não usa `Date.now()` para domínio. `as_of` ilegível → a linha não aparece. | Não exibir `as_of` (o rótulo velho fica sem explicação); "Situação em {data com fuso}" (versão anterior desta spec). | P1, P3 |
| D17 | `ArtworkImage` ganha a variante `card` (lazy, `alt=""` porque o nome do link vem do título, falha só visual). Destaque e página do lote usam `large` (eager). `object-fit: contain` em caixa de proporção fixa: nunca cortar a obra. | Reaproveitar `large` nos rails (eager, legenda dentro do link). | DESIGN §11, blueprint §11 |
| D18 | *(Escopo original; ampliado pela D21.)* Testes do front só `node --test` de lógica pura: `route.ts`, `lotPhase.ts`, `vitrine.ts`, `api/publicLots.ts` (type guards). Imports internos com extensão `.ts` (lição da 2.4). Cada módulo novo com lógica no nível do módulo é importado por um teste. | Vitest/Testing Library (dependência nova; 2.4 Q1). | 2.4 Q1 |
| D19 | *(Lista original; `package.json`, `package-lock.json`, `verify.sh`, `.dockerignore` e `.gitignore` deixaram de ser intocados pela D21.)* Intocados: `main.py`, `spa.py` (o fallback já serve `/lots/*`, `/login`, `/auctioneer/*`), `catalog.py`, `artic.py`, `access.py`, `seed.py`, migrations, `Dockerfile`, `vite.config.ts`, `package.json`. | Ajustar o fallback da SPA. | CA14, P9 |
| D20 | **Aprovada.** `policy_by_route` (teste da 2.2) passa a indexar por `(path, method, kind)`, com uma entrada por método da rota (WebSocket: `method = None`). Hoje a chave `(path, kind)` faria `GET /api/lots` (`PUBLIC`) sobrescrever `POST /api/lots` (`AUCTIONEER`) no mapa. Uma chave repetida no mapa passa a falhar alto, em vez de sobrescrever. O verificador `policy_problems` e os meta-testes não mudam; testes novos com dois métodos no mesmo caminho e com chave repetida. | Manter a chave e testar o POST à parte (o teste de igualdade perderia uma rota em silêncio); registrar o GET público noutro caminho (contraria a P1). | 2.2 P9, CA5 |
| D21 | **Acrescentada em 25/10/2026, depois do teste manual (não fazia parte da spec aprovada).** O teste manual justificou testes de navegador. Acrescentei `@playwright/test` (versão exata, só `devDependencies`) em `frontend/e2e/`, com a API simulada por interceptação de rede e o Chromium baixado por `npx playwright install chromium`; `npm run test:e2e`. **Fora do `verify` padrão**: opt-in com `VERIFY_E2E=1 ./verify.sh`. Tocam: `package.json` e `package-lock.json` (dependência e scripts, `typecheck` inclui `e2e/tsconfig.json`), `verify.sh` (gancho opt-in), `.dockerignore` e `.gitignore` (resultados do Playwright), `playwright.config.ts`. `real-stack.spec.ts` só roda com `E2E_REAL_BASE_URL`. Não reabre P1 a P9; `node --test` (D18) segue valendo para lógica pura. | Incluir o Playwright sempre no `verify` (exigiria o browser como pré-requisito silencioso); só em CI; teste de componente com Testing Library (continua fora). | Teste manual de 25/10/2026; review M1 |

## 3. Consequências registradas

- **D1 × READ COMMITTED.** O snapshot do statement é tirado no início dele, e o
  `clock_timestamp()` é avaliado logo depois, na execução: `snapshot <= as_of`. Logo,
  toda linha devolvida foi confirmada antes do `as_of` (inclusive o `created_at`, que é
  anterior ao commit). Um lote confirmado nos microssegundos entre o snapshot e o
  `as_of` fica de fora e aparece no próximo `GET`; nunca entra um lote que ainda não
  existia no `as_of`. (A versão anterior, com duas consultas, permitia o contrário.)
- **API leniente com o UUID.** `/api/lots/<UUID em maiúsculas>` responde 200 (parse do
  Pydantic); o front nunca gera esse formato e o trata como "não encontrado".
- **Soft 404.** `GET /qualquer-rota` responde 200 com `index.html` (fallback da 1.3) e a
  SPA mostra "Página não encontrada". `/api/*` nunca recebe HTML.
- **Back depois do login.** O destino substitui `/login` no histórico; um Back seguinte
  passa pela página de origem (que é o próprio destino) antes de sair.

## 4. Adendo de 25/10/2026: identidade ÁTRIO

Não é uma decisão da spec original nem reabre P1 a P9 ou D1 a D20. Depois do teste manual,
o produto passou a se chamar **ÁTRIO — Leilões de Arte** (nome de trabalho anterior: "Casa
de Leilões"). É mudança de marca e de direção visual, não de escopo funcional: nenhuma
funcionalidade das referências (lance, contagem regressiva, favoritos, busca, carteira) foi
antecipada, e a vitrine, a navegação e o contrato da API ficaram como aprovados.

- **Onde mora o nome:** `frontend/src/brand.ts` (`PRODUCT_NAME`, `PRODUCT_TAGLINE`,
  `documentTitle`); símbolo em `AtrioMark.tsx` e `public/favicon.svg`.
- **O que não mudou:** repositório, bancos, tabela `lots`, módulos, `/api/*`, URLs e
  nomes técnicos (AD-30). Descartei um rename técnico porque a marca é de interface.
- **Texto histórico:** D6 a D20 e as seções acima citam "Casa de Leilões" onde a spec foi
  escrita assim; preservei, e a correspondência está em `frontend-navigation.md` §9.
