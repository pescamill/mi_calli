from pydantic import BaseModel
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str
    email: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True