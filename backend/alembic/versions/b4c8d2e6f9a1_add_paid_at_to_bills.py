"""add_paid_at_to_bills

Revision ID: b4c8d2e6f9a1
Revises: a3b7c9d1e5f2
Create Date: 2026-06-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c8d2e6f9a1"
down_revision: str | Sequence[str] | None = "a3b7c9d1e5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'Paid At' column to bills."""
    op.add_column("bills", sa.Column("Paid At", sa.Date(), nullable=True))


def downgrade() -> None:
    """Drop 'Paid At' column from bills."""
    op.drop_column("bills", "Paid At")
