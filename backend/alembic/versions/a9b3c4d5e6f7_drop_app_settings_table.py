"""drop_app_settings_table

El precio por hora de limpieza dejó de gestionarse como un ajuste global clave-valor;
ahora lo define cada tipo de limpieza (tabla cleaning_types), por lo que la tabla
app_settings queda sin uso y se elimina.

Revision ID: a9b3c4d5e6f7
Revises: f8a2b3c4d5e6
Create Date: 2026-07-03 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "f8a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the now-unused app_settings table."""
    op.drop_table("app_settings")


def downgrade() -> None:
    """Recreate the app_settings key-value table."""
    op.create_table(
        "app_settings",
        sa.Column("Setting Key", sa.String(length=100), nullable=False),
        sa.Column("Setting Value", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("Setting Key"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
