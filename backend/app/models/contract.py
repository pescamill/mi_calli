from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    file_path = Column(String, nullable=True)
    tenant_token = Column(String, nullable=True, index=True)
    token_generated_at = Column(DateTime(timezone=True), nullable=True)
    admin_signed_at = Column(DateTime(timezone=True), nullable=True)
    tenant_signed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", back_populates="contracts")
    tenant = relationship("User", back_populates="contracts", foreign_keys=[tenant_id])
    payments = relationship("Payment", back_populates="contract")