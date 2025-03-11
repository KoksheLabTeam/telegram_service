from app.core.schemas.base import BaseSchema
from typing import Optional


class CategoryRead(BaseSchema):
    id: int
    name: str


class CategoryCreate(BaseSchema):
    name: str

    model_config = {"str_strip_whitespace": True}


class CategoryUpdate(BaseSchema):
    name: Optional[str] = None

    model_config = {"str_strip_whitespace": True}
