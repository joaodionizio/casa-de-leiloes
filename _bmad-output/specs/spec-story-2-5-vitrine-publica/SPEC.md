---
id: SPEC-story-2-5-vitrine-publica
companions:
  - decisions.md
  - backend-contract.md
  - public-lot-dtos.md
  - frontend-navigation.md
  - frontend-vitrine.md
  - test-plan.md
  - implementation-map.md
  - ../spec-story-2-4-criacao-lotes/backend-contract.md
  - ../spec-story-2-3-busca-obras-aic/backend-contract.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../planning-artifacts/VITRINE-BLUEPRINT.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/2-5-vitrine-pública-e-página-do-lote.md
---

> **Atualização R6.4-01 — 29/10/2026:** o contrato público vigente está em
> [public-lot-dtos.md](public-lot-dtos.md). A decisão humana substitui neste
> documento a proibição histórica de `settlement_status`, as contagens 9/17 e
> o rótulo incondicional de `ended`: resumo/detalhe têm 10/18 campos, incluindo
> `settlement_status` obrigatório (`pending|settled`), derivado exclusivamente
> do settlement persistido. Vitrine: `ended+pending` → “Encerrado, apurando
> resultado”; `ended+settled` → “Encerrado”. Os demais trechos registram o
> escopo original da 2.5.


> **Contrato canônico.** Esta SPEC e os arquivos em `companions:` são o contrato
> completo da Story 2.5. P1 a P9 foram aprovadas pelo Joaodionizio antes desta spec e
> **não são reabertas** (`decisions.md` §1). D1 a D20 detalham essas aprovações e os
> pontos que a story deixou "para o `bmad-spec`" (`decisions.md` §2). Nenhuma questão
> aberta. A 2.5 consome o modelo `Lot` e `image_url_for` reais da 2.4 e da 2.3
> (companions adotados); P2 foi refinada em 25/10/2026 (mesmo snapshot para `as_of` e
> lotes, D1).

# Story 2.5: vitrine pública e página do lote

## Why

Mandato do desafio (FR6, parte do NFR2): qualquer pessoa, sem login, vê os lotes
separados em ao vivo, agendados e encerrados e abre cada um. Hoje o anônimo cai no
formulário de login e o `BIDDER` vê uma tela vazia; a 2.5 transforma os lotes que a 2.4
grava em produto público navegável, com URL própria por lote, que a sala (3.5, 4.1) e o
comprovante (5.2) vão reaproveitar. Três riscos guiam o desenho: dois relógios
divergirem (por isso o estado sai só do servidor, com um instante do PostgreSQL por
leitura), uma leitura alterar estado (AD-19) e o contrato público vazar dados internos.

## Capabilities

- **CAP-1**
  - **intent:** Qualquer pessoa obtém a vitrine completa, agrupada e ordenada pelo servidor, sem sessão.
  - **success:** `GET /api/lots` (`AccessPolicy.PUBLIC`) → 200 `PublicLotsResponse` `{as_of, live, scheduled, ended}` com **todos** os lotes, sem paginação nem limite, `Cache-Control: no-store`; cada lote aparece em exatamente um grupo; ordem `live` por `ends_at ASC, id ASC`, `scheduled` por `starts_at ASC, id ASC`, `ended` por `ends_at DESC, id ASC`; banco vazio → 200 com `as_of` preenchido e três listas vazias; anônimo, `BIDDER`, `AUCTIONEER` e cookie inválido recebem o mesmo corpo para o mesmo banco e o mesmo instante.
- **CAP-2**
  - **intent:** Qualquer pessoa obtém a página pública de um lote pelo identificador.
  - **success:** `GET /api/lots/{lot_id}` (`PUBLIC`) → 200 `PublicLotDetailResponse` `{as_of, lot}`, `no-store`; UUID válido inexistente → 404 `not_found` com `no-store`; `lot_id` que não é UUID → 422 `validation_error` com `details` `[{"loc": ["path","lot_id"], "type": <tipo real do Pydantic>}]`; erro inesperado → 500 genérico da 2.1.
