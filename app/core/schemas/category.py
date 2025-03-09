from app.core.schemas.base import BaseSchema

class CategoryRead(BaseSchema):
    id: int
    name: str

class CategoryCreate(BaseSchema):
    name: str

    model_config = {"str_strip_whitespace": True}