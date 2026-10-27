# Plano de testes — Story 3.4

> **Nota de revisão da decisão (27/10/2026).** Esta spec foi escrita e implementada com a AD-5 anterior (`ends_at + 2 min`, nunca `now + 2 min`). Revisei a AD-5 em 27/10/2026: a regra vigente é `novo fim = now + 2 min` (mesmo `now` lido sob a trava; exatamente 2 min restantes: sem mudança e flag falsa). O texto abaixo permanece como registro do que eu decidi na época e **não foi reescrito**. Ver `docs/ARQUITETURA.md`, AD-5.

Regras: PostgreSQL real para tudo que toca banco (AD-17); nenhum `sleep` como prova
(o estado final decide; `wait_for_blocked_lock` é evidência auxiliar); margens de
minutos/horas no relógio real, nunca segundos colados no limite (Q5); nenhum teste
existente afrouxado.

## 1. Apoio (`tests/bid_support.py`, novo)

| Helper | Faz |
| --- | --- |
| `integrity_secrets()` | `(audit, pseudonym)` em `bytes`, lidos do ambiente que o `conftest` preparou |
| `add_bidder(factory, total=0)` | Usuário `BIDDER` novo + carteira (além dos dois semeados) |
| `live_lot(factory, **cols)` | `insert_lot` assinado, início −1 h, fim +1 h (padrão) |
| `run_bid(factory, lot_id, bidder_id, amount)` | Serviço numa `Session` própria; `commit` se `PlacedBid`, senão `rollback`; devolve o resultado |
| `hold_bid(session, ...)` | Serviço sem commit: segura as travas (orquestração) |
| `db_snapshot(factory)` | `(lots completos, bids, wallets)` ordenados: comparação "nada mudou" |
| `assert_authenticated(factory, lot_id)` | Recompõe com os primitives da 3.3: cadeia, âncora (segredo de auditoria), vínculo operacional |
| `assert_invariants(factory)` | I1–I5 em todos os lotes e carteiras |
| `before_statement(engine, marker, action, once_per_thread=True)` | Generaliza `before_public_read`: roda `action` antes do statement que contém `marker` |
| `tamper(factory, sql, params)` | Adulteração direta por SQL |
| `drop_checks(engine, names)` (fixture) | Remove CHECKs para estados que só um atacante com DDL cria; restauração determinística abaixo |
| `role_ordered_locks(...)` | Só para o controle negativo de deadlock |
| `call_log(monkeypatch)` | Envolve, em `app.bids`, os primitives públicos que o gate usa (`verify_bid_chain`, `verify_anchor_hmac`) e `evaluate_pre_wallet`; cada chamada anota um evento e delega à função real |

**`drop_checks` (determinístico e seguro):**

1. Recebe uma lista fixa de nomes do próprio teste (nunca entrada externa) e confere
   o banco de teste (`assert_connection_is_test_database`). Só aceita CHECKs das
   tabelas `lots` e `bids` (as únicas que o finalizador limpa); nome de outra tabela
   reprova o teste antes de qualquer `DROP`.
2. Antes do `DROP`, captura de `pg_constraint` (junto de `pg_class`) para cada nome:
   tabela, nome e `pg_get_constraintdef(oid)`. Nome ausente reprova o teste.
3. `ALTER TABLE <tabela> DROP CONSTRAINT <nome>` só para os capturados.
4. Finalizador (`yield` + `try/finally`), executado mesmo com falha do teste: limpa as
   linhas que violariam as CHECKs (`TRUNCATE bids, lots`, sem `CASCADE`) e recria
   **somente** as removidas com `ALTER TABLE <tabela> ADD CONSTRAINT <nome>
   <definição capturada>`. Nenhum SQL de CHECK escrito à mão na fixture.
5. Reconsulta o catálogo e afirma que `(tabela, nome, definição)` são iguais aos
   capturados. Um teste de adulteração nunca deixa o schema contaminado.

