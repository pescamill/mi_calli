from fastapi import FastAPI
from app.db.database import Base, engine
import app.models  # Import models to register them with SQLAlchemy
from sqlalchemy import text

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "mi_calli running"}

@app.get("/health/db")
def db_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "database": "connected"
        }

    except Exception as e:
        return {
            "database": "disconnected",
            "error": str(e)
        }