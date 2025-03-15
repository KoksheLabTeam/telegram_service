from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.models.base import Base
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, Enum
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"  # Ожидает
    IN_PROGRESS = "in_progress"  # В процессе
    COMPLETED = "completed"  # Завершен
    CANCELED = "canceled"  # Отменен

class Order(Base):
    """Модель заказа."""
    __tablename__ = "orders"

    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ID заказчика
    executor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # ID исполнителя (опционально)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)  # ID категории
    title: Mapped[str] = mapped_column(nullable=False)  # Название заказа
    description: Mapped[str | None] = mapped_column(nullable=True)  # Описание заказа (опционально)
    desired_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # Желаемая цена
    due_date: Mapped[datetime] = mapped_column(nullable=False)  # Срок выполнения
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)  # Дата создания
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)  # Статус заказа

    # Связи с другими моделями
    customer: Mapped["User"] = relationship("User", foreign_keys="Order.customer_id", back_populates="orders_created")  # Заказчик
    executor: Mapped["User"] = relationship("User", foreign_keys="Order.executor_id", back_populates="orders_executed")  # Исполнитель
    category: Mapped["Category"] = relationship("Category")  # Категория
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="order")  # Предложения по заказу
    review: Mapped["Review"] = relationship("Review", back_populates="order", uselist=False)  # Отзыв по заказу