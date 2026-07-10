"""baseline

Esquema heredado: apartamentos, reservas y columnas de notas/color añadidas
posteriormente en desarrollo, consolidadas aquí para el despliegue inicial.

Revision ID: c796a5e365dc
Revises:
Create Date: 2026-05-17 18:12:37.452783

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c796a5e365dc"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the legacy core schema (apartments and bookings)."""
    op.create_table(
        "Apartamentos",
        sa.Column("Booking ID", mysql.CHAR(10), nullable=False),
        sa.Column("Comunidad", sa.String(25), nullable=True),
        sa.Column("Booking Name", sa.String(80), nullable=True),
        sa.Column("Direccion", sa.String(75), nullable=True),
        sa.Column("Nº Habitaciones", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("Nº Banos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("Nº Parking", sa.String(10), server_default=sa.text("'N/A'"), nullable=False),
        sa.Column("Ocupacion Total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("Owner Name", sa.String(50), nullable=True),
        sa.Column("Email", sa.String(35), nullable=True),
        sa.Column("Nº Telefono", sa.String(15), nullable=True),
        sa.Column("Color", sa.String(length=7), nullable=True),
        sa.PrimaryKeyConstraint("Booking ID"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.create_table(
        "bookings",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "Booking ID",
            mysql.CHAR(10, charset="utf8mb4", collation="utf8mb4_unicode_ci"),
            nullable=False,
        ),
        sa.Column("Check-In", sa.Date(), nullable=False),
        sa.Column("Check-Out", sa.Date(), nullable=False),
        sa.Column("Nombre,Apellidos", sa.String(100), nullable=False),
        sa.Column("Nº Noches", sa.Integer(), nullable=True),
        sa.Column("Nº Personas", sa.Integer(), nullable=True),
        sa.Column("Nº Adultos", sa.Integer(), nullable=True),
        sa.Column("Nº Niños", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("Nº Booking", sa.String(45), nullable=True),
        sa.Column("Status", sa.String(10), nullable=True),
        sa.Column(
            "Electric Allowance", mysql.SMALLINT(), server_default=sa.text("0"), nullable=True
        ),
        sa.Column("Email", sa.String(100), nullable=True),
        sa.Column("Movil", sa.String(20), nullable=True),
        sa.Column(
            "Comm y Cargos", sa.Numeric(10, 2), server_default=sa.text("0.00"), nullable=True
        ),
        sa.Column("Precio", sa.Numeric(10, 2), server_default=sa.text("0.00"), nullable=True),
        sa.Column("Notes", sa.Text(), nullable=True),
        sa.Column("Notes_Cleaning", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("ID"),
        sa.UniqueConstraint("ID", name="ID"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("fk_bookings_Apartamentos_Booking_ID", "bookings", ["Booking ID"])
    op.create_foreign_key(
        "fk_bookings_Apartamentos_Booking_ID",
        "bookings",
        "Apartamentos",
        ["Booking ID"],
        ["Booking ID"],
        onupdate="CASCADE",
    )


def downgrade() -> None:
    """Drop the baseline schema."""
    op.drop_constraint("fk_bookings_Apartamentos_Booking_ID", "bookings", type_="foreignkey")
    op.drop_index("fk_bookings_Apartamentos_Booking_ID", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("Apartamentos")
