---
id: SPEC-story-2-4-criacao-lotes
companions:
  - decisions.md
  - database-schema.md
  - backend-contract.md
  - seed-plan.md
  - frontend-lot-creation.md
  - test-plan.md
  - implementation-map.md
  - ../spec-story-2-3-busca-obras-aic/backend-contract.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md
---

> **Contrato canônico.** Esta SPEC e os arquivos em `companions:` são o contrato
> completo da Story 2.4. P1 a P9 foram aprovadas pelo Joaodionizio antes desta spec
> e não são reabertas (`decisions.md` §1). As decisões D1 a D14 são detalhamento
> dentro dessas aprovações (`decisions.md` §2). Q1 foi aprovada (`node --test`) e os
> ajustes A2 a A4 da aprovação final estão em `decisions.md` §3. Nenhuma questão
> aberta. A 2.4 reutiliza `catalog.get_artwork()` e o contrato `ArtworkDetail` da 2.3
> (companion adotado).

# Story 2.4: criação de lotes pelo leiloeiro e lote demo semeado

## Why

Mandato do desafio (FR3 e a parte de lote do FR19): o leiloeiro transforma uma obra
elegível do catálogo da 2.3 em lote, e o avaliador encontra um lote demo aberto sem
precisar agir. É o primeiro dado de negócio persistido e o ponto de partida do fluxo
vertical (AD-16): a 2.5 exibe, a 3.x dá lance, a 4.x encerra. Dois riscos guiam o
desenho: um cliente adulterado gravar metadados falsos de obra (por isso o servidor é
a única fonte do snapshot) e o lote depender da AIC depois de criado (por isso o
snapshot é copiado e nenhuma leitura de lote fala com a AIC).

## Capabilities

- **CAP-1**
  - **intent:** O `AUCTIONEER` cria um lote a partir de uma obra elegível, com termos próprios, e recebe o lote gravado.
  - **success:** `POST /api/lots` com `{external_id, starting_bid_cents, min_increment_cents, starts_at?, ends_at}` e sessão `AUCTIONEER` → 201 `LotResponse` (`backend-contract.md` §3) com `Cache-Control: no-store`; a linha em `lots` tem os mesmos valores da resposta; `auctioneer_id` é o `id` do usuário da sessão.
- **CAP-2**
  - **intent:** O snapshot gravado vem só do servidor, nunca do cliente.
  - **success:** Só a criação manual resolve a obra: `resolve_artwork_for_lot(client, external_id)` chama `catalog.get_artwork()` uma única vez por criação, e `create_lot` grava os 11 campos de `database-schema.md` §2 do `ArtworkDetail` que obteve; qualquer campo além dos cinco do corpo (`auctioneer_id`, `title`, `artist_display`, `image_id`, `is_public_domain`, `is_demo`, `snapshot`...) → 422 `extra_forbidden`, sem chamada à AIC e sem linha; nenhum byte de imagem é gravado.
- **CAP-3**
  - **intent:** Obra inelegível ou catálogo indisponível recusam a criação sem gravar nada.
  - **success:** AIC 404, `NOT_PUBLIC_DOMAIN` ou `NO_IMAGE` → 422 `artwork_not_eligible` (um código só, sem motivo no corpo; motivo só no log); qualquer `CatalogUnavailable` (timeout, conexão, 3xx, 403, 429, 5xx, JSON inválido, formato incompatível) → 503 `catalog_unavailable`; nos dois casos a contagem de `lots` não muda e nenhuma transação de escrita foi aberta.
- **CAP-4**
  - **intent:** Lance inicial e incremento são dinheiro exato em centavos de ponta a ponta.
  - **success:** A mesma faixa, `1 <= valor <= 9007199254740991` (`Number.MAX_SAFE_INTEGER`, limite técnico, não comercial), vale na API, no serviço (`LotTerms`, também usado pelo seed) e no banco (`BIGINT` com CHECK `> 0 AND <= 9007199254740991` em cada coluna); `100.0`, `"100"`, `true`, `0`, `-1`, `1e2` e 9007199254740992 → 422 na API; no PostgreSQL real, 1 e o máximo entram, 0, negativo e máximo + 1 são recusados; o front converte reais em centavos por texto (`frontend-lot-creation.md` §4), sem `parseFloat`, `Number(...)` sobre texto com vírgula nem aritmética de ponto flutuante, e esse conversor tem teste automatizado por `node --test` no `verify` (Q1).
