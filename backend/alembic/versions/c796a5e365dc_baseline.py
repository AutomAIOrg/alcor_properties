"""baseline

Revision ID: c796a5e365dc
Revises:
Create Date: 2026-05-17 18:12:37.452783

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c796a5e365dc"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
