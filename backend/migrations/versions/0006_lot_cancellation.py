"""lot cancellation

Marcador de cancelamento do lote (Story 3.6, AD-6, AD-7, AD-11). Uma coluna aditiva:
`lots.cancelled_at TIMESTAMPTZ NULL`. Sem `server_default` (o instante é o
`clock_timestamp()` que o serviço lê depois da trava do lote), sem backfill (todo lote
existente fica não cancelado), sem CHECK ligando a coluna a `bid_count` (a 6.6 cancela
lote com lances) e sem índice (nenhuma consulta o justifica nesta escala). O `downgrade`
remove só a coluna; o marcador de cancelamento se perde com ela.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lots", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("lots", "cancelled_at")
