"""add_refresh_token_jti

Almacena el jti del refresh token activo por usuario para rotación y
detección de reutilización.

Revision ID: c8e1a4b7d2f0
Revises: b7d2e9f4a1c3
Create Date: 2026-09-21 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8e1a4b7d2f0"
down_revision: str | Sequence[str] | None = "b7d2e9f4a1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add RefreshTokenJti column to users."""
    op.add_column(
        "users",
        sa.Column("RefreshTokenJti", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    """Drop RefreshTokenJti column from users."""
    op.drop_column("users", "RefreshTokenJti")
