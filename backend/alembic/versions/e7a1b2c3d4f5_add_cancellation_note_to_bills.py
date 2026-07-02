"""add_cancellation_note_to_bills

Revision ID: e7a1b2c3d4f5
Revises: d6e0f4a8b3c5
Create Date: 2026-07-02 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a1b2c3d4f5"
down_revision: str | Sequence[str] | None = "d6e0f4a8b3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'Cancellation Note' column to bills."""
    op.add_column("bills", sa.Column("Cancellation Note", sa.String(500), nullable=True))


def downgrade() -> None:
    """Drop 'Cancellation Note' column from bills."""
    op.drop_column("bills", "Cancellation Note")