`lot_support.insert_lot` passa a gravar âncora vazia válida por padrão
(`anchored=True`); `anchored=False` cria o lote legado (`anchor_hmac NULL`).

Invariantes: **I1** um líder; lance atual e líder = último lance. **I2** `0 <=
committed <= total`. **I3** `committed` de cada usuário = soma de `current_bid_cents`
dos lotes que lidera. **I4** `sequence` 1..N, `bid_count = N`, `final_hash` = hash do
N-ésimo, HMAC confere. **I5** sem bifurcação. **I6** resultado = alguma ordem serial.

## 2. Matriz PostgreSQL (22 cenários da story)

Coluna "Concorrência": transações simultâneas e ponto de sincronização. "—" = uma
transação.

| ID | Precondição | Concorrência | Esperado | Invariantes |
| --- | --- | --- | --- | --- |
| T-MIG | `0005` aplicada; para backfill: `downgrade 0004`, lotes inseridos, `upgrade head` | — | Colunas, tipos (`information_schema`), nulos, defaults, 8+6 CHECKs e FKs com nomes exatos, `pk_bids`, `uq_bids_lot_id_previous_hash`; lote antigo com `0`/genesis/`NULL`; literais = `MAX_CENTS` e genesis = `GENESIS_HASH`; cada CHECK recusa por nome; segundo "primeiro lance" do lote recusado pela UNIQUE; `downgrade` remove só o que criou | estrutura |
| T-ROLE | Lote vivo; usuários semeados | — | 401 sem sessão; `AUCTIONEER` 403 sem nenhum `FOR UPDATE` no recorder e banco igual; lote inexistente 404; `lot_id` inválido 422; corpo 0, −1, `1.5`, `true`, `"100"`, `MAX_CENTS+1`, campo extra, ausente, JSON malformado → 422 `validation_error`; sem `Origin` 403; não JSON 415 | banco igual |
| T-FIRST | Lote sem lances, inicial 10 000 | — | 10 000 → 201, `sequence 1`, `previous_hash` genesis; 9 999 → 422 `below_minimum` | I1–I4 |
| T-NEXT | Lote com lance 10 000, incremento 1 000 | — | 11 000 → 201; 10 999 → 422 `below_minimum` | I1–I4 |
| T-SELF | Licitante lidera | — | 422 `already_winning`; nenhuma carteira travada | banco igual |
| T-BAL | Licitante lidera outro lote com 5 000; total 10 000 | — | 6 000 → 422 `insufficient_balance`; 5 000 (exato disponível) → 201 e `committed = 10 000` | I2, I3 |
| T-OUTBID | A lidera com `c`; A também lidera outro lote; B com saldo | — | B com `a` → 201; `C_A −= c`, `C_B += a`, totais iguais; compromisso de A no outro lote preservado; resposta com campos exatos e `wallet` de B | I1–I4 |
| T-PHASE | Agendado (início +1 h); vencido (início −2 h, fim −1 h) | — | `lot_not_started` / `lot_ended`; `ends_at` e tudo igual; nada liquidado | banco igual |
| T-SNIPE | (1) fim `E = agora + 60 s`; (2) fim +1 h; (3) fim +60 s; (4) fim +60 s | (3): A aceita e segura a trava; B espera; A confirma | (1) `ends_at == E + 2 min` exato e `anti_sniping_applied`; (2) inalterado; (3) **B aceito com `anti_sniping_applied = False` e `ends_at == E + 2 min`** (leu o fim de A); (4) recusa (mínimo e saldo) não estende. Cumulatividade entre aceites sucessivos: prova pura da 3.2 (IC-1) | I4 |
| T-CLOCK | Lote vivo | (b): A segura a trava; B espera (`wait_for_blocked_lock`); teste lê `T1 = clock_timestamp()` noutra conexão; A confirma | (a) recorder: `FOR UPDATE` em `lots` antes do único `clock_timestamp()` da transação; spy em `app.bids.database_now` guarda o instante devolvido; o `placed_at` **relido do banco** é igual a esse instante (µs); o `placed_at` da resposta, convertido em `datetime`, é o mesmo instante (comparação semântica, nunca de string); `CanonicalBid` reconstruído do `placed_at` persistido produz bytes com `.ffffffZ` e o hash gravado; (b) `A.placed_at < T1 < B.placed_at`; (c) `SHOW transaction_isolation` dentro do serviço = `read committed` | — |
| T-ORDER | Dois arranjos: líder com `user_id` menor e maior; com e sem extensão | — | Recorder: sequência exata de statements (lote `FOR UPDATE`, clock, `SELECT bids` sem agregação, carteiras em `user_id` crescente, `UPDATE wallets`, `INSERT bids`, **um** `UPDATE lots`); o `SET` desse `UPDATE` tem `current_bid_cents`, `current_leader_id`, `bid_count`, `final_hash`, `anchor_hmac` sem extensão, e esses mais `ends_at` com extensão; recusa pré-carteira e 409 sem `SELECT wallets` | — |
| T-CONC-2 | Lote sem lances | A segura a trava (aceito, sem commit); B espera; A confirma. Variantes: (a) ambos com o inicial; (b) B com inicial + incremento; (c) mesmo licitante duas vezes; (d) B pelo HTTP | (a) B → `below_minimum`; (b) B → `sequence 2`, `previous_hash = hash1`, A liberado; (c) `already_winning`; (d) 422/201 equivalentes | I1–I5 |
| T-CONC-N | 4 licitantes, 1 e 2 lotes, saldos amplos | Corrida livre: barreira, threads com `run_bid`, 5 rodadas (`parametrize`) | Todo resultado é `PlacedBid` ou recusa; nenhum 500; aceitos formam a cadeia; consecutivos respeitam mínimo e alternam licitante | I1–I6 |
| T-DEADLOCK | U1 lidera L1, U2 lidera L2 | U2 em L1 e U1 em L2; barreira antes do primeiro `SELECT wallets` de cada thread (ambas já com seu lote) | Ambos 201; sem `deadlock detected`; U1 lidera L2, U2 lidera L1, comprometidos trocados. Controle negativo (`role_ordered_locks`: novo líder primeiro, barreira entre a primeira e a segunda carteira): uma thread recebe SQLSTATE 40P01 | I2, I3 |
| T-DEPOSIT | Licitante com total `T` | (a) lance segura a carteira, depósito espera; (b) depósito segura a carteira, lance (já com o lote) espera; (c) = (b) com a carteira pré-carregada na `Session` do lance | (a) `total = T + D`, `committed = a`; (b)/(c) lance que só cabe com `D` é aceito | I2 |
| T-ATOM | Lote com líder | — | Falha em (A1) depois de F1, (A2) depois de F2 e antes da nova âncora, (A3) simulada no commit **antes de o `COMMIT` ser enviado**, (A4) CHECK de carteira em F1: 500 genérico, recorder confirma o statement anterior executado, `db_snapshot` igual. Falha de conexão depois de enviar o `COMMIT` não é testável deterministicamente (`transaction-contract.md` §7) | todas |
| T-REFUSE-NOOP | Cada recusa e cada categoria de 409 | — | `db_snapshot` antes = depois; nenhuma HMAC nova | todas |
| T-CHAIN | 5 aceites alternados | — | `verify_bid_chain` ok; âncora confere com o segredo de auditoria e **não** com o de pseudônimo; bytes reconstruídos das colunas → hash gravado; alias de cada linha = HMAC do pseudônimo; mesmo usuário com alias diferente em outro lote | I4, I5 |
| T-GATE | 2–3 lances legítimos; depois a adulteração | — | Cada caso §3: 409 com corpo idêntico, `db_snapshot` igual, log com a categoria esperada e sem segredo/hash/alias | — |
| T-INIT | — | Seed: dois seeds simultâneos (existente) | `POST /api/lots` e seed: `bid_count 0`, genesis, âncora válida do próprio id, `NULL` no resto; legado → 409; seed com demo legado aberto cria um assinado e não toca o legado; segunda execução `(0, False)`; sem `UPDATE`/`DELETE`; `create_lot` com segredo `b""` → `ValueError` e nenhuma linha | — |
| T-SECRETS | — | — | Ausente, 31 bytes, `"é" * 15 + "a"` (31 bytes) recusados; `"é" * 16` (32 bytes) aceito; iguais entre si; igual ao `JWT_SECRET`; surrogate → erro sem caractere; nada disso ecoa o valor; `repr` de `IntegritySettings`/`IntegrityConfig` sem segredo; seed por subprocesso (`seed-and-lot-creation.md` §4); `caplog` e respostas de um fluxo completo sem os dois segredos | — |
| T-REUSE | — | — | Spies em `app.bids`: `evaluate_pre_wallet` e `evaluate_post_wallet` 1× no aceite; recusa pré-carteira não chama a pós nem `lock_wallet`; `database_now` 1×; `available_cents` 1× com os valores travados; `bids.py` sem relógio (detector de `test_domain_purity` aplicado ao arquivo). **Ordem semântica (SR-01):** com `call_log`, num lote com lances, a primeira chamada a `verify_bid_chain`/`verify_anchor_hmac` acontece antes de `evaluate_pre_wallet`; num 409, `evaluate_pre_wallet` não é chamado. O teste observa os primitives públicos da 3.3 e da 3.2, não o nome do helper do gate | — |

