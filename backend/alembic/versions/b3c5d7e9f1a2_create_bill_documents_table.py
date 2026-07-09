"""create_bill_documents_table

Revision ID: b3c5d7e9f1a2
Revises: a1c3e5d7b9f2
Create Date: 2026-07-06 19:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3c5d7e9f1a2"
down_revision: str | Sequence[str] | None = "a1c3e5d7b9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create bill_documents table for NAS-stored invoice PDF metadata."""
    op.create_table(
        "bill_documents",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Bill ID", sa.Integer(), nullable=False),
        sa.Column("Filename", sa.String(length=255), nullable=False),
        sa.Column("NAS Path", sa.String(length=1024), nullable=False),
        sa.Column("Content Type", sa.String(length=100), nullable=False),
        sa.Column("Size Bytes", sa.Integer(), nullable=False),
        sa.Column("Uploaded By", sa.Integer(), nullable=False),
        sa.Column("Uploaded At", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["Bill ID"], ["bills.ID"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["Uploaded By"], ["users.ID"]),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("Bill ID", name="uq_bill_documents_bill_id"),
    )


def downgrade() -> None:
    """Drop bill_documents table."""
    op.drop_table("bill_documents")
