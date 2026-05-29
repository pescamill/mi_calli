from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File

from app.db.database import Base, engine
import time
import logging

from app.api.properties import router as properties_router
from app.api.users import router as users_router
from app.api.contracts import router as contracts_router

from sqlalchemy import text

import app.models
import shutil

app = FastAPI()

@app.on_event("startup")
def create_tables():
    """Try once to create tables at startup; if DB isn't ready, log and continue.

    Migrations are handled by the separate `migrate` service. Use `/setup`
    to force table creation manually if needed.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logging.warning("Could not create tables at startup: %s", e)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(users_router)
app.include_router(properties_router)
app.include_router(contracts_router)

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