## 3. Casos de T-GATE

Base: lote com lances legítimos. Esperado sempre 409 idêntico, zero efeitos, nada
reparado nem reassinado (exceto G18).

| # | Adulteração | Categoria |
| --- | --- | --- |
| G1 | `amount_cents` do lance 1 alterado, sem recalcular | `chain_mismatch` |
| G2 | Lance 1 alterado, cadeia toda recalculada, `final_hash` novo, HMAC antiga (S-01) | `anchor_mismatch` |
| G3 | Cadeia recalculada, `final_hash` e HMAC antigos | `summary_mismatch` |
| G4 | Último lance apagado | `summary_mismatch` |
| G5 | Último apagado e `bid_count`/`final_hash` ajustados ao anterior | `anchor_mismatch` |
| G6 | Só `bid_count` | `anchor_mismatch` |
| G7 | Só `final_hash` | `anchor_mismatch` |
| G8 | Âncora (vazia e com lances) copiada de outro lote | `anchor_mismatch` |
| G9 | `anchor_hmac = NULL` com zero e com N lances; lote legado | `missing_anchor` |
| G10 | `current_leader_id` trocado | `operational_mismatch` |
| G11 | `current_bid_cents` trocado (≥ inicial) | `operational_mismatch` |
| G12 | `bidder_id` do último lance e `current_leader_id` trocados juntos | `operational_mismatch` |
| G13 | Lance extra válido no fim, sem atualizar o lote | `summary_mismatch` |
| G14 | `anchor_hmac` com formato inválido (CHECK removida) | `malformed_state` |
| G15 | Zero lances com líder e lance atual (CHECKs removidas) | `operational_mismatch` |
| G16 | `bid_count > 0` com lance atual e líder `NULL` (CHECKs removidas) | `operational_mismatch` |
| G17 | `canonical_version = 2` / alias malformado (CHECKs removidas) | `malformed_state` |
| G18 | `starting_bid_cents` elevado acima do lance atual (termos do lote **não** são cobertos pela âncora; CHECK removida): o gate passa e `LotBidState` levanta | **500**, não 409 (`ValueError` fora do gate) |
| G19 | Inserção no meio: lance novo como `sequence 2`, posteriores renumerados, cadeia recalculada a partir dele, `bid_count`/`final_hash` ajustados, HMAC antiga | `anchor_mismatch` |
| G20 | Remoção do meio **sem** renumerar (lacuna na sequência) | `chain_mismatch` |
| G21 | Remoção do meio **com** renumeração e cadeia recalculada, `bid_count`/`final_hash` ajustados, HMAC antiga | `anchor_mismatch` |
| G22 | Só `bidder_id` do último lance alterado (líder intocado) | `operational_mismatch` |
| G23 | Âncora bem formada e coerente com a cadeia, assinada com **outro** `AUDIT_HMAC_SECRET` | `anchor_mismatch` |

