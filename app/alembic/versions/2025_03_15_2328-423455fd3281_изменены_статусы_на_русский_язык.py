"""Изменены статусы на русский язык

Revision ID: 423455fd3281
Revises: 0ed9e05ec864
Create Date: 2025-03-15 23:28:31.488773

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "423455fd3281"
down_revision: Union[str, None] = "0ed9e05ec864"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
