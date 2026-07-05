"""create_cleaning_types_table

Revision ID: e7f1a2b3c4d5
Revises: e7a1b2c3d4f5
Create Date: 2026-07-03 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "e7a1b2c3d4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create cleaning_types catalog table."""
    op.create_table(
        "cleaning_types",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Name", sa.String(length=100), nullable=False),
        sa.Column("Hourly Rate", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("Active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("Name", name="uq_cleaning_types_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    """Drop cleaning_types table."""
    op.drop_table("cleaning_types")
