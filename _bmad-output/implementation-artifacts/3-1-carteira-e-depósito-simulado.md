# Story 3.1 — Carteira e depósito simulado

Status: done

Chave do sprint: `3-1-carteira-e-depósito-simulado`
Épico: 3 (Carteira e lances íntegros). Data de criação: 25/10/2026.

## Story e objetivo

Como licitante,
quero ver meus saldos e depositar um valor simulado,
para que eu tenha saldo para dar lances.

Nesta story entrego: a tabela `wallets` (migration Alembic nova), uma carteira para
**todo** usuário existente e para os semeados, nos dois cenários de banco (já
existente e limpo); as invariantes de saldo garantidas pelo PostgreSQL; a leitura da
carteira com total, comprometido e disponível (disponível sempre derivado, nunca
persistido); o depósito simulado em centavos inteiros, correto sob concorrência; a
política de acesso das rotas novas; a tela "Carteira" do licitante; testes em
PostgreSQL real; documentação.

`committed_balance_cents` nasce aqui porque pertence à carteira e à invariante
`committed <= total`. Nesta story ele só existe e vale 0: quem o altera por causa de
um lance é a Story 3.4.

> **Leitura desta story (25/10/2026).** Decidi P1 a P8 em 25/10/2026, antes de
> qualquer spec ou código. As decisões vigentes estão em **"Decisões fechadas (P1 a
> P8)"**, e os critérios, o esquema, o contrato, os testes e as tarefas abaixo já as
> refletem. A seção "Questões abertas" fica como registro histórico de antes da
> decisão; onde a minha decisão diverge da recomendação de lá (P3: código próprio
> `balance_limit_exceeded`, e não `details.type`), vale "Decisões fechadas".

*(Estado de quando escrevi esta story, antes da spec: o status era `ready-for-dev`,
indicando que o artefato existia e que não havia questão bloqueante para a spec; eu
ainda não tinha rodado `bmad-spec` nem `bmad-build`. Depois rodei os dois, e o code
review; o estado atual está em "Registro de implementação" e "Registro e status".)*

## Fontes usadas

