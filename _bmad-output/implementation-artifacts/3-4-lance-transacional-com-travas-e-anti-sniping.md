
> **Nova revisão humana da AD-5 — 27/10/2026 (antes da Story 4.3).** Decidi voltar à regra cumulativa: com `0 < ends_at - now <= 2 minutos`, cada lance válido acrescenta 2 minutos ao término vigente (`ends_at vigente + 2 minutos`), inclusive com exatamente 2:00 restantes (flag verdadeira). A decisão intermediária `now + 2 minutos` foi revogada. Preservo abaixo o texto original como registro histórico; fórmulas e notas anteriores devem ser lidas na sua data. Lote encerrado nunca reabre; frontend/WebSocket apenas aplicam o `ends_at` persistido. Ver AD-5 em `docs/ARQUITETURA.md`.

# Story 3.4 — Lance transacional com travas e anti-sniping

Status: done

Chave do sprint: `3-4-lance-transacional-com-travas-e-anti-sniping`
Épico: 3 (Carteira e lances íntegros). Criação: 26/10/2026. Consolidação: 26/10/2026.

> **Nota de revisão da decisão (27/10/2026).** A AD-5 foi revisada por mim em
> 27/10/2026: a regra passou a ser `novo fim = now + 2 min` (renovação a partir do lance;
> com exatamente 2 min restantes não há mudança). Este documento registra o que eu decidi
> e implementei em 26/10/2026 (Story 3.4) com a regra anterior (`ends_at + 2 min`); **não o reescrevi**. A
> regra vigente está em `docs/ARQUITETURA.md`, AD-5.

> **Decisões consolidadas em 26/10/2026.** Decidi P1–P9 (§12) antes da spec. Nenhuma
> decisão bloqueante resta para `/bmad-spec`. A documentação já foi sincronizada
> (`docs/ARQUITETURA.md`: AD-7, AD-13, AD-20, Q3, Q4; `CLAUDE.md`; três linhas
> factuais de `epics.md`). Esta consolidação não autoriza spec, build nem código.

## 1. Story

Como licitante,
quero dar um lance que reserve meu saldo, devolva o do líder anterior, aplique o
anti-sniping e grave a cadeia de integridade na mesma operação,
para que o leilão nunca fique inconsistente, mesmo com lances simultâneos, e todo
lance seja auditável.

**ADs:** AD-3, AD-5, AD-6, AD-7 (refinado nesta story), AD-8, AD-10, AD-11, AD-13
(refinado), AD-17, AD-19, AD-20 (refinado na 3.3), AD-21, AD-24, AD-25 (só
"evento depois do commit", que nasce na 4.1), AD-26, AD-29, AD-30.
**Questões:** Q3 resolvida na 3.3 (alias persistido); Q5 decidida em
`ARQUITETURA.md` (limite exato com `now` fixo, já provado na 3.2; caminho real com
margens); Q9 fica para a 4.4 (aqui, lote vencido **só recusa** com `lot_ended`).

## 2. Objetivo e contexto

A 3.2 entregou a regra pura em duas etapas (`evaluate_pre_wallet`,
`evaluate_post_wallet`). A 3.3 entregou os primitives puros de integridade e a
receita de autenticar o estado anterior antes de estender o histórico (S-01,
`integrity-contract.md` §9). A 3.4 junta tudo numa transação única no PostgreSQL,
sob a trava do lote e com a hora do banco, e expõe `POST /api/lots/{lot_id}/bids`.

O endpoint pertence a esta story (`epics.md`, critério 1 da 3.4; AD-10). A 3.5 é a
interface; a 4.1, a publicação do evento. Não puxo nada delas.

## 3. Fontes lidas e estado real encontrado

Li `CLAUDE.md`, `docs/ARQUITETURA.md` (inteiro), `docs/desafio-elite-dev.md`,
`epics.md` (visão geral, Épico 3, 4.x, 6.6), `sprint-status.yaml`,
`deferred-work.md`, a Story 3.3 final, a spec da 3.3 (`SPEC.md`, `decisions.md`,
`integrity-contract.md`, `implementation-map.md`, `test-plan.md`), a spec da 3.2
(`SPEC.md`, `decisions.md`, §9–§10 de `domain-contract.md`) e os trechos da Story
3.2 sobre a 3.4. Código: `bid_rules.py`, `bid_integrity.py`, `lot_time.py`,
`money.py`, `lots.py`, `wallet.py`, `users.py`, `config.py`, `db.py`, `main.py`,
`access.py`, `errors.py`, `csrf.py`, `auth.py`, `seed.py`, `scripts/start.sh`, as
quatro migrations, `tests/conftest.py`, `wallet_support.py`, `lot_support.py`,
`test_wallet_concurrency.py` e trechos de `test_lots_migration.py`,
`test_openapi.py`, `test_seed.py`. Sem `.env*`, sem testes, sem banco, sem deploy,
sem Git.

| Área | Evidência e consequência |
| --- | --- |
| Migrations | `0001`–`0004`; a 3.4 cria `0005` |
| `lots` | Termos, snapshot, horários, `is_demo`, `created_at`. Sem lance atual, líder, count, hash final, âncora ou cancelamento |
| `bids` | Não existe. Todo lote atual tem zero lances por construção, mas nenhum tem âncora |
| `wallets` | PK/FK `user_id`, total e comprometido com CHECKs; `committed` sempre 0 até aqui |
| Trava de carteira | `wallet.lock_wallet` (`FOR UPDATE` + `populate_existing`, feito para a 3.4) e `available_cents` existem |
| Hora | `lots.database_now(session)` lê `clock_timestamp()` em UTC |
| Isolamento | `READ COMMITTED` (padrão; `test_seed.py` o afirma no seed) |
| Regra pura | `evaluate_pre_wallet(lot, attempt, now)` e `evaluate_post_wallet(eligible, available)`; `BidAccepted.ends_at` já é o fim efetivo |
| Integridade | `bid_integrity.py`: `GENESIS_HASH`, `CanonicalBid`, `AnchorState`, `VerifiableBid`, `generate_bidder_alias`, `compute_bid_hash`, `compute_anchor_hmac`, `verify_anchor_hmac`, `verify_bid_chain`; segredos `bytes` explícitos; assinatura ausente → `ValueError` |
| Configuração | `Settings`, `SpaSettings`, `OriginSettings`, `AuthSettings` (`JWT_SECRET`, ≥ 32 caracteres, `SecretStr`, `hide_input_in_errors`). Sem segredos de integridade |
| Seed | `start.sh`: migrations → seed → uvicorn, a cada boot. O demo nasce por `create_lot`; hoje o seed só precisa de `DATABASE_URL` (testado) |
| Rotas e erros | `api_route(..., policy=...)`; CSRF por middleware em todo `POST /api/*`; envelope `{status, code, message[, details]}` com catálogo `MESSAGES`; depósito recusa com 422 (precedente) |
| Testes | `conftest` gera `JWT_SECRET` por execução, recria o schema e faz `TRUNCATE wallets, lots, users` **sem `CASCADE`**; `test_openapi.py` e `test_lots_migration.py`/`LOT_COLUMNS` fixam listas exatas; `wallet_support` tem a orquestração de concorrência |
| Produção | Render com `DATABASE_URL`, `APP_ORIGIN`, `JWT_SECRET`; sem segredos de integridade; ao menos um demo (72 h) e possivelmente lotes manuais, todos sem âncora. Não confirmei o banco real |

