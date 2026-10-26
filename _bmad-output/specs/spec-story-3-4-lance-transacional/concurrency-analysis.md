# Travas, isolamento e deadlock — Story 3.4

Referências do PostgreSQL 18: §13.2.1 (Read Committed e reavaliação da linha
atualizada em `SELECT ... FOR UPDATE`), §13.3.2 (conflitos entre travas de linha),
§13.3.4 (deadlocks), §9.9.5 (`clock_timestamp()`).

## 1. Travas adquiridas por um lance aceito

| # | Statement | Trava de linha | Observação |
| --- | --- | --- | --- |
| 2 | `SELECT lots ... WHERE id = $1 FOR UPDATE` | `FOR UPDATE` em `lots(L)` | Só a tabela `lots`, sem `JOIN` |
| 4 | `SELECT ... FROM bids WHERE lot_id = $1` | nenhuma | Leitura MVCC |
| 7 | `SELECT wallets ... FOR UPDATE` (1 ou 2, crescente) | `FOR UPDATE` em `wallets(u)` | `lock_wallet` |
| F1 | `UPDATE wallets` | já coberta | Coluna não-chave |
| F2 | `INSERT bids` | FK: `FOR KEY SHARE` em `lots(L)` (já temos `FOR UPDATE`, compatível com a própria transação) e em `users(bidder)` | Índices PK e UNIQUE: sem espera, chave nova sob a trava do lote |
| F3 | `UPDATE lots` | já coberta | FK de `current_leader_id`: `FOR KEY SHARE` em `users(bidder)` |

`FOR KEY SHARE` só conflita com `FOR UPDATE` (e com `DELETE`/mudança de chave).
Ninguém pega `FOR UPDATE` em `users` nem apaga usuário: as travas em `users` nunca
esperam.

Efeito defensivo de `FOR UPDATE` (e não `FOR NO KEY UPDATE`) no lote: qualquer
`INSERT` em `bids` de outro caminho precisa de `FOR KEY SHARE` em `lots(L)` e espera
o nosso commit; não intercala dentro da nossa transação. Se um caminho fora do
protocolo inserir depois, o próximo gate falha (fail-closed).

## 2. Isolamento: por que `READ COMMITTED` basta

Premissa (provada em `current-state.md` §4): toda escrita legítima em `bids` e no
estado de lance do lote acontece com a trava `FOR UPDATE` do lote.

1. **Lote.** Se T₂ espera a trava que T₁ segura, ao acordar o PostgreSQL relê a
   versão **confirmada** da linha (reavaliação do `WHERE`) e a trava. Com
   `populate_existing`, o ORM substitui os atributos. T₂ vê líder, lance atual,
   `ends_at`, `bid_count`, `final_hash` e `anchor_hmac` de T₁.
2. **Cadeia.** A leitura de `bids` (passo 4) é outro statement: em `READ COMMITTED`
   ganha snapshot novo, tirado depois de T₂ obter a trava. T₁ já está confirmada
   (a trava só é liberada depois do commit), então T₂ vê o `INSERT` de T₁. Lote e
   cadeia vêm do mesmo estado confirmado. Por isso a trava não pode ter `JOIN` com
   `bids`: dentro do statement que esperou, as outras tabelas viriam do snapshot
   anterior à espera.
3. **Nenhuma escrita concorrente na cadeia do lote** entre o passo 4 e o commit:
   exigiria a trava do lote (premissa) ou `FOR KEY SHARE` que espera (§1).
4. **Carteiras.** `FOR UPDATE` + `populate_existing`: o saldo usado é o último
   confirmado; depósito e lances de outros lotes serializam na linha.
5. **Hora.** `clock_timestamp()` num statement depois da trava: nunca anterior à
   espera.
6. **Âncora.** Escrita só em F3, sob a trava, sobre valores autenticados no passo 4.

