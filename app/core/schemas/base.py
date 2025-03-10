from pydantic import BaseModel

class BaseSchema(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        # Убираем alias_generator=camelize
    }