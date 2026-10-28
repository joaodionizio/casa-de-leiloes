"""Atomic settlement and privacy limited receipt records.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MAX_CENTS = 9007199254740991
GENESIS_HASH = "0" * 64


def upgrade() -> None:
    op.create_table(
        "lot_settlements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("winner_user_id", sa.Uuid(), nullable=True),
        sa.Column("winner_alias", sa.Text(), nullable=True),
        sa.Column("winning_bid_sequence", sa.BigInteger(), nullable=True),
        sa.Column("final_amount_cents", sa.BigInteger(), nullable=True),
        sa.Column("bid_count", sa.BigInteger(), nullable=False),
        sa.Column("final_hash", sa.Text(), nullable=False),
        sa.Column("anchor_hmac", sa.Text(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_id"),
        sa.UniqueConstraint("id", "lot_id", name="uq_lot_settlements_id_lot_id"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["lot_id", "winning_bid_sequence"],
            ["bids.lot_id", "bids.sequence"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("outcome IN ('sold', 'unsold')", name="outcome_valid"),
        sa.CheckConstraint("bid_count >= 0", name="bid_count_nonnegative"),
        sa.CheckConstraint("final_hash ~ '^[0-9a-f]{64}$'", name="final_hash_format"),
        sa.CheckConstraint("anchor_hmac ~ '^[0-9a-f]{64}$'", name="anchor_hmac_format"),
        sa.CheckConstraint(
            "(outcome = 'sold' AND winner_user_id IS NOT NULL "
            "AND winner_alias IS NOT NULL "
            "AND winning_bid_sequence IS NOT NULL AND final_amount_cents IS NOT NULL "
            "AND bid_count > 0 AND winning_bid_sequence = bid_count "
            f"AND final_amount_cents > 0 AND final_amount_cents <= {MAX_CENTS} "
            "AND winner_alias ~ '^Licitante-[0-9A-F]{16}$') OR "
            "(outcome = 'unsold' AND winner_user_id IS NULL AND winner_alias IS NULL "
            "AND winning_bid_sequence IS NULL AND final_amount_cents IS NULL "
            f"AND bid_count = 0 AND final_hash = '{GENESIS_HASH}')",
            name="outcome_fields",
        ),
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("settlement_id", sa.Uuid(), nullable=False),
        sa.Column("winning_bid_sequence", sa.BigInteger(), nullable=False),
        sa.Column("winner_alias", sa.Text(), nullable=False),
        sa.Column("final_amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bid_count", sa.BigInteger(), nullable=False),
        sa.Column("final_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_id"),
        sa.UniqueConstraint("settlement_id"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["settlement_id", "lot_id"],
            ["lot_settlements.id", "lot_settlements.lot_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id", "winning_bid_sequence"],
            ["bids.lot_id", "bids.sequence"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "bid_count > 0 AND winning_bid_sequence = bid_count",
            name="winning_bid_count",
        ),
        sa.CheckConstraint(
            f"final_amount_cents > 0 AND final_amount_cents <= {MAX_CENTS}",
            name="amount_range",
        ),
        sa.CheckConstraint(
            "winner_alias ~ '^Licitante-[0-9A-F]{16}$'", name="winner_alias_format"
        ),
        sa.CheckConstraint("final_hash ~ '^[0-9a-f]{64}$'", name="final_hash_format"),
    )


def downgrade() -> None:
    op.drop_table("receipts")
    op.drop_table("lot_settlements")
