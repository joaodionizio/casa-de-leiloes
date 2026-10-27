# Trabalho adiado

## Deferred from: code review of 2-1-formato-de-erros-e-validacao-de-origin.md (24/10/2026)

- O `loc` do 422 pode ecoar chaves escolhidas pelo cliente em modelos `dict[str, ...]` ou `extra="forbid"`, e `details` não tem limite de itens. Inalcançável com as rotas atuais; mudar o conteúdo do `loc` exige rever a D1 da 2.1.
- **Resolvido administrativamente em 26/10/2026:** este review registrou
  `epic-1: in-progress` e 1.4 `review`. O sprint já tinha 1.4 `done`; corrigi o
  cabeçalho da story e Epic 1 para `done`, com base nas evidências públicas da
  própria 1.4. Não executei novo deploy nem inventei review agregado histórico;
  integração retrospectiva dos Epics 1/2 concluída e aprovada posteriormente,
  conforme registro final abaixo.

## Deferred from: code review of 2-2-login-papéis-e-política-de-acesso.md (24/10/2026)

- Para a Story 4.1: `websocket_route` só funciona hoje com `AccessPolicy.PUBLIC`. Com `OPTIONAL`, `AUTHENTICATED` ou papel, as dependências esperam `Request` e a conexão quebra (`TypeError: require_user() missing 1 required positional argument: 'request'`, reproduzido no review). Decidir na 4.1 se `websocket_route` fica limitado a `PUBLIC` (recusando outra política no registro) ou se o WebSocket ganha um mecanismo de autenticação próprio.

## Deferred from: code review of 2-3-busca-de-obras-no-art-institute-of-chicago.md (24/10/2026)

- Chamadas repetidas de mídia à AIC (D1): a rota `GET /api/catalog/images/{image_id}` é pública, sem cache (`no-store`) e serve a imagem de 843 px também para as miniaturas. Uma busca com 20 resultados pode disparar até 20 chamadas ao IIIF, e a miniatura e a imagem grande da mesma obra usam a mesma URL. Não sei se a cota do IIIF é compartilhada com a da API (60 req/min por IP anônimo na documentação). Cache de navegador ou de servidor, miniatura menor e limite de requisições na nossa rota ficam fora da Story 2.3; decidir na 2.5 (vitrine pública usa as mesmas imagens), medindo o 429/503 real.
- A guarda de rede dos testes (`tests/conftest.py`, `socket.getaddrinfo`) não trata `HTTPS_PROXY`/`ALL_PROXY`: com um proxy no ambiente, um cliente httpx sem `MockTransport` poderia conectar ao proxy local em vez de resolver o host externo. LOW teórico, hoje inalcançável (os testes do catálogo injetam `MockTransport` e o teste do cliente padrão falha de forma visível); revisitar se algum teste passar a criar um cliente httpx real.

## Deferred from: implementation of 2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md (24/10/2026)

- `Idempotency-Key` (P7): criar lote não tem idempotência no servidor. Um timeout depois do commit seguido de nova tentativa manual pode criar dois lotes da mesma obra; a interface manda conferir "Meus lotes" antes de repetir. Revisitar se o duplo envio aparecer na prática.
- Paginação de "Meus lotes" (A2): `GET /api/lots/mine` devolve todos os lotes do leiloeiro, sem limite. Aceitável na escala do desafio; com volume real, a resposta cresce e as miniaturas disparam muitas chamadas de mídia à AIC (D1 da 2.3). Paginar ou carregar sob demanda quando houver necessidade.
- Para a Story 2.5: registrar `GET /api/lots/{lot_id}` **depois** de `GET /api/lots/mine`; senão "mine" cai no parâmetro. `GET /api/lots` (público) também nasce lá; hoje responde 405.
- Para a Story 3.6: o predicado do demo aberto ganha `AND cancelled_at IS NULL` (`app/seed.py`, `seed_demo_lot`). Para a 4.4: o catch-up de fechamento entra antes do `run_seed` na inicialização.
- Testes automatizados de componentes do front-end: a 2.4 só testa lógica pura (`money.ts`, `lotTime.ts` e `lotDraft.ts`). Componentes (formulário, revisão, "Meus lotes") dependem do teste manual e do code review.
- O `loc` do 422 de `extra_forbidden` em `POST /api/lots` contém o nome da chave enviada pelo cliente (item já deferido na 2.1; aqui o corpo é um modelo com `extra="forbid"`).

## Deferred from: code review of 2-4-criação-de-lotes-pelo-leiloeiro-e-lote-demo-semeado.md (25/10/2026)

