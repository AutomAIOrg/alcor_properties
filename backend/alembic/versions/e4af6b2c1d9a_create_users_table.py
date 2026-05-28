"""create_users_table

Revision ID: e4af6b2c1d9a
Revises: ac8b440e58b0
Create Date: 2026-05-27 12:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4af6b2c1d9a"
down_revision: str | Sequence[str] | None = "ac8b440e58b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users table and seed the initial admin user."""
    op.create_table(
        "users",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Username", sa.String(length=255), nullable=False),
        sa.Column("Password", sa.String(length=255), nullable=False),
        sa.Column("Name", sa.String(length=255), nullable=False),
        sa.Column("Lastname", sa.String(length=255), nullable=False),
        sa.Column("Email", sa.String(length=255), nullable=False),
        sa.Column("Role", sa.String(length=100), nullable=False),
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
