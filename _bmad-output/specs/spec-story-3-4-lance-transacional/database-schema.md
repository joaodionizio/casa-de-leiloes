# Schema e migration `0005` — Story 3.4

Desenho para o build. **Nenhuma migration foi criada.** Padrões seguidos: `0003`/
`0004` (`op.f(...)` com nomes finais, literais monetários sem importar a aplicação,
`downgrade` que remove só o que criou), `NAMING_CONVENTION` de `app/db.py`,
PostgreSQL 18.

## 1. `lots`: colunas novas

| Coluna | Tipo | Nulo | Default no banco | FK |
| --- | --- | --- | --- | --- |
| `current_bid_cents` | `BIGINT` | sim | — | — |
| `current_leader_id` | `UUID` | sim | — | `users.id` `ON DELETE RESTRICT` |
| `bid_count` | `BIGINT` | não | `0` | — |
| `final_hash` | `TEXT` | não | `'000…0'` (64 zeros, literal) | — |
| `anchor_hmac` | `TEXT` | sim | **nenhum** | — |

`anchor_hmac` sem default é deliberado: qualquer `INSERT` que não passe por
`create_lot` nasce **não autenticado** (409 no lance).

CHECKs novas (nome final no banco):

| Nome | Expressão |
| --- | --- |
| `ck_lots_current_bid_range` | `current_bid_cents > 0 AND current_bid_cents <= 9007199254740991` |
| `ck_lots_current_bid_at_least_starting` | `current_bid_cents >= starting_bid_cents` |
| `ck_lots_current_bid_with_leader` | `(current_bid_cents IS NULL) = (current_leader_id IS NULL)` |
| `ck_lots_bid_count_matches_current_bid` | `(bid_count = 0) = (current_bid_cents IS NULL)` |
| `ck_lots_bid_count_non_negative` | `bid_count >= 0` |
| `ck_lots_final_hash_format` | `final_hash ~ '^[0-9a-f]{64}$'` |
| `ck_lots_empty_lot_is_genesis` | `bid_count > 0 OR final_hash = '000…0'` (64 zeros) |
| `ck_lots_anchor_hmac_format` | `anchor_hmac ~ '^[0-9a-f]{64}$'` |

FK: `fk_lots_current_leader_id_users`. CHECK com `NULL` passa (resultado
desconhecido), então as de faixa e formato não precisam de `IS NULL OR`. Sem índice
novo em `lots` (nenhuma consulta filtra por líder nesta story).

**Lotes existentes:** `ADD COLUMN` com default constante preenche `bid_count = 0`,
`final_hash` genesis e `NULL` nas outras três. Todas as CHECKs passam; o lote fica
representável, **não autenticado** e bloqueado para lance. A migration não lê
segredo, não faz `UPDATE` de backfill e não assina nada.

## 2. `bids`

| Coluna | Tipo | Nulo | Regra |
| --- | --- | --- | --- |
| `lot_id` | `UUID` | não | FK `lots.id` `RESTRICT` |
| `sequence` | `BIGINT` | não | `>= 1` |
| `bidder_id` | `UUID` | não | FK `users.id` `RESTRICT`; privado |
| `bidder_alias` | `TEXT` | não | `^Licitante-[0-9A-F]{16}$`; sem UNIQUE |
| `amount_cents` | `BIGINT` | não | `1..9007199254740991` |
| `placed_at` | `TIMESTAMPTZ` | não | sem default (o `now` do passo 3) |
| `previous_hash` | `TEXT` | não | `^[0-9a-f]{64}$` |
| `current_hash` | `TEXT` | não | `^[0-9a-f]{64}$` |
| `canonical_version` | `SMALLINT` | não | `= 1` |

| Restrição | Nome |
| --- | --- |
| `PRIMARY KEY (lot_id, sequence)` | `pk_bids` |
| `UNIQUE (lot_id, previous_hash)` | `uq_bids_lot_id_previous_hash` (explícito, D12) |
| FK `lot_id` | `fk_bids_lot_id_lots` |
| FK `bidder_id` | `fk_bids_bidder_id_users` |
| CHECKs | `ck_bids_sequence_positive`, `ck_bids_amount_range`, `ck_bids_bidder_alias_format`, `ck_bids_previous_hash_format`, `ck_bids_current_hash_format`, `ck_bids_canonical_version` |