- `frontend-lot-creation.md` §1 (linha AD-6) ainda diz "nenhuma comparação com o relógio do navegador", contradizendo a revisão de 25/10/2026 no §5 (validação preventiva com `now` injetado). Corrigir na spec quando eu decidir. **Resolvido em 25/10/2026**, antes do fechamento da 2.4: decidi corrigir, a spec foi sincronizada (§1 e §5, `SPEC.md`, `decisions.md`) e o re-review final validou. Mantido aqui só como histórico.

## Deferred from: implementation of 2-5-vitrine-pública-e-página-do-lote.md (25/10/2026)

- Lista pública sem paginação (P7): `GET /api/lots` devolve todos os lotes, e os demos encerrados se acumulam (um novo a cada boot depois de 72 h). A tela limita a renderização a 6 encerrados com "Mostrar mais", mas a resposta JSON cresce com o tempo. O OPT1 (6.5), com busca e filtro, pode trazer paginação.
- Imagens sem cache e risco de volume/429 (D1 da 2.3, mantido pela P9): a vitrine multiplica as chamadas ao proxy público de imagem (843 px, `no-store`) contra o limite de 60 req/min por IP da AIC. Cada rail renderiza todas as miniaturas (`lazy`), então um 429 real pode mostrar placeholders. Registrar a evidência do teste manual (429/503 observado ou não), sem mudar a estratégia. **Registro (25/10/2026, review L4):** no teste manual da Story 2.5 *não* foi observado novo 429 da AIC nem novo 503 de imagem nesta rodada. A observação manual de 503 de imagem com placeholder funcionando é da Story 2.3 e **não** é evidência manual da 2.5.
- Para a Story 3.6: o filtro de cancelados (`cancelled_at IS NULL`) entra em `read_public_snapshot` e `read_public_lot_snapshot` **na condição do `LEFT OUTER JOIN`**, nunca num `WHERE` (o `WHERE` apagaria a linha do `as_of` quando não sobra lote), além do predicado do seed já registrado acima.
- Componentes do front sem teste unitário de DOM: a 2.5 testa lógica pura com `node --test` e, depois do teste manual (25/10/2026), tem testes de navegador com Playwright (`frontend/e2e/`, API simulada, só Chromium) para navegação, foco, layout e imagem quebrada. Continua sem teste de componente isolado (React Testing Library) e sem Firefox/WebKit; o visual real depende do meu olhar e do code review. A 2.4 (formulário de criação, revisão, "Meus lotes") segue sem cobertura de navegador.
- Testes de navegador fora do `./verify.sh` padrão (decisão de 25/10/2026): exigem o Chromium do Playwright e sobem um servidor; entram com `VERIFY_E2E=1`. Revisitar se as stories seguintes os tornarem indispensáveis ao fluxo de CI.
- A resolução de `Para a Story 2.5` (registrar `GET /api/lots/{lot_id}` depois de `/mine` e criar o `GET /api/lots` público) foi cumprida: a ordem é fixada por teste em `app.routes`.

A P3 (a fase não muda sozinha com a página aberta) é comportamento deliberado, documentado no README em "Comportamentos que podem surpreender", e não é dívida.

## Deferred from: rebranding ÁTRIO (25/10/2026)

- Refinamento visual final do logotipo e da identidade (Story 6.2): o símbolo e a palavra
  de hoje são uma interpretação vetorial inicial e fiel à direção da referência, feita sem
  intenção de arte final (proporções do arco, peso e espaçamento do wordmark, versão
  monocromática, favicon em tamanhos pequenos, `apple-touch-icon`/manifest, versão para
  fundo escuro com o dark mode). Hoje o favicon é só SVG.
- A marca usa fonte de UI do sistema (`system-ui`) no wordmark; uma fonte própria exigiria
  decidir hospedagem/licença de fonte (fora desta rodada).
- Texto "Casa de Leilões" que permanece de propósito: enunciado do desafio
  (`docs/desafio-elite-dev.md`), `docs/CRONOGRAMA.md` (plano feito com o nome anterior),
  `backend/pyproject.toml` (descrição do pacote, nome técnico), specs/stories históricas
  e o genérico "casa de leilões" (tipo de negócio) em DESIGN/EXPERIENCE/BLUEPRINT/ARQUITETURA.

## Deferred from: implementation of 3-1-carteira-e-depósito-simulado.md (25/10/2026)

