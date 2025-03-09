from pydantic import BaseModel
from humps import camelize

class BaseSchema(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": camelize,
    }