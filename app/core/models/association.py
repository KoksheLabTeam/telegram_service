from sqlalchemy import Table, Column, Integer, ForeignKey
from app.core.models.base import Base

user_categories = Table(
    "user_categories",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),  # ID пользователя
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),  # ID категории
)  # Таблица связи многие-ко-многим между пользователями и категориями