## 4. Escopo

**Entra:**
1. Migration `0005` (aditiva): `bids` e as colunas de lance atual, líder e âncora em
   `lots` (§7).
2. ORM `Bid` e ampliação de `Lot`.
3. Configuração operacional de `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` (P5).
4. Âncora vazia assinada em todo lote novo (POST e seed); lote legado com
   `anchor_hmac NULL` bloqueado para lance (P3, P4).
5. `backend/app/bids.py`: adaptadores, gate, serviço transacional e rota.
6. `POST /api/lots/{lot_id}/bids` (P6, P7).
7. Testes (§10), ajustes nos existentes (§9.4) e documentação (§11).

**Fora (confirmação explícita):** interface da sala, mensagens na tela e endpoint de
"meu pseudônimo" (3.5); cancelamento (3.6); WebSocket, eventos, snapshot (4.1/4.2);
fechamento, liquidação, `receipts`, scheduler, catch-up, "fechar antes de responder"
(4.3/4.4, Q9); painel de resultado (4.5); auditoria pública e detecção pública dos
cinco ataques (5.1); comprovante e meus arremates (5.2/5.3); estorno (6.6); leitura
pública do lance atual na vitrine (3.5); **comando manual de autenticação de lotes
legados** (registrado em `deferred-work.md`);
idempotência por chave; outbox; rotação de segredos; qualquer mudança nas regras da
3.2 ou em bytes, tipos e golden vectors da 3.3.

## 5. Critérios de aceite

1. **CA1 — Rota e papéis.** `POST /api/lots/{lot_id}/bids`, corpo
   `{"amount_cents": <Cents>}` com `extra="forbid"`, política `BIDDER` por
   `api_route`. Sem sessão 401; `AUCTIONEER` 403 sem tocar no lote; lote inexistente
   404; corpo inválido 422 `validation_error`; CSRF 403/415 pelo middleware. A rota
   entra no teste de política e na lista de `test_openapi.py`.
2. **CA2 — Recusa de negócio.** `lot_not_started`, `lot_ended`, `below_minimum`,
   `already_winning`, `insufficient_balance` saem com **HTTP 422** no envelope
   único, `code` = valor do `BidRefusal` e mensagem em português do catálogo, na
   precedência da 3.2. A rota só traduz o resultado; não decide nada. Recusa não
   cria lance nem muda carteira, lote, `ends_at`, cadeia ou âncora.
3. **CA3 — Aceite completo e atômico.** **HTTP 201.** Na mesma transação: lance
   gravado (`sequence`, `bidder_id`, `bidder_alias`, `amount_cents`, `placed_at`,
   `previous_hash`, `current_hash`, `canonical_version = 1`); lote com novo líder e
   novo lance atual; comprometido do novo líder +`amount_cents`; do líder anterior
   −lance atual anterior; `bid_count`, `final_hash` e `anchor_hmac` no novo estado
   assinado. A resposta contém só o lance em representação pública, o estado
   atualizado do lote e a carteira do usuário autenticado (P6).
4. **CA4 — Anti-sniping.** Aceite com `0 < ends_at − now <= 2 min` grava `ends_at`
   = fim atual lido sob a trava + 2 min, cumulativo e sem teto; acima disso, não
   muda; recusa nunca estende; `now >= ends_at` é `lot_ended` e nunca reabre.
5. **CA5 — Hora.** Um único `clock_timestamp()` por operação, lido depois da trava
   do lote, usado na fase, no anti-sniping e como `timestamp` canônico, igual ao
   `placed_at` gravado. Nenhum relógio Python, `now()`/`CURRENT_TIMESTAMP` ou hora
   do navegador.
6. **CA6 — Ordem das travas.** Lote primeiro (`SELECT ... FOR UPDATE`), depois as
   carteiras do licitante e do líder anterior em `user_id` crescente. Recusa antes
   da etapa de saldo não trava carteira.
7. **CA7 — Gate de autenticação anterior (P1, P2).** Sob a trava, depois da hora e
   antes das regras pré-carteira: cadeia válida para o lote; âncora anterior com
   `lot_id`, `bid_count` e `final_hash` iguais à cadeia; HMAC anterior válida;
   `anchor_hmac` não nulo; e o vínculo operacional da P2. Falha → **HTTP 409**
   `lot_integrity_conflict` com mensagem genérica; nenhum lance, carteira, líder,
   lance atual, `ends_at`, count, hash final ou HMAC muda; nenhuma assinatura nova;
   nada é reparado.
8. **CA8 — Sequência e cadeia.** `sequence` = `bid_count` autenticado + 1;
   `previous_hash` = `final_hash` autenticado; nunca `MAX(sequence) + 1`. Depois de
   N aceites, cadeia 1..N contínua, encadeada, com âncora válida.
9. **CA9 — Concorrência.** Lances simultâneos no mesmo lote produzem o resultado de
   alguma ordem serial: um líder, nenhum saldo negativo, nada comprometido perdido
   ou duplicado, sequência contínua, sem bifurcação, âncora final válida
   (PostgreSQL real).
10. **CA10 — Falha no meio.** Qualquer falha depois do primeiro efeito (inclusive
    entre gravar o lance e gravar a nova HMAC) desfaz tudo.
11. **CA11 — Inicialização da âncora (P3, P4).** Lote criado por `POST /api/lots` e
    demo do seed nascem com `bid_count = 0`, `final_hash = GENESIS_HASH` e
    `anchor_hmac` válida para o próprio `lot_id`, na mesma transação do `INSERT`.
    Lote legado com `anchor_hmac NULL` recusa lance com 409. Nenhum caminho (lance,
    boot, seed, migration) assina estado encontrado no banco.
12. **CA12 — Segredos (P5).** `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` existem, têm
    ≥ 32 bytes em UTF-8, são diferentes entre si e do `JWT_SECRET`; falha impede a
    inicialização sem ecoar valor. Nunca em banco, Git, log, resposta ou payload.
13. **CA13 — Reuso.** Regras só de `bid_rules`; alias, bytes, hashes e HMAC só de
    `bid_integrity`; hora só de `database_now`; trava de carteira só de
    `lock_wallet`; disponível só de `available_cents`.
14. **CA14 — Verificação.** `./verify.sh` exit 0 com saída real registrada; nenhum
    teste afrouxado (os ajustes da §9.4 acrescentam colunas, paths, tabelas e
    segredos esperados).