**A justificativa é o protocolo:** trava do lote primeiro, e cada statement posterior
com snapshot novo, tirado depois da trava. Isso dá a T₂ o estado confirmado por T₁
sem retry. `REPEATABLE READ`/`SERIALIZABLE` não trariam ganho e mudariam o
comportamento: nesses níveis, um `SELECT ... FOR UPDATE` sobre uma linha atualizada
por transação confirmada depois do snapshot falha com SQLSTATE `40001` (could not
serialize access due to concurrent update), o que exigiria retry, fora do escopo
(D13). Mantido `READ COMMITTED` (padrão do engine). Teste afirma o nível
(precedente: `test_the_seed_runs_in_read_committed`).

## 3. Deadlock: análise

**Ordem global:** cada transação de lance adquire, nesta ordem, (a) exatamente uma
trava de lote, (b) zero, uma ou duas travas de carteira em `user_id` crescente.
Antes de (a) ela não segura trava de linha (a leitura do `User` não trava; travas de
tabela `ACCESS SHARE` só conflitam com DDL/`TRUNCATE`). Depósito segura uma carteira
e nada mais. Travas em `users` nunca esperam (§1).

**Prova.** Num ciclo de espera, cada participante segura algo que outro espera.
- Uma transação esperando um **lote** não segura nada → não fecha ciclo.
- Logo, todas as esperas do ciclo são por **carteiras**. Quem espera a carteira `w`
  só segura carteiras `< w` (ordem crescente) e um lote que ninguém do ciclo espera.
  Seguindo o ciclo, os `user_id` esperados cresceriam estritamente e voltariam ao
  início: contradição. **Não há ciclo** entre lance × lance, lance × depósito, em
  lotes iguais ou diferentes.

**Mesmo lote:** serializa na trava do lote; as carteiras nem chegam a disputar.

**Lotes diferentes, carteiras cruzadas (T-DEADLOCK):** U1 lidera L1, U2 lidera L2.
T_A = U2 em L1 trava L1 → {U1, U2}; T_B = U1 em L2 trava L2 → {U1, U2}. Ambas pedem
`min(U1, U2)` primeiro: uma espera a outra terminar; nenhuma segura a maior
esperando a menor. Ordenar por papel (novo líder primeiro) cria o ciclo: é o
controle negativo.

**Residual.** Fora do protocolo, o PostgreSQL ainda pode abortar uma transação com
`deadlock_detected` (40P01) depois de `deadlock_timeout`: futuras stories que travem
carteira antes de lote, ou em outra ordem; DDL/`TRUNCATE` concorrente (só testes e
migrations). Comportamento aceito: a transação abortada é desfeita, a requisição
recebe 500 genérico, a outra segue. **Retry fora do escopo** (D13). Não afirmo
"impossível" para além dos caminhos listados; afirmo que nenhum caminho existente
nem previsto, seguindo AD-8, forma ciclo.

**Sem timeout.** Uma transação travada esperando mantém conexão do pool e thread.
Aceito na escala do desafio (A2/A3, `decisions.md`).

## 4. Passada adversarial 1 — concorrência (autorrevisão)

| Ataque | Resultado na spec | Ajuste feito |
| --- | --- | --- |
| Deadlock | Prova §3; T-DEADLOCK + controle negativo | — |
| Lost update no lote | Só `place_bid` escreve, sob trava; valores relidos | — |
| Lost update na carteira | Escrita absoluta via ORM é segura só porque a linha está travada e relida; `populate_existing` é obrigatório | Mutação M-11 e T-DEPOSIT pré-carregando a carteira na `Session` |
| `UPDATE` parcial do lote reprovado pela CHECK | Autoflush antes de F3 geraria `UPDATE` com `current_bid` sem `bid_count` | D1: nenhuma mutação do `Lot` antes de F3; mutação M-15 |
| Sequência duplicada | `bid_count` autenticado sob trava; PK | — |
| Bifurcação | Gate + PK + UNIQUE | — |
| Saldo obsoleto | Regra de saldo só depois da trava da carteira | — |
| Leitura não repetível perigosa | Lote e cadeia lidos depois da trava, em statements próprios; ninguém escreve na cadeia sem a trava | Proibido `JOIN` no `FOR UPDATE` (D2) |
| Extensão perdida | O segundo lê o `ends_at` confirmado; T-SNIPE (3) observa `anti_sniping_applied = False` em B | IC-1 |
| Identity map servindo `Lot` antigo | `populate_existing` no lote; histórico por colunas (D4); `rollback()` antes do serviço (D5) | — |
| Fila longa na trava | Conexões e threads presas; sem timeout | A2/A3 |

