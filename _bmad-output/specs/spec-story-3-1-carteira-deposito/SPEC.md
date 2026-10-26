---
id: SPEC-story-3-1-carteira-deposito
companions:
  - decisions.md
  - database-schema.md
  - backend-contract.md
  - seed-plan.md
  - frontend-wallet.md
  - test-plan.md
  - implementation-map.md
  - ../spec-story-2-5-vitrine-publica/frontend-navigation.md
  - ../spec-story-2-4-criacao-lotes/backend-contract.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/3-1-carteira-e-depósito-simulado.md
---

> **Contrato canônico.** Esta SPEC e os arquivos em `companions:` formam o contrato
> completo da Story 3.1. P1 a P8 foram decididas pelo Joaodionizio antes desta spec e
> **não são reabertas** (`decisions.md` §1). D1 a D16 detalham essas decisões dentro do
> que elas permitem (`decisions.md` §2). Nenhuma questão aberta. A 3.1 reutiliza a
> navegação da 2.5 e o padrão monetário da 2.4 (companions adotados).

# Story 3.1: carteira e depósito simulado

## Why

Mandato do desafio (FR7, FR8 e a base do FR12): o licitante vê saldo total, comprometido
e disponível e faz depósito simulado, porque sem saldo não há lance (3.4). É a primeira
escrita financeira do sistema e a primeira linha que a futura transação de lance vai
travar (AD-8). Três riscos guiam o desenho: perder depósito concorrente (lost update),
um saldo sair da faixa que o JavaScript representa sem perda (`formatCents` lança
`RangeError` acima de `2^53 − 1`) e haver usuário sem carteira quando a 3.4 precisar
dela.

## Capabilities

- **CAP-1**
  - **intent:** Todo usuário, existente ou semeado, tem exatamente uma carteira, em banco já existente e em banco limpo.
  - **success:** Banco em `0003` com usuários → `upgrade head` → cada usuário com uma linha em `wallets` com `0`/`0`; banco vazio em `head` → `run_seed` → 3 usuários e 3 carteiras `0`/`0`; os dois estados finais de `wallets` são iguais para os mesmos usuários; um usuário sem carteira inserido por SQL ganha carteira no próximo seed; a segunda execução do seed não insere nem altera nada em `wallets` (nenhum `UPDATE` em `wallets` registrado).
- **CAP-2**
  - **intent:** O PostgreSQL garante as invariantes da carteira, sem depender da aplicação.
  - **success:** Migration `0004` cria `wallets` exatamente como em `database-schema.md`; por SQL direto, `-1` em qualquer saldo, `committed > total` e `MAX_CENTS + 1` em qualquer saldo são recusados com o nome da CHECK; segunda carteira do mesmo usuário e `user_id` inexistente são recusados; `DELETE` de usuário com carteira é recusado pela FK; não há coluna `available_balance_cents` nem `id`; `downgrade 0003` remove só `wallets`.
- **CAP-3**
  - **intent:** O teto monetário tem uma única fonte na aplicação, igual ao literal das migrations.
  - **success:** `app/money.py` define `MAX_CENTS == 2**53 − 1` e `Cents`; `app/lots.py` não define mais nenhum dos dois e os importa de `app.money`; o literal das CHECKs de `lots` e de `wallets` (`pg_get_constraintdef`) contém `str(app.money.MAX_CENTS)`; os testes da 2.4 continuam verdes sem afrouxar asserção.
- **CAP-4**
  - **intent:** O licitante lê a própria carteira com o disponível derivado.
  - **success:** `GET /api/wallet` com sessão `BIDDER` → 200 `{total_balance_cents, committed_balance_cents, available_balance_cents}`, inteiros, `available = total − committed` (inclusive com `committed > 0` inserido por SQL), `Cache-Control: no-store`; o banco recebe só `SELECT`, sem `FOR UPDATE`; anônimo ou sessão inválida → 401; `AUCTIONEER` → 403.
- **CAP-5**
  - **intent:** O licitante deposita um valor simulado positivo e o total aumenta exatamente nesse valor.
  - **success:** `POST /api/wallet/deposit` `{"amount_cents": n}` com sessão `BIDDER` → 200 com o snapshot novo, `no-store`; a linha gravada é igual à resposta; o total sobe exatamente `n`; o comprometido não muda; a carteira alterada é sempre a do usuário da sessão.