- Depósito duplicado por nova tentativa manual (P8): não há `Idempotency-Key`, ledger nem tabela de idempotência. Um timeout depois do commit, seguido de nova tentativa **manual** do usuário, ainda pode duplicar o depósito. A tela bloqueia o botão durante o envio, nunca reenvia sozinha e, em erro ambíguo, faz uma única releitura do saldo sem afirmar o resultado, mas isso não impede a repetição manual. Idempotência real exige mecanismo próprio (chave de idempotência persistida ou ledger de movimentos) e fica fora da 3.1. Descrito no README em "Comportamentos que podem surpreender".
- Sem histórico de movimentos da carteira: só o estado agregado. O `DESIGN.md` §5 menciona "números e movimentos", mas nenhuma fonte obrigatória (enunciado, `epics.md`, `EXPERIENCE.md` §8) exige a lista; um ledger resolveria também a idempotência acima.
- Log do seed sem contagem de carteiras: `run_seed` mantém o retorno `(users, created)` e a linha de `main()` só afirma, depois do commit, usuários e lote. A contagem de carteiras inseridas não é registrada porque não há forma simples de logá-la depois do commit sem mudar o contrato do `run_seed`. Revisitar se a contagem fizer falta na operação.
- `populate_existing` em `lock_wallet` é defesa, não necessidade hoje: no caminho HTTP a `Session` nunca carrega a `Wallet` antes da trava (a política só carrega `User`), então a mutação que o remove só é pega pelo teste de serviço que pré-carrega o objeto. Manter: protege a 3.4, onde a mesma `Session` pode ler a carteira antes de travá-la.
- Para a Story 3.4: `committed_balance_cents` só passa a mudar com o lance, sempre na mesma transação que o lote e as carteiras travados na ordem do AD-8 (lote, depois carteiras por `user_id` crescente). O depósito trava só uma carteira e nenhum lote, então não cria ciclo de deadlock com essa ordem. A CHECK `committed <= total` vale a cada `UPDATE`: na liquidação, cuidar da ordem das atualizações.

## Deferred from: consolidação da 3-4-lance-transacional-com-travas-e-anti-sniping.md (26/10/2026)

- **Autenticação manual de lotes legados.** A migration da 3.4 pode deixar lotes preexistentes com `anchor_hmac = NULL`. Esses lotes são não autenticados e não recebem lance. A 3.4 não confia automaticamente em "zero lances + genesis + âncora ausente" (reabriria a lavagem por reautenticação, S-01). Trabalho futuro possível: um comando administrativo explícito, executado conscientemente por um operador com `AUDIT_HMAC_SECRET`, que autentique só lotes legados comprovadamente vazios, sem fallback automático no runtime e com trilha e documentação operacional. Não é requisito da 3.4 e não está desenhado.

## Deferred from: spec e build da 3-4-lance-transacional-com-travas-e-anti-sniping.md (26/10/2026)

Obrigações para as próximas stories (`spec-story-3-4-lance-transacional/current-state.md` §5). Nada abaixo foi implementado na 3.4.

- **Gate compartilhado (SR-08 B).** 3.6, 4.3 e 6.6 decidem com líder, lance atual ou `bid_count`: precisam do **mesmo** gate de `app/bids.py` (`authenticate_previous_state`), reutilizado ou extraído quando a primeira delas for implementada. Não duplicar a lógica. Hoje ele é função de módulo, sem API pública prematura.
- **Premissa da trava do lote.** Toda escrita em `bids` e no estado de lance do lote (`current_bid_cents`, `current_leader_id`, `bid_count`, `final_hash`, `anchor_hmac`, `ends_at`) passa pela trava `lock_lot` (`SELECT ... FOR UPDATE`), antes de qualquer carteira (AD-8). 3.6, 4.3 e 6.6 herdam a ordem: lote, depois carteiras por `user_id` crescente; nunca carteira antes de lote. Hoje só `create_lot` (INSERT de lote novo) e `place_bid` escrevem nesse estado.
- **3.6 (cancelar sem lances):** trava o lote; decide "sem lances" com o `bid_count` autenticado pelo gate; acrescenta `cancelled_at IS NULL` ao predicado do demo aberto no seed.
- **4.3 (liquidação):** trava o lote, roda o gate antes de usar líder ou lance atual, trava carteiras (vencedor, leiloeiro) em `user_id` crescente; nunca escreve em `bids`; o comprovante usa `bid_count` e `final_hash` autenticados. A CHECK `committed <= total` vale a cada `UPDATE`: cuidar da ordem.
- **Estado terminal (SR-08 A), 4.3 e 6.6:** persistir um marcador terminal para que, depois de liquidar ou estornar, nenhum `place_bid` posterior libere de novo o comprometido do líder. A 3.4 não cria essa coluna.
- **`auctioneer_id` fora da âncora (SR-08 D), 4.3:** a liquidação credita o leiloeiro por `lots.auctioneer_id`, que a âncora v1 não cobre. Tratar no desenho da 4.3; o `CanonicalBid` v1 não muda.
- **6.6 (estorno):** o mesmo gate antes de liberar o comprometido do líder; histórico intocado.
- **4.4 (Q9):** se fechar dentro da tentativa de lance, fecha em transação própria antes; nunca trava carteira antes de lote.
- **5.1 (auditoria pública, SR-08 C):** ler lote e `bids` num snapshot coerente. Em `READ COMMITTED`, dois statements separados podem ver um lance confirmado entre eles e acusar falso positivo: usar um statement único ou uma transação `REPEATABLE READ` somente leitura.
- **IC-1 (confirmada):** o "+4 min" do T-SNIPE da story é inviável pelo caminho real sem esperar. Foi substituído por T-SNIPE (3), em que o segundo lance lê o fim já estendido e não estende, e pelo teste de extensão exata sobre o fim lido; a cumulatividade entre aceites sucessivos continua provada pela regra pura da 3.2.
- **Falha de conexão depois de enviar o `COMMIT` (F-6):** resultado indeterminado para o cliente; sem chave de idempotência, assim como no depósito.
- **Rotação de segredos (A1 da 3.3, F-4, SR-09):** não suportada. Trocar `AUDIT_HMAC_SECRET` invalida todas as âncoras (o demo, com `anchor_hmac` não nulo, continua "aberto" até vencer e responde 409); trocar `PSEUDONYM_SECRET` bloqueia lotes com lances.
- **Sem `lock_timeout`, sem `statement_timeout` e sem retry de deadlock (D13):** uma fila longa na trava do lote prende conexões e threads do pool; um deadlock fora do protocolo vira 500 genérico. Aceito na escala do desafio.
- **Ponto de atenção do build:** `SELECT ... FOR UPDATE` em `lots` seguido de `UPDATE` parcial do lote viola a CHECK `(bid_count = 0) = (current_bid_cents IS NULL)` (CHECK não é adiável). Por isso o serviço grava o lote num único `UPDATE` final (D1). Candidata a "Armadilhas conhecidas" do `CLAUDE.md`, que eu decido.


