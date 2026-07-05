"""add_token_version_to_users

Revision ID: a1c3e5d7b9f2
Revises: f8b2c4d6e0a1
Create Date: 2026-07-05 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3e5d7b9f2"
down_revision: str | Sequence[str] | None = "f8b2c4d6e0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'TokenVersion' column to users to allow session invalidation."""
    op.add_column(
        "users",
        sa.Column("TokenVersion", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop 'TokenVersion' column from users."""
    op.drop_column("users", "TokenVersion")