- **CAP-5**
  - **intent:** Início e fim seguem uma regra única, decidida com a hora do PostgreSQL.
  - **success:** Horários só como string ISO 8601 com offset; sem offset, número ou data sem hora → 422; `starts_at` ausente/`null` → `starts_at = now`; `starts_at <= now` → 422 `starts_at_not_in_future`; `ends_at <= início efetivo` → 422 `ends_at_not_after_start`; `now` é um único `clock_timestamp()` lido dentro da transação de escrita e também vira `created_at`; tudo gravado e devolvido em UTC (`Z`); limite exato coberto com `now` fixo.
- **CAP-6**
  - **intent:** Só o `AUCTIONEER` cria e lista os próprios lotes, e recusas não geram tráfego externo nem escrita.
  - **success:** As duas rotas declaram `AccessPolicy.AUCTIONEER` por `api_route`; sem sessão → 401, `BIDDER` → 403, ambos com zero requisições ao transporte falso da AIC e contagem de `lots` inalterada; `Origin` estrangeiro ou ausente → 403 `csrf_*`, sem JSON → 415, handler não roda; o teste de política da 2.2 passa sem mudar o verificador.
- **CAP-7**
  - **intent:** A criação é atômica e não segura transação aberta enquanto espera a AIC.
  - **success:** Ordem da `backend-contract.md` §5; a leitura da autenticação é encerrada antes da chamada à AIC (statements no banco durante a chamada: zero); uma exceção forçada depois do `INSERT` e antes do commit → 500 genérico e zero linhas.
- **CAP-8**
  - **intent:** O leiloeiro vê os próprios lotes, inclusive o recém-criado, sem depender da AIC.
  - **success:** `GET /api/lots/mine` → 200 `{"items": [LotResponse...]}` com **todos** os lotes de `auctioneer_id` da sessão, ordem `created_at DESC, id DESC`, sem paginação e sem limite, `no-store`; vazio → `{"items": []}`; lote de outro `AUCTIONEER` nunca aparece; com o transporte da AIC sempre falhando a resposta é igual; durante a chamada o banco só recebe `SELECT`; não aceita `auctioneer_id` por query.
- **CAP-9**
  - **intent:** A aplicação sempre inicia com um lote demo aberto, sem rede e sem duplicar.
  - **success:** `python -m app.seed` cria, numa única transação sob `pg_advisory_xact_lock`, um lote `is_demo = true` da obra 27992 a partir de `backend/app/seed_data/demo_artwork.json`, pelo mesmo `create_lot` da criação manual e sem passar por `resolve_artwork_for_lot`, `catalog.get_artwork`, `ArticClient` nem `httpx` (teste com esses pontos trocados por funções que falham), ligado ao leiloeiro semeado, com `starts_at = now`, `ends_at = now + 72 h`, 10000/1000 centavos, só se não houver `is_demo AND ends_at > now`; nunca `UPDATE`/`DELETE` em `lots`; demo encerrado continua idêntico e um novo nasce; duas execuções simultâneas criam no máximo um; sem `APP_ORIGIN`, `JWT_SECRET`, `app.main` e rede (`seed-plan.md`).
- **CAP-10**
  - **intent:** O leiloeiro cria lote pela interface, em português, com revisão antes de publicar e confirmação depois.
  - **success:** Roteiro manual (`test-plan.md` §9) passa: busca → detalhe → "Criar lote com esta obra" → formulário (obra só leitura) → "Revisar lote" → "Publicar lote" → confirmação com os valores devolvidos pelo servidor → "Meus lotes" com o lote novo no topo; erros pelo `code`/`details.type`; 503 mantém o que foi digitado e oferece "Tentar novamente"; o botão de publicar fica desabilitado durante o envio e um segundo clique não gera segunda requisição.
- **CAP-11**
  - **intent:** O esquema nasce por migration reversível e é verificado no PostgreSQL real.
  - **success:** Revisão `0003` cria `lots` com tipos, FK `ON DELETE RESTRICT`, CHECKs e índice de `database-schema.md`; `downgrade` remove a tabela; `GET /health` e `create_app()` continuam sem banco e sem rede.
- **CAP-12**
  - **intent:** O contrato novo fica documentado e fixado por teste.
  - **success:** OpenAPI ganha `/api/lots` e `/api/lots/mine` depois de `/api/catalog/images/{image_id}`, com `ErrorResponse` em 401/403/422/503 no POST e 401/403 no GET, e schemas `CreateLotRequest`, `LotResponse`, `MyLotsResponse` com exatamente os campos do contrato; `MESSAGES` ganha só `artwork_not_eligible`.
- **CAP-13**
  - **intent:** A entrega fica verificada e documentada, sem antecipar a 2.5.
  - **success:** `./verify.sh` completo, já com a etapa "Frontend: test", passa com saída real registrada; README, `docs/uso_de_ia.md`, Q4 em `docs/ARQUITETURA.md` (questões e histórico, sem AD nova), story 2.4 e `sprint-status.yaml` atualizados, com a conferência de coerência documental da story antes de `done`.

