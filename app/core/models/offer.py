from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.models.base import Base
from decimal import Decimal
from sqlalchemy import Enum, ForeignKey, Numeric
import enum

class OfferStatus(str, enum.Enum):
    PENDING = "pending"  # Ожидает
    ACCEPTED = "accepted"  # Принято
    REJECTED = "rejected"  # Отклонено

class Offer(Base):
    """Модель предложения."""
    __tablename__ = "offers"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)  # ID заказа
    executor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ID исполнителя
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # Цена предложения
    estimated_time: Mapped[int] = mapped_column(nullable=False)  # Оценочное время выполнения (в часах)
    status: Mapped[OfferStatus] = mapped_column(Enum(OfferStatus), default=OfferStatus.PENDING, nullable=False)  # Статус предложения
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)  # Дата создания
    start_date: Mapped[datetime | None] = mapped_column(nullable=True)  # Добавлено поле для даты начала

    # Связи с другими моделями
    order: Mapped["Order"] = relationship("Order", back_populates="offers")  # Заказ
    executor: Mapped["User"] = relationship("User", back_populates="offers")  # Исполнитель