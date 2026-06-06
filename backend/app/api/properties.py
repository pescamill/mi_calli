from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import SessionLocal
from app.models import User, Property, PropertyImage, HouseExpense
from app.schemas.property import (
    PropertyCreate, PropertyResponse,
    HouseExpenseCreate, HouseExpenseResponse
)

router = APIRouter()

@router.post("/properties", response_model=PropertyResponse)
def create_property(data: PropertyCreate):
    db: Session = SessionLocal()
    owner = db.query(User).filter(User.id == data.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="owner not found")
    if owner.role != "admin":
        raise HTTPException(status_code=400, detail="property owner must be an admin")
    prop = Property(name=data.name, address=data.address, owner_id=data.owner_id)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    # Eagerly load images before closing session
    _ = prop.images
    db.close()
    return prop

@router.get("/properties", response_model=list[PropertyResponse])
def get_properties():
    db: Session = SessionLocal()
    props = db.query(Property).options(joinedload(Property.images)).all()
    db.close()
    return props

@router.post("/properties/{property_id}/images")
def add_property_image(property_id: int, payload: dict):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    db: Session = SessionLocal()
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="property not found")
    img = PropertyImage(property_id=property_id, url=url)
    db.add(img)
    db.commit()
    db.refresh(img)
    db.close()
    return {"id": img.id, "url": img.url}

@router.delete("/properties/{property_id}/images/{image_id}")
def delete_property_image(property_id: int, image_id: int):
    db: Session = SessionLocal()
    img = db.query(PropertyImage).filter(
        PropertyImage.id == image_id,
        PropertyImage.property_id == property_id
    ).first()
    if not img:
        raise HTTPException(status_code=404, detail="image not found")
    db.delete(img)
    db.commit()
    db.close()
    return {"deleted": True}

@router.post("/properties/{property_id}/expenses", response_model=HouseExpenseResponse)
def add_expense(property_id: int, data: HouseExpenseCreate):
    db: Session = SessionLocal()
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="property not found")
    expense = HouseExpense(
        property_id=property_id,
        description=data.description,
        amount=data.amount,
        year=data.year,
        month=data.month,
        receipt_url=data.receipt_url,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    db.close()
    return expense

@router.get("/properties/{property_id}/expenses", response_model=list[HouseExpenseResponse])
def get_expenses(property_id: int):
    db: Session = SessionLocal()
    expenses = db.query(HouseExpense).filter(HouseExpense.property_id == property_id).all()
    db.close()
    return expenses

@router.post("/properties/{property_id}/expenses/{expense_id}/mark_paid")
def mark_expense_paid(property_id: int, expense_id: int):
    from datetime import datetime
    db: Session = SessionLocal()
    expense = db.query(HouseExpense).filter(
        HouseExpense.id == expense_id,
        HouseExpense.property_id == property_id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="expense not found")
    expense.paid_at = datetime.utcnow()
    db.add(expense)
    db.commit()
    db.refresh(expense)
    db.close()
    return {"paid": True}