## 5. Passada adversarial 2 — segurança e integridade (autorrevisão)

| Ataque | Por que não passa | Teste |
| --- | --- | --- |
| Lavagem por reautenticação (S-01) | Gate antes de qualquer escrita; nova âncora só sobre estado autenticado | T-GATE (cadeia recalculada + `final_hash` novo + HMAC antiga) |
| Âncora `NULL` confiável | `MISSING_ANCHOR` primeiro; migration/seed/boot não assinam | T-GATE, T-INIT |
| Adulterar líder/lance atual | Vínculo com o último lance autenticado | T-GATE |
| Recusa de negócio decidida sobre estado não autenticado (SR-01) | Gate antes de `evaluate_pre_wallet`: 409 tem prioridade sobre `lot_ended`, `below_minimum`, `already_winning` | G9b, G10b, G11b, T-REUSE, M-24 |
| Trocar `bidder_id` do último lance junto com o líder | Alias recalculado do líder ≠ alias autenticado | G12 |
| Trocar só `bidder_id` do último lance | `≠ current_leader_id` | G22 |
| Inserção/remoção no meio (com ou sem renumerar) | Lacuna na cadeia ou HMAC antiga sobre resumo novo | G19, G20, G21 |
| Âncora assinada com outro `AUDIT_HMAC_SECRET` | HMAC não confere com o segredo operacional; nada é reassinado | G23 |
| Replay de alias de outro lote | Alias é HMAC de `lot_id:user_id`; o do último lance está na cadeia | T-GATE (alias do mesmo usuário em outro lote) |
| Replay de âncora/cadeia entre lotes | `AnchorState` com o `lot_id` da rota; `CanonicalBid.lot_id` no hash | T-GATE (vazia e com lances) |
| Truncamento / inserção | `count ≠ len` ou `final_hash ≠ último` | T-GATE |
| Commit parcial | Uma transação; falhas injetadas em F1, F2, F3 e antes de enviar o `COMMIT`; falha de conexão depois de enviar é indeterminada para o cliente (F-6) | T-ATOM |
| Confusão de segredos | Testes com segredos distintos verificam a âncora com o de auditoria e falham com o de pseudônimo; alias com o de pseudônimo | T-CHAIN, M-12 |
| Segredo em log/resposta/`repr` | `SecretStr`, `repr=False`, `hide_input_in_errors`, log só com categoria | T-SECRETS |
| Exposição HTTP | DTO com campos exatos; nomes proibidos ausentes do OpenAPI e da resposta; 409 idêntico para toda categoria | T-ROLE, T-GATE, `test_openapi` |
| Oráculo pela ordem 409/422 | Lote legado/adulterado responde 409 a qualquer licitante: revela só "não autenticado", não dado secreto | aceito |
| Dado ilegível pelo driver (`placed_at = infinity`) | Erro na leitura → 500, sem efeito (fail-closed), não 409 | limitação |
| Rollback consistente de cadeia + âncora antigas | Passa (sem âncora externa) | limitação AD-13 |
| Termos do lote (`ends_at`) e saldos adulterados | Não autenticados pela âncora v1 | limitação AD-13 |
| Seed com `IS NOT NULL` manipulável | Escolhe demo, não prova validade; o lance continua passando pelo gate | F-4, SR-09 |