## 6. Fluxo transacional final

Registrado também no AD-7 (refinado em 26/10/2026). A contagem antiga de 16 passos
não é contrato; a ordem e a atomicidade são.

| # | Passo | Origem |
| --- | --- | --- |
| — | Rota: `require_bidder`, corpo validado, CSRF já aplicado; `user.id` guardado | AD-11, AD-29 |
| 1 | BEGIN (transação da `Session`, `READ COMMITTED`) | AD-7 |
| 2 | `SELECT lots ... WHERE id = :lot_id FOR UPDATE` com `populate_existing`; ausente → rollback, 404 | AD-6, AD-8, AD-9 |
| 3 | `now = database_now(session)`, um único instante | AD-6, AD-26 |
| 4 | Autenticar cadeia, âncora e HMAC anteriores e vincular lance atual/líder ao último lance (§9.1). Falha → rollback, 409, log interno | P1, P2, S-01 |
| 5 | `evaluate_pre_wallet(LotBidState, BidAttempt(user.id, amount), now)`; recusa → rollback, 422 | AD-7, 3.2 |
| 6 | Carteiras: licitante e, se houver, `current_leader_id` (autenticado no passo 4) | AD-7 |
| 7 | `lock_wallet` em `sorted()` por `UUID` | AD-8 |
| 8 | `evaluate_post_wallet(eligible, available_cents(total, committed))` da carteira travada; recusa → rollback, 422 | AD-7, 3.2 |
| 9 | Líder anterior: `committed -= current_bid_cents` anterior | FR12 |
| 10 | Licitante: `committed += amount_cents` | FR12 |
| 11 | Lote: `current_bid_cents = amount`, `current_leader_id = user.id` | AD-7 |
| 12 | Lote: `ends_at = accepted.ends_at` (calculado sobre o `ends_at` lido sob a trava) | AD-5 |
| 13 | `sequence = bid_count autenticado + 1` | P8 |
| 14 | `alias = generate_bidder_alias(lot_id, user.id, pseudonym_secret)` | AD-20 |
| 15 | `CanonicalBid(v=1, lot_id, sequence, alias, amount, timestamp=now, previous_hash=final_hash autenticado)` | AD-21 |
| 16 | `current_hash = compute_bid_hash(...)`; `INSERT` em `bids` | AD-13 |
| 17 | `AnchorState(v=1, lot_id, sequence, current_hash)` → `compute_anchor_hmac`; grava `bid_count`, `final_hash`, `anchor_hmac` | AD-13 |
| 18 | COMMIT; resposta 201. Evento de sala só na 4.1, depois do commit | AD-7, AD-25 |

Falha em qualquer ponto → ROLLBACK integral (o `with` de `get_session` desfaz a
transação em exceção; recusas e falha do gate fazem `session.rollback()` explícito
antes de responder, como o depósito).

Notas obrigatórias:
- `TIMESTAMPTZ` guarda microssegundos, como o canônico v1: o `placed_at` gravado
  reconstrói os mesmos bytes. Sem `server_default=now()` nem hora gerada no `INSERT`.
- Em `READ COMMITTED`, depois de esperar a trava, o `FOR UPDATE` devolve a versão
  confirmada do lote, e a leitura de `bids` do passo 4 (statement seguinte) vê os
  lances de quem segurava a trava. Não ler lote nem `bids` antes da trava na mesma
  transação; não subir o isolamento (o snapshot seria anterior à espera).
- A leitura do `User` pela autenticação acontece antes do passo 2 e não interfere.
- Só os `ValueError` nascidos da montagem dos objetos de integridade a partir das
  linhas do banco no passo 4 viram 409. Outros `ValueError` continuam 500: captura
  ampla esconderia bug.

## 7. Schema (direção aprovada para a spec; nenhuma migration criada)

O AD-13 fixa a âncora no lote; o AD-7 (passo 11) fixa lance atual e líder como
estado persistido. A spec valida compatibilidade com o PostgreSQL 18 e os padrões
atuais (`NAMING_CONVENTION`, literais monetários na migration com teste de igualdade
a `MAX_CENTS`, `downgrade` que remove só o que criou).

**`lots` (colunas novas):**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `current_bid_cents` | `BIGINT NULL` | `1..MAX_CENTS`; `NULL` = sem lance |
| `current_leader_id` | `UUID NULL`, FK `users.id` `RESTRICT` | `NULL` ⇔ `current_bid_cents NULL` |
| `bid_count` | `BIGINT NOT NULL DEFAULT 0` | `>= 0` |
| `final_hash` | `TEXT NOT NULL DEFAULT '0'×64` | hex 64 minúsculo; `bid_count = 0` ⇒ genesis |
| `anchor_hmac` | `TEXT NULL` | hex 64 minúsculo; `NULL` = lote legado **não autenticado** |

CHECKs de coerência: `(current_bid_cents IS NULL) = (current_leader_id IS NULL)`;
`(bid_count = 0) = (current_bid_cents IS NULL)`; `current_bid_cents >=
starting_bid_cents`. A migration preenche os lotes existentes com `0`, genesis,
`NULL` (âncora, lance atual, líder): estado coerente, representável e bloqueado para
lance. A migration não lê segredo.

**`bids`:**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `lot_id` | `UUID NOT NULL`, FK `lots.id` `RESTRICT` | — |
| `sequence` | `BIGINT NOT NULL` | `>= 1` |
| `bidder_id` | `UUID NOT NULL`, FK `users.id` `RESTRICT` | privado; **não** autenticado pelo canônico v1 |
| `bidder_alias` | `TEXT NOT NULL` | `^Licitante-[0-9A-F]{16}$`; sem UNIQUE |
| `amount_cents` | `BIGINT NOT NULL` | `1..MAX_CENTS` |
| `placed_at` | `TIMESTAMPTZ NOT NULL` | o `now` do passo 3; sem default |
| `previous_hash` | `TEXT NOT NULL` | hex 64 minúsculo |
| `current_hash` | `TEXT NOT NULL` | hex 64 minúsculo |
| `canonical_version` | `SMALLINT NOT NULL` | `= 1` |

Chaves: `PRIMARY KEY (lot_id, sequence)`; `UNIQUE (lot_id, previous_hash)` contra
bifurcação. Sem UUID substituto nem índice extra (o de `bidder_id`, se necessário,
nasce na 5.3).

`bidder_id` serve a necessidades operacionais (vínculo do líder, futuras 4.3/5.3),
mas nunca decide sozinho um efeito financeiro: para o líder atual, só vale depois
do vínculo com o alias autenticado (P2).

## 8. Concorrência e travas

**Travas:** lote (`FOR UPDATE`, como o AD-9) → carteiras em `user_id` crescente.
`sorted()` de `uuid.UUID` dá a mesma ordem do PostgreSQL (`UUID.int` big-endian;
comparação de 16 bytes). `lock_wallet` uma vez por carteira, na ordem.

