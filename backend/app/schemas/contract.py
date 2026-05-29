from pydantic import BaseModel
from datetime import datetime


class ContractCreate(BaseModel):
    property_id: int
    tenant_id: int
    year: int
    month: int
    amount: float


class ContractResponse(BaseModel):
    id: int
    property_id: int
    tenant_id: int
    year: int
    month: int
    amount: float
    file_path: str | None
    admin_signed_at: datetime | None
    tenant_signed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
