"""empty message

Revision ID: 0ed9e05ec864
Revises: b343e50c4c1a
Create Date: 2025-03-15 23:27:28.254177

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0ed9e05ec864"
down_revision: Union[str, None] = "b343e50c4c1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
