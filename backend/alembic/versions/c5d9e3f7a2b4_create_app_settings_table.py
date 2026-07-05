"""create_app_settings_table

Revision ID: c5d9e3f7a2b4
Revises: b4c8d2e6f9a1
Create Date: 2026-06-21 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d9e3f7a2b4"
down_revision: str | Sequence[str] | None = "b4c8d2e6f9a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create app_settings key-value table."""
    op.create_table(
        "app_settings",
        sa.Column("Setting Key", sa.String(length=100), nullable=False),
        sa.Column("Setting Value", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("Setting Key"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    """Drop app_settings table."""
    op.drop_table("app_settings")
