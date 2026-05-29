from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles

from app.db.database import Base, engine

from app.api.properties import router as properties_router
from app.api.users import router as users_router

from sqlalchemy import text

import app.models
import shutil
import time

app = FastAPI()


@app.on_event("startup")
def create_tables():
    # Wait for the database to become available (useful during container startup)
    max_retries = 30
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                break
        except Exception:
            if attempt == max_retries:
                raise
            time.sleep(1)

    Base.metadata.create_all(bind=engine)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(users_router)
app.include_router(properties_router)

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

@app.post("/upload")
def upload_file(file: UploadFile = File(...)):

    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "url": f"/uploads/{file.filename}"
    }

@app.post("/setup")
def setup_database():
    Base.metadata.create_all(bind=engine)

    return {
        "message": "database tables created"
    }

