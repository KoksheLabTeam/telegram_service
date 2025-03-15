from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.models.base import Base
from sqlalchemy import ForeignKey, CheckConstraint

class Review(Base):
    """Модель отзыва."""
    __tablename__ = "reviews"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)  # ID заказа
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ID автора отзыва
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ID получателя отзыва
    rating: Mapped[int] = mapped_column(CheckConstraint("rating BETWEEN 1 AND 5"), nullable=False)  # Рейтинг (от 1 до 5)
    comment: Mapped[str | None] = mapped_column(nullable=True)  # Комментарий (опционально)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)  # Дата создания

    # Связи с другими моделями
    order: Mapped["Order"] = relationship("Order", back_populates="review")  # Заказ
    author: Mapped["User"] = relationship("User", foreign_keys="Review.author_id", back_populates="reviews_written")  # Автор
    target: Mapped["User"] = relationship("User", foreign_keys="Review.target_id", back_populates="reviews_received")  # Получатель