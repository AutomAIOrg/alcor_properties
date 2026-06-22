"""add_notes_cleaning_to_bookings

Revision ID: b7c8d9e0f1a2
Revises: e4af6b2c1d9a
Create Date: 2026-06-20 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "e4af6b2c1d9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("Notes_Cleaning", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "Notes_Cleaning")