- **CAP-3**
  - **intent:** O estado temporal de cada lote é derivado no servidor com um único instante do PostgreSQL por leitura, e esse instante e as linhas lidas pertencem ao mesmo snapshot.
  - **success:** Função pura `lot_phase(starts_at, ends_at, now)` → `scheduled` se `now < starts_at`, `live` se `starts_at <= now < ends_at`, `ended` se `now >= ends_at`, exata em microssegundos, `now` ingênuo → `ValueError`; cada rota executa **exatamente um** statement, com `clock_timestamp()` uma única vez num CTE `MATERIALIZED` e as linhas de `lots` por `LEFT OUTER JOIN` a partir dele (`backend-contract.md` §3), então `as_of` e o conjunto de lotes vêm do mesmo snapshot de `READ COMMITTED`; todo lote devolvido foi confirmado antes do `as_of` (`created_at <= as_of`), e um lote confirmado por outra conexão imediatamente antes da leitura aparece com essa garantia (teste por injeção determinística); todos os itens são classificados com o `as_of` devolvido; nenhum `clock_timestamp()` por linha; o navegador nunca classifica nem reclassifica.
- **CAP-4**
  - **intent:** As leituras públicas nunca alteram estado nem esperam travas.
  - **success:** Nas duas rotas o banco só recebe o statement de leitura (`WITH … SELECT`, sem `FOR UPDATE`/`FOR SHARE`, `INSERT`, `UPDATE`, `DELETE`); `lot_rows` idênticas antes e depois, inclusive de lote vencido; o seed não roda; com outra conexão segurando `UPDATE` não confirmado num lote, as duas rotas respondem dentro do timeout do teste e mostram o valor confirmado (MVCC); a transação de leitura é encerrada pelo handler antes de devolver a resposta.
- **CAP-5**
  - **intent:** O contrato público expõe só o que a vitrine e a página do lote mostram.
  - **success:** Chaves exatas de `public-lot-dtos.md` em cada item e no detalhe; nenhuma resposta nem schema público contém `auctioneer_id`, `is_demo`, `created_at`, `image_id`, `email`, `password_hash`, `role`, `status` ou `settlement_status`; `image_url` = `/api/catalog/images/{image_id}`; dinheiro em centavos inteiros exatos; timestamps em UTC com `Z`; o lote demo é indistinguível de um lote manual.
- **CAP-6**
  - **intent:** A vitrine e a página do lote não dependem da AIC para nada além dos bytes da imagem.
  - **success:** Com o transporte falso da AIC sempre falhando, as duas rotas devolvem o mesmo corpo e `fake.requests == []`; nenhum componente público chama `/api/catalog/artworks*`; a mídia usa a rota existente `/api/catalog/images/{image_id}` sem mudança de cabeçalho, tamanho ou cache (P9).
- **CAP-7**
  - **intent:** `GET /api/lots/mine` continua privado e não é capturado pelo detalhe.
  - **success:** Em `app.routes`, `/api/lots/mine` vem antes de `/api/lots/{lot_id}`; `GET /api/lots/mine` segue 401 anônimo, 403 `BIDDER`, 200 `AUCTIONEER`; `PUT`/`DELETE /api/lots` seguem 405; `POST /api/lots` da 2.4 intacto.
- **CAP-8**
  - **intent:** A aplicação abre na vitrine pública e o login é uma ação explícita.
  - **success:** `/` sem sessão mostra a vitrine (nunca o formulário); "Entrar" no header leva a `/login`; depois do login a pessoa volta à página pública de onde clicou (vitrine ou `/lots/{id}`), ou à vitrine se abriu `/login` direto; um `returnTo` fora das rotas internas conhecidas é ignorado; "Sair" leva à vitrine; o header segue o papel (`frontend-navigation.md` §5); criação de lote e "Meus lotes" da 2.4 continuam funcionando em URLs próprias.