**Prioridade 409 sobre 422 (SR-01).** Em cada caso abaixo a regra pura, se rodasse
antes do gate, daria uma recusa de negócio. O resultado obrigatório é 409, com
`db_snapshot` igual e **nenhum** `SELECT wallets` no recorder:

| # | Adulteração | 422 que sairia sem o gate primeiro | Categoria |
| --- | --- | --- | --- |
| G9b | Lote legado (`anchor_hmac NULL`) **e** `ends_at < agora` | `lot_ended` | `missing_anchor` |
| G10b | Último lance de U1; `current_leader_id` trocado para U2, que é quem tenta o lance (valor válido) | `already_winning` | `operational_mismatch` |
| G11b | `current_bid_cents` elevado (≥ inicial) de modo que o valor tentado fique abaixo de `atual + incremento` | `below_minimum` | `operational_mismatch` |

## 4. Testes sem banco e ajustes

| Arquivo | Conteúdo |
| --- | --- |
| `tests/test_bids_gate.py` (novo; a story chamava `test_bids_adapter.py`) | `authenticate_previous_state` com objetos simples: cada categoria, ordem das categorias, só `ValueError` da montagem vira `malformed_state` |
| `tests/test_config.py` | Parte de T-SECRETS |
| `tests/test_errors.py` | Catálogo literal + seis entradas |
| `tests/test_bid_rules.py` | `test_refusal_codes_are_not_http_catalog_codes` vira `..._are_http_catalog_codes` (conjunto ⊆ `MESSAGES`) |
| `tests/test_openapi.py` | Caminho novo, posições, schemas com campos exatos, `409` e `404` com `ErrorResponse`, nomes proibidos ausentes |
| `tests/test_access_policy.py` | `("/api/lots/{lot_id}/bids", "POST", "http"): BIDDER` |
| `tests/test_domain_purity.py` | Detector de relógio também em `app/bids.py` (sem allowlist de imports: não é módulo de domínio) |

