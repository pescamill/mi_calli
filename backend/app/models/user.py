from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="tenant", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owned_properties = relationship("Property", back_populates="owner", foreign_keys="Property.owner_id")
    contracts = relationship("Contract", back_populates="tenant", foreign_keys="Contract.tenant_id")