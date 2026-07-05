"""add_password_reset_jti_to_users

Revision ID: f8b2c4d6e0a1
Revises: e7a1b2c3d4f5
Create Date: 2026-07-05 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8b2c4d6e0a1"
down_revision: str | Sequence[str] | None = "e7a1b2c3d4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'PasswordResetJti' column to users for single-use reset tokens."""
    op.add_column("users", sa.Column("PasswordResetJti", sa.String(36), nullable=True))


def downgrade() -> None:
    """Drop 'PasswordResetJti' column from users."""
    op.drop_column("users", "PasswordResetJti")
