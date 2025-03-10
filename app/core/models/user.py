from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.models.base import Base
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, CheckConstraint

class User(Base):
    """Модель для пользователей."""
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    is_customer: Mapped[bool] = mapped_column(default=False)
    is_executor: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=0.0)
    completed_orders: Mapped[int] = mapped_column(default=0)

    # Связи
    city: Mapped["City"] = relationship("City", back_populates="users")
    categories: Mapped[list["Category"]] = relationship(
        "Category", secondary="user_categories", back_populates="users"
    )
    orders_created: Mapped[list["Order"]] = relationship(
        "Order", foreign_keys="Order.customer_id", back_populates="customer"
    )
    orders_executed: Mapped[list["Order"]] = relationship(
        "Order", foreign_keys="Order.executor_id", back_populates="executor"
    )
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="executor")
    reviews_received: Mapped[list["Review"]] = relationship(
        "Review", foreign_keys="Review.target_id", back_populates="target"
    )
    reviews_written: Mapped[list["Review"]] = relationship(
        "Review", foreign_keys="Review.author_id", back_populates="author"
    )