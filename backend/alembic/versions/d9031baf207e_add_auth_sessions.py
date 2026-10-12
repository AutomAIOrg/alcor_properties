"""Persist independently revocable refresh-token families.
Revision ID: d9031baf207e
Revises: c8e1a4b7d2f0
"""

import sqlalchemy as sa

from alembic import op

revision = "d9031baf207e"
down_revision = "c8e1a4b7d2f0"
branch_labels = ("auth_sessions",)
depends_on = None


def upgrade():
    op.drop_column("users", "RefreshTokenJti")
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.ID", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("refresh_jti", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    # Tokens issued before session tracking cannot be attributed to a family.
    op.execute(sa.text("UPDATE users SET TokenVersion = TokenVersion + 1"))


def downgrade():
    op.add_column("users", sa.Column("RefreshTokenJti", sa.String(36), nullable=True))
    op.drop_table("auth_sessions")
