from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Numeric, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.models.base import Base
import sqlalchemy as sa


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class Order(Base):
    __tablename__ = "orders"
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    executor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    desired_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.current_timestamp(), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(sa.Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    customer: Mapped["User"] = relationship("User", foreign_keys="Order.customer_id", back_populates="orders_created")
    executor: Mapped["User"] = relationship("User", foreign_keys="Order.executor_id", back_populates="orders_executed")
    category: Mapped["Category"] = relationship("Category")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="order")
    review: Mapped["Review"] = relationship("Review", back_populates="order", uselist=False)
