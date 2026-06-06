from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_year = Column(Integer, nullable=False)
    start_month = Column(Integer, nullable=False)
    duration_months = Column(Integer, nullable=False, default=12)
    pay_day = Column(Integer, nullable=False, default=1)
    amount = Column(Numeric(10, 2), nullable=False)
    inventory = Column(Text, nullable=True)
    admin_signed_at = Column(DateTime(timezone=True), nullable=True)
    tenant_signed_at = Column(DateTime(timezone=True), nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="contracts")
    tenant = relationship("User", back_populates="contracts", foreign_keys=[tenant_id])
    months = relationship("ContractMonth", back_populates="contract", cascade="all, delete-orphan")


class ContractMonth(Base):
    __tablename__ = "contract_months"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    file_path = Column(String, nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="months")
    payments = relationship("Payment", back_populates="contract_month", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    contract_month_id = Column(Integer, ForeignKey("contract_months.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    receipt_url = Column(String, nullable=True)

    contract_month = relationship("ContractMonth", back_populates="payments")