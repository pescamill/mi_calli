from pydantic import BaseModel
from datetime import datetime

class RoomCreate(BaseModel):
    property_id: int
    name: str
    default_amount: float | None = None
    default_pay_day: int | None = None
    default_duration_months: int | None = None

class RoomUpdate(BaseModel):
    name: str | None = None
    default_amount: float | None = None
    default_pay_day: int | None = None
    default_duration_months: int | None = None

class RoomImageResponse(BaseModel):
    id: int
    url: str
    created_at: datetime
    class Config:
        from_attributes = True

class RoomResponse(BaseModel):
    id: int
    property_id: int
    name: str
    default_amount: float | None
    default_pay_day: int | None
    default_duration_months: int | None
    created_at: datetime
    images: list[RoomImageResponse] = []
    occupied: bool = False
    class Config:
        from_attributes = True