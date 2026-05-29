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
    admin_signed_at = Column(DateTime(timezone=True), nullable=True)
    tenant_signed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property")
    tenant = relationship("User")
    payments = relationship("Payment", back_populates="contract")
