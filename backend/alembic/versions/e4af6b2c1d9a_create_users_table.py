"""create_users_table

Tabla de usuarios con soporte de sesión (TokenVersion) y restablecimiento
de contraseña de un solo uso (PasswordResetJti).

Revision ID: e4af6b2c1d9a
Revises: c796a5e365dc
Create Date: 2026-05-27 12:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4af6b2c1d9a"
down_revision: str | Sequence[str] | None = "c796a5e365dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users table."""
    op.create_table(
        "users",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Username", sa.String(length=255), nullable=False),
        sa.Column("Password", sa.String(length=255), nullable=False),
        sa.Column("Name", sa.String(length=255), nullable=False),
        sa.Column("Lastname", sa.String(length=255), nullable=True),
        sa.Column("Email", sa.String(length=255), nullable=True),
        sa.Column("Role", sa.String(length=100), nullable=False),
        sa.Column("PasswordResetJti", sa.String(36), nullable=True),
        sa.Column("TokenVersion", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("Email", name="uq_users_email"),
        sa.UniqueConstraint("Username", name="uq_users_username"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    """Drop users table."""
    op.drop_table("users")