`TIMESTAMPTZ` guarda microssegundos: `placed_at` relido reconstrói o `timestamp`
canônico byte a byte. Sem UUID substituto, sem `created_at`, sem índice extra.

**Por que `bidder_id` não entra no `CanonicalBid` v1 nem é autenticado
diretamente:** os bytes v1 são fixos pela 3.3 (golden vectors) e públicos (a 5.1
mostra o histórico para recálculo); colocar o UUID real no canônico exporia a
identidade (AD-20). O vínculo vem pelo alias: `HMAC(PSEUDONYM_SECRET,
"{lot_id}:{user_id}")` é um compromisso com chave sobre o usuário, e o alias do
último lance está dentro da cadeia autenticada. Por isso, só o `bidder_id` **do
último lance**, igual ao líder, fica vinculado (P2). Os `bidder_id` anteriores não são
autenticados e não decidem dinheiro nesta story.

## 3. Análise da `UNIQUE (lot_id, previous_hash)` (D12)

- **Primeiro lance:** `previous_hash` = genesis; a UNIQUE admite um só por lote.
  Correto: só existe um primeiro lance.
- **Uma cadeia por lote:** numa cadeia legítima cada `previous_hash` é o
  `current_hash` do anterior; repetição exigiria colisão SHA-256 (ou um
  `current_hash` igual ao genesis). Não restringe nenhum histórico legítimo.
- **Valor sob PK + trava:** a trava e a sequência autenticada já impedem bifurcação;
  a PK impede sequência repetida. A UNIQUE pega o que a PK não pega: um bug que use o
  predecessor certo com sequência errada (ex.: `MAX(sequence) + 1` sobre linha
  fantasma, ou contagem divergente) criaria dois filhos do mesmo hash com sequências
  diferentes. Custo: um índice B-tree por lance.
- **Não é defesa contra quem escreve no banco** (pode remover a constraint); isso é
  papel do gate.
- Conclusão: **mantida**, não redundante, não prejudicial. Nenhuma incompatibilidade.

Índices: a PK `(lot_id, sequence)` atende `WHERE lot_id = ? ORDER BY sequence`;
a UNIQUE cria o seu. FKs sem índice (usuários e lotes nunca são apagados; `RESTRICT`).

## 4. `downgrade`

Ordem inversa: `drop_table("bids")`; remover as 8 CHECKs e a FK de `lots`; remover as
5 colunas. Perde lances e estado de lance (só desenvolvimento; README já registra o
precedente da `0004`).

## 5. ORM

- `Lot` (`app/lots.py`) espelha as colunas e CHECKs (`name=` curto; a convenção
  prefixa `ck_lots_`), `server_default` de `bid_count` e `final_hash` iguais à
  migration. `current_leader_id` com `ForeignKey("users.id", ondelete="RESTRICT")`.
- `Bid` (`app/bids.py`): PK composta (`lot_id`, `sequence`), `UniqueConstraint(...,
  name="uq_bids_lot_id_previous_hash")`, CHECKs espelhadas. **Sem `relationship()`**
  (nada de carregamento preguiçoso; a ordem dos statements é explícita, D1).
- O schema dos testes vem sempre da migration; o ORM não é usado para criar tabela.

## 6. Tipos e limites

| Valor | Python | Banco | Extremo |
| --- | --- | --- | --- |
| `sequence`, `bid_count` | `int` exato | `BIGINT` | `> 2^63 − 1` → erro do driver → 500, rollback (inalcançável) |
| `amount_cents`, `current_bid_cents` | `int` | `BIGINT` | `MAX_CENTS` (CHECK) |
| `canonical_version` | `int` | `SMALLINT` | só `1` (CHECK e `CanonicalBid`) |
| `placed_at` | `datetime` com fuso | `TIMESTAMPTZ` µs | `infinity` ou fora do `datetime` do Python: o driver falha na leitura → 500 sem efeito (fail-closed, não 409) |
