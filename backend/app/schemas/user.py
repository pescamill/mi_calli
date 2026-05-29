from pydantic import BaseModel
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    role: str = "tenant"
    property_id: int | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: str
    property_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True