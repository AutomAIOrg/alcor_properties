"""add_unique_record_id_to_bills

Revision ID: a3b7c9d1e5f2
Revises: f1a2b3c4d5e6
Create Date: 2026-06-21 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b7c9d1e5f2"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unique constraint on Record ID to prevent duplicate bills per booking."""
    op.create_unique_constraint("uq_bills_record_id", "bills", ["Record ID"])


def downgrade() -> None:
    """Remove unique constraint on Record ID."""
    op.drop_constraint("uq_bills_record_id", "bills", type_="unique")
