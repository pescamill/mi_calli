from pydantic import BaseModel
from datetime import datetime


class PropertyCreate(BaseModel):
    name: str
    address: str
    owner_id: int


class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    image_url: str | None
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True