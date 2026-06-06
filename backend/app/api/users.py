from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserResponse
from sqlalchemy.exc import ProgrammingError

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
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
    return db_user

@router.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    try:
        return db.query(User).all()
    except ProgrammingError:
        raise HTTPException(status_code=503, detail="Database tables missing; run migrations")