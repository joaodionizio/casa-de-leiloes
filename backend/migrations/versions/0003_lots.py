"""lots

Tabela de lotes da Story 2.4: snapshot da obra (AD-23), termos em centavos (AD-3) e
horários em `TIMESTAMPTZ`. Sem `status` (P3: a fase é derivada do tempo), sem lance,
sem cancelamento e sem liquidação: essas colunas nascem, aditivas, nas stories que as
usam. A faixa do dinheiro, `1..9007199254740991`, é a mesma da API e do serviço.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auctioneer_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("artist_display", sa.Text(), nullable=True),
        sa.Column("date_display", sa.Text(), nullable=True),
        sa.Column("medium_display", sa.Text(), nullable=True),
        sa.Column("dimensions", sa.Text(), nullable=True),
        sa.Column("department_title", sa.Text(), nullable=True),
        sa.Column("artwork_type_title", sa.Text(), nullable=True),
        sa.Column("image_id", sa.String(length=36), nullable=False),
        sa.Column("credit_line", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("starting_bid_cents", sa.BigInteger(), nullable=False),
        sa.Column("min_increment_cents", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lots")),
        sa.ForeignKeyConstraint(
            ["auctioneer_id"],
            ["users.id"],
            name=op.f("fk_lots_auctioneer_id_users"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "starting_bid_cents > 0 AND starting_bid_cents <= 9007199254740991",
            name=op.f("ck_lots_starting_bid_range"),
        ),
        sa.CheckConstraint(
            "min_increment_cents > 0 AND min_increment_cents <= 9007199254740991",
            name=op.f("ck_lots_min_increment_range"),
        ),
        sa.CheckConstraint(
            "ends_at > starts_at", name=op.f("ck_lots_ends_after_starts")
        ),
        sa.CheckConstraint(
            "external_id > 0", name=op.f("ck_lots_external_id_positive")
        ),
        sa.CheckConstraint(
            "image_id ~ "
            "'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name=op.f("ck_lots_image_id_format"),
        ),
    )
    op.create_index(op.f("ix_lots_auctioneer_id"), "lots", ["auctioneer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_lots_auctioneer_id"), table_name="lots")
    op.drop_table("lots")
