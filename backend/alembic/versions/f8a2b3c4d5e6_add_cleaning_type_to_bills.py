"""add_cleaning_type_to_bills

Revision ID: f8a2b3c4d5e6
Revises: e7f1a2b3c4d5
Create Date: 2026-07-03 10:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e7f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add cleaning type reference and snapshot name to bills."""
    op.add_column("bills", sa.Column("Cleaning Type ID", sa.Integer(), nullable=True))
    op.add_column("bills", sa.Column("Cleaning Type Name", sa.String(length=100), nullable=True))
    op.create_foreign_key(
        "fk_bills_cleaning_type",
        "bills",
        "cleaning_types",
        ["Cleaning Type ID"],
        ["ID"],
    )


def downgrade() -> None:
    """Drop cleaning type reference and snapshot name from bills."""
    op.drop_constraint("fk_bills_cleaning_type", "bills", type_="foreignkey")
    op.drop_column("bills", "Cleaning Type Name")
    op.drop_column("bills", "Cleaning Type ID")