**Histórico sob a trava:** sem trava extra em `bids`, **com a premissa** de que toda
escrita legítima em `bids` e no estado de lances do lote passa pela trava do lote. A
spec deve provar a premissa em todos os caminhos de escrita existentes depois da
3.4 (só o serviço de lance escreve em `bids`; `create_lot` só insere lote novo) e
registrá-la como obrigação das futuras 3.6, 4.3 e 6.6. O `INSERT` em `bids` pega
`FOR KEY SHARE` no lote pela FK, compatível com a própria trava. `READ COMMITTED`
permanece, salvo incompatibilidade concreta demonstrada na spec.

**Invariantes (PostgreSQL real):**
- I1: no máximo um líder por lote; lance atual e líder iguais ao último lance.
- I2: `0 <= committed <= total` em toda carteira.
- I3: comprometido de cada licitante = soma de `current_bid_cents` dos lotes em
  que lidera.
- I4: `sequence` 1..N contínua; `bid_count = N`; `final_hash` = hash do N-ésimo;
  HMAC confere.
- I5: nenhuma bifurcação.
- I6: resultado de lances simultâneos = alguma ordem serial.

**Passada adversarial A (concorrência):**

| Ataque | Por que não quebra |
| --- | --- |
| Dois licitantes simultâneos no mesmo lote | O segundo espera a trava, relê lote e `bids` confirmados, autentica `count = 1`, avalia o mínimo sobre o primeiro, usa `sequence = 2`, `previous_hash = hash1` |
| Mesmo licitante, dois envios | O segundo vê o primeiro como líder: `already_winning`, sem efeito |
| Licitantes compartilhando carteira | Impossível: carteira 1:1 com `users` |
| Líder anterior e novo licitante | Carteiras distintas (o líder não supera a si mesmo), travadas em ordem crescente; liberação e comprometimento em linhas diferentes |
| Deadlock | Mesmo lote serializa na trava do lote. Lotes diferentes com licitantes cruzados travam {U1, U2} na mesma ordem. Depósito trava uma carteira e nenhum lote |
| Sequência duplicada | Count autenticado sob trava; PK como defesa |
| Duas âncoras para o mesmo predecessor | Trava serializa; `UNIQUE (lot_id, previous_hash)` recusa bifurcação |
| Dois anti-sniping concorrentes | O segundo soma +2 min sobre o `ends_at` já estendido pelo primeiro: cumulativo (AD-5) |
| Comprometido incorreto | Liberação usa o lance atual autenticado; saldo validado na carteira travada; CHECK reprova subtração abaixo de zero |
| Depósito concorrente com lance | Cada um espera a trava da carteira do outro e opera sobre o valor confirmado |
| Hora obsoleta | `clock_timestamp()` só depois da trava |

## 9. Segurança e integridade

### 9.1 Gate do passo 4 (P1, P2) e consumo da 3.3

1. Ler `bids` do lote `ORDER BY sequence` e montar a tuple de `VerifiableBid`
   (`CanonicalBid` com `v = canonical_version`, `lot_id`, `sequence`,
   `bidder_alias`, `amount_cents`, `placed_at`, `previous_hash`; mais
   `current_hash`).
2. `anchor_hmac IS NULL` → falha (lote legado não autenticado). Sem fallback
   `NULL + zero lances = confiável`.
3. Montar `AnchorState(v=1, lot_id=<lote da rota>, bid_count, final_hash)` das
   colunas do lote.
4. Avaliar, antes de combinar: `verify_bid_chain(records, lot_id=<lote da rota>)`;
   `verify_anchor_hmac(estado anterior, anchor_hmac, audit_hmac_secret)`;
   `bid_count == len(records)`; `final_hash == records[-1].current_hash` (ou
   `GENESIS_HASH` sem registros).
5. Vínculo operacional:
   - `bid_count == 0`: `current_bid_cents` e `current_leader_id` nulos; âncora
     exatamente `0`/genesis com HMAC válida; não existe último lance.
   - `bid_count > 0`: último registro tem `sequence == bid_count`;
     `current_bid_cents == último.amount_cents`; `current_leader_id ==
     último.bidder_id`; `generate_bidder_alias(lot_id, current_leader_id,
     pseudonym_secret) == último.bidder_alias`.
6. Qualquer falha ou `ValueError` na montagem dos objetos a partir das linhas →
   409, rollback, zero efeitos, sem reparar nem reassinar.

O recálculo do item 5 é **só do alias do líder operacional atual**, para vinculá-lo
ao alias já autenticado do último evento. Não reabre a 3.3: a auditoria histórica
usa o alias persistido, nunca recalcula nem reescreve aliases antigos. A composição
fica em `bids.py`, sem helper público novo em `bid_integrity.py` (D13 da 3.3).

Nova âncora (passo 17): `compute_anchor_hmac(AnchorState(v=1, lot_id, bid_count + 1,
current_hash), audit_hmac_secret=...)`.

### 9.2 Passada adversarial B (integridade)

| Ataque | Resultado |
| --- | --- |
| Lance antigo alterado sem recalcular | Cadeia inválida → 409, nada muda |
| Cadeia recalculada, `final_hash` atualizado, HMAC antiga | HMAC anterior inválida → 409; o serviço nunca assina o estado adulterado (S-01) |
| Cadeia recalculada, resumo e HMAC antigos | Vínculo de `final_hash` falha → 409 |
| Lance legítimo depois de qualquer adulteração acima | 409; zero efeitos; nenhuma HMAC nova |
| Truncar o último lance | `count ≠ len` ou `final_hash ≠ último` → 409 |
| Trocar só `bid_count` ou só `final_hash` | HMAC anterior inválida → 409 |
| Âncora de outro lote (inclusive vazia) | O estado é montado com o `lot_id` da rota; a HMAC copiada não confere → 409 (S-02) |
| `anchor_hmac NULL` (legado ou apagada) | 409; nada reassina no lance, no boot, no seed ou na migration |
| Trocar `current_leader_id`/`current_bid_cents` no lote | Vínculo operacional falha → 409 |
| Trocar `bids.bidder_id` do último lance junto com o líder | Alias recalculado do líder ≠ alias autenticado → 409 |
| Erro entre gravar o lance e gravar a nova HMAC | Transação única: rollback total (T-ATOM) |
| Restaurar cadeia **e** âncora antigas válidas | Passa: limitação do AD-13 (sem âncora externa) |
| Segredo de auditoria comprometido | Fora da garantia (AD-13) |

**Risco resolvido (achado P2).** A HMAC da âncora protege o histórico canônico, mas
o `CanonicalBid` v1 não contém `current_leader_id` nem o identificador real do
usuário. Sem vínculo adicional, adulterar esses ponteiros poderia direcionar a
liberação de saldo à carteira errada. A mitigação desta story é o vínculo
operacional do passo 4, sem alterar os bytes v1.

