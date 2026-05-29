from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import User, Property
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    db: Session = SessionLocal()

    if user.role not in {"admin", "tenant"}:
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'tenant'")

    if user.role == "tenant" and user.property_id is None:
        raise HTTPException(
            status_code=400,
            detail="tenant users must belong to a property",
        )

    if user.property_id is not None:
        property_obj = db.query(Property).filter(Property.id == user.property_id).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail="property not found")

    if user.role == "admin" and user.property_id is not None:
        raise HTTPException(
            status_code=400,
            detail="admin users should not belong to a property",
        )

    db_user = User(
        username=user.username,
        password_hash=user.password,  # still not production
        email=user.email,
        role=user.role,
        property_id=user.property_id,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()

    return db_user


@router.get("/users", response_model=list[UserResponse])
def get_users():
    db: Session = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users

