from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models import User
from app.schemas.user import UserCreate, UserResponse
from sqlalchemy.exc import ProgrammingError

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    db: Session = SessionLocal()
    if user.role not in {"admin", "tenant"}:
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'tenant'")
    db_user = User(
        username=user.username,
        password_hash=user.password,
        email=user.email,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return db_user

@router.get("/users", response_model=list[UserResponse])
def get_users():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
    except ProgrammingError:
        db.close()
        raise HTTPException(status_code=503, detail="Database tables missing; run migrations")
    db.close()
    return users