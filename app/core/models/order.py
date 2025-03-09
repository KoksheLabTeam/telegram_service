from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.models.base import Base
from decimal import Decimal

class Order(Base):
    """Модель для заказов."""
    __tablename__ = "orders"

    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    executor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    desired_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    is_completed: Mapped[bool] = mapped_column(default=False)

    # Связи
    customer: Mapped["User"] = relationship("User", foreign_keys="Order.customer_id", back_populates="orders_created")
    executor: Mapped["User"] = relationship("User", foreign_keys="Order.executor_id", back_populates="orders_executed")
    category: Mapped["Category"] = relationship("Category")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="order")
    review: Mapped["Review"] = relationship("Review", back_populates="order")