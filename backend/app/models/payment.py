from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    receipt_path = Column(String, nullable=True)

    contract = relationship("Contract", back_populates="payments")
