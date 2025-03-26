from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from app.core.models.order import OrderStatus
from typing import Optional

class OrderCreate(BaseModel):
    category_id: int
    title: str
    description: Optional[str] = None
    desired_price: Decimal
    due_date: datetime

class OrderUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    desired_price: Optional[Decimal] = None
    due_date: Optional[datetime] = None
    status: Optional[OrderStatus] = None

class OrderRead(BaseModel):
    id: int
    customer_id: int
    executor_id: Optional[int] = None
    category_id: int
    title: str
    description: Optional[str] = None
    desired_price: Decimal
    due_date: datetime
    created_at: datetime
    status: OrderStatus

    class Config:
        from_attributes = True