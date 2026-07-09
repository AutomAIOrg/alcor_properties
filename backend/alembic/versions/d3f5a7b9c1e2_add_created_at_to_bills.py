"""add_created_at_to_bills

Revision ID: d3f5a7b9c1e2
Revises: a1c3e5d7b9f2
Create Date: 2026-07-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f5a7b9c1e2"
down_revision: str | Sequence[str] | None = "a1c3e5d7b9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'Bill Created At' column to bills (fecha de generación, congelada)."""
    op.add_column("bills", sa.Column("Bill Created At", sa.Date(), nullable=True))


def downgrade() -> None:
    """Drop 'Bill Created At' column from bills."""
    op.drop_column("bills", "Bill Created At")
