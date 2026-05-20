from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.property import Property
from app.schemas.property import (
    PropertyCreate,
    PropertyResponse
)

router = APIRouter()


@router.post("/properties", response_model=PropertyResponse)
def create_property(property_data: PropertyCreate):

    db: Session = SessionLocal()

    property_obj = Property(
        name=property_data.name,
        address=property_data.address,
        owner_id=property_data.owner_id
    )

    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)

    return property_obj


@router.get("/properties", response_model=list[PropertyResponse])
def get_properties():

    db: Session = SessionLocal()

    properties = db.query(Property).all()

    return properties