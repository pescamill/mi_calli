from pydantic import BaseModel
from datetime import datetime

class PropertyCreate(BaseModel):
    name: str
    address: str
    owner_id: int

class PropertyImageResponse(BaseModel):
    id: int
    url: str
    created_at: datetime
    class Config:
        from_attributes = True

class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    owner_id: int
    created_at: datetime
    images: list[PropertyImageResponse] = []
    class Config:
        from_attributes = True

class HouseExpenseCreate(BaseModel):
    property_id: int
    description: str
    amount: float
    year: int
    month: int
    receipt_url: str | None = None

class HouseExpenseResponse(BaseModel):
    id: int
    property_id: int
    description: str
    amount: float
    year: int
    month: int
    paid_at: datetime | None
    receipt_url: str | None
    created_at: datetime
    class Config:
        from_attributes = True