from pydantic import BaseModel
from datetime import datetime


class PaymentCreate(BaseModel):
    amount: float
    recorded_by: int | None = None


class PaymentResponse(BaseModel):
    id: int
    contract_id: int
    amount: float
    paid_at: datetime
    recorded_by: int | None

    class Config:
        from_attributes = True