- **CAP-9**
  - **intent:** Cada vista tem URL real, que funciona por clique, Back/Forward, refresh e link direto.
  - **success:** `parseRoute`/`routePath` puros testados por `node --test`; cliques em `<a href>` internos viram `pushState` (clique com modificador abre aba nova normalmente); `popstate` troca a vista; em produção `GET /lots/<uuid>`, `/login` e `/auctioneer/lots` recebem `index.html` e `GET /api/lots/<uuid>` recebe JSON; no Vite, o mesmo; caminho desconhecido mostra "Página não encontrada" sem chamar a API.
- **CAP-10**
  - **intent:** O visitante entende o que está ao vivo, o que vem depois e o que terminou, numa composição editorial de casa de leilões.
  - **success:** Roteiro manual (`test-plan.md` §9) passa: destaque image-led (`live[0]`, senão `scheduled[0]`, senão vazio editorial), seções "Ao vivo", "Próximos lotes" e "Encerrados" com densidade decrescente, estado sempre em texto ("Ao vivo", "Agendado", "Encerrado, apurando resultado"), lance inicial em reais por `formatCents`, horários absolutos com fuso, encerrados com 6 itens e "Mostrar mais encerrados" local; estados de carregando, erro com "Tentar novamente", vazio por grupo e imagem quebrada; sem "Dar lance", countdown, carteira ou link sem destino.
- **CAP-11**
  - **intent:** A página do lote mostra a obra e os termos do leilão, sem antecipar a sala.
  - **success:** Roteiro manual: imagem ou placeholder, título ("Sem título" se `null`), artista, data, técnica, dimensões, departamento, tipo, crédito, nº no acervo, link da fonte identificado como externo, lance inicial e incremento mínimo em reais, início e término com fuso, estado em texto; `ended` mostra "Encerrado, apurando resultado" sem afirmar vencedor; estados carregando, não encontrado e erro do servidor; nenhum controle de lance, nem desabilitado.
- **CAP-12**
  - **intent:** Vitrine, página do lote e login funcionam em desktop, 375 px e 320 px, por teclado e leitor de tela.
  - **success:** Sem rolagem horizontal global nas três larguras com títulos longos, R$ 90.071.992.547.409,91 e datas; um `h1` por vista, focado ao navegar; foco visível; cada lote é um link com nome que inclui o título; `aria-current="page"` no item ativo do header; nada essencial depende de hover (`frontend-vitrine.md` §8 e §9).
- **CAP-13**
  - **intent:** O contrato novo fica documentado e fixado por teste, e a entrega verificada.
  - **success:** OpenAPI com `/api/lots` (`get` e `post`), `/api/lots/mine` e `/api/lots/{lot_id}` nessa ordem, schemas públicos com propriedades exatas e `LotPhase` com os três valores; `policy_by_route` indexado por `(path, method, kind)` e `EXPECTED_POLICIES` com `GET /api/lots` e `GET /api/lots/{lot_id}` `PUBLIC`, `POST /api/lots` e `GET /api/lots/mine` `AUCTIONEER` (D20); `./verify.sh` completo passa com saída real; README, `docs/uso_de_ia.md`, Q8 em `docs/ARQUITETURA.md` (questões e histórico, sem AD nova), `CLAUDE.md` (resumo da Q8), `deferred-work.md`, story 2.5 e `sprint-status.yaml` atualizados na implementação, com a conferência documental da story antes de `done`.

## Constraints

