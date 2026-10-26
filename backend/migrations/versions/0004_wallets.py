"""wallets

Carteira da Story 3.1: estado agregado atual do licitante, sem ledger e sem
timestamps. `user_id` é a chave primária e a FK para `users` (1:1). Os saldos são
`BIGINT` em centavos; o disponível nunca é persistido. A faixa, `0..9007199254740991`,
é a mesma da API e do serviço. O backfill dá uma carteira zerada a cada usuário que já
existe; num banco limpo a tabela nasce vazia e o seed completa.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "total_balance_cents",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "committed_balance_cents",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_wallets")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_wallets_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "total_balance_cents >= 0 AND total_balance_cents <= 9007199254740991",
            name=op.f("ck_wallets_total_range"),
        ),
        sa.CheckConstraint(
            "committed_balance_cents >= 0 "
            "AND committed_balance_cents <= 9007199254740991",
            name=op.f("ck_wallets_committed_range"),
        ),
        sa.CheckConstraint(
            "committed_balance_cents <= total_balance_cents",
            name=op.f("ck_wallets_committed_within_total"),
        ),
    )
    # Saldos pelos defaults (zero). Banco limpo: nenhuma linha.
    op.execute("INSERT INTO wallets (user_id) SELECT id FROM users")


def downgrade() -> None:
    # Perde os saldos: aceitável no desafio e registrado no README.
    op.drop_table("wallets")
