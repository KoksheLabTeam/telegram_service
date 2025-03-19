from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "В_ожидании"  # Используем русские значения, как в миграции 3057d1616d62
    IN_PROGRESS = "В_прогрессе"
    COMPLETED = "Выполнен"
    CANCELED = "Отменен"

class OrderRead(BaseSchema):
    id: int
    customer_id: int
    executor_id: Optional[int]
    category_id: int
    city_id: int
    title: str
    description: Optional[str]
    desired_price: float
    due_date: datetime
    created_at: datetime
    status: OrderStatus

    @classmethod
    def from_orm(cls, obj):
        data = super().from_orm(obj).__dict__
        # Безопасно обрабатываем случай, если customer отсутствует
        data["city_id"] = obj.customer.city_id if obj.customer else 0
        return cls(**data)

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