## Auditoria administrativa de processo — 26/10/2026

- **Deploy Epic 2 — RESOLVIDO no fechamento registrado em 27/10/2026:** o deploy
  não aconteceu no fechamento original por falha de processo. O usuário confirmou
  recuperação conjunta **2+3**, merge/push manuais da `main`, commit publicado
  `3d3ea97`, configuração do Render, validação pública, aplicação funcionando e
  smoke concluído. Não houve deploy retroativo isolado do Epic 2. Evidências:
  `docs/DEPLOY-RECUPERACAO-EPICS-2-3.md`; detalhes dos cenários não individualizados.
- **Reviews — RESOLVIDO:** agregado Epic 3 aprovado após correção/re-review de
  F-01 MEDIUM; retrospectivos de integração Epics 1/2 aprovados; LOW documental
  do Epic 2 resolvido. Limites históricos de comparação preservados nos relatórios.
- **Verify final — RESOLVIDO:** `VERIFY_E2E=1 ./verify.sh` pós-correção e anterior
  ao merge, exit 0 conforme evidência fornecida: pytest 2036, npm test 160,
  Playwright 189 passed/5 skipped; Ruff, format, ESLint, tsc, Vite/Docker build
  passaram. Não executei verify nesta atualização documental.
- **Fechamento Epic 3 — RESOLVIDO:** stories 3.1–3.6 e Epic 3 `done`, após
  reviews/correções/verify e confirmação manual de merge/deploy/smoke.
- **LOW opcional preservado:** teste discriminante do uso da entry capturada
  pelo passive effect da sala, conforme re-review final do Epic 3, seção 7.
  Aceito como não bloqueante; não implementado nesta tarefa.
- **Dívidas futuras preservadas:** rotação de secrets, idempotência/COMMIT ambíguo,
  lock/statement timeout, settlement, auditoria pública e demais itens anteriores
  continuam com os limites e obrigações documentados. Epics 4–6 em backlog.
- **Notas de transição acima preservadas como histórico:** a 3.6 já reutiliza o
  gate `authenticate_previous_state`, filtra cancelados nas leituras e no seed,
  e grava `cancelled_at` sob a trava do lote. As previsões "Para a Story 3.6" e
  "Hoje só create_lot/place_bid escrevem" descrevem o estado na 3.4; não são
  pendências atuais. Catch-up/liquidação/estado terminal/4.3/4.4/5.1/6.6 continuam
  futuros; nenhuma dessas stories foi iniciada nesta auditoria.
- Fonte única dos gates: `docs/FECHAMENTO-DE-EPICO.md`. Não transformei a
  retrospective opcional do BMAD em obrigação do projeto.
