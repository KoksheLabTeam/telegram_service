from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema
import enum
from decimal import Decimal  # Добавлен импорт

class OrderStatus(str, enum.Enum):
    PENDING = "В_ожидании"  # Приводим к верхнему регистру
    IN_PROGRESS = "В_прогрессе"
    COMPLETED = "Выполнен"
    CANCELED = "Отменен"

class OrderRead(BaseSchema):
    id: int
    customer_id: int
    executor_id: Optional[int]
    category_id: int
    title: str
    description: Optional[str]
    desired_price: Decimal
    due_date: datetime
    created_at: datetime
    status: OrderStatus

class OrderCreate(BaseSchema):
    category_id: int
    title: str
    description: Optional[str] = None
    desired_price: float
    due_date: datetime

    model_config = {"str_strip_whitespace": True}

class OrderUpdate(BaseSchema):
    executor_id: Optional[int] = None
    status: Optional[OrderStatus] = None