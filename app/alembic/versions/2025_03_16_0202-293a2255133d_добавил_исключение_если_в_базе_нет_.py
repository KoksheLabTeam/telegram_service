"""Добавил исключение, если в базе нет городов

Revision ID: 293a2255133d
Revises: 7f9dd6a7c3de
Create Date: 2025-03-16 02:02:26.614308

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "293a2255133d"
down_revision: Union[str, None] = "7f9dd6a7c3de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
