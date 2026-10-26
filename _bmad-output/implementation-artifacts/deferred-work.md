# Trabalho adiado

## Deferred from: code review of 2-1-formato-de-erros-e-validacao-de-origin.md (24/10/2026)

- O `loc` do 422 pode ecoar chaves escolhidas pelo cliente em modelos `dict[str, ...]` ou `extra="forbid"`, e `details` não tem limite de itens. Inalcançável com as rotas atuais; mudar o conteúdo do `loc` exige rever a D1 da 2.1.
- `sprint-status.yaml` ainda registra `epic-1: in-progress` e a 1.4 como `review`. Pré-existente; fechar quando o épico 1 for formalmente encerrado.

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
