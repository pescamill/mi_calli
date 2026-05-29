from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    address = Column(String, nullable=False)

    image_url = Column(String, nullable=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    owner = relationship(
        "User",
        back_populates="owned_properties",
        foreign_keys=[owner_id],
    )

    tenants = relationship(
        "User",
        back_populates="assigned_property",
        foreign_keys="User.property_id",
    )