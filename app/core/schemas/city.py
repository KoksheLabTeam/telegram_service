from app.core.schemas.base import BaseSchema

class CityRead(BaseSchema):
    id: int
    name: str

class CityCreate(BaseSchema):
    name: str

    model_config = {"str_strip_whitespace": True}