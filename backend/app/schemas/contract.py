from pydantic import BaseModel, validator
from datetime import datetime

class ContractCreate(BaseModel):
    room_id: int
    tenant_id: int
    start_year: int
    start_month: int
    duration_months: int = 12
    pay_day: int = 1
    amount: float
    inventory: str | None = None

    @validator("pay_day")
    def pay_day_range(cls, v):
        if not 1 <= v <= 28:
            raise ValueError("pay_day must be between 1 and 28")
        return v

    @validator("duration_months")
    def duration_positive(cls, v):
        if v < 1:
            raise ValueError("duration_months must be at least 1")
        return v

class PaymentCreate(BaseModel):
    amount: float
    recorded_by: int | None = None
    receipt_url: str | None = None

class PaymentResponse(BaseModel):
    id: int
    contract_month_id: int
    amount: float
    paid_at: datetime
    recorded_by: int | None
    receipt_url: str | None
    class Config:
        from_attributes = True

class ContractMonthResponse(BaseModel):
    id: int
    contract_id: int
    year: int
    month: int
    file_path: str | None
    reminder_sent_at: datetime | None
    payments: list[PaymentResponse] = []
    class Config:
        from_attributes = True

class ContractResponse(BaseModel):
    id: int
    room_id: int
    tenant_id: int
    start_year: int
    start_month: int
    duration_months: int
    pay_day: int
    amount: float
    inventory: str | None
    admin_signed_at: datetime | None
    tenant_signed_at: datetime | None
    terminated_at: datetime | None
    created_at: datetime
    months: list[ContractMonthResponse] = []
    class Config:
        from_attributes = True