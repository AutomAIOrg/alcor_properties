"""add_check_times_to_bookings

Horas de entrada y salida pactadas por reserva. NULL significa "hora estándar del
complejo" (entrada 16:00, salida 11:00), que es el caso de todas las reservas
existentes: solo se rellenan cuando el administrador acuerda una hora distinta.

Revision ID: a3c5e7d1f9b2
Revises: f1b3c7d9e2a5
Create Date: 2026-07-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c5e7d1f9b2"
down_revision: str | Sequence[str] | None = "f1b3c7d9e2a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Check-In Time / Check-Out Time columns to bookings."""
    op.add_column("bookings", sa.Column("Check-In Time", sa.Time(), nullable=True))
    op.add_column("bookings", sa.Column("Check-Out Time", sa.Time(), nullable=True))


def downgrade() -> None:
    """Drop Check-In Time / Check-Out Time columns from bookings."""
    op.drop_column("bookings", "Check-Out Time")
    op.drop_column("bookings", "Check-In Time")