- AD-6/AD-26 e P2 (refinada): um `clock_timestamp()` por leitura, avaliado uma vez no mesmo statement que lê os lotes; `as_of` e o conjunto de linhas pertencem ao mesmo snapshot; nunca duas consultas independentes em `READ COMMITTED`, nunca `clock_timestamp()` por linha, nunca trava; a regra recebe `now`; nenhum relógio do navegador decide estado.
- AD-19/AD-29: GET/HEAD/OPTIONS nunca escrevem, liquidam, rodam seed nem travam lote; `ended` é só fim temporal.
- P3: nenhum temporizador, polling, countdown nem `Date.now()` usado para estado no front.
- P7: nenhuma paginação, `LIMIT` ou truncamento na API; "Mostrar mais" nunca chama a API.
- P8: nenhuma coluna, campo, enum ou valor de liquidação; o único eixo é `phase`.
- P9 e AD-22: rota de imagem da 2.3 intacta (`no-store`, 843 px, sem cache); bytes nunca guardados.
- Sem migration, coluna `status`, `settlement_status` nem índice novo; necessidade real de schema volta como questão bloqueante.
- AD-11/2.2: rotas só por `api_route`, `PUBLIC` (a resposta não depende de quem pede, então a sessão nem é lida); handlers e dependências `def`.
- AD-4 e P5: sem React Router nem dependência de runtime nova; TypeScript simples; navegação por History API própria. *(A única dependência acrescentada depois, `@playwright/test`, é de desenvolvimento; ver D21.)*
- 2.4 D6/P9: `LotResponse` e "Meus lotes" continuam privados e inalterados; os DTOs públicos são outros.
- DESIGN/EXPERIENCE/VITRINE-BLUEPRINT: obra protagonista, roxo só como assinatura, estado nunca só por cor, nenhum controle sem função, sem `LotCard` universal, sem cara de SaaS.
- AD-30: código, API e rotas do front em inglês; interface em português.
- Testes existentes só ganham acréscimos, exceto as asserções que fixavam o contrato antigo (`GET /api/lots` → 405; `paths[-2:]`; `set(paths["/api/lots"]) == {"post"}`), trocadas conscientemente pelo contrato novo, e a chave de `policy_by_route`, que ganha o método para não colapsar POST e GET de `/api/lots` (D20).

## Non-goals

- Lance, carteira, saldo, histórico, posição, "você está ganhando", anti-sniping, sala, WebSocket, countdown, polling (3.x, 4.x).
- Fechamento, liquidação, catch-up, resultado, vencedor, total recebido, `settlement_status` (4.3 a 4.5).
- Auditoria e comprovante (5.x); cancelamento e o filtro de cancelados (3.6).
- Busca, filtro e paginação de lotes (OPT1, 6.5); links "Ver todos", "Ver agenda", "Ver arquivo"; âncoras no header.
- Cache novo, miniatura menor ou limite de requisições da rota de imagem.
- Teste de componente ou DOM; ferramenta de teste nova no front. *(Escopo original, aprovado antes do teste manual. Em 25/10/2026, a partir da evidência manual, decidi acrescentar o Playwright como camada de navegador opt-in; ver D21 em `decisions.md`. Teste de componente/DOM continua fora.)*
- Dark mode (6.7); revisão visual global (6.2).
- Mudar `main.py`, `spa.py` ou o fallback da SPA (já servem deep-links).

## Success signal

- Numa aba anônima, abro `/` e vejo o demo semeado em destaque como "Ao vivo", com "Lance inicial R$ 100,00" e o término com fuso; abro o lote, recarrego com Cmd+R e continuo nele; Back volta à vitrine com o foco no lote; colo `/lots/<uuid>` numa aba nova e ele abre; "Entrar" como `bidder1@example.com` me devolve à página do lote. Com a rede externa cortada, tudo continua, exceto as imagens no placeholder. `./verify.sh` passa.

## Assumptions

- O SQLAlchemy 2.x instalado emite `WITH clock AS MATERIALIZED (…)` por `CTE.prefix_with("MATERIALIZED")` e o `LEFT OUTER JOIN lots ON true` por `outerjoin(Lot, true())`; o teste confere o SQL emitido.
- O tipo de erro do Pydantic para UUID inválido no caminho é `uuid_parsing`; o teste fixa o tipo real observado.
- O FastAPI 0.162 com `uuid.UUID` no caminho aceita também UUID com maiúsculas ou sem hífens (parse leniente do Pydantic); o front só gera e só aceita o formato minúsculo com hífens.
- `history.state` sobrevive ao refresh na mesma entrada (comportamento dos navegadores atuais); se não sobreviver, o login cai na vitrine, que é o destino seguro.
- O fallback do Vite em desenvolvimento serve `index.html` a `/lots/<uuid>` (UUID não tem ponto); conferido no roteiro manual.
