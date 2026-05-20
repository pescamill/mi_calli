from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):

    db: Session = SessionLocal()

    db_user = User(
        username=user.username,
        password_hash=user.password,  # still not production
        email=user.email
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user  

@router.get("/users", response_model=list[UserResponse])
def get_users():
    db: Session = SessionLocal()
    users = db.query(User).all()
    return users

