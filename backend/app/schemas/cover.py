from pydantic import BaseModel


class CoverOut(BaseModel):
    id: str
    content_type: str
    byte_size: int
