"""bids

Lances e estado de lance do lote (Story 3.4, AD-3, AD-7, AD-13, AD-20, AD-21).

`bids` guarda os campos que reconstroem o `CanonicalBid` v1 mais `current_hash`; o
`bidder_id` é privado e não entra nos bytes canônicos. `lots` ganha lance atual, líder,
contagem, hash final e a âncora HMAC. A migration é aditiva, não lê segredo e não
assina nada: lotes existentes ficam com `bid_count = 0`, hash genesis e `anchor_hmac`
nulo, um estado coerente e **não autenticado**, que recusa lance (409) até a story
que o autenticar. Os literais monetários são os mesmos de `MAX_CENTS`.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENESIS_HASH = "0" * 64

LOT_CHECKS = (
    (
        "ck_lots_current_bid_range",
        "current_bid_cents > 0 AND current_bid_cents <= 9007199254740991",
    ),
    (
        "ck_lots_current_bid_at_least_starting",
        "current_bid_cents >= starting_bid_cents",
    ),
    (
        "ck_lots_current_bid_with_leader",
        "(current_bid_cents IS NULL) = (current_leader_id IS NULL)",
    ),
    (
        "ck_lots_bid_count_matches_current_bid",
        "(bid_count = 0) = (current_bid_cents IS NULL)",
    ),
    ("ck_lots_bid_count_non_negative", "bid_count >= 0"),
    ("ck_lots_final_hash_format", "final_hash ~ '^[0-9a-f]{64}$'"),
    (
        "ck_lots_empty_lot_is_genesis",
        f"bid_count > 0 OR final_hash = '{GENESIS_HASH}'",
    ),
    ("ck_lots_anchor_hmac_format", "anchor_hmac ~ '^[0-9a-f]{64}$'"),
)


def upgrade() -> None:
    # `ADD COLUMN` com default constante preenche os lotes existentes: 0, genesis e
    # NULL nas demais. `anchor_hmac` não tem default de propósito.
    op.add_column(
        "lots", sa.Column("current_bid_cents", sa.BigInteger(), nullable=True)
    )
    op.add_column("lots", sa.Column("current_leader_id", sa.Uuid(), nullable=True))
    op.add_column(
        "lots",
        sa.Column(
            "bid_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False
        ),
    )
    op.add_column(
        "lots",
        sa.Column(
            "final_hash",
            sa.Text(),
            server_default=sa.text(f"'{GENESIS_HASH}'"),
            nullable=False,
        ),
    )
    op.add_column("lots", sa.Column("anchor_hmac", sa.Text(), nullable=True))
    op.create_foreign_key(
        op.f("fk_lots_current_leader_id_users"),
        "lots",
        "users",
        ["current_leader_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    for name, expression in LOT_CHECKS:
        op.create_check_constraint(op.f(name), "lots", expression)

    op.create_table(
        "bids",
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("bidder_id", sa.Uuid(), nullable=False),
        sa.Column("bidder_alias", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.Text(), nullable=False),
        sa.Column("current_hash", sa.Text(), nullable=False),
        sa.Column("canonical_version", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("lot_id", "sequence", name=op.f("pk_bids")),
        sa.UniqueConstraint(
            "lot_id", "previous_hash", name=op.f("uq_bids_lot_id_previous_hash")
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["lots.id"],
            name=op.f("fk_bids_lot_id_lots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["bidder_id"],
            ["users.id"],
            name=op.f("fk_bids_bidder_id_users"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("sequence >= 1", name=op.f("ck_bids_sequence_positive")),
        sa.CheckConstraint(
            "amount_cents > 0 AND amount_cents <= 9007199254740991",
            name=op.f("ck_bids_amount_range"),
        ),
        sa.CheckConstraint(
            "bidder_alias ~ '^Licitante-[0-9A-F]{16}$'",
            name=op.f("ck_bids_bidder_alias_format"),
        ),
        sa.CheckConstraint(
            "previous_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_bids_previous_hash_format"),
        ),
        sa.CheckConstraint(
            "current_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_bids_current_hash_format"),
        ),
        sa.CheckConstraint(
            "canonical_version = 1", name=op.f("ck_bids_canonical_version")
        ),
    )


def downgrade() -> None:
    # Remove só o que a 0005 criou. Perde lances e estado de lance: aceitável em
    # desenvolvimento e registrado no README, como na 0004.
    op.drop_table("bids")
    for name, _ in reversed(LOT_CHECKS):
        op.drop_constraint(op.f(name), "lots", type_="check")
    op.drop_constraint(
        op.f("fk_lots_current_leader_id_users"), "lots", type_="foreignkey"
    )
    for column in (
        "anchor_hmac",
        "final_hash",
        "bid_count",
        "current_leader_id",
        "current_bid_cents",
    ):
        op.drop_column("lots", column)