- **CAP-6**
  - **intent:** Entrada inválida e teto recusam o depósito sem gravar nada, com o erro certo.
  - **success:** `0`, `-1`, `100.5`, `1e2`, `"100"`, `true`, `null`, ausente, JSON malformado, campo extra e `MAX_CENTS + 1` → 422 `validation_error` com o `details.type` real; `amount_cents` válido com `total + amount_cents > MAX_CENTS` → 422 `balance_limit_exceeded`, corpo `{status, code, message}` sem `details`, `no-store`; `total + amount_cents == MAX_CENTS` aceito; nenhum caso altera a linha.
- **CAP-7**
  - **intent:** Depósitos concorrentes na mesma carteira nunca se perdem nem passam do teto.
  - **success:** No PostgreSQL real, a sessão A deposita sem confirmar e a sessão B, em outra thread, fica bloqueada (observada em `pg_locks`); A confirma, B confirma; total = inicial + a + b. Perto do teto (`MAX_CENTS − 10`), com A = 6: B = 6 é recusado com `balance_limit_exceeded` e B = 4 é aceito, ambos decididos sobre o total que A confirmou. Um controle negativo no próprio teste (leitura-soma-escrita sem trava) perde um depósito, provando que o teste detecta a falta da trava.
- **CAP-8**
  - **intent:** Só o licitante usa a carteira, e as escritas seguem a proteção existente.
  - **success:** As duas rotas são `AccessPolicy.BIDDER` por `api_route`; o verificador de política passa sem mudança; `AUCTIONEER` → 403 no `GET` e no `POST`, sem alterar carteira; `Origin` estrangeiro/ausente → 403 `csrf_*`, sem JSON → 415, handler não roda; nenhum cabeçalho CORS.
- **CAP-9**
  - **intent:** Usuário autenticado sem carteira é tratado como violação de invariante, nunca escondido.
  - **success:** Carteira apagada por SQL de um `BIDDER` → `GET` e `POST` respondem 500 `internal_error` genérico, o traceback fica só no log do servidor, nenhuma carteira é criada.
- **CAP-10**
  - **intent:** O licitante abre "Carteira" e deposita pela interface, em português, com feedback direto e sem duplicar envio.
  - **success:** Roteiro manual e Playwright: `BIDDER` vê "Carteira" no header (`aria-current` em `/bidder/wallet`), vê o disponível em destaque e total e comprometido; deposita e vê os saldos da resposta; recusa mostra a mensagem; duplo clique gera exatamente um `POST`; erro ambíguo gera exatamente um `GET` de releitura e mostra o saldo real, ou uma mensagem que não afirma o resultado se a releitura falhar, sem novo `POST`.
- **CAP-11**
  - **intent:** A rota da carteira segue a navegação existente para cada tipo de sessão.
  - **success:** `/bidder/wallet` por clique, Back/Forward, refresh e link direto; anônimo → `/login` com `returnTo` no `history.state` → login `BIDDER` volta à carteira, login `AUCTIONEER` vai a `/`; `AUCTIONEER` em `/bidder/wallet` vê "Área do licitante" e o navegador não faz nenhum `GET /api/wallet`; `AUCTIONEER` e anônimo não veem "Carteira" no header; sem React Router.
- **CAP-12**
  - **intent:** A carteira e o header do licitante funcionam no celular.
  - **success:** Em 1440, 375 e 320 px: sem rolagem horizontal na carteira; header do `BIDDER` (marca, Vitrine, Carteira, e-mail, Licitante, Sair) sem sobreposição, alvos de ~44 px; o maior valor (`R$ 90.071.992.547.409,91`) cabe sem estourar.
- **CAP-13**
  - **intent:** O contrato novo fica fixado por teste e a entrega verificada e documentada.
  - **success:** OpenAPI com `/api/wallet` (`get`) e `/api/wallet/deposit` (`post`) depois das rotas de lotes, `WalletResponse` e `DepositRequest` com propriedades exatas, `ErrorResponse` em 401/403 (GET) e 401/403/422 (POST), sem `HTTPValidationError`; `MESSAGES` ganha só `balance_limit_exceeded`; `EXPECTED_POLICIES` ganha as duas rotas `BIDDER`; `./verify.sh` e `VERIFY_E2E=1 ./verify.sh` passam com saída real registrada; README, `docs/uso_de_ia.md`, `deferred-work.md` (risco da P8), story e `sprint-status.yaml` atualizados.

