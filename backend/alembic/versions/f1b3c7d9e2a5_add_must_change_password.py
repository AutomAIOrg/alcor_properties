"""add_must_change_password

Marca los usuarios que aún tienen la contraseña inicial del sistema (alta o
restablecimiento por el administrador) y deben fijar una propia antes de usar
la aplicación.

Revision ID: f1b3c7d9e2a5
Revises: d4e6f8a0b2c4
Create Date: 2026-07-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1b3c7d9e2a5"
down_revision: str | Sequence[str] | None = "d4e6f8a0b2c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add MustChangePassword column to users."""
    # Los usuarios existentes ya tienen contraseña propia: no se les fuerza el cambio.
    op.add_column(
        "users",
        sa.Column(
            "MustChangePassword",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Drop MustChangePassword column from users."""
    op.drop_column("users", "MustChangePassword")
