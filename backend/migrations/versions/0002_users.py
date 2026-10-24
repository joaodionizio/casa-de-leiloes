"""users

Tabela de usuários da Story 2.2: contas semeadas com papel `AUCTIONEER` ou
`BIDDER`. Sem carteira (Story 3.1) e sem dados pessoais além do e-mail.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.CheckConstraint(
            "email = lower(email)", name=op.f("ck_users_email_lowercase")
        ),
        sa.CheckConstraint(
            "role IN ('AUCTIONEER', 'BIDDER')", name=op.f("ck_users_role")
        ),
    )


def downgrade() -> None:
    op.drop_table("users")
