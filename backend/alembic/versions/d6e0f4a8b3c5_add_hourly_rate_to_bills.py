"""add_hourly_rate_to_bills

Revision ID: d6e0f4a8b3c5
Revises: c5d9e3f7a2b4
Create Date: 2026-06-21 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e0f4a8b3c5"
down_revision: str | Sequence[str] | None = "c5d9e3f7a2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'Hourly Rate' column to bills."""
    op.add_column("bills", sa.Column("Hourly Rate", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    """Drop 'Hourly Rate' column from bills."""
    op.drop_column("bills", "Hourly Rate")
