from typing import Optional, List
from app.core.schemas.base import BaseSchema

# app\core\schemas\user.py
from typing import Optional, List
from app.core.schemas.base import BaseSchema

class UserRead(BaseSchema):
    id: int
    telegram_id: int
    name: str
    username: Optional[str]
    is_customer: bool
    is_executor: bool
    is_admin: bool
    city_id: int
    rating: float
    completed_orders: int
    category_ids: Optional[List[int]] = None  # Добавляем поле для категорий

    @classmethod
    def from_orm(cls, obj):
        data = super().from_orm(obj).__dict__
        data["category_ids"] = [cat.id for cat in obj.categories] if obj.categories else []
        return cls(**data)

class UserCreate(BaseSchema):
    telegram_id: int
    name: str
    username: Optional[str]
    is_customer: bool = False
    is_executor: bool = False
    city_id: int
    category_ids: Optional[List[int]] = None

    model_config = {"str_strip_whitespace": True}

class UserUpdate(BaseSchema):
    name: Optional[str] = None
    username: Optional[str] = None
    is_customer: Optional[bool] = None
    is_executor: Optional[bool] = None
    city_id: Optional[int] = None
    category_ids: Optional[List[int]] = None

    model_config = {"str_strip_whitespace": True}