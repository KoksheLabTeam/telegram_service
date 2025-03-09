from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema

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
    is_completed: bool

class OrderCreate(BaseSchema):
    category_id: int
    title: str
    description: Optional[str]
    desired_price: float
    due_date: datetime

    model_config = {"str_strip_whitespace": True}

class OrderUpdate(BaseSchema):
    executor_id: Optional[int] = None
    is_completed: Optional[bool] = None