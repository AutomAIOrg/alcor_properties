"""Persist login admission counters.
Revision ID: a91c03e47b20
Revises: b7d2e9f4a1c3
"""

import sqlalchemy as sa

from alembic import op

revision = "a91c03e47b20"
down_revision = "b7d2e9f4a1c3"
branch_labels = ("auth_rate_limit",)
depends_on = None


def upgrade():
    op.create_table(
        "auth_login_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("auth_login_limits")