`CLAUDE.md`; `docs/ARQUITETURA.md` (AD-2, AD-3, AD-8, AD-11, AD-17, AD-19, AD-24,
AD-27, AD-29, AD-30; questões 4 e 10); `docs/desafio-elite-dev.md` ("Carteira do
licitante", "Saldo comprometido", "Dados de teste"); `README.md`; `docs/uso_de_ia.md`;
`_bmad-output/planning-artifacts/epics.md` (Story 3.1, FR7, FR8, FR12, D2);
`sprint-status.yaml`; `deferred-work.md`; `DESIGN.md` (§5, §10, §13, §14);
`EXPERIENCE.md` (§2, §5, §8, §16); as Stories 2.2, 2.4 e 2.5 e as specs da 2.4
(`SPEC.md`, `backend-contract.md`, `database-schema.md`, `seed-plan.md`,
`test-plan.md`) e da 2.5 (`SPEC.md`, `backend-contract.md`, `frontend-navigation.md`,
`test-plan.md`).

O skill `bmad-create-story` não está instalado, assim como nas Stories 2.2 e 2.4.
Segui a estrutura das stories 2.2, 2.4 e 2.5.

ADs: o `epics.md` declara AD-3, AD-8, AD-11 e AD-30 para a 3.1. Também considero
AD-2 (transação e trava no PostgreSQL), AD-17 (concorrência em PostgreSQL real), AD-27
(`verify`) e AD-29 (CSRF), pela dependência direta abaixo. AD-19 entra só porque o
`GET` da carteira não pode escrever. AD-24 entra porque o seed passa a criar
carteiras. Nenhuma outra AD é tocada.

## Estado real encontrado (conferido nos arquivos, sem git)

**Banco e migrations.** A cadeia é `0001_baseline` → `0002_users` → `0003_lots`
(`backend/migrations/versions/`). **A próxima revisão é a `0004`**, com
`down_revision = "0003"`. `users` tem `id UUID PK` sem default (os IDs do seed são
fixos), `email`, `password_hash` e `role` com CHECK, e **nenhuma** coluna de
carteira, nem `created_at`. `lots.auctioneer_id` tem FK `ON DELETE RESTRICT` para
`users`. Naming convention em `app/db.py` (`ck_%(table_name)s_%(constraint_name)s`
etc.). Não existe tabela `wallets` nem modelo `Wallet`.

**Dinheiro no back-end.** `MAX_CENTS = 9_007_199_254_740_991` e o tipo
`Cents = Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]` vivem em `app/lots.py`,
junto com o modelo `Lot`, o catálogo da AIC e as rotas. A migration `0003` escreve o
literal na CHECK, e um teste confere esse literal contra `MAX_CENTS`
(`test_money_check_literal_matches_the_application_limit`).

**Política de acesso.** `app/access.py`: `api_route(app, path, methods, policy=...)`,
`AccessPolicy.BIDDER` com `require_bidder` (401 sem sessão, 403 com outro papel, ambos
com `no-store`); `NO_STORE`. `tests/access_policy.py` reprova rota sem política ou
sem a dependência dela; `policy_by_route` usa a chave `(path, method, kind)` (2.5,
D20). Hoje **nenhuma rota real** é `BIDDER`: só as rotas sintéticas de
`tests/synthetic_api.py`.

**Proteção das escritas.** `app/csrf.py`: todo `POST` sob `/api` exige `Origin` (ou
`Referer`) igual a `APP_ORIGIN` e `Content-Type: application/json`, antes do
roteamento (403 `csrf_*` / 415).

**Erros.** `app/errors.py`: envelope `{status, code, message[, details]}`,
`error_response`, `error_responses(...)` para o OpenAPI e o catálogo `MESSAGES`,
fixado por igualdade exata em `test_errors.py`. Precedente de 422 com código próprio e
sem `details`: `artwork_not_eligible` (2.4).

**Sessão de banco.** `get_session`: `Session` curta, sem commit automático,
`expire_on_commit=False`, `hide_parameters=True`; isolamento padrão `READ COMMITTED`
(um teste do seed fixa isso).

**Seed.** `app/seed.py`: `run_seed` faz, numa transação, a trava consultiva, depois
`seed_users` (`INSERT ... ON CONFLICT (id) DO NOTHING RETURNING id`, nunca `UPDATE`),
depois `database_now` e `seed_demo_lot`; devolve `(users, created)`. `main()` faz um
commit e loga `"seed: %d user(s) inserted; demo lot %s"`. Os testes da 2.2 e da 2.4
fixam `run_seed → (3, True)`, a substring `"3 user(s) inserted"` e a ordem
migrations → seed → uvicorn (`start.sh`). O seed não cria carteira.

**Inicialização.** `backend/scripts/start.sh`: `alembic upgrade head` →
`python -m app.seed` → `uvicorn`, com `set -eu`. As migrations rodam **antes** do
seed. Daí os dois cenários da seção "Impacto no seed".

**Testes.** `tests/conftest.py`: o banco `_test` é recriado por sessão a partir das
migrations; `clean_users` faz `TRUNCATE lots, users` **sem `CASCADE`, de propósito**
(2.4, D11): uma tabela nova que referencie `users` faz esse `TRUNCATE` falhar.
`test_database.py` fixa as tabelas `["alembic_version", "lots", "users"]`.
`test_openapi.py` fixa `paths[-3:] == [LOTS, MINE, LOT_DETAIL]`.
`test_access_policy.py` fixa `EXPECTED_POLICIES` por igualdade.

**Front-end.** Navegação própria pela History API (`route.ts` puro e testado;
`navigation.ts` com os efeitos), sem React Router. Rotas: `/`, `/lots/{uuid}`,
`/login`, `/auctioneer/lots/new` e `/auctioneer/lots`. `isAuctioneerRoute` e
`safeReturnPath(value, role)` só conhecem as áreas do leiloeiro. `App.tsx` manda o
anônimo de área restrita para `/login` com `returnTo` e mostra ao `BIDDER` a vista
"Área do leiloeiro" (D9 da 2.5). `SiteHeader.tsx` dá ao `BIDDER` só "Vitrine", e o
comentário diz "Nada de carteira". Dinheiro: `money.ts` (`MAX_CENTS`,
`parseReaisToCents`, `formatCents` textual, `moneyErrorMessage`) e `MoneyField.tsx`
(campo de reais com "Valor reconhecido"), ambos da 2.4 e já testados em
`money.test.ts`. `formatCents` **lança `RangeError`** para valor que não é inteiro
seguro. Os testes são `node --test` (no `verify`) e Playwright (opt-in,
`VERIFY_E2E=1`), com a API simulada em `e2e/support/mockApi.ts`, que hoje não
conhece `/api/wallet`.

**Asserção existente que a 3.1 contraria de propósito.** `e2e/session.spec.ts`
(teste "BIDDER: Vitrine, identificação e Sair…") afirma
`page.getByText(/carteira/i)).toHaveCount(0)` na página do lote do `BIDDER`. Com o
link "Carteira" no header, ela falha. Decidi (P7) que é mudança de contrato do
produto, não afrouxamento: a intenção ("a página do lote não tem carteira nem lance")
passa a ser conferida no conteúdo principal, e o header passa a ter "Carteira" para o
`BIDDER`.

## Divergências entre as fontes e o código real

1. **ADs da story.** O `epics.md` lista AD-3, AD-8, AD-11 e AD-30. A instrução desta
   sessão acrescenta AD-2, AD-17, AD-27 e AD-29. É acréscimo, não contradição.
2. **UX.** O `epics.md` diz que não há documento de UX; depois dele aprovei
   `DESIGN.md` e `EXPERIENCE.md`, que o `CLAUDE.md` torna vinculantes. Sigo o
   `CLAUDE.md`, como nas 2.4 e 2.5.
3. **"Movimentos" na carteira.** O `DESIGN.md` §5 diz "carteira: números e
   movimentos". O §10 do mesmo documento, o `EXPERIENCE.md` §8, o enunciado e o
   `epics.md` pedem só os três saldos e o depósito. Nenhuma fonte obrigatória exige
   histórico de depósitos. Fechado: **sem ledger nem lista de movimentos** nesta
   story.
4. **AD-3 "não negativo".** Na carteira a CHECK é `>= 0` (zero é saldo legítimo),
   diferente de lance inicial e incremento da 2.4 (`> 0`). Coerente com o AD-3.
5. **`GET` da carteira.** O AD-30 lista literalmente `/api/wallet` entre as rotas; o
   caminho do depósito e as políticas foram fechados na P5.
6. **Dívida administrativa herdada (não corrijo nesta story; exige ação separada):**
   - `sprint-status.yaml` registra `epic-1: in-progress`, mas 1.1 a 1.4 estão
     `done`. O `deferred-work.md` (2.1) ainda diz "a 1.4 como `review`", o que também
     já não é verdade.
   - O fim da seção da 2.5 em `docs/uso_de_ia.md` diz "o `epic-2` continua
     `in-progress`", mas o `sprint-status.yaml` registra `epic-2: done`.
   - Critério de saída de todo épico (`epics.md`): "o deploy está atualizado". O
     README diz que os pré-requisitos do próximo deploy (2.1 e 2.2: `APP_ORIGIN` e
     `JWT_SECRET` no painel) "ainda não foram feitos", a branch do Render é `epic-1`,
     e as Stories 2.4 e 2.5 registram "sem deploy". O épico 2 está `done` sem deploy
     atualizado registrado. Também não verifiquei o estado do banco do Render (pelo
     README, o último deploy aplicou só a `0001`).
   - O "Como validar" do README ainda descreve o OpenAPI público como "rotas
     `/health`, `/api/auth/*` e `/api/me`".

## Dependências herdadas

| Story | O que a 3.1 usa |
| --- | --- |
| 2.1 | Envelope único de erro, catálogo `MESSAGES`, 422 com `details {loc, type}`, proteção `Origin`/`Referer` + JSON antes do roteamento, 500 genérico |
| 2.2 | `users` com IDs fixos, `UserRole.BIDDER`, `api_route`, `AccessPolicy.BIDDER`/`require_bidder`, 401/403 com `no-store`, verificador de política e meta-testes, `error_responses`, seed idempotente sem `UPDATE`, `hide_parameters` |
| 2.4 | `MAX_CENTS` (`2**53 - 1`) e o padrão "mesma faixa na API, no serviço, no front e na CHECK" (A4); `StrictInt`; literal na migration com teste contra a constante; `money.ts` e `MoneyField.tsx`; `clean_users` sem `CASCADE` (D11); seed em uma transação com trava consultiva; precedente de 422 com código próprio (`artwork_not_eligible`); "sem `Idempotency-Key`" (P7) como precedente |
| 2.5 | Navegação própria (`route.ts`, `navigation.ts`, `AppLink`), `safeReturnPath`, `returnTo` em `history.state`, vista de papel errado (D9), foco no `h1` (D11), `documentTitle`, header por papel, Playwright opt-in com `mockApi.ts`, `policy_by_route` por método (D20), identidade ÁTRIO |

## O que existe, o que reutilizo e o que nasce

| Item | Existe | Reutilizo | Nasce na 3.1 |
| --- | --- | --- | --- |
| Tabela/modelo de carteira | não | `Base`, naming convention | `wallets` (`0004`), modelo `Wallet` |
| Carteira dos usuários existentes/semeados | não | `run_seed`, trava consultiva | backfill na `0004` + garantia genérica no seed (P2) |
| Limite monetário | `MAX_CENTS`/`Cents` em `app/lots.py` | o valor e o padrão A4 | `app/money.py` como fonte única; `lots.py` refatorado para importar dele (P3) |
| Política `BIDDER` | sim (só em teste) | `api_route`, `require_bidder` | primeiras rotas reais `BIDDER` |
| Erros e CSRF | sim | todos | código `balance_limit_exceeded` em `MESSAGES` (P3) |
| Depósito concorrente | não | `READ COMMITTED`, `pg_locks` nos testes do seed | `SELECT ... FOR UPDATE` na carteira (P4) |
| Conversor e campo de reais | `money.ts`, `MoneyField.tsx` | os dois, sem parser novo | — |
| Rota/vista de carteira no front | não | `route.ts`, `AppLink`, padrão D9/D11 | `/bidder/wallet`, `WalletPage`, `api/wallet.ts`, link no header (P7, P8) |

## Critérios de aceitação

Os critérios 1 a 13 da instrução da sessão de criação estão todos aqui, sem
enfraquecimento, já com as decisões P1 a P8.

1. **CA1 — Carteira para todo usuário (P2).** Depois de aplicada a story, todo usuário
   de `users` tem exatamente uma carteira, inclusive os três semeados, nos dois
   cenários: (A) banco já existente com usuários: a `0004` faz o backfill e cada
   usuário termina com carteira; (B) banco limpo: a `0004` roda sem usuários, o seed
   cria o `AUCTIONEER` e os dois `BIDDER` e, na mesma transação, garante carteira para
   **todo usuário sem carteira** (não só os três IDs fixos). Os dois cenários terminam
   no mesmo estado. Só `INSERT` das carteiras ausentes; nunca altera saldo de carteira
   existente. Não existe cadastro público (D2 = A).
2. **CA2 — Esquema (P1).** `wallets.user_id` é `PRIMARY KEY` e `FOREIGN KEY` para
   `users.id` com `ON DELETE RESTRICT`; não existe `wallets.id`.
   `total_balance_cents` e `committed_balance_cents` são `BIGINT NOT NULL DEFAULT 0`.
   **Não existe coluna `available_balance_cents`** nem outra forma persistida do
   disponível.
3. **CA3 — Invariantes no PostgreSQL (P3).** CHECKs nomeadas garantem
   `total_balance_cents >= 0`, `committed_balance_cents >= 0`,
   `committed_balance_cents <= total_balance_cents`,
   `total_balance_cents <= 9007199254740991` e
   `committed_balance_cents <= 9007199254740991`. Um `INSERT` ou `UPDATE` direto que
   viole qualquer uma é recusado pelo banco.
4. **CA4 — Disponível derivado.** `available_balance_cents = total_balance_cents -
   committed_balance_cents`, calculado no servidor a partir da linha lida, em inteiros,
   e devolvido só na resposta.
5. **CA5 — Leitura (P5).** `GET /api/wallet`, `AccessPolicy.BIDDER`: o `BIDDER`
   autenticado lê a própria carteira e recebe `total_balance_cents`,
   `committed_balance_cents` e `available_balance_cents`, em centavos inteiros, com
   `Cache-Control: no-store`. Sem sessão: 401; `AUCTIONEER`: 403. A leitura só faz
   `SELECT`, sem `INSERT`, `UPDATE`, `DELETE` nem `FOR UPDATE` (AD-19). Usuário
   autenticado sem carteira: 500 genérico e log interno; a leitura não cria carteira.
6. **CA6 — Depósito (P4, P5).** `POST /api/wallet/deposit`, `AccessPolicy.BIDDER`,
   corpo `{"amount_cents": <int>}`: o `BIDDER` deposita na **própria** carteira (dono
   sempre o usuário da sessão), o total aumenta **exatamente** `amount_cents`, o
   comprometido não muda, e a resposta é **200** com o snapshot atualizado dos três
   valores, com `no-store`. Usuário sem carteira: 500 genérico e log; o depósito não
   cria carteira.
7. **CA7 — Entrada inválida e teto (P3).** `0`, negativo, `100.5`, `1e2`, `"100"`,
   `true`, `null`, campo ausente, JSON malformado, campo extra (`user_id`,
   `total_balance_cents`, `committed_balance_cents`...) e `amount_cents >
   9007199254740991` → 422 `validation_error` no envelope da 2.1, com o `details.type`
   real do Pydantic (`greater_than`, `less_than_equal`, `int_type`, `missing`,
   `json_invalid`, `extra_forbidden`...). `amount_cents` válido, mas com
   `total_balance_cents + amount_cents > 9007199254740991` → **422
   `balance_limit_exceeded`**, com a mensagem em português do catálogo `MESSAGES`. Em
   todos os casos, nada é gravado.
8. **CA8 — Concorrência sem lost update (P4).** Dois depósitos simultâneos e válidos
   na mesma carteira, em duas sessões/transações realmente concorrentes no PostgreSQL
   real, confirmam os dois, e o total final é `inicial + a + b`. O teste força a
   sobreposição (a segunda transação espera a trava da primeira, observada em
   `pg_locks`), não depende de sorte, e há controle negativo e/ou mutação que mostra
   que ele falha sem a proteção.
9. **CA9 — Concorrência perto do teto (P3, P4).** Com o total perto do teto, a
   segunda transação, depois de a primeira confirmar, enxerga o total novo sob a trava
   e é aceita ou recusada com `balance_limit_exceeded` com base nesse estado. O total
   nunca passa de `MAX_CENTS` e nenhum depósito confirmado se perde.
10. **CA10 — Papéis.** `AUCTIONEER` recebe 403 `forbidden` no `GET` e no depósito, sem
    alterar nenhuma carteira. As rotas novas declaram política pelo `api_route` da 2.2
    e passam no verificador de política sem mudar o verificador; `EXPECTED_POLICIES`
    ganha `("/api/wallet", "GET", "http")` e `("/api/wallet/deposit", "POST", "http")`
    como `BIDDER`.
11. **CA11 — Proteção das escritas.** O depósito passa pela proteção da 2.1 sem
    exceção: `Origin` estrangeiro ou ausente → 403 `csrf_*`; sem
    `Content-Type: application/json` → 415. Em nenhum dos casos o handler roda nem a
    carteira muda. Nenhum cabeçalho CORS.
12. **CA12 — Sem float e um limite só (P3).** Nenhuma regra financeira usa `float`,
    fração, `parseFloat`, `Number(...)` sobre texto com vírgula nem divisão: a API
    recebe `StrictInt`, o banco usa `BIGINT`, o front converte reais em centavos pelo
    `money.ts` existente. `MAX_CENTS` tem uma só fonte no back-end, `app/money.py`;
    `app/lots.py` passa a importá-la, sem mudar comportamento. As migrations escrevem
    o literal, e os testes provam que as CHECKs de `lots` e de `wallets` e a aplicação
    usam o mesmo limite.
13. **CA13 — Interface (P7, P8).** O `BIDDER` vê "Carteira" no header e abre
    `/bidder/wallet`, com os três saldos, o disponível como número mais acionável e o
    depósito simulado com feedback direto, em português, sem gráfico, sem estado só por
    cor, utilizável a 375 e 320 px sem rolagem horizontal e com o header sem
    sobreposição. O `AUCTIONEER` não vê "Carteira"; em `/bidder/wallet` digitado à mão
    vê "Área do licitante" **sem** chamar `GET /api/wallet`. O anônimo em
    `/bidder/wallet` vai a `/login` com `returnTo=/bidder/wallet`; depois do login, só
    o `BIDDER` volta à carteira, e o `AUCTIONEER` vai à vitrine. Depósito: botão
    bloqueado enquanto o `POST` estiver pendente; nunca dois `POST`s automáticos;
    sucesso mostra o saldo da resposta do `POST`; erro conhecido de validação ou
    autorização é mostrado normalmente; erro ambíguo (rede ou servidor) faz uma
    releitura de `GET /api/wallet`, que, se funcionar, mostra o estado real e, se
    falhar, não afirma se o depósito entrou. O front nunca é autoridade.
14. **CA14 — Seed e regressões (P2, P6).** Saldo inicial zero para todos, inclusive as
    contas demo; o seed não pré-carrega saldo. O seed continua idempotente: a segunda
    execução não cria carteira duplicada nem altera saldo, usuário ou lote; o lote demo
    continua funcionando; lotes demo antigos continuam intactos. `GET /health` e
    `create_app()` seguem sem banco. O OpenAPI documenta as rotas e os schemas novos
    com o envelope real e sem `HTTPValidationError`.
15. **CA15 — Verificação e documentação.** `./verify.sh` completo com a saída real
    registrada (sem número que não venha de comando executado); README,
    `docs/uso_de_ia.md`, `deferred-work.md` (risco residual da P8), esta story e
    `sprint-status.yaml` atualizados na implementação. Paro na 3.1.

## Decisões já fechadas pela arquitetura (não reabro)

| Fonte | O que já está decidido |
| --- | --- |
| AD-3 | Centavos em `BIGINT`, nomes `total_balance_cents` e `committed_balance_cents`; CHECK de não negativo e `committed <= total`; sem `float` |
| AD-30 | Tabela `wallets`; coluna `user_id`; rota `/api/wallet`; código em inglês, interface em português |
| AD-11 | `BIDDER` deposita; `AUCTIONEER` não; papéis só como `UserRole.*` |
| AD-29, 2.1 | Escrita só por `POST` JSON com `Origin`/`Referer` validado; sem CORS |
| AD-19 | `GET` nunca escreve: a leitura da carteira não cria carteira ausente |
| AD-8 | A futura ordem de travas é lote → carteiras em `user_id` crescente; o depósito não cria outra ordem |
| AD-17, AD-27 | Concorrência e saldo testados em PostgreSQL real; `verify` fail-fast |
| AD-24, 2.2 | Seed idempotente, IDs fixos, nunca `UPDATE` em conta existente; nunca altera nem apaga lote antigo |
| 2.2 P9 | Política só por `api_route`; verificador e meta-testes intactos |
| 2.4 A4 | Uma faixa monetária só em API, serviço, front e CHECK; literal na migration com teste contra a constante |
| 2.5 P5 | Sem React Router; navegação própria |

## Decisões fechadas (P1 a P8, 25/10/2026)

Decidi tudo antes da spec e do código. Registro cada decisão e o que descartei.

| Questão | Decidi | Descartei |
| --- | --- | --- |
| P1 identidade | `wallets.user_id` é `PRIMARY KEY` e `FOREIGN KEY` para `users.id`, `ON DELETE RESTRICT`; sem `wallets.id`; `total_balance_cents` e `committed_balance_cents` `BIGINT NOT NULL DEFAULT 0`; sem timestamps (não há ledger nem regra de tempo na carteira). A PK expressa o 1:1 e prepara a trava por `user_id` do AD-8 | `wallets.id` próprio + `UNIQUE(user_id)` (dois identificadores sem uso); saldos em `users` (contraria o AD-30 e mistura credencial com dinheiro); `ON DELETE CASCADE` (apagaria saldo em silêncio) |
| P2 cenários | A `0004` faz backfill para todos os usuários existentes; o seed, **depois** de criar os usuários que faltam e na mesma transação, garante de forma genérica carteira para **todo** usuário sem carteira; só `INSERT` das ausentes, nunca altera saldo existente; banco existente e banco limpo terminam no mesmo estado; usuário autenticado sem carteira em runtime é violação de invariante: 500 genérico e log interno, sem criar carteira em `GET` nem em `POST` | só o seed (lacuna num banco migrado sem seed e no teste do cenário A); trigger `AFTER INSERT ON users` (lógica escondida no banco); garantir só os três IDs fixos; criar carteira na leitura ou no depósito (esconderia a inconsistência, e o `GET` escreveria, contra o AD-19); responder saldo zero inventado |
| P3 teto | `app/money.py` é a fonte compartilhada de `MAX_CENTS = 9_007_199_254_740_991`; `app/lots.py` é refatorado para reutilizá-la (sem duas cópias da regra, sem mudança de comportamento). O teto vale para `amount_cents` e para o `total_balance_cents` resultante. As migrations continuam autônomas e escrevem o literal; os testes provam que banco e aplicação usam o mesmo limite. `amount_cents` fora da faixa → 422 `validation_error`. `amount_cents` válido com total resultante acima do teto → **422 com code `balance_limit_exceeded`** e mensagem em português no catálogo. O banco impede `total_balance_cents > MAX_CENTS` e `committed_balance_cents > MAX_CENTS` | importar `MAX_CENTS` de `app.lots` (a carteira dependeria do módulo de lotes); constante duplicada na carteira; teto comercial por depósito; a minha proposta inicial de 422 `validation_error` com `details.type = balance_limit_exceeded`; 409 `wallet_limit_exceeded`; confiar só na CHECK |
| P4 atomicidade | `SELECT ... FOR UPDATE` na linha da carteira antes de ler e somar: (1) inicia a transação, (2) trava a carteira, (3) relê o saldo sob a trava, (4) valida o teto com o estado atual, (5) atualiza o total, (6) confirma tudo ou faz rollback. Testes determinísticos em PostgreSQL real com duas sessões/transações realmente concorrentes, inclusive perto do teto; controle negativo e/ou mutação quando viável | `UPDATE` atômico com o teto no `WHERE` (motivo ambíguo quando volta zero linha); `UPDATE` sem condição + tradução da `IntegrityError` da CHECK; o padrão inseguro "ler fora da trava → somar em Python → `UPDATE`" |
| P5 contrato | `GET /api/wallet` e `POST /api/wallet/deposit`, ambos `AccessPolicy.BIDDER`; corpo `{"amount_cents"}` estrito em centavos; o `POST` responde **200** com o snapshot atualizado; `GET` e `POST` devolvem `total_balance_cents`, `committed_balance_cents` e `available_balance_cents` (sempre `total - committed`, nunca persistido); `no-store`, política, envelope de erro e proteção `Origin`/`Referer` + JSON existentes | `POST /api/wallet/deposits` (promete uma coleção que não existe); `PATCH /api/wallet`; `201`; `GET` com `AUTHENTICATED` (carteira do leiloeiro sem tela nem ação nesta story) |
| P6 saldo inicial | Zero para todos, inclusive as contas demo; o seed não pré-carrega saldo. O mesmo comportamento em banco existente e limpo, e o depósito fica demonstrável na avaliação | pré-carregar todos os `BIDDER`; pré-carregar só o `bidder1` (nos dois casos o saldo só apareceria em banco limpo, porque o seed nunca altera carteira existente) |
| P7 front | URL `/bidder/wallet`, navegação própria pela History API, sem React Router. `BIDDER`: acessa e vê "Carteira" no header. `AUCTIONEER`: sem link; em `/bidder/wallet` digitado vê "Área do licitante", sem chamar `GET /api/wallet`. Anônimo: `/login` com `returnTo=/bidder/wallet`. Depois do login, só o `BIDDER` volta à carteira; o `AUCTIONEER` vai à vitrine. A asserção antiga de `session.spec.ts` (BIDDER sem "carteira") é atualizada porque o contrato mudou, sem afrouxar. Os testes de header/layout a 375 e 320 px continuam obrigatórios com o item novo | `/wallet` sem prefixo de papel; React Router; chamar a API para o `AUCTIONEER` e mostrar o 403; mandar o `AUCTIONEER` para a carteira depois do login |
| P8 repetição | Sem `Idempotency-Key`, ledger ou tabela de idempotência; sem retry automático. Front: botão bloqueado enquanto o `POST` está pendente; nunca dois `POST`s automáticos; sucesso usa a resposta do `POST`; erro conhecido de validação/autorização é mostrado normalmente; erro ambíguo (rede/servidor) dispara uma releitura de `GET /api/wallet`, que, se funcionar, mostra o estado real; se a releitura falhar, a tela não afirma se o depósito entrou e não repete o `POST`. Registro em `deferred-work.md` (na implementação) que um timeout depois do commit seguido de nova tentativa **manual** ainda pode duplicar o depósito, e que idempotência real exige mecanismo próprio, fora da 3.1 | `Idempotency-Key` com tabela de chaves; retry automático; afirmar sucesso ou falha sem confirmação do servidor |

**Ajustes derivados, também decididos:**

- `clean_users` passa a `TRUNCATE wallets, lots, users`, com `wallets` antes de `users`,
  preservando a estratégia sem `CASCADE` (2.4, D11).
- Sem ledger nem histórico de movimentos.
- Nenhuma lógica de lance antecipada.
- `committed_balance_cents` nasce na 3.1 e fica zero nesta story; a movimentação por
  lance é da 3.4.
- As divergências administrativas de Epic 1, Epic 2 e deploy não são corrigidas aqui;
  pedem uma ação separada.
- Nenhum número de teste ou evidência inventado.

**Detalhes que ficam para a spec (não bloqueiam; seguem as decisões acima):**

- Texto exato da mensagem de `balance_limit_exceeded` no catálogo e se o 422 leva
  `details` (proposta: sem `details`, como `artwork_not_eligible`).
- Se o tipo `Cents` também passa para `app/money.py` ou só a constante (o
  comportamento de `lots.py` não muda nos dois casos).
- Se a contagem de carteiras criadas entra na tupla de `run_seed` (ajuste consciente
  dos testes da 2.2 e da 2.4) ou só no log.
- Nomes finais das CHECKs, dos arquivos de teste e os textos da interface.

## Questões abertas (registro histórico, decididas em 25/10/2026)

Texto de antes da decisão, mantido como registro. As decisões vigentes estão em
"Decisões fechadas (P1 a P8)".

### P1 — Identidade da carteira e comportamento da FK

**Problema.** A carteira é 1:1 com o usuário. Falta decidir a chave e o que acontece se
um usuário com carteira for apagado (hoje nenhum caminho apaga usuário).

- **(a)** `user_id UUID` como PK **e** FK para `users.id`.
- **(b)** `id UUID` próprio como PK + `user_id UUID NOT NULL UNIQUE` com FK.
- **(c)** Colunas de saldo direto em `users` (sem tabela `wallets`).

Em (a) e (b), proponho `ON DELETE RESTRICT`, igual a `lots.auctioneer_id`, e
`server_default 0` nas duas colunas de saldo, sem timestamps.

**Consequências.** (a) garante o 1:1 pela PK e trava por `WHERE user_id IN (...) ORDER
BY user_id FOR UPDATE`, a ordem do AD-8; (b) exige `UNIQUE` e um segundo identificador;
(c) contraria o AD-30 e mistura credencial com dinheiro.

**Recomendação:** (a), com `ON DELETE RESTRICT`, `server_default 0` e sem timestamps.

### P2 — Carteira nos dois cenários (backfill, seed, novo usuário)

**Problema.** Migrations rodam antes do seed: no cenário A os usuários já existem; no B
o seed os cria depois. Os dois têm de terminar com carteira, de forma idempotente.

- **(a)** Backfill na `0004` **e** garantia no seed para todo usuário sem carteira, por
  uma função de serviço, só `INSERT ... ON CONFLICT DO NOTHING`.
- **(b)** Só o seed garante as carteiras.
- **(c)** Trigger `AFTER INSERT ON users` + backfill.

Em runtime, carteira ausente não é criada numa leitura (AD-19); proposta: 500 e log.

**Recomendação:** (a), e carteira ausente em runtime = 500 genérico com log.

### P3 — Teto monetário da carteira e onde mora o contrato compartilhado

**Problema.** `MAX_CENTS` mora em `app/lots.py`. Falta decidir o lugar compartilhado,
onde o teto vale e como a recusa por total aparece. `formatCents` lança `RangeError`
acima do inteiro seguro; o `BIGINT` não estoura com valores até `2^53 - 1`.

- **(a)** `app/money.py`; teto no depósito e no total, CHECK no total.
- **(b)** A carteira importa de `app.lots`.
- **(c)** (a) + teto comercial por depósito.

Proposta para a recusa do total: 422 `validation_error` com
`details.type = balance_limit_exceeded`; alternativa: 409 com código novo.

**Recomendação:** (a), com 422 `validation_error` e `details.type`.
*(Decidi diferente na recusa: 422 com code próprio `balance_limit_exceeded`; ver
"Decisões fechadas".)*

### P4 — Operação atômica do depósito

- **(a)** `SELECT ... FOR UPDATE`, teto em Python sobre o valor travado, `UPDATE`.
- **(b)** `UPDATE` atômico com o teto no `WHERE` e `RETURNING`.
- **(c)** `UPDATE` sem condição, confiando na CHECK.

O depósito trava uma só carteira e não trava lote: não fecha ciclo de deadlock com a
3.4. **Recomendação:** (a), com teste determinístico, corrida livre, controle negativo
no teste e mutação temporária.

### P5 — Rota do depósito e política do `GET /api/wallet`

- P5.1: **(a)** `POST /api/wallet/deposit` 200; **(b)** `POST /api/wallet/deposits`;
  **(c)** `PATCH /api/wallet`.
- P5.2: **(a)** `BIDDER`; **(b)** `AUTHENTICATED`.

**Recomendação:** P5.1 (a) e P5.2 (a).

### P6 — Saldo inicial das contas demo

- **(a)** zero; **(b)** pré-carregado só na criação; **(c)** só o `bidder1`.

Com P2 (a), o saldo pré-carregado só apareceria em banco limpo.
**Recomendação:** (a).

### P7 — Rota e integração da carteira no front

- **(a)** `/bidder/wallet`; **(b)** `/wallet`. Padrão D9/D11 da 2.5 para anônimo e
  papel errado.

**Recomendação:** (a), sem React Router.

### P8 — Depósito repetido e resultado incerto

- **(a)** Sem `Idempotency-Key`; botão desabilitado; releitura do saldo em erro
  ambíguo; README.
- **(b)** `Idempotency-Key` obrigatório com tabela.

**Recomendação:** (a).

## Esquema esperado (decidido em P1, P2 e P3)

| Coluna | Tipo | Nulo | Default |
| --- | --- | --- | --- |
| `user_id` | `UUID` | não | — |
| `total_balance_cents` | `BIGINT` | não | `0` |
| `committed_balance_cents` | `BIGINT` | não | `0` |

| Constraint (nome proposto; o final fica na spec) | Definição |
| --- | --- |
| `pk_wallets` | `PRIMARY KEY (user_id)` |
| `fk_wallets_user_id_users` | `FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT` |
| `ck_wallets_total_range` | `total_balance_cents >= 0 AND total_balance_cents <= 9007199254740991` |
| `ck_wallets_committed_range` | `committed_balance_cents >= 0 AND committed_balance_cents <= 9007199254740991` |
| `ck_wallets_committed_within_total` | `committed_balance_cents <= total_balance_cents` |

Sem índice extra: a PK serve à busca e à trava.

**Migration `0004_wallets.py`:** `revision = "0004"`, `down_revision = "0003"`.
`upgrade()`: `create_table` e o backfill por SQL
(`INSERT INTO wallets (user_id) SELECT id FROM users`), com os defaults zerando os
saldos. Literal `9007199254740991` escrito na migration, sem importar código da
aplicação. `downgrade()`: `drop_table("wallets")`. O downgrade perde os saldos; é
aceitável no desafio e fica registrado. Compatível com banco existente (backfill) e
com banco do zero (tabela vazia; o seed completa). Os testes de downgrade das 2.2 e 2.4
(`downgrade 0001` e `downgrade 0002`) passam a atravessar a `0004` primeiro e devem
continuar verdes.

## Contrato de API (decidido em P3 e P5)

| Rota | Política | Entrada | Sucesso | Erros |
| --- | --- | --- | --- | --- |
| `GET /api/wallet` | `BIDDER` | nenhuma | 200 `WalletResponse`, `no-store` | 401, 403, 500 se carteira ausente (P2) |
| `POST /api/wallet/deposit` | `BIDDER` | `DepositRequest {amount_cents}` (`extra="forbid"`, `StrictInt`, `1..MAX_CENTS`) | 200 `WalletResponse`, `no-store` | 401, 403, 422 `validation_error`, 422 `balance_limit_exceeded`, 500 se carteira ausente, 403 `csrf_*`/415 da 2.1 |

```json
POST /api/wallet/deposit
{"amount_cents": 50000}

200
{"total_balance_cents": 50000, "committed_balance_cents": 0, "available_balance_cents": 50000}
```

Fluxo do depósito (P4): CSRF da 2.1 → `require_bidder` (lê o `User`) → corpo validado
→ `SELECT ... FROM wallets WHERE user_id = :id FOR UPDATE` → carteira ausente: 500 e
log → `total + amount_cents > MAX_CENTS`: rollback e 422 `balance_limit_exceeded` →
`UPDATE` do total → commit → resposta montada com a linha confirmada. Nenhuma chamada
externa. Handler e dependências `def` (threadpool). `no-store` no sucesso e nos erros
montados no handler (o 422 do handler global segue sem `no-store`, precedente C4 da
2.3). OpenAPI: `error_responses(401, 403)` no `GET` e `(401, 403, 422)` no `POST`;
`MESSAGES` ganha `balance_limit_exceeded`.

## Impacto no seed

- `run_seed`: trava consultiva → `seed_users` → **garantia genérica de carteiras**
  (todo usuário sem carteira, por uma função de serviço da carteira) → `database_now`
  → `seed_demo_lot`, tudo na mesma transação.
- Só `INSERT` das carteiras ausentes, com saldo zero (P6); nunca `UPDATE` em
  `wallets`, `users` ou `lots`.
- Banco existente (backfill da `0004`) e banco limpo (seed) terminam no mesmo estado.
- A assinatura `run_seed → (users, created)` e a linha de log com `"3 user(s)
  inserted"` são fixadas pelos testes da 2.2 e da 2.4; a spec decide como a contagem de
  carteiras aparece (ver "Detalhes que ficam para a spec").
- Lote demo, trava consultiva, `READ COMMITTED` e independência de `APP_ORIGIN`,
  `JWT_SECRET`, `app.main` e rede continuam como na 2.4.

## Impacto no front-end

- `src/api/wallet.ts`: tipos `WalletResponse` e `DepositRequest`; guarda
  `isWalletResponse` (centavos inteiros seguros, não negativos, `available = total −
  committed`); resultados tipados que separam erro conhecido (`validation`,
  `balance_limit_exceeded`, `unauthorized`, `forbidden`) de erro ambíguo (rede, 5xx,
  corpo fora do contrato); mensagens pelo `code`/`details.type`, nunca pelo `message`
  do servidor.
- `src/route.ts`: rota `{kind: 'wallet'}` em `/bidder/wallet`, `isBidderRoute`,
  `safeReturnPath` que só devolve `/bidder/wallet` para `BIDDER` (`AUCTIONEER` → `/`).
- `src/WalletPage.tsx`: três números primeiro (`DESIGN.md` §10), com o **disponível**
  em destaque (`EXPERIENCE.md` §8), total e comprometido como apoio; valores por
  `formatCents`; sem gráfico, sem card dentro de card; formulário com `MoneyField`
  ("Valor do depósito") e um botão primário. Feedback (P8): botão bloqueado durante o
  `POST`; sucesso com os saldos da resposta e mensagem em `role="status"`; erro
  conhecido no campo ou no formulário; erro ambíguo → uma releitura de
  `GET /api/wallet` → estado real se ela funcionar, ou mensagem neutra que não afirma
  se o depósito entrou se ela falhar; nunca um segundo `POST` automático. Texto e
  símbolo, nunca só cor. A decisão do que mostrar depois do `POST` pode ser uma função
  pura testável por `node --test`.
- `SiteHeader.tsx`: "Carteira" só para `BIDDER`, depois de "Vitrine", com
  `aria-current`. **Obrigatório:** header do `BIDDER` sem sobreposição e sem rolagem
  horizontal a 375 e 320 px, com alvos de toque de ~44 px (testes da 2.5).
- `App.tsx`: vista da carteira; anônimo → `/login` com `returnTo`; `AUCTIONEER` →
  "Área do licitante", sem chamar a API; 401 durante o uso → login com "Sua sessão
  expirou." e retorno à carteira; `documentTitle('Carteira')`; foco no `h1` em
  navegação interna (D11 da 2.5).
- Sem dependência nova. A validação do front (formato, zero, teto do valor) é só UX: o
  servidor revalida tudo, inclusive o teto do total.

## Concorrência, lost update e overflow (riscos)

- **Lost update:** leitura-soma-escrita sem trava perde depósito. Mitigação: P4;
  prova: teste determinístico, controle negativo no teste e mutação temporária.
- **Total acima do inteiro seguro:** quebraria `formatCents` e a precisão no
  JavaScript. Mitigação: teto no total, checado com a linha travada, e CHECKs no total
  e no comprometido.
- **Overflow de `BIGINT`:** impossível com valores limitados a `2^53 − 1` (a soma de
  dois cabe em `2^63 − 1`); registrado para não virar falsa preocupação.
- **Deadlock com a 3.4:** o depósito trava só uma carteira e não espera outra trava
  depois; não fecha ciclo com "lote → carteiras em `user_id` crescente".
- **Carteira ausente:** só se um usuário surgir fora do seed e depois da `0004`. Em
  runtime, 500 com log (P2); nunca criação silenciosa.
- **Duplo depósito:** residual pela P8 (nova tentativa manual depois de timeout
  pós-commit), documentado em `deferred-work.md` e no README.
- **Log:** uma violação de CHECK em `wallets` faria o `DETAIL` do PostgreSQL mostrar a
  linha (`user_id` e saldos) no log do servidor (limite conhecido de
  `hide_parameters`, 2.2 L1). Nenhum caminho previsto viola a CHECK.
- **Contas demo públicas:** qualquer pessoa deposita nas contas demo da URL pública
  (inerente ao desafio, como a senha pública).

## Matriz de testes esperados

Toda contagem virá do `verify` desta story. Banco: PostgreSQL `_test` real, nunca
SQLite.

| Grupo | Casos |
| --- | --- |
| Migration e esquema | `wallets` criada pela `0004`; colunas exatas na ordem `user_id`, `total_balance_cents`, `committed_balance_cents` (sem `available_balance_cents`, sem `id`); `BIGINT` real pelo `information_schema`; `NOT NULL` e default `0`; PK em `user_id`; FK com `ondelete` `RESTRICT` no inspector; segunda carteira para o mesmo usuário recusada; `user_id` inexistente recusado; `DELETE` de usuário com carteira recusado pela FK; CHECKs: total `-1` e comprometido `-1` recusados, `0` aceito; `committed = total + 1` recusado, `committed = total` aceito; `MAX_CENTS` aceito e `MAX_CENTS + 1` recusado no total e no comprometido, com o nome da CHECK; literal das CHECKs de `wallets` e de `lots` (`pg_get_constraintdef`) igual a `str(MAX_CENTS)` de `app.money`; downgrade para `0003` remove `wallets` e mantém `users`/`lots`, upgrade recria; `test_database.py` com `wallets` na lista |
| Cenário A | banco em `0003` com usuários (inseridos por SQL), `upgrade head` → cada usuário com exatamente uma carteira zerada; nenhum usuário alterado |
| Cenário B e equivalência | banco em `head` sem usuários, `run_seed` → 3 usuários e 3 carteiras zeradas; o estado final de `wallets` é igual ao do cenário A com os mesmos usuários; um usuário não semeado sem carteira (inserido por SQL) também ganha carteira no seed; segunda execução → nenhuma carteira nova, linhas idênticas; carteira com saldo alterado por SQL continua igual depois do seed; nenhum `UPDATE` em `wallets` (`statement_recorder`) |
| Contrato monetário | `app.money.MAX_CENTS == 2**53 - 1`; `app.lots` usa a mesma constante (identidade ou igualdade conferida); testes da 2.4 sobre dinheiro continuam verdes sem mudança de asserção |
| Domínio/serviço | `available = total − committed` para valores variados, inclusive `committed > 0` inserido por SQL; depósito soma exatamente; comprometido intacto; teto do valor (422 `validation_error`) e do total (422 `balance_limit_exceeded`), inclusive o limite exato (`total + amount == MAX_CENTS` aceito, `MAX_CENTS + 1` recusado); falha forçada depois do `UPDATE` e antes do commit → nada gravado; carteira ausente → 500 genérico, log e nenhuma linha criada |
| HTTP leitura | `BIDDER` lê os três saldos com `no-store` e chaves exatas; anônimo, cookie adulterado e expirado → 401; `AUCTIONEER` → 403; só `SELECT` e sem `FOR UPDATE` (`statement_recorder`); `HEAD`/`OPTIONS` sem efeito |
| HTTP depósito | `BIDDER` deposita e recebe 200 com os saldos novos; linha gravada = resposta; dono = sessão mesmo com corpo tentando `user_id` (422 `extra_forbidden`); `0`, `-1`, `100.5`, `1e2`, `"100"`, `true`, `null`, ausente, JSON malformado, campos extras, `MAX_CENTS + 1` → 422 `validation_error` com o `type` real, nada gravado; total resultante acima do teto → 422 `balance_limit_exceeded` com o corpo exato do catálogo e `no-store`, nada gravado; anônimo 401; `AUCTIONEER` 403 sem alterar nenhuma carteira; `Origin` estrangeiro/ausente → 403 `csrf_*` e sem JSON → 415, handler não roda; `GET`/`PUT`/`DELETE` em `/api/wallet/deposit` → 405 |
| Concorrência (PostgreSQL real) | determinístico: a conexão A trava a carteira (`FOR UPDATE`), a thread B fica bloqueada (observada em `pg_locks`), A deposita e confirma, B confirma → total = inicial + a + b; corrida livre com `threading.Barrier`, repetida, pelo serviço e pelo HTTP; perto do teto: A confirma, B enxerga o total novo sob a trava e é aceita ou recusada com `balance_limit_exceeded` conforme esse estado, total nunca acima de `MAX_CENTS`; controle negativo no próprio teste (leitura-soma-escrita sem trava perde um depósito); mutação temporária do serviço (tirar o `FOR UPDATE`) registrada na story |
| Política e contrato | `EXPECTED_POLICIES` com as duas rotas `BIDDER`; verificador sem problemas, com e sem SPA; OpenAPI com as rotas novas, `WalletResponse`/`DepositRequest` com propriedades exatas, `ErrorResponse` em 401/403/422, sem `HTTPValidationError`; `test_openapi.py` (`paths[-3:]`) atualizado conscientemente; `test_errors.py` ganha `balance_limit_exceeded` no catálogo por igualdade exata |
| Regressões | suítes da 2.2, 2.4 e 2.5 verdes; `clean_users` com `TRUNCATE wallets, lots, users` (sem `CASCADE`); lote demo e vitrine intactos; `/health` e `create_app()` sem banco; `docker build` |
| Front (`node --test`) | `api/wallet.ts`: guarda aceita a resposta válida e recusa centavos não inteiros, negativos, não seguros, chave ausente e `available` incoerente; classificação das respostas (sucesso, erro conhecido, ambíguo); `/bidder/wallet` em `parseRoute`/`routePath` (ida e volta); `isBidderRoute`; `safeReturnPath('/bidder/wallet', 'BIDDER') === '/bidder/wallet'` e `safeReturnPath('/bidder/wallet', 'AUCTIONEER') === '/'`; dinheiro pelo `money.ts` existente, sem parser novo |
| Front (Playwright, opt-in, API simulada) | "Carteira" no header do `BIDDER` (com `aria-current` na carteira) e ausente para anônimo e `AUCTIONEER`; `AUCTIONEER` em `/bidder/wallet` → "Área do licitante" e **zero** `GET /api/wallet`; anônimo em `/bidder/wallet` → `/login` → login como `BIDDER` → carteira; o mesmo fluxo entrando como `AUCTIONEER` → vitrine; depósito com feedback e saldos da resposta; recusa 422 com mensagem; duplo clique → exatamente um `POST`; erro ambíguo → um `GET` de releitura e o saldo real; releitura falhando → mensagem neutra e nenhum `POST` novo; 1440, 375 e 320 px sem rolagem horizontal e header do `BIDDER` sem sobreposição; atualização consciente da asserção `/carteira/i` de `session.spec.ts`. O Playwright não substitui o teste transacional |
| Manual (meu, antes do review) | depositar como `bidder1`; ver os três números; valores inválidos; duplo clique; servidor parado; `AUCTIONEER` sem carteira no header e com "Área do licitante" na URL; 375 e 320 px; teclado |

## Documentação a sincronizar (na implementação, não agora)

- Esta story: registro de implementação e evidências reais.
- `sprint-status.yaml`: a story avança conforme o fluxo BMAD.
- `README.md`: seção "Carteira" (rotas, política, limite técnico no depósito e no
  total, disponível derivado, saldo inicial zero), seed com carteiras,
  "Comportamentos que podem surpreender" (sem histórico de depósitos; nova tentativa
  manual depois de timeout pode duplicar; limite técnico do total).
- `docs/uso_de_ia.md`: seção da 3.1.
- `deferred-work.md`: o risco residual da P8 (timeout depois do commit seguido de nova
  tentativa manual pode duplicar o depósito; idempotência real exige mecanismo
  próprio, fora da 3.1).
- `docs/ARQUITETURA.md`: não prevejo mudança; nenhuma questão numerada é da 3.1 e
  nenhuma AD muda.
- Spec da 3.1: só depois do `bmad-spec`, quando eu mandar. *(Feita depois: está em
  `_bmad-output/specs/spec-story-3-1-carteira-deposito/`.)*

## Tarefas e subtarefas

- [x] **T1 — Decidir comigo (todas as CAs).** P1 a P8 decididas em 25/10/2026 e
  registradas em "Decisões fechadas", em primeira pessoa e com as alternativas
  descartadas.
- [x] **T2 — Contrato monetário (CA3, CA7, CA12, P3).** `app/money.py` com
  `MAX_CENTS`; `lots.py` refatorado para importá-lo, sem mudança de comportamento;
  `balance_limit_exceeded` em `MESSAGES`.
- [x] **T3 — Migration e modelo (CA1, CA2, CA3, P1, P2).** `0004_wallets.py` com
  backfill e `downgrade`; modelo `Wallet`.
- [x] **T4 — Serviço (CA4, CA6, CA8, CA9, P2, P4).** Leitura com disponível derivado;
  depósito sob `FOR UPDATE`; teto do total; carteira ausente → 500 e log; garantia
  genérica de carteiras para o seed.
- [x] **T5 — Rotas (CA5, CA6, CA7, CA10, CA11, P5).** `GET /api/wallet` e
  `POST /api/wallet/deposit` por `api_route` com `BIDDER`; `no-store`; OpenAPI com
  `error_responses`.
- [x] **T6 — Seed (CA1, CA14, P2, P6).** Garantia de carteiras na transação do seed,
  saldo zero, idempotência.
- [x] **T7 — Testes do back-end (CA1 a CA12, CA14).** Matriz acima; ajustes
  conscientes em `conftest.py`, `test_database.py`, `test_openapi.py`,
  `test_access_policy.py`, `test_errors.py` e, se for o caso, nos testes de seed.
- [x] **T8 — Front-end (CA13, P7, P8).** `api/wallet.ts`, rota `/bidder/wallet`,
  `WalletPage`, header, `App.tsx`; testes `node --test`; Playwright opt-in;
  atualização consciente de `session.spec.ts`; `mockApi.ts` com as rotas da carteira.
- [x] **T9 — Verificar e documentar (CA15).** `./verify.sh` e `VERIFY_E2E=1
  ./verify.sh` com a saída real; README, `docs/uso_de_ia.md`, `deferred-work.md`,
  esta story, `sprint-status.yaml`. Parar na 3.1.

## Arquivos prováveis (previsão, não implementação)

| Área | Arquivo | Ação prevista |
| --- | --- | --- |
| Back-end | `backend/app/money.py` | novo (P3) |
| Back-end | `backend/app/wallet.py` | novo: modelo, schemas, serviço, rotas |
| Back-end | `backend/app/lots.py` | importar `MAX_CENTS` de `app.money` (P3), sem mudança de comportamento |
| Back-end | `backend/app/errors.py` | `balance_limit_exceeded` no catálogo (P3) |
| Back-end | `backend/app/main.py` | registrar as rotas da carteira |
| Back-end | `backend/app/seed.py` | garantir carteiras (P2, P6) |
| Migration | `backend/migrations/versions/0004_wallets.py` | novo |
| Testes | `tests/conftest.py`, `integration/test_database.py`, `test_openapi.py`, `test_access_policy.py`, `test_errors.py`, `integration/test_seed.py`, `integration/test_lots_migration.py` (origem da constante) | ajustes conscientes |
| Testes | `integration/test_wallets_migration.py`, `integration/test_wallet_routes.py`, `integration/test_wallet_concurrency.py`, `test_wallet_rules.py`, `wallet_support.py` | novos (nomes na spec) |
| Front-end | `src/api/wallet.ts`, `src/api/wallet.test.ts`, `src/WalletPage.tsx` | novos |
| Front-end | `src/route.ts`, `src/route.test.ts`, `src/App.tsx`, `src/SiteHeader.tsx`, `src/App.css` | alterados |
| E2E | `e2e/support/mockApi.ts`, `e2e/session.spec.ts`, um spec novo da carteira | alterados/novo |
| Docs | `README.md`, `docs/uso_de_ia.md`, esta story, `sprint-status.yaml`, `deferred-work.md` | alterados |
| Sem mudança prevista | `app/access.py`, `app/csrf.py`, `app/auth.py`, `app/users.py`, `app/catalog.py`, `app/artic.py`, `app/spa.py`, `tests/access_policy.py`, `start.sh`, `Dockerfile`, `verify.sh`, `money.ts`, `MoneyField.tsx` | intocados |

## Fora de escopo

- Regras de aceitação de lance, primeiro lance e incremento, líder cobrindo o próprio
  lance, anti-sniping, `clock_timestamp()` depois da trava do lote (3.2, 3.4).
- `current_bid_cents`, `leader_id`, tabela `bids`, comprometer ou liberar saldo por
  lance, `POST /api/lots/{lot_id}/bids` (3.4).
- Pseudônimo, serialização canônica, SHA-256, `previous_hash`, hash atual, HMAC (3.3,
  3.4).
- WebSocket, histórico de lances, "você está ganhando"/"foi superado" (3.5, 4.x).
- Cancelamento (3.6), fechamento, liquidação, comprovante, auditoria pública (4.x,
  5.x).
- Ledger, histórico de depósitos, "movimentos", saque, estorno, transferência.
- `Idempotency-Key`, tabela de idempotência, retry automático (P8).
- Tela ou leitura de carteira para o `AUCTIONEER` (P5).
- Saldo pré-carregado nas contas demo (P6).
- Cadastro público (D2 = A). React Router. Dependência nova de runtime.
- Correção das dívidas administrativas herdadas (divergência 6).
- Não crio spec, não rodo `bmad-spec` nem `bmad-build`, não inicio a 3.2 e não uso git.
  *(Regra da sessão de criação da story. A spec e o build vieram depois, cada um na sua
  sessão; a 3.2 continua não iniciada e o git continua sendo só meu.)*

## Fechamento (regra de toda story)

Antes de `done`, confiro a coerência entre esta story, a spec da 3.1, `README.md`,
`docs/uso_de_ia.md`, `deferred-work.md`, `sprint-status.yaml` e, só se um resumo ficar
desatualizado, `CLAUDE.md` e `docs/ARQUITETURA.md`. Preservo: decisão → motivo →
alternativa descartada → evidência → mudança de plano → limitação. Não altero AD para
registrar detalhe local.

## Registro de implementação (25/10/2026)

Implementado pelo `bmad-build` (Sonnet), direto, a partir da spec em
`_bmad-output/specs/spec-story-3-1-carteira-deposito/`. Sem git, sem deploy, sem a 3.2.
Todo número abaixo vem de comando executado nesta sessão.

### O que existe

| Área | O quê |
| --- | --- |
| Banco | migration `0004_wallets.py`: `wallets (user_id PK/FK RESTRICT, total_balance_cents, committed_balance_cents)`, CHECKs `ck_wallets_total_range`, `ck_wallets_committed_range`, `ck_wallets_committed_within_total`, backfill zerado por `INSERT ... SELECT id FROM users`, literal `9007199254740991` na migration |
| Contrato monetário | `app/money.py` (`MAX_CENTS`, `Cents`); `app/lots.py` importa dele e continua exportando os dois nomes |
| Carteira | `app/wallet.py`: `Wallet`, `MissingWalletError`, `DepositRefusal`, `available_cents`, `apply_deposit`, `ensure_wallets`, `read_wallet`, `lock_wallet` (`FOR UPDATE` + `populate_existing`), `deposit`, `DepositRequest`, `WalletResponse`, `register_wallet_routes` |
| Rotas | `GET /api/wallet` e `POST /api/wallet/deposit`, ambas `AccessPolicy.BIDDER`, `no-store`; OpenAPI com `error_responses(401, 403)` e `(401, 403, 422)` |
| Erros | `balance_limit_exceeded` em `MESSAGES`: "O depósito ultrapassaria o limite de saldo da carteira." (422, sem `details`) |
| Seed | `run_seed` chama `ensure_wallets` depois de `seed_users`, mesma transação; retorno `(users, created)` inalterado; **sem log de contagem de carteiras** (ver desvios) |
| Front | `/bidder/wallet` (`route.ts`), `api/wallet.ts`, `walletFeedback.ts`, `WalletPage.tsx`, `BidderOnly` e redirecionamentos por `isRestrictedRoute` em `App.tsx`, "Carteira" no `SiteHeader.tsx`, seção de CSS |
| Documentação | README (seção "Carteira", contas demo, seed, "Comportamentos que podem surpreender"), `docs/uso_de_ia.md`, `deferred-work.md` (P8 e correlatos) |

### Testes novos e alterados

- Novos (back-end): `tests/wallet_support.py`, `test_wallet_rules.py`, `integration/test_wallets_migration.py`, `integration/test_wallet_service.py`, `integration/test_wallet_routes.py`, `integration/test_wallet_concurrency.py`.
- Novos (front): `src/api/wallet.test.ts`, `src/walletFeedback.test.ts`, `e2e/wallet.spec.ts`.
- Alterados por mudança real de contrato: `conftest.py` (`TRUNCATE wallets, lots, users`, sem `CASCADE`), `test_database.py` (tabelas), `test_openapi.py` (paths e schemas), `test_errors.py` (`MESSAGES`), `test_access_policy.py` (`EXPECTED_POLICIES`), `test_seed.py` (carteiras no subprocesso), `route.test.ts` ("as seis rotas", carteira, `safeReturnPath`), `e2e/session.spec.ts` (asserção `/carteira/i` escopada ao `main` e asserção positiva do link no header), `e2e/touch-targets.spec.ts` (caso `BIDDER`), `e2e/support/mockApi.ts` (rotas da carteira). Nenhuma asserção foi afrouxada.

### Evidências (comandos executados)

- `./verify.sh`: exit 0. Ruff ok; `ruff format --check` 66 arquivos ok; `pytest` **1174 passed**; ESLint ok; `tsc` ok; `npm test` **107 pass, 0 fail**; build ok; `docker build` ok.
- `VERIFY_E2E=1 ./verify.sh`: exit 0, as mesmas etapas, mais Playwright (Chromium): **123 passed, 5 skipped** (os 5 são `real-stack.spec.ts`, que só roda com `E2E_REAL_BASE_URL`).
- Referência de antes da story (registrada na 2.5, não medida aqui): 1058 testes do back-end.
- **Mutação temporária (registrada, não versionada).** Sem `.with_for_update()` em `lock_wallet`: 11 testes falharam (C1, C2, C3, C4, C4b, as cinco repetições de C5 e o teste de serviço do `FOR UPDATE`); por exemplo C1 terminou com total `1500` em vez de `1800` e C3 com `9007199254740985` em vez de `9007199254740991`, ou seja, o depósito de A se perdeu. Sem `populate_existing`: falhou só `test_the_lock_statement_is_a_for_update_select_with_a_fresh_read` (os testes de concorrência usam sessões novas e não o detectam; o `populate_existing` é defesa para a 3.4). Os dois arquivos foram restaurados e o `app/wallet.py` final foi comparado por `diff` com a cópia original.
- Controle negativo dentro do próprio teste (C6): o padrão ler-somar-gravar sem trava termina com `300` ou `500`, nunca `800`.
- Conferência de arquivos alterados (por marcador de baseline, sem git): todos dentro da lista prevista; nenhum arquivo "Intocados" mudou; nenhum arquivo de segredo alterado.

### Desvios da spec e justificativa

1. **D10 (log do seed).** `run_seed` não loga `wallet(s) inserted`, e `main()` segue só com a linha de usuários e lote, depois do commit. Pedido meu na revisão final: nunca afirmar sucesso antes de o commit confirmar. Os testes do subprocesso do seed afirmam a ausência do log de carteira.
2. **`pg_locks` só auxiliar.** `wait_for_blocked_lock` devolve `bool` (não levanta) e consulta `pg_stat_activity` **ou** `pg_locks`. O gatilho de sincronização é o primeiro `SELECT` de `wallets` de B (evento `before_cursor_execute`), não o `FOR UPDATE`, para a mutação falhar pelo estado final. A prova é o total no banco e o resultado de B sobre o saldo confirmado por A.
3. **CHECKs em testes.** O PostgreSQL informa a primeira CHECK que falha; um total negativo também viola `committed <= total`. Os casos aceitam o conjunto de CHECKs da regra violada em vez de uma só.
4. `fetchWallet` aceita um `AbortSignal` opcional (a spec previa sem argumentos).
5. O aviso de erro conhecido usa `role="alert"` (a spec previa `status`).
6. `deferred-work.md` real é `_bmad-output/implementation-artifacts/deferred-work.md` (`docs/deferred-work.md` não existe).
7. Sem subagente: implementação direta. O passo de revisão do `bmad-build` (step-04) e o `bmad-code-review` **não foram rodados**, por instrução minha.

### Riscos e limitações restantes

- Teste manual (`test-plan.md` §10) ainda é meu; os testes de navegador usam API simulada e só Chromium. Servidor parado de verdade, 320 px e 375 px reais e teclado não foram observados por mim.
- Depósito duplicado por nova tentativa **manual** depois de timeout pós-commit continua possível (P8, `deferred-work.md`).
- A violação de uma CHECK em `wallets` faria o `DETAIL` do PostgreSQL mostrar a linha no log do servidor (limite conhecido de `hide_parameters`, 2.2 L1); nenhum caminho previsto viola.
- Contas demo públicas: qualquer pessoa deposita nelas.
- Deploy: a `0004` ainda não foi aplicada em nenhum ambiente publicado (sem deploy nesta story; o banco do Render está em revisão desconhecida).

### Correções do code review (25/10/2026)

O `bmad-code-review` (sete camadas) não achou BLOCKER nem HIGH; achou um MEDIUM (F-08)
e LOWs. Aprovei F-01 a F-03, F-05 a F-13; F-04 (expansão de e2e) ficou de fora.

| Finding | Correção |
| --- | --- |
| F-08 (MEDIUM) | Depósito em andamento fora da `WalletPage`, em `src/walletDeposit.ts`: um registro por conta (e-mail da sessão) com o `POST` e a releitura única do erro ambíguo. A página remontada durante o envio nasce com "Depositando…", botão e campo travados, e mostra o resultado daquele mesmo `POST`; nenhum segundo `POST` sai. A conta B nunca herda o bloqueio nem o resultado da conta A. Uma leitura iniciada antes de um saldo vindo do depósito não o sobrescreve. `App.tsx` passa `owner={session.user.email}` |
| F-01 | `MoneyField` com `readOnly` opcional, usado enquanto o `POST` está pendente; editar o valor apaga um "confirmado" anterior (o aviso incerto fica) |
| F-02 | Sucesso e resultado incerto num `p role="status"` sempre montado no formulário; erro do formulário em `role="alert"` |
| F-03 | Testes de `credentials: 'same-origin'` no GET e no POST, 422 com code desconhecido e sem JSON, 403 sem corpo (`rejected`), 201 e 204 (`ambiguous`) |
| F-05 | Código morto e `caplog` sem uso removidos do teste do 500; anotação de `refusal_of` corrigida |
| F-06 | Evidência auxiliar de espera: `pg_blocking_pids` em `pg_stat_activity`, só `current_database()` e sem a própria conexão |
| F-07 | "As seis rotas" agora confere as seis; comentário do duplo envio descreve o que roda |
| F-09 | `apply_deposit` levanta `ValueError` para valor fora de `Cents` (≤ 0, acima de `MAX_CENTS`, `bool`, não inteiro); a rota continua com o 422 do Pydantic |
| F-10 | README: conta demo no teto → usar a outra conta de licitante |
| F-11 | Teste: anônimo com corpo inválido → 401, `AUCTIONEER` com corpo inválido/extra → 403, nada gravado |
| F-12 | `dl` com um nível só (`div` → `dt`/`dd`), agrupamento visual pelo grid; teste de estrutura e de `term` |
| F-13 | Trechos desatualizados desta story e da spec (`seed-plan.md`, `decisions.md` D10, `test-plan.md`, `frontend-wallet.md`) marcados como estado anterior ou desvio |

**Evidências (comandos executados nesta rodada):**

- Mutação do F-08: com `useState(false)` no lugar do estado inicial vindo do registro (o
  comportamento anterior), o teste "voltar à carteira com o depósito pendente…" falhou
  ("Depositando…" não encontrado). Arquivo restaurado e conferido com `cmp`.
- `./verify.sh`: exit 0. Ruff ok; `ruff format --check` 66 arquivos ok; `pytest`
  **1187 passed**; ESLint ok; `tsc` ok; `npm test` **114 pass, 0 fail**; build ok;
  `docker build` ok.
- `VERIFY_E2E=1 ./verify.sh`: exit 0, as mesmas etapas, mais Playwright (Chromium):
  **127 passed, 5 skipped** (`real-stack.spec.ts`, só com `E2E_REAL_BASE_URL`).

**Desvios desta rodada:** `depositFailureNotice` deixou de devolver `'reread'` (a decisão
foi para `sendDeposit`; o teste mudou de arquivo, sem afrouxar). O erro de campo vindo do
servidor continua sem reanúncio quando o foco já está no campo (padrão do `MoneyField` da
2.4, não alterado). A rodada rodou no Opus, na mesma sessão do review, e não no Sonnet
previsto pelo `CLAUDE.md`.

**Roteiro manual do F-08 (meu):** concluído antes da re-review (depositar, navegar para
"Carteira" ou sair e voltar antes da resposta, conferir "Depositando…", botão bloqueado,
um só depósito e o saldo final).

### Re-review independente (25/10/2026)

Como as correções rodaram no Opus, na mesma sessão do review, pedi uma re-review
independente (Opus, sessão nova), só das correções, das regressões e principalmente do
F-08, sem refazer o review inteiro, sem git, sem deploy e sem alterar código.

- **Resultado:** F-01 a F-03, F-05 a F-13 corrigidos; **F-08 confirmado como corrigido**
  (a barreira contra o segundo `POST` é o registro por conta, síncrona e independente da
  montagem; isolamento entre contas e releitura única do P8 preservados; navegação da
  2.5 mantida). Nenhum BLOCKER, HIGH ou MEDIUM introduzido.
- **LOWs aceitos como opcionais (não corrigidos, sem nova story):**
  - **F-04:** expansão opcional de cobertura e2e.
  - **LOW-1:** ao voltar pelo login com o `POST` pendente, se a resposta chegar entre a
    renderização e o efeito de montagem, o botão pode ficar em "Depositando…" até a
    próxima navegação (sem segundo `POST`, saldo correto). Correção possível: guardar a
    entrada vista na primeira renderização.
  - **LOW-2:** na remontagem, se o `POST` terminar antes do `GET`, a região `status`
    nasce já preenchida e o leitor de tela pode não anunciar a confirmação. Correção
    possível: região `status` fora da condição `ready`.
- **Comandos executados pela re-review:** `npm test` (114 pass, 0 fail) e
  `npx playwright test e2e/wallet.spec.ts --repeat-each=3` (84 passed). Os números de
  `./verify.sh` e `VERIFY_E2E=1 ./verify.sh` acima são os da rodada de correções.
- **Gate:** aprovada com LOWs opcionais. Aprovei o fechamento.

## Registro e status

Status: **done** (25/10/2026). Implementação concluída e verificada (`./verify.sh` e
`VERIFY_E2E=1 ./verify.sh`, exit 0), code review feito, correções aprovadas aplicadas,
roteiro manual do F-08 concluído e re-review independente aprovada com LOWs opcionais
(F-04, LOW-1, LOW-2). A Story 3.2 não foi iniciada. Sem git, sem deploy.
