from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String, 
        unique=True, 
        index=True, 
        nullable=False
    )

    password_hash = Column(
        String, 
        nullable=False
    )

    role = Column(
        String, 
        default="worker"
    )

    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now()
    )