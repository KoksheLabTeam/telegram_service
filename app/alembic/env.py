from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import DB_URL
from app.core.models.base import Base
from app.core.models.user import User
from app.core.models.association import user_categories
from app.core.models.category import Category
from app.core.models.city import City
from app.core.models.offer import Offer
from app.core.models.order import Order
from app.core.models.review import Review

# Настраиваем логирование
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

# Указываем метаданные для автогенерации
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн-режиме."""
    url = DB_URL  # Используем DB_URL из config.py
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Запуск миграций в онлайн-режиме."""
    connectable = engine_from_config(
        {"sqlalchemy.url": DB_URL},  # Используем DB_URL напрямую
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()  # Добавлен вызов функции с правильным отступом