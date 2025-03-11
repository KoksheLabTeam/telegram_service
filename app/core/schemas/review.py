from typing import Optional
from datetime import datetime
from app.core.schemas.base import BaseSchema

class ReviewRead(BaseSchema):
    id: int
    order_id: int
    author_id: int
    target_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

class ReviewCreate(BaseSchema):
    order_id: int
    target_id: int
    rating: int
    comment: Optional[str] = None

    model_config = {"str_strip_whitespace": True}

class ReviewUpdate(BaseSchema):
    rating: Optional[int] = None
    comment: Optional[str] = None

    model_config = {"str_strip_whitespace": True}