**Limitação declarada:** a âncora v1 não autentica os termos do lote (inclusive
`ends_at`) nem os saldos das carteiras.

### 9.3 Segredos (P5)

- Primitives da 3.3 inalterados: `bytes` exatos não vazios.
- Contrato operacional (`IntegritySettings`, padrão de `AuthSettings`): os dois
  segredos existem, têm ≥ 32 bytes depois de `.encode("utf-8")`, são diferentes
  entre si e diferentes do `JWT_SECRET`; `SecretStr`, `hide_input_in_errors`;
  validação fail-fast em `create_app` (e no seed, só o de auditoria); erro sem ecoar
  valor. Montados uma vez em `app.state`, convertidos para `bytes`.
- 32 bytes não garantem entropia: o README pede valores aleatórios fortes (ex.:
  gerados por `secrets.token_urlsafe`).
- Nunca em banco, Git, log, resposta ou payload público. O log do 409 leva só a
  categoria interna da falha e o `lot_id` (público), nunca alias, `user_id`, hash,
  HMAC ou segredo. O engine já usa `hide_parameters=True`.

### 9.4 Testes e arquivos existentes que mudam (sem afrouxar)

| Arquivo | Mudança | Motivo |
| --- | --- | --- |
| `tests/conftest.py` | Gerar `PSEUDONYM_SECRET` e `AUDIT_HMAC_SECRET` aleatórios, distintos entre si e do `JWT_SECRET`; incluir `bids` nos `TRUNCATE` (ainda sem `CASCADE`) | `bids` referencia `lots` e `users` |
| `tests/lot_support.py` | `LOT_COLUMNS` com as colunas novas; `insert_lot` grava âncora vazia válida (com opção explícita de lote legado sem âncora) | Lotes de teste aptos a lance |
| `tests/integration/test_lots_migration.py` | Colunas novas na lista exata | Lista fixada |
| `tests/test_openapi.py` | `/api/lots/{lot_id}/bids` na ordem de registro | Lista fixada |
| `tests/integration/test_seed.py` | `test_module_runs_alone_with_only_database_url` passa a exigir `DATABASE_URL` e `AUDIT_HMAC_SECRET` (sem `PSEUDONYM_SECRET`, `APP_ORIGIN`, `JWT_SECRET`); predicado do demo autenticado | P4 |
| `tests/integration/test_lot_creation.py` | Afirmar âncora vazia válida | CA11 |

## 10. Testes em PostgreSQL real

Novos: `tests/test_bids_adapter.py` (unitário) e `tests/integration/`
`test_bids_migration.py`, `test_bid_service.py`, `test_bid_routes.py`,
`test_bid_concurrency.py`, `test_bid_integrity_gate.py`; apoio em
`tests/bid_support.py`, reaproveitando `wallet_support`. Nenhum `sleep` como prova;
decide o estado final.

**Tempo sem fragilidade.** O limite exato do anti-sniping (2 min, 2 min − 1 µs,
`now == ends_at`) já tem prova pura na 3.2. Na 3.4 não há teste que dependa de
acertar um microssegundo real. O caminho real prova: (a) que a hora vem de
`clock_timestamp()` lido depois da trava do lote; (b) os comportamentos com margens
determinísticas (minutos, nunca segundos colados no limite).

| ID | Cenário | Prova |
| --- | --- | --- |
| T-MIG | `0005`: colunas, tipos, defaults, nulabilidade, nomes de constraints, FKs, PK e UNIQUE; lotes existentes com `0`/genesis/`NULL`; CHECKs; literais = `MAX_CENTS`; `downgrade` | Estrutura |
| T-ROLE | 401; `AUCTIONEER` 403 sem efeito; 404; 422 para 0, negativo, `float`, `bool`, string, > `MAX_CENTS`, campo extra; CSRF 403/415 | CA1 |
| T-FIRST / T-NEXT | Primeiro `= starting_bid` aceito e −1 recusado; `atual + incremento` aceito e −1 recusado (422 `below_minimum`) | CA2/CA3 |
| T-SELF | Líder tenta cobrir o próprio lance → 422 `already_winning`, sem efeito | CA2 |
| T-BAL | Insuficiente → 422; disponível considera comprometido de outro lote; disponível exato é aceito | CA2/CA3 |
| T-OUTBID | B supera A: comprometidos exatos, totais intactos, líder e lance atual corretos, resposta 201 com lance, lote e carteira | CA3 |
| T-PHASE | Agendado (início em +1 h) → `lot_not_started`; vencido (fim em −1 h) → `lot_ended`; sem efeito, sem liquidar | CA2/CA4 |
| T-SNIPE | Fim em +1 min → aceito e `ends_at` + 2 min exatos sobre o fim lido; fim em +1 h → sem extensão; dois aceites na janela → +4 min | CA4 |
| T-CLOCK | Recorder: `FOR UPDATE` em `lots` antes de `clock_timestamp()`, uma leitura por operação; A segura a trava, B espera, `B.placed_at` > instante lido por A antes de confirmar; `placed_at` = timestamp canônico | CA5 |
| T-ORDER | Recorder: lote → carteiras crescentes nos dois arranjos; recusa pré-carteira e 409 não travam carteira | CA6 |
| T-CONC-2 | A segura a trava, B espera, A confirma: resultado serial, `sequence` 1 e 2 encadeadas, âncora válida | CA9 |
| T-CONC-N | Corrida livre com barreira, várias rodadas: I1–I6 | CA9 |
| T-DEADLOCK | Líderes cruzados em L1/L2, lances simultâneos: ambos terminam, sem `deadlock detected`; controle negativo com ordem por papel provoca deadlock | AD-8 |
| T-DEPOSIT | Depósito e lance sobrepostos na mesma carteira | CA9 |
| T-ATOM | Falha injetada depois do `INSERT` e antes da HMAC; depois de liberar o líder; no commit: banco igual ao anterior | CA10 |
| T-REFUSE-NOOP | Cada recusa e cada 409: `lots`, `bids`, `wallets` idênticos antes e depois | CA2/CA7 |
| T-CHAIN | Após N aceites: cadeia relida passa em `verify_bid_chain`; âncora em `verify_anchor_hmac`; bytes reconstruídos das colunas = hash gravado | CA8 |
| T-GATE | Adulteração direta antes de um lance legítimo (cada linha da §9.2 até "bidder_id junto com o líder"): 409 `lot_integrity_conflict`, mensagem genérica idêntica em todos os casos, zero efeitos, nenhuma HMAC nova | CA7 |
| T-INIT | POST e seed criam lote com âncora vazia válida; legado com `NULL` → 409; boot repetido não cria demo duplicado nem assina legado | CA11 |
| T-SECRETS | Ausente, curto em bytes (inclusive texto multibyte no limite), igual ao outro, igual ao `JWT_SECRET` → falha sem ecoar; nenhuma resposta, linha ou log capturado contém os segredos | CA12 |
| T-REUSE | Spies: pré e pós-carteira uma vez no aceite; recusa pré-carteira não chama a pós nem `lock_wallet`; `database_now` uma vez | CA13 |