Arquivos de integração novos: `test_bids_migration.py`, `test_bid_service.py`,
`test_bid_routes.py`, `test_bid_concurrency.py`, `test_bid_integrity_gate.py`.

## 5. Injeção de falha (D11)

| Ponto | Mecanismo | Prova da posição |
| --- | --- | --- |
| A1 depois de F1 | Envoltório de `app.bids.generate_bidder_alias` que delega e levanta quando o recorder já viu `UPDATE wallets` (o gate também chama a função) | `UPDATE wallets` no recorder antes da exceção |
| A2 depois de F2, antes da nova âncora | `app.bids.compute_anchor_hmac` levanta (o gate usa `verify_anchor_hmac`, de outro módulo) | `INSERT INTO bids` no recorder |
| A3 depois de F3, antes de enviar o `COMMIT` | `Session.commit` levanta sem chamar o original (precedente: `test_lot_creation`) | `UPDATE lots` no recorder; nenhum `COMMIT` enviado |
| A4 falha real do banco | `committed` do líder < lance atual (SQL) → CHECK em F1 | `IntegrityError`; resposta sem nome de constraint |

Sem hook no código de produção. `raise_server_exceptions=False` nas versões HTTP.

## 6. Mutações dirigidas (aplicar uma, rodar o teste, ver falhar, restaurar)

