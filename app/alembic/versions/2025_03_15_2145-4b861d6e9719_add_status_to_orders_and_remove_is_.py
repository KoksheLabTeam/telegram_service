"""add status to orders and remove is_completed

Revision ID: 4b861d6e9719
Revises: 02487aa00d87
Create Date: 2025-03-15 21:45:30.776605
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4b861d6e9719"
down_revision: Union[str, None] = "02487aa00d87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Определение ENUM-типа с значениями в верхнем регистре
orderstatus = sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", "CANCELED", name="orderstatus")

def upgrade() -> None:
    """Upgrade schema."""
    # Создание типа orderstatus перед добавлением колонки
    orderstatus.create(op.get_bind(), checkfirst=True)

    # Добавление колонки status с типом orderstatus и значением по умолчанию
    op.add_column(
        "orders",
        sa.Column(
            "status",
            orderstatus,
            nullable=False,
            server_default="PENDING"  # Значение по умолчанию в верхнем регистре
        ),
    )

    # Удаление колонки is_completed
    op.drop_column("orders", "is_completed")

def downgrade() -> None:
    """Downgrade schema."""
    # Добавление обратно колонки is_completed
    op.add_column(
        "orders",
        sa.Column(
            "is_completed", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
    )

    # Удаление колонки status
    op.drop_column("orders", "status")

    # Удаление типа orderstatus
    orderstatus.drop(op.get_bind(), checkfirst=True)