"""Update order status enum

Revision ID: 3057d1616d62
Revises: b2677e3291ae
Create Date: 2025-03-18 15:02:00

"""
from alembic import op
import sqlalchemy as sa

revision = "3057d1616d62"
down_revision = "b2677e3291ae"
branch_labels = None
depends_on = None

def upgrade():
    # Создаем временный новый enum
    new_enum = sa.Enum("В_ожидании", "В_прогрессе", "Выполнен", "Отменен", name="orderstatus_new")
    new_enum.create(op.get_bind(), checkfirst=True)

    # Добавляем временную колонку с новым enum
    op.add_column("orders", sa.Column("status_new", new_enum, nullable=True))

    # Переносим данные со старого статуса на новый с явным приведением типов
    op.execute("""
        UPDATE orders
        SET status_new = CASE
            WHEN status = 'PENDING' THEN 'В_ожидании'::orderstatus_new
            WHEN status = 'IN_PROGRESS' THEN 'В_прогрессе'::orderstatus_new
            WHEN status = 'COMPLETED' THEN 'Выполнен'::orderstatus_new
            WHEN status = 'CANCELED' THEN 'Отменен'::orderstatus_new
            ELSE 'В_ожидании'::orderstatus_new
        END
    """)

    # Удаляем старую колонку
    op.drop_column("orders", "status")

    # Переименовываем новую колонку и делаем её NOT NULL
    op.alter_column("orders", "status_new", new_name="status", nullable=False, server_default="В_ожидании")

    # Переименовываем enum
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_old")
    op.execute("ALTER TYPE orderstatus_new RENAME TO orderstatus")
    op.execute("DROP TYPE orderstatus_old")

def downgrade():
    # Создаем старый enum
    old_enum = sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", "CANCELED", name="orderstatus_old")
    old_enum.create(op.get_bind(), checkfirst=True)

    # Добавляем временную колонку со старым enum
    op.add_column("orders", sa.Column("status_old", old_enum, nullable=True))

    # Переносим данные обратно с явным приведением типов
    op.execute("""
        UPDATE orders
        SET status_old = CASE
            WHEN status = 'В_ожидании' THEN 'PENDING'::orderstatus_old
            WHEN status = 'В_прогрессе' THEN 'IN_PROGRESS'::orderstatus_old
            WHEN status = 'Выполнен' THEN 'COMPLETED'::orderstatus_old
            WHEN status = 'Отменен' THEN 'CANCELED'::orderstatus_old
            ELSE 'PENDING'::orderstatus_old
        END
    """)

    # Удаляем новую колонку
    op.drop_column("orders", "status")

    # Переименовываем старую колонку и делаем её nullable
    op.alter_column("orders", "status_old", new_name="status", nullable=True, server_default="PENDING")

    # Переименовываем enum обратно
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_new")
    op.execute("ALTER TYPE orderstatus_old RENAME TO orderstatus")
    op.execute("DROP TYPE orderstatus_new")