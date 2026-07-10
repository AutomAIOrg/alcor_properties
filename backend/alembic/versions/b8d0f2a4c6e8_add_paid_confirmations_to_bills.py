"""add_paid_confirmations_to_bills

Revision ID: b8d0f2a4c6e8
Revises: d3f5a7b9c1e2
Create Date: 2026-07-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d0f2a4c6e8"
down_revision: str | Sequence[str] | None = "d3f5a7b9c1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Doble confirmación de pago: instante (fecha + hora) y nombre congelado por rol."""
    op.add_column("bills", sa.Column("Paid Confirmed By Admin", sa.DateTime(), nullable=True))
    op.add_column(
        "bills", sa.Column("Paid Confirmed By Admin Name", sa.String(length=200), nullable=True)
    )
    op.add_column("bills", sa.Column("Paid Confirmed By Cleaner", sa.DateTime(), nullable=True))
    op.add_column(
        "bills", sa.Column("Paid Confirmed By Cleaner Name", sa.String(length=200), nullable=True)
    )


def downgrade() -> None:
    """Drop payment confirmation columns from bills."""
    op.drop_column("bills", "Paid Confirmed By Cleaner Name")
    op.drop_column("bills", "Paid Confirmed By Cleaner")
    op.drop_column("bills", "Paid Confirmed By Admin Name")
    op.drop_column("bills", "Paid Confirmed By Admin")
