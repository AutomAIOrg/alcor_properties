"""alter_bills_cleaning_type_fk_set_null

La FK bills → cleaning_types se creó sin acción ON DELETE, por lo que borrar un tipo
de limpieza usado por alguna factura fallaba con un error de integridad (1451). La
factura ya guarda el nombre del tipo como snapshot histórico, así que basta con perder
la referencia viva: recreamos la FK con ON DELETE SET NULL.

Revision ID: b2d4f6a8c0e1
Revises: a9b3c4d5e6f7
Create Date: 2026-07-03 11:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d4f6a8c0e1"
down_revision: str | Sequence[str] | None = "a9b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recreate the bills → cleaning_types FK with ON DELETE SET NULL."""
    op.drop_constraint("fk_bills_cleaning_type", "bills", type_="foreignkey")
    op.create_foreign_key(
        "fk_bills_cleaning_type",
        "bills",
        "cleaning_types",
        ["Cleaning Type ID"],
        ["ID"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Restore the FK without ON DELETE behaviour."""
    op.drop_constraint("fk_bills_cleaning_type", "bills", type_="foreignkey")
    op.create_foreign_key(
        "fk_bills_cleaning_type",
        "bills",
        "cleaning_types",
        ["Cleaning Type ID"],
        ["ID"],
    )
