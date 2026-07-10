"""create_billing_schema

Dominio de facturación: catálogo de tipos de limpieza, facturas y metadatos
de documentos PDF almacenados en NAS.

Revision ID: d4e6f8a0b2c4
Revises: e4af6b2c1d9a
Create Date: 2026-07-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e6f8a0b2c4"
down_revision: str | Sequence[str] | None = "e4af6b2c1d9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create cleaning_types, bills and bill_documents tables."""
    op.create_table(
        "cleaning_types",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Name", sa.String(length=100), nullable=False),
        sa.Column("Hourly Rate", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("Active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("Name", name="uq_cleaning_types_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.create_table(
        "bills",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Record ID", sa.Integer(), nullable=True),
        sa.Column("Created At", sa.Date(), nullable=True),
        sa.Column("Clean Hours", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("Cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("Hourly Rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("Cleaning Type ID", sa.Integer(), nullable=True),
        sa.Column("Cleaning Type Name", sa.String(length=100), nullable=True),
        sa.Column("Apartment ID", sa.String(length=255), nullable=False),
        sa.Column("State", sa.String(length=100), nullable=False),
        sa.Column("Paid At", sa.Date(), nullable=True),
        sa.Column("Paid Confirmed By Admin", sa.DateTime(), nullable=True),
        sa.Column("Paid Confirmed By Admin Name", sa.String(length=200), nullable=True),
        sa.Column("Paid Confirmed By Cleaner", sa.DateTime(), nullable=True),
        sa.Column("Paid Confirmed By Cleaner Name", sa.String(length=200), nullable=True),
        sa.Column("Cancellation Note", sa.String(500), nullable=True),
        sa.Column("Bill Created At", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["Record ID"], ["bookings.ID"]),
        sa.ForeignKeyConstraint(["Apartment ID"], ["Apartamentos.Booking ID"]),
        sa.ForeignKeyConstraint(
            ["Cleaning Type ID"],
            ["cleaning_types.ID"],
            name="fk_bills_cleaning_type",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("Record ID", name="uq_bills_record_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

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
        sa.Column("Status", sa.String(length=50), nullable=False),
        sa.Column("Operation", sa.String(length=50), nullable=False),
        sa.Column("Attempts", sa.Integer(), nullable=False),
        sa.Column("Last Error", sa.String(length=1000), nullable=True),
        sa.Column("Next Retry At", sa.DateTime(), nullable=True),
        sa.Column("Completed At", sa.DateTime(), nullable=True),
        sa.Column("Previous NAS Path", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["Bill ID"], ["bills.ID"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["Uploaded By"], ["users.ID"]),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("Bill ID", name="uq_bill_documents_bill_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    """Drop billing schema tables."""
    op.drop_table("bill_documents")
    op.drop_table("bills")
    op.drop_table("cleaning_types")