## 11. Documentação

**Já sincronizada nesta consolidação:** `docs/ARQUITETURA.md` (quadro do AD-7;
AD-7 com 18 passos e refinamento; AD-13 com gate, vínculo operacional, âncora na
criação, legado não autenticado e segredos; AD-20 com alias de 16 hex persistido e
rotação não suportada; Q3 resolvida; Q4 com o predicado do demo autenticado;
histórico), `CLAUDE.md` (AD-7, AD-13, AD-20, Q3) e `epics.md` (AR5 "16 passos",
"AD-7 passo 15" e pendência Q3, só fatos desatualizados).

**No build:** esta story (registro, comandos, saídas reais), `sprint-status.yaml`,
`docs/uso_de_ia.md`, `deferred-work.md` (o que surgir no build) e
`README.md`: as duas variáveis novas no painel do Render **antes** do deploy (sem o
de auditoria o seed falha e o servidor não sobe), valores aleatórios fortes,
lotes legados sem lance, anti-sniping cumulativo e sem teto, recusas com motivo,
409 de integridade, rotação de segredos não suportada, rollback consistente da
âncora não detectado.

## 12. Decisões fechadas (26/10/2026)

### P1 — Gate depois da hora e antes das regras pré-carteira — decidida

Decidi: BEGIN → trava do lote → `clock_timestamp()` → autenticação do estado
anterior → só então as regras pré-carteira da 3.2. `current_bid_cents` e
`current_leader_id` entram no mínimo e no "já está ganhando" e não podem ser tratados
como confiáveis antes do vínculo com o histórico autenticado. Qualquer falha do gate
impede todos os efeitos posteriores. Refinamento registrado no AD-7.
**Descartei** o gate depois da etapa pré-carteira (recusas sairiam sobre estado não
autenticado) e verificar depois de escrever (assinaria estado adulterado).

### P2 — Vínculo entre histórico autenticado e estado operacional — decidida

Decidi o conteúdo do §9.1, item 5: com lances, último registro na `sequence ==
bid_count`, lance atual e líder iguais ao último lance e alias recalculado **só do
líder operacional atual** igual ao alias autenticado; sem lances, lance atual e
líder vazios e âncora `0`/genesis com HMAC válida. Não reabre a 3.3: a auditoria usa
o alias persistido e nunca recalcula nem reescreve aliases históricos. **Descartei**
a receita §9 sozinha (não protege o estado derivado) e a igualdade sem o alias (não
pega troca coordenada de líder e `bidder_id`).

### P3 — Bootstrap — decidida

Decidi: todo lote novo nasce com `bid_count = 0`, `final_hash = GENESIS_HASH` e
`anchor_hmac` válida para o próprio `lot_id`, usando `AUDIT_HMAC_SECRET` na mesma
transação do `INSERT`. Lotes legados com `anchor_hmac NULL` são explicitamente não
autenticados e não aceitam lance. Sem fallback `NULL + zero lances = confiável`.
Nenhum comando manual de reassinatura na 3.4 (trabalho adiado, se desejado). O seed
garante um demo novo e autenticado: o predicado de "demo realmente aberto" passa a
ser `is_demo AND ends_at > agora AND anchor_hmac IS NOT NULL`, sem transformar
legado em confiável. **A spec deve analisar a idempotência do seed real**: no
primeiro boot da 3.4 em produção, um demo legado aberto não conta e um demo
autenticado é criado; nos boots seguintes ele conta e nada é criado; dois seeds
simultâneos continuam serializados pela trava consultiva; nenhum caminho cria demo a
cada boot. **Descartei** migration com segredo, reassinar no boot (qualquer filtro é
dado manipulável do banco) e o comando manual nesta story.

### P4 — Seed — decidida

Decidi: o seed precisa de `DATABASE_URL` e `AUDIT_HMAC_SECRET`; não exige
`PSEUDONYM_SECRET` (não gera alias). O teste que afirma "só `DATABASE_URL`" é
atualizado no build para o novo contrato exato. **Descartei** demo sem âncora (quebra
FR19).

### P5 — Segredos operacionais — decidida

Decidi separar o contrato dos primitives (3.3, inalterado: `bytes` não vazios) do
contrato operacional do §9.3: ambos existem, ≥ 32 bytes em UTF-8, diferentes entre si
e do `JWT_SECRET`, fail-fast. Não afirmo que 32 bytes garantem entropia; documento
valores aleatórios fortes. **Descartei** mínimo só não vazio e não comparar com o
`JWT_SECRET`.

### P6 — Contrato HTTP — decidida

Decidi: `POST /api/lots/{lot_id}/bids`, só `BIDDER` pela política existente. Aceite
**201** com resposta mínima e suficiente para a UI: lance aceito em representação
pública/segura, estado atualizado necessário do lote e snapshot da carteira do
usuário autenticado. Nunca segredos, dados pessoais, `bidder_id`, hashes, HMAC ou
informação interna desnecessária. A spec fixa os schemas exatos nos padrões do
projeto (DTOs Pydantic, `response_model`, `responses=error_responses(...)`,
`Cache-Control: no-store`). Recusas da 3.2 → **422** no envelope único com o código de
domínio preservado; a rota não duplica a decisão. **Descartei** 409 para recusas e
200 com união fora do envelope.

### P7 — Falha de integridade — decidida

Decidi: **409** com `code = "lot_integrity_conflict"` e mensagem externa genérica
(sem indicar se falhou SHA, count, `final_hash`, HMAC, alias ou líder). Detalhe
técnico só no log interno, sem segredo. Falha fechada: não repara, não reassina, não
continua; zero efeitos. **Descartei** 500 genérico (indistinguível de bug) e 503.

### P8 — Schema — decidida (direção para a spec)

Decidi a §7: colunas de lance atual, líder e âncora em `lots`, com CHECKs/FKs e o
estado legado `anchor_hmac NULL` representável só dentro das coerências; `bids` com
os campos que reconstroem exatamente o `CanonicalBid` v1 mais `current_hash` e
`canonical_version`; `bidder_id` persistido para uso operacional, não autenticado
pelo v1 e nunca usado sozinho para decisão financeira; `PRIMARY KEY (lot_id,
sequence)` e `UNIQUE (lot_id, previous_hash)`; sem UUID substituto; sequência = `bid_count`
autenticado + 1 sob `FOR UPDATE`, nunca `MAX(sequence) + 1`. A spec confirma a
compatibilidade com o PostgreSQL e os padrões atuais.

### P9 — Documentação — decidida

