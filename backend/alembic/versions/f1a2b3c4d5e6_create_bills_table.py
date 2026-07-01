"""create_bills_table

Revision ID: f1a2b3c4d5e6
Revises: b7c8d9e0f1a2
Create Date: 2026-06-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create bills table."""
    op.create_table(
        "bills",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Record ID", sa.Integer(), sa.ForeignKey("bookings.ID"), nullable=True),
        sa.Column("Created At", sa.Date(), nullable=True),
        sa.Column("Clean Hours", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("Cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "Apartment ID",
            sa.String(length=255),
            sa.ForeignKey("Apartamentos.Booking ID"),
            nullable=False,
        ),
        sa.Column("State", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("ID"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    """Drop bills table."""
    op.drop_table("bills")
