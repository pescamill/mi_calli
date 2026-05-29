from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import User
from app.models.property import Property
from app.schemas.property import (
    PropertyCreate,
    PropertyResponse,
)

router = APIRouter()


@router.post("/properties", response_model=PropertyResponse)
def create_property(property_data: PropertyCreate):
    db: Session = SessionLocal()

    owner = db.query(User).filter(User.id == property_data.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="owner not found")

    if owner.role != "admin":
        raise HTTPException(
            status_code=400,
            detail="property owner must be an admin user",
        )

    property_obj = Property(
        name=property_data.name,
        address=property_data.address,
        owner_id=property_data.owner_id,
        image_url=property_data.image_url,
    )

    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)
    db.close()

    return property_obj


@router.get("/properties", response_model=list[PropertyResponse])
def get_properties():
    db: Session = SessionLocal()
    properties = db.query(Property).all()
    db.close()
    return properties