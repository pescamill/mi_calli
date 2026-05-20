from fastapi import FastAPI
from app.db.database import Base, engine
from app.api.users import router as users_router
from sqlalchemy import text
import app.models 

app = FastAPI()
app.include_router(users_router)

#Base.metadata.create_all(bind=engine)

@app.post("/setup")
def setup_database():
    Base.metadata.create_all(bind=engine)

    return {
        "message": "database tables created"
    }

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