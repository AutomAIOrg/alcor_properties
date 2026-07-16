"""add_electric_allowance_to_apartments

Mueve la configuración del cupo eléctrico del .env a la base de datos: cada apartamento
decide si lo aplica y con qué importe por noche, editable desde la gestión de apartamentos.

Antes, la variable de entorno ELECTRIC listaba los apartamentos con cupo y el importe
(4 €/noche) estaba fijo en el código. Para no cambiar el comportamiento existente, la
migración activa el cupo en los apartamentos que ELECTRIC lista en este entorno y deja el
importe por defecto en 4,00 € en todos los apartamentos.

Revision ID: b7d2e9f4a1c3
Revises: a3c5e7d1f9b2
Create Date: 2026-07-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from config import settings

# revision identifiers, used by Alembic.
revision: str = "b7d2e9f4a1c3"
down_revision: str | Sequence[str] | None = "a3c5e7d1f9b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_RATE = "4.00"


def upgrade() -> None:
    """Add Electric Allowance columns to apartments and seed them from ELECTRIC."""
    op.add_column(
        "Apartamentos",
        sa.Column(
            "Electric Allowance",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "Apartamentos",
        sa.Column(
            "Electric Allowance Rate",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text(DEFAULT_RATE),
        ),
    )

    electric_ids = [item.strip() for item in settings.ELECTRIC.split(",") if item.strip()]
    if electric_ids:
        apartments = sa.table(
            "Apartamentos",
            sa.column("Booking ID", sa.String),
            sa.column("Electric Allowance", sa.Boolean),
        )
        op.execute(
            apartments.update()
            .where(sa.column("Booking ID").in_(electric_ids))
            .values({"Electric Allowance": True})
        )


def downgrade() -> None:
    """Drop Electric Allowance columns from apartments."""
    op.drop_column("Apartamentos", "Electric Allowance Rate")
    op.drop_column("Apartamentos", "Electric Allowance")
