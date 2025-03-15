from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema
import enum

class OfferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class OfferRead(BaseSchema):
    id: int
    order_id: int
    executor_id: int
    price: float
    estimated_time: int
    status: OfferStatus
    created_at: datetime
    start_date: Optional[datetime]  # Добавлено

class OfferCreate(BaseSchema):
    order_id: int
    price: float
    estimated_time: int
    start_date: Optional[datetime]  # Добавлено

    model_config = {"str_strip_whitespace": True}

class OfferUpdate(BaseSchema):
    price: Optional[float] = None
    estimated_time: Optional[int] = None
    status: Optional[OfferStatus] = None
    start_date: Optional[datetime] = None  # Добавлено