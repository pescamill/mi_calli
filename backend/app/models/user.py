from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from sqlalchemy.sql import func

from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash = Column(
        String,
        nullable=False,
    )

    role = Column(
        String,
        default="tenant",
        nullable=False,
    )

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    owned_properties = relationship(
        "Property",
        back_populates="owner",
        foreign_keys="Property.owner_id",
    )

    assigned_property = relationship(
        "Property",
        back_populates="tenants",
        foreign_keys=[property_id],
    )