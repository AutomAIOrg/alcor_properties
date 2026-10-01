"""add_cleaning_required_to_bookings

Indica por reserva si hay que limpiar el piso antes de su entrada. Si está desactivado, la
limpieza de esa reserva no aparece en la lista de limpiezas pendientes. Todas las reservas
existentes quedan marcadas como "requiere limpieza", que era el comportamiento hasta ahora.

Revision ID: c2f4a6b8d0e1
Revises: b7d2e9f4a1c3
Create Date: 2026-09-28 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2f4a6b8d0e1"
down_revision: str | Sequence[str] | None = "b7d2e9f4a1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Cleaning Required column to bookings."""
    op.add_column(
        "bookings",
        sa.Column(
            "Cleaning Required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )


def downgrade() -> None:
    """Drop Cleaning Required column from bookings."""
    op.drop_column("bookings", "Cleaning Required")
