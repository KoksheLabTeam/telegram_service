from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"

class OrderRead(BaseSchema):
    id: int
    customer_id: int
    executor_id: Optional[int]
    category_id: int
    title: str
    description: Optional[str]
    desired_price: float
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