## Constraints

- AD-3/P3: dinheiro só em inteiros de centavos, `BIGINT`, `StrictInt`; nenhum `float`, fração ou divisão; faixa `0..MAX_CENTS` nos saldos e `1..MAX_CENTS` no depósito, com `MAX_CENTS` só em `app/money.py` e o literal só nas migrations.
- P4/AD-2: o depósito é uma transação curta que trava a carteira com `SELECT ... FOR UPDATE` antes de ler o saldo; proibido ler fora da trava e escrever depois; nenhuma chamada externa dentro dela.
- AD-8: o depósito trava uma única carteira, por `user_id`, e nenhum lote; nada nesta story cria outra ordem de travas.
- AD-19: `GET /api/wallet` nunca escreve nem trava; carteira ausente nunca é criada fora da migration e do seed (P2).
- P2/AD-24: o seed só faz `INSERT` em `wallets` com `ON CONFLICT DO NOTHING`; nunca `UPDATE`/`DELETE` em `wallets`, `users` ou `lots`; `run_seed` mantém o retorno `(users, created)`.
- AD-11/2.2: rotas só por `api_route` com `AccessPolicy.BIDDER`; dono da carteira sempre a sessão; corpo com `extra="forbid"`.
- 2.1/AD-29: erro só no envelope único e mensagens só do catálogo; escrita só `POST` JSON com `Origin`/`Referer`.
- 2.4 D11: limpeza de testes sem `CASCADE` (`TRUNCATE wallets, lots, users`).
- 2.5 P5/AD-4: navegação própria pela History API, `returnTo` só em `history.state`, sem React Router nem dependência nova; TypeScript simples.
- DESIGN/EXPERIENCE: três números primeiro, disponível como o mais acionável, sem gráfico, estado nunca só por cor, nenhum controle sem função.
- AD-30: código, banco, API e rotas do front em inglês; interface em português.
- Testes existentes só mudam onde o contrato muda (lista de paths do OpenAPI, catálogo de mensagens, tabelas do banco, `EXPECTED_POLICIES`, `clean_users`, a asserção `/carteira/i` de `session.spec.ts`); nenhuma asserção é afrouxada.

## Non-goals

- Ledger, histórico de depósitos, "movimentos", saque, estorno, transferência, timestamps em `wallets`.
- `Idempotency-Key`, tabela de idempotência, retry automático do depósito.
- Qualquer lógica de lance: regras, `bids`, `current_bid_cents`, `leader_id`, comprometer ou liberar saldo, anti-sniping, pseudônimo, hash, HMAC, WebSocket (3.2 a 4.x). `committed_balance_cents` fica sempre 0 nesta story.
- Carteira para o `AUCTIONEER` na API ou na interface; cancelamento, liquidação, comprovante, auditoria.
- Saldo pré-carregado nas contas demo; cadastro público.
- Correção das dívidas administrativas de Epic 1, Epic 2 e deploy.

## Success signal

- Numa aba anônima, abro `/bidder/wallet`, entro como `bidder1@example.com` e volto à carteira com `R$ 0,00` disponível; deposito `1.250,00` e vejo `R$ 1.250,00` disponível e total, comprometido `R$ 0,00`; um duplo clique não deposita duas vezes. Como `auctioneer@example.com`, não vejo "Carteira" e `/bidder/wallet` mostra "Área do licitante". Os testes de concorrência em PostgreSQL real passam e `./verify.sh` passa.

## Assumptions

- Em `READ COMMITTED`, um `SELECT ... FOR UPDATE` bloqueado devolve a versão confirmada pela transação que segurava a trava; com `populate_existing`, o objeto ORM reflete essa versão.
- O 500 de carteira ausente sai do handler global da 2.1 (sem `no-store`, como todo 500 genérico); o traceback registrado pelo uvicorn é o "log interno" da P2.
- `pg_locks` com `NOT granted` é observável por uma terceira conexão enquanto a sessão B espera a trava de linha (a espera aparece como lock `transactionid`).
