from app.core.schemas.base import BaseSchema
from typing import Optional


class CityRead(BaseSchema):
    id: int
    name: str


class CityCreate(BaseSchema):
    name: str

    model_config = {"str_strip_whitespace": True}


class CityUpdate(BaseSchema):
    name: Optional[str] = None

    model_config = {"str_strip_whitespace": True}