Decidi sincronizar **agora**, antes da spec, sem commit separado proposto por mim (Git é
meu): `ARQUITETURA.md`, `CLAUDE.md` e só as linhas factualmente desatualizadas de
`epics.md` (§11). Rejeitei a proposta de commit separado de documentação.

## 13. Riscos

| Risco | Tratamento |
| --- | --- |
| Deadlock | Ordem única lote → carteiras crescentes; T-DEADLOCK com controle negativo; 4.3/6.6 herdam a ordem |
| Saldo comprometido perdido/duplicado | Mesma transação, valores autenticados e travados, CHECK por `UPDATE`, I3 em corrida livre |
| CHECK violada por corrupção | `IntegrityError` → rollback → 500; nunca "conserta" saldo |
| Sequência duplicada / bifurcação | Count autenticado sob trava; PK e `UNIQUE (lot_id, previous_hash)` |
| Lavagem por reautenticação (S-01) | Gate no passo 4, antes de qualquer efeito |
| Ponteiros de líder/lance atual adulterados (achado P2) | **Resolvido** pelo vínculo operacional, sem mudar bytes v1 |
| Bootstrap reabre S-01 | Nada reassina; legado `NULL` bloqueado |
| Seed duplica demo ou falha sem segredo | Predicado autenticado + trava consultiva (spec analisa idempotência); segredo configurado antes do deploy, fail-fast com mensagem clara |
| Lotes legados de produção sem lance | Demo novo autenticado; README |
| Premissa "toda escrita passa pela trava" violada no futuro | Spec registra a obrigação para 3.6/4.3/6.6 |
| Leitura O(n) da cadeia por tentativa | Aceitável na escala do desafio |
| Teste temporal intermitente | Limite exato só na 3.2; margens de minutos na 3.4 |
| `ValueError` virando 409/recusa por captura ampla | Tradução só na montagem do gate |
| Rollback consistente de cadeia + âncora; âncora sem termos/saldos | Limitações do AD-13, README |
| Rotação de segredo bloqueia lances | A1 da 3.3; README |

## 14. Tarefas (build, depois da spec)

- [x] T0 — Fechar P1–P9 e sincronizar documentação (esta consolidação).
- [x] T1 — Spec da 3.4 (`/bmad-spec`, sessão autorizada).
- [x] T2 — Migration `0005`, ORM + T-MIG (CA3, CA8, CA11).
- [x] T3 — `IntegritySettings`, `create_app`, `conftest` + T-SECRETS (CA12).
- [x] T4 — Âncora vazia em `create_lot` (POST e seed), predicado do demo + T-INIT (CA11).
- [x] T5 — `bids.py`: adaptadores, gate, serviço (CA3–CA10, CA13).
- [x] T6 — Rota, códigos e mensagens (CA1, CA2, CA7).
- [x] T7 — Testes da §10 e ajustes da §9.4 (CA9, CA10, CA14).
- [x] T8 — README, `uso_de_ia.md`, `deferred-work.md`, story, sprint; `./verify.sh` com saída real (CA14).

## 15. Dev Notes

### Arquivos previstos

| Arquivo | Ação |
| --- | --- |
| `backend/migrations/versions/0005_bids.py` | Novo |
| `backend/app/bids.py` | Novo: `Bid`, adaptadores, gate, serviço, rota, DTOs; não importa `app.main` |
| `backend/app/lots.py` | Colunas de `Lot`; `create_lot` assina a âncora vazia com o segredo recebido explicitamente |
| `backend/app/config.py` | `IntegritySettings` |
| `backend/app/main.py` | Configuração de integridade em `app.state`; registro da rota |
| `backend/app/seed.py` | `AUDIT_HMAC_SECRET`; predicado do demo autenticado |
| `backend/app/errors.py` | Cinco códigos de recusa e `lot_integrity_conflict`, mensagens em português |
| `backend/app/wallet.py` | Sem mudança esperada |
| `bid_rules.py`, `bid_integrity.py`, `lot_time.py`, `money.py` | Intocados |
| `frontend/` | Intocado (3.5) |

### Armadilhas

- `populate_existing` no `FOR UPDATE` do lote, como em `lock_wallet`.
- `uuid.UUID` dos dois lados na ordenação; nunca string.
- `Cents` (`StrictInt`) já recusa `bool`/`float` com 422.
- `CanonicalBid` exige `datetime` com fuso (o psycopg devolve `TIMESTAMPTZ` com
  fuso); nunca `replace(tzinfo=...)`.
- `AnchorState` com `bid_count = 0` e hash não genesis levanta `ValueError`;
  `verify_anchor_hmac` levanta com assinatura `None`: no gate, ambos são 409.
- `get_session` não faz commit; recusas e 409 fazem rollback explícito.
- `TRUNCATE` dos fixtures continua sem `CASCADE`.
- Sem evento (4.1), sem liquidação (4.4).

### Referências

- `docs/ARQUITETURA.md`: AD-3, AD-5, AD-6, AD-7 (refinamento 26/10), AD-8, AD-9,
  AD-10, AD-13 (refinamento 26/10), AD-17, AD-19, AD-20, AD-21, AD-24, AD-26, AD-29,
  AD-30, Q3, Q4, Q5.
- `_bmad-output/planning-artifacts/epics.md`, Story 3.4.
- `_bmad-output/specs/spec-story-3-3-integridade-historico/integrity-contract.md`
  §9–§10; `decisions.md` D13/D14.
- `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/domain-contract.md`
  §9–§10; `decisions.md` D2/D3/D8.
- `_bmad-output/implementation-artifacts/deferred-work.md` (nota para a 3.4).
- `backend/app/wallet.py`, `backend/app/lots.py`, `backend/tests/wallet_support.py`.
- Manual do PostgreSQL 18 (isolamento de transação; `SELECT ... FOR UPDATE`;
  `clock_timestamp()`): a spec cita as seções. Não fiz pesquisa web nestas sessões.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`): criação via `bmad-create-story` e consolidação. Build (26/10/2026): Claude Sonnet 5.5 (`claude-sonnet-5-5`), via `bmad-build`, direto da spec (`_bmad-output/specs/spec-story-3-4-lance-transacional/`). O pedido indicava outro modelo como implementador; a sessão rodou neste.

### Completion Notes List

- Criação e consolidação (26/10/2026): P1–P9 fechadas, documentação sincronizada.
- Build (26/10/2026): implementei exatamente o desenho da spec, sem redesenhar. Q-3 (IC-1) confirmada: o "+4 min" foi substituído por T-SNIPE (3) e pela extensão exata sobre o fim lido. Q-1: `backend/.env.example` **não foi lido nem alterado** (decisão do dono); a instrução fica no README e no relatório.
- Migration `0005_bids.py`: 5 colunas e 8 CHECKs nomeadas e 1 FK em `lots`; tabela `bids` (PK `(lot_id, sequence)`, `uq_bids_lot_id_previous_hash`, 2 FKs, 6 CHECKs). Aditiva, sem segredo, sem backfill assinado.
- `app/bids.py` (novo): `Bid`, gate `authenticate_previous_state`, `place_bid` (F1 `UPDATE wallets`, F2 `INSERT bids`, F3 **um** `UPDATE lots`) e a rota. `lots.py`: `lock_lot`, `get_integrity_config`, colunas, `create_lot` com `audit_hmac_secret` obrigatório. `config.py`: `AuditSettings`, `IntegritySettings`, `IntegrityConfig`, `integrity_config`. `seed.py`: `AUDIT_HMAC_SECRET` e predicado do demo autenticado. `errors.py`: 6 códigos. Intocados: `bid_rules.py`, `bid_integrity.py`, `lot_time.py`, `money.py`, `wallet.py` (nas mutações, `wallet.py` só foi alterado temporariamente e restaurado).
- Ajustes em testes existentes sem afrouxar nada (colunas, FKs, CHECKs, paths, tabela `bids`, catálogo de mensagens, inversão prevista pela 3.2, assinatura de `create_lot`, `run_seed` com segredo, `test_database`, `test_lot_rules`).
- Um comando que eu escrevi continha por engano `git status`; a permissão foi negada e **nada de Git foi executado**.

### Mutações realmente executadas (uma por vez, restauradas; conferi por `cmp`)

Script em arquivo temporário da sessão, `pytest -x` sobre os arquivos de lance, seed, criação de lote, config, pureza e OpenAPI. Morreram: M-1, M-2, M-3, M-4, M-5, M-24, M-6a, M-6b, M-7, M-8, M-9, M-10, M-11, M-12, M-13, M-14, M-15, M-16, M-17, M-18, M-19, M-20, M-21, M-22, M-23, M-25, M-26b, M-26c e as extras E1 (alias com segredo de auditoria), E2 (sem persistir a extensão), E4 (líder anterior não liberado), E5 (recusa vira 409), E6 (aceite com 200), E8 (âncora do lote novo com outro id), E9 (verificação com o segredo de pseudônimo).

**Sobreviveram (relato honesto):**
- **E3 (`ends_at` sempre atribuído):** equivalente. O ORM não inclui no `SET` um atributo cujo valor não mudou, então o `UPDATE` é o mesmo; a propriedade SR-02 (T-ORDER) é garantida pelo comportamento, não por um hack.
- **E7 (sem `session.rollback()` antes do serviço, D5):** sobrevive; é defesa (transação limpa, `User` fora do identity map) sem efeito observável hoje em `READ COMMITTED`.
- **M-26a (`server_default` no banco):** **não executada**: o `conftest` recria o schema a cada sessão, então o default não sobreviveria; a mutação sem o default só quebra por `NOT NULL` (morte trivial, não relevante).
- M-18 morreu no teste de ordem/relógio (a asserção de `FOR UPDATE`), não no T-CONC-2.

### Comandos e saídas reais

- `uv run ruff format --check .` e `uv run ruff check .`: sem pendências.
- `uv run pytest -q`: **1970 passed, 1 warning** (a mesma `StarletteDeprecationWarning` do `httpx`, anterior à 3.4). Os seis arquivos novos de lance coletam 206 testes.
- `./verify.sh` (completo, com `docker build`): **exit 0**, "verify.sh: todas as etapas passaram." Backend `1970 passed`; front `tests 114, pass 114, fail 0`; build do Vite e `docker build` ok. Saída completa conferida no log da sessão.

### Review final e fechamento (26/10/2026)

Registrei o resultado informado pelo responsável: o review independente principal,
iniciado com GPT-6 Astra High, foi interrompido pelo limite de uso após encontrar
1 LOW, antes de concluir toda a auditoria e a consolidação. O complemento focado,
feito com modelo mais econômico, verificou writers, HTTP/security, qualidade dos
testes e mutation spot-check.

Resultado consolidado: **0 BLOCKER, 0 HIGH, 0 MEDIUM, nenhum LOW técnico**.
O único finding, **F-01 LOW documental**, foi corrigido: acrescentei
`AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET` ao exemplo de `docker run` do README,
somente com placeholders sintéticos, explicitando mínimo de 32 bytes em UTF-8 por
segredo e valores diferentes entre si e de `JWT_SECRET`.
**Recomendação final: aprovada.** Não tratei a auditoria principal como concluída;
a aprovação considera o processo principal mais o complemento informado.

Fechei somente a Story 3.4 como `done`; o Epic 3 permanece `in-progress` e a
Story 3.5 permanece `backlog`, sem ser iniciada. Neste fechamento alterei apenas
README, esta story, `sprint-status.yaml` e `docs/uso_de_ia.md`, sem código produtivo,
testes, specs ou arquitetura; nenhum `.env*` foi lido/editado e nenhum Git executado.

Verificação deste fechamento, separada dos resultados históricos do build:

- `./verify.sh`: exit 2 na primeira etapa, pois o `uv` não conseguiu criar um
  arquivo temporário no cache padrão (Operation not permitted).
- `UV_CACHE_DIR=/private/tmp/story-3-4-uv-cache COMPOSE_DISABLE_ENV_FILE=1 ./verify.sh`:
  Ruff lint passou; formato: `82 files already formatted`; exit 1 na checagem de
  infraestrutura: Docker não instalado ou daemon não rodando. O script parou
  antes de subir PostgreSQL, executar pytest, verificar frontend ou construir a imagem.
- Não repeti a suíte PostgreSQL nem mutation testing. O verify completo aprovado
  do build permanece como registro histórico acima; não afirmo nova execução completa
  bem-sucedida neste fechamento documental.

### File List (build; fechamento documental registrado acima)

- `backend/migrations/versions/0005_bids.py` (novo)
- `backend/app/bids.py` (novo)
- `backend/app/lots.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/seed.py`, `backend/app/errors.py`
- Testes novos: `backend/tests/bid_support.py`, `tests/test_bids_gate.py`, `tests/integration/{test_bids_migration,test_bid_service,test_bid_routes,test_bid_concurrency,test_bid_integrity_gate}.py`
- Testes alterados: `tests/conftest.py`, `tests/lot_support.py`, `tests/integration/{test_lots_migration,test_seed,test_wallet_service,test_public_lots,test_lot_creation,test_database}.py`, `tests/{test_openapi,test_access_policy,test_errors,test_bid_rules,test_config,test_domain_purity,test_lot_rules}.py`
- `README.md`, `docs/uso_de_ia.md`, `_bmad-output/implementation-artifacts/deferred-work.md`, `_bmad-output/implementation-artifacts/sprint-status.yaml` (3.4 → `review`), esta story.
- `backend/.env.example`: **não lido, não alterado**. Para o dono: acrescentar `AUDIT_HMAC_SECRET=` e `PSEUDONYM_SECRET=` (sem valor, ou placeholder fictício), e pôr os valores reais no `backend/.env` e no painel do Render.
