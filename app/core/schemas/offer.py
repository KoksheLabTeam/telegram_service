from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema
import enum  # Добавляем импорт enum

# Определяем OfferStatus как перечисление
class OfferStatus(str, enum.Enum):  # Наследуемся от str и enum.Enum
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class OfferRead(BaseSchema):
    id: int
    order_id: int
    executor_id: int
    price: float
    estimated_time: int
    status: OfferStatus  # Теперь Pydantic понимает этот тип
    created_at: datetime

class OfferCreate(BaseSchema):
    order_id: int
    price: float
    estimated_time: int

    model_config = {"str_strip_whitespace": True}

class OfferUpdate(BaseSchema):
    status: Optional[OfferStatus] = None  # Используем тот же OfferStatus