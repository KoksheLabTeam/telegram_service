from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.models.base import Base
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, CheckConstraint

class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)  # Уникальный Telegram ID
    name: Mapped[str] = mapped_column(nullable=False)  # Имя пользователя
    username: Mapped[str | None] = mapped_column(unique=True, nullable=True)  # Уникальное имя в Telegram (опционально)
    is_customer: Mapped[bool] = mapped_column(default=False)  # Является ли заказчиком
    is_executor: Mapped[bool] = mapped_column(default=False)  # Является ли исполнителем
    is_admin: Mapped[bool] = mapped_column(default=False)  # Является ли администратором
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)  # ID города
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=0.0, nullable=False)  # Рейтинг пользователя
    completed_orders: Mapped[int] = mapped_column(default=0, nullable=False)  # Количество завершенных заказов

    # Связи с другими моделями
    city: Mapped["City"] = relationship("City", back_populates="users")  # Связь с городом
    categories: Mapped[list["Category"]] = relationship(
        "Category", secondary="user_categories", back_populates="users"  # Связь с категориями через таблицу user_categories
    )
    orders_created: Mapped[list["Order"]] = relationship(
        "Order", foreign_keys="Order.customer_id", back_populates="customer"  # Заказы, созданные пользователем
    )
    orders_executed: Mapped[list["Order"]] = relationship(
        "Order", foreign_keys="Order.executor_id", back_populates="executor"  # Заказы, выполненные пользователем
    )
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="executor")  # Предложения пользователя
    reviews_received: Mapped[list["Review"]] = relationship(
        "Review", foreign_keys="Review.target_id", back_populates="target"  # Полученные отзывы
    )
    reviews_written: Mapped[list["Review"]] = relationship(
        "Review", foreign_keys="Review.author_id", back_populates="author"  # Написанные отзывы
    )

    __table_args__ = (
        CheckConstraint("NOT (is_customer AND is_executor)", name="check_role_exclusivity"),  # Проверка: нельзя быть заказчиком и исполнителем одновременно
    )