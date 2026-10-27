# Esquema — tabela `wallets` (migration `0004`)

Padrões herdados: `Base` com `NAMING_CONVENTION` (`app/db.py`), CHECKs nomeadas por
`op.f(...)`, literal monetário escrito na migration (migrations não importam código da
aplicação). O modelo `Wallet` espelha a migration; os testes recebem o esquema só das
migrations.

## 1. Colunas (nesta ordem)

| Coluna | Tipo | Nulo | Default (`server_default`) |
| --- | --- | --- | --- |
| `user_id` | `UUID` | não | — |
| `total_balance_cents` | `BIGINT` | não | `0` |
| `committed_balance_cents` | `BIGINT` | não | `0` |

Não existem `id`, `available_balance_cents`, `created_at` nem `updated_at` (P1, P5).

## 2. Constraints

| Nome | Definição | Por quê |
| --- | --- | --- |
| `pk_wallets` | `PRIMARY KEY (user_id)` | 1:1 com `users`; trava por `user_id` (AD-8) |
| `fk_wallets_user_id_users` | `FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT` | apagar usuário com carteira é recusado (P1) |
| `ck_wallets_total_range` | `total_balance_cents >= 0 AND total_balance_cents <= 9007199254740991` | AD-3, P3 |
| `ck_wallets_committed_range` | `committed_balance_cents >= 0 AND committed_balance_cents <= 9007199254740991` | AD-3, P3 |
| `ck_wallets_committed_within_total` | `committed_balance_cents <= total_balance_cents` | AD-3; disponível nunca negativo |

Nenhum índice extra: a PK serve à busca e à trava. As CHECKs são imediatas (não
`DEFERRABLE`), como exige o AD-3 para a liquidação futura.

No modelo: `CheckConstraint(..., name="total_range")`, `name="committed_range"`,
`name="committed_within_total"`, com `MAX_CENTS` de `app.money` interpolado (como
`Lot`).

## 3. Migration `0004_wallets.py`

- Docstring: carteira da Story 3.1; estado agregado sem ledger nem timestamps; backfill
  dos usuários existentes; faixa `0..9007199254740991`, igual à aplicação.
- `revision = "0004"`, `down_revision = "0003"`.
- `upgrade()`:
  1. `op.create_table("wallets", ...)` com as colunas da §1 (`sa.Uuid()`,
     `sa.BigInteger()`, `server_default=sa.text("0")`) e as constraints da §2;
  2. `op.execute("INSERT INTO wallets (user_id) SELECT id FROM users")` — saldos pelos
     defaults; banco limpo insere zero linhas.
- `downgrade()`: `op.drop_table("wallets")` (perde os saldos; aceitável e registrado no
  README).

## 4. Compatibilidade

| Banco antes | Depois de `upgrade head` | Depois do seed |
| --- | --- | --- |
| `0003` com N usuários | N carteiras `0`/`0` | nada muda em `wallets` (usuários semeados já existiam) ou carteiras dos usuários novos |
| vazio | `wallets` vazia | 3 carteiras `0`/`0` |
| `head`, usuário sem carteira inserido por SQL | — | ganha carteira `0`/`0` |

O estado final para os mesmos usuários é sempre "uma carteira `0`/`0` por usuário" (P2,
P6). Em produção (Render), o banco está em revisão desconhecida (o README indica `0001`);
qualquer dos casos acima termina igual.

## 5. Modelo `Wallet` (`app/wallet.py`)

```python
class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (CheckConstraint(...total_range), CheckConstraint(...committed_range),
                      CheckConstraint(...committed_within_total))
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    total_balance_cents: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    committed_balance_cents: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
```

Sem `relationship()`. O modelo nunca cria tabelas.
