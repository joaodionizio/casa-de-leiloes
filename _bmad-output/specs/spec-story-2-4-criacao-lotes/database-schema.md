# Esquema — tabela `lots` (migration `0003`)

Padrões herdados: `Base` com `NAMING_CONVENTION` (`app/db.py`), UUID sem default no
banco (como `users`), `TIMESTAMPTZ` (`sa.DateTime(timezone=True)`), CHECKs nomeados por
`op.f(...)`. O modelo `Lot` espelha a migration; os testes recebem o esquema só da
migration.

## 1. Colunas

| Coluna | Tipo | Nulo | Default | Origem |
| --- | --- | --- | --- | --- |
| `id` | `UUID` | não | — | `uuid.uuid4()` na aplicação |
| `auctioneer_id` | `UUID` | não | — | `user.id` da sessão, ou o leiloeiro semeado (seed) |
| `external_id` | `INTEGER` | não | — | snapshot (AIC) |
| `title` | `TEXT` | sim | — | snapshot |
| `artist_display` | `TEXT` | sim | — | snapshot |
| `date_display` | `TEXT` | sim | — | snapshot |
| `medium_display` | `TEXT` | sim | — | snapshot |
| `dimensions` | `TEXT` | sim | — | snapshot |
| `department_title` | `TEXT` | sim | — | snapshot |
| `artwork_type_title` | `TEXT` | sim | — | snapshot |
| `image_id` | `VARCHAR(36)` | não | — | snapshot (referência IIIF) |
| `credit_line` | `TEXT` | sim | — | snapshot (crédito/origem) |
| `source_url` | `TEXT` | não | — | snapshot (URL da fonte) |
| `starting_bid_cents` | `BIGINT` | não | — | corpo / constante do seed |
| `min_increment_cents` | `BIGINT` | não | — | corpo / constante do seed |
| `starts_at` | `TIMESTAMPTZ` | não | — | corpo, ou `now` quando ausente |
| `ends_at` | `TIMESTAMPTZ` | não | — | corpo / `now + 72 h` no seed; mutável na 3.4 (AD-5), só para frente |
| `is_demo` | `BOOLEAN` | não | `false` (`server_default`) | só o seed grava `true` |
| `created_at` | `TIMESTAMPTZ` | não | — | o mesmo `now` da operação |

Ordem das colunas na migration: a da tabela (o teste confere `list(columns)`).

## 2. Snapshot

Os 11 campos de P2, na mesma nulabilidade do `ArtworkDetail` da 2.3: `external_id`,
`image_id` e `source_url` obrigatórios; os 8 textos podem ser `NULL` (a 2.3 já
normaliza vazio/ausente para `None`). Colunas próprias, não JSON: o contrato fica
tipado no banco e a 2.5 lê por coluna. `image_url` não é coluna (P2). Nenhum byte de
imagem.

## 3. Constraints

| Nome (convenção) | Definição | Por quê |
| --- | --- | --- |
| `pk_lots` | `PRIMARY KEY (id)` | — |
| `fk_lots_auctioneer_id_users` | `FOREIGN KEY (auctioneer_id) REFERENCES users (id) ON DELETE RESTRICT` | o dono vem da sessão; apagar usuário com lote é recusado |
| `ck_lots_starting_bid_range` | `starting_bid_cents > 0 AND starting_bid_cents <= 9007199254740991` | P5, A4: mesma faixa da API e do serviço |
| `ck_lots_min_increment_range` | `min_increment_cents > 0 AND min_increment_cents <= 9007199254740991` | P5, A4 |
| `ck_lots_ends_after_starts` | `ends_at > starts_at` | P4; continua válida quando a 3.4 empurra `ends_at` |
| `ck_lots_external_id_positive` | `external_id > 0` | espelha a validação da API (2.3 `gt=0`) |
| `ck_lots_image_id_format` | `image_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'` | espelha `IMAGE_ID_PATTERN`; o `image_id` vira caminho do proxy |

Sem `UNIQUE` em `external_id` (P7). Sem CHECK de `is_demo`.

**Faixa do dinheiro (A4).** `9007199254740991` é `Number.MAX_SAFE_INTEGER`, o limite
técnico que a API e o front representam sem perda (D3); não é teto comercial. A
migration escreve o literal inteiro na CHECK (migrations não importam código da
aplicação; nunca `float` nem notação científica); o modelo usa `MAX_CENTS` de
`app/lots.py`; um teste lê a definição da CHECK no banco e confere o literal contra
`MAX_CENTS`.

Nomes: com `NAMING_CONVENTION` (`"ck": "ck_%(table_name)s_%(constraint_name)s"`), o
`CheckConstraint(..., name="starting_bid_range")` no modelo e
`op.f("ck_lots_starting_bid_range")` na migration, como a `0002`.

## 4. Índice

`ix_lots_auctioneer_id` em `auctioneer_id` (o PostgreSQL não indexa FK; serve ao
`GET /api/lots/mine` e ao `RESTRICT`). Nenhum outro: poucos demos, consulta do seed
barata.

## 5. Evolução sem desmontar

| Story | Acréscimo previsto (não criar agora) |
| --- | --- |
| 3.4 | `current_bid_cents`, `leader_id` (FK `users`), `bid_count`, `final_hash`, `anchor_hmac`; `UPDATE ends_at` para frente |
| 3.6 | `cancelled_at TIMESTAMPTZ NULL`; "demo aberto" ganha `AND cancelled_at IS NULL` |
| 4.3 | `settled_at`, vencedor; CHECK de exclusão entre cancelado e liquidado |

Todas são `ADD COLUMN` nulas ou com default. O lote continua uma linha travável por
`SELECT ... FOR UPDATE` (AD-8, AD-9).

## 6. Migration `0003_lots.py`

- `revision = "0003"`, `down_revision = "0002"`, docstring com o escopo (sem estado,
  sem lance, sem cancelamento).
- `upgrade()`: `op.create_table("lots", ...)` com colunas, PK, FK, CHECKs; depois
  `op.create_index(op.f("ix_lots_auctioneer_id"), "lots", ["auctioneer_id"])`.
- `downgrade()`: `op.drop_index(...)` e `op.drop_table("lots")`.

## 7. Modelo `Lot` (`app/lots.py`)

`Mapped[...]` como `User`; `starting_bid_cents: Mapped[int] = mapped_column(BigInteger)`;
timestamps `DateTime(timezone=True)`; `is_demo` com `server_default=false()`;
`ForeignKey("users.id", ondelete="RESTRICT")`, `index=True`; `__table_args__` com os
cinco `CheckConstraint`. O modelo nunca é usado para criar tabelas.