## Constraints

- AD-3: dinheiro só em inteiros de centavos, `BIGINT`, sufixo `_cents`; nenhum `float` em nenhuma camada.
- AD-6/AD-26: a regra de horário é função pura que recebe `now`; a aplicação lê `clock_timestamp()` uma vez, dentro da transação de escrita (não há trava de lote: a linha é nova); o navegador nunca é a autoridade (a tela só valida de forma preventiva, com `now` injetado, e o servidor revalida tudo).
- AD-12/AD-22/AD-23: a AIC só é chamada no `POST`, antes da transação; leitura de lote e seed nunca chamam a AIC; `image_id` persistido, bytes nunca.
- Dois níveis na criação (A3): `resolve_artwork_for_lot` (integração externa, só a criação manual) e `create_lot` (regra e persistência, sem rede, sem cliente HTTP no parâmetro, compartilhada com o seed). Compartilha-se a regra, nunca a dependência externa.
- Dinheiro: uma faixa só, `1..9007199254740991`, na API, no serviço e no banco (A4).
- AD-11/2.2: rotas só por `api_route`; dependências e handlers `def`; política resolve antes do corpo.
- AD-19/AD-29: `GET /api/lots/mine` nunca escreve; escrita só por `POST` JSON com `Origin` validado.
- 2.1: erro só pelo envelope único; mensagens só do catálogo `MESSAGES`; 422 com `details` `{loc, type}`.
- 2.3: reutilizar `catalog.get_artwork()`, `LookupStatus`, `image_url_for`, `IMAGE_ID_PATTERN`, `MAX_EXTERNAL_ID`; nenhum parser novo da AIC; `catalog.py` e `artic.py` intocados.
- P3: nenhuma coluna `status`; o esquema permite colunas aditivas futuras sem desmontar nada.
- P7: sem `UNIQUE` em `external_id` e sem chave de idempotência.
- Seed: fixture dentro de `backend/app/` (o `.dockerignore` exclui `backend/tests`); o seed não importa `app.main`.
- AD-4: TypeScript simples; sem React Router, sem biblioteca de UI; nenhuma dependência nova de front (o teste usa `node:test`, embutido no Node 24).
- AD-30: código, banco e API em inglês; interface em português.
- Testes existentes só ganham acréscimos ou ajuste de limpeza (D11); nenhuma asserção é afrouxada.

## Non-goals

- Vitrine, página pública do lote, `GET /api/lots`, `GET /api/lots/{lot_id}`, roteador, fase "ao vivo/agendado/encerrado" ou "Encerrado, apurando resultado" em qualquer resposta (2.5, Q8).
- Lances, carteira, saldo, anti-sniping, WebSocket, encerramento, liquidação, catch-up, auditoria, comprovante, resultado e total recebido.
- Cancelar, editar ou excluir lote; busca, filtro e paginação de lotes (OPT1).
- Deduplicação de envio no servidor; regra "uma obra por lote".
- Duração mínima, horizonte máximo, teto comercial de valor.
- Cache da AIC, miniatura menor, limite de requisições do proxy de imagem.
- Ferramenta de teste de front-end com dependência nova; teste de componente ou de DOM.

## Success signal

- Logado como `auctioneer@example.com`, busco "seurat", abro a obra 27992, crio um lote com início "Assim que eu publicar", fim amanhã, R$ 1.250,00 e R$ 50,00, reviso, publico e vejo a confirmação com `starts_at` do servidor; "Meus lotes" mostra o lote novo no topo e o demo semeado. Com a rede externa desligada, "Meus lotes" continua listando (só as imagens caem no placeholder) e publicar mostra o erro do catálogo sem perder o que digitei. `./verify.sh` passa, e um banco vazio sobe com exatamente um lote demo aberto.

## Assumptions

- O título nulo na AIC é aceito e gravado como `null` (story P1, sub-ponto), exibido como "Sem título".
- O `ArtworkDetail` da 2.3 não muda nesta story; se mudar, o snapshot muda junto.
- O PostgreSQL usa o isolamento padrão `READ COMMITTED` nas conexões da aplicação e do seed (o algoritmo do seed depende disso; `seed-plan.md` §3).
- Recarregar a página volta à vista "Criar lote" no estado inicial, mantendo a sessão.
- O type stripping do Node (`process.features.typescript === "strip"`, conferido no Node 24.22 local) roda `money.test.ts` sem transpilador; o `node:24-slim` do Docker só compila o front e não roda o teste.