| # | Mutação | Morre em |
| --- | --- | --- |
| M-1 | `datetime.now(UTC)` no lugar de `database_now` | T-CLOCK (a), detector de relógio |
| M-2 | Hora lida antes de `lock_lot` | T-CLOCK (a)(b) |
| M-3 | Carteiras sem `sorted()` / por papel | T-ORDER, T-DEADLOCK |
| M-4 | `sequence` por `MAX(sequence) + 1` | T-ORDER (statement com agregação) — sob gate íntegro o valor coincide |
| M-5 | Gate depois das travas de carteira | T-ORDER (409 sem `SELECT wallets`) |
| M-6 | Gate só com HMAC (sem cadeia / sem vínculo de resumo) | G1 / G3 |
| M-7 | Sem comparar líder/lance atual com o último lance | G10, G11 |
| M-8 | Sem recalcular o alias do líder | G12 |
| M-9 | Liberar `amount_cents` novo em vez do lance atual | T-OUTBID |
| M-10 | `committed = amount` em vez de `+=` | T-BAL, T-OUTBID |
| M-11 | `lock_wallet` sem `populate_existing` | T-DEPOSIT (c) |
| M-12 | Âncora com o segredo de pseudônimo | T-CHAIN |
| M-13 | Persistir `now + 2 min` | T-SNIPE (1) |
| M-14 | Nova âncora sobre `bid_count`/`final_hash` antigos | T-CHAIN, T-FIRST (gate do lance seguinte) |
| M-15 | Mutar o `Lot` antes de F2 | T-FIRST (CHECK reprova o `UPDATE` parcial) |
| M-16 | Aceitar `anchor_hmac NULL` com zero lances | G9 |
| M-17 | `try/except ValueError` em todo o serviço | G18 |
| M-18 | Trava do lote sem `FOR UPDATE` | T-CONC-2 (a) |
| M-19 | Tamanho do segredo em caracteres | T-SECRETS (`"é" * 16`) |
| M-20 | Alias ou segredo no log | T-GATE (log), T-SECRETS |
| M-21 | `bidder_id` no DTO | `test_openapi`, T-OUTBID (chaves exatas) |
| M-22 | Seed sem `anchor_hmac IS NOT NULL` | T-INIT |
| M-23 | Seed lendo `PSEUDONYM_SECRET` | T-SECRETS (subprocesso) |
| M-24 | Gate movido para **depois** de `evaluate_pre_wallet`, ainda antes das carteiras | G9b, G10b, G11b; ordem semântica em T-REUSE |
| M-25 | Sem o tratamento do `ValueError` estrutural da reconstrução/verificação do estado persistido (vira 500) | G14, G17 (exigem 409) |
| M-26 | `placed_at` gerado pelo banco: (a) `server_default` e a coluna omitida no `INSERT`; (b) `now()` no `INSERT`; (c) `clock_timestamp()` no `INSERT` | T-CLOCK (a), nas três variantes: o `placed_at` gravado difere do instante devolvido por `database_now` (`now()` é o início da transação, anterior à trava; um segundo `clock_timestamp()` é posterior, separado por vários statements). T-CLOCK (b) também mata a variante `now()` (`B.placed_at < T1`) |

Não há mutação de "releitura": reler do banco o mesmo `TIMESTAMPTZ` de microssegundos
devolve o mesmo instante e é equivalente ao `now` em memória.

Registro no build: mutação, teste que falhou, restauração conferida. Sem framework.

## 7. Repetibilidade

- Orquestração A segura / B espera / A confirma, como `test_wallet_concurrency`.
- Barreiras com timeout; `JOIN_SECONDS` como lá; threads sempre liberadas em `finally`.
- Corrida livre em 5 rodadas; o veredito é o estado final.
- `clean_users` (com `bids`) antes de cada teste que grava; `drop_checks` limpa e
  recria as CHECKs mesmo em falha.
