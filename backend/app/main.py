from fastapi import FastAPI, UploadFile, File, Depends, Form
from fastapi.staticfiles import StaticFiles
from app.db.database import engine, SessionLocal, get_db
from app.api.properties import router as properties_router
from app.api.users import router as users_router
from app.api.contracts import router as contracts_router, send_email, effective_pay_day
from app.api.rooms import router as rooms_router
from app.models import Contract, ContractMonth, User, Property, Room
from app.scripts.import_xlsx_template import run_import
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
import app.models
import shutil
import os
import asyncio
import httpx
import csv
import io
import logging
import tempfile
import pandas as pd
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager


logger = logging.getLogger("uvicorn.error")


async def poll_google_sheet():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        logger.warning("GOOGLE_SHEET_ID not set, skipping sheet polling")
        return
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    while True:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url)
                reader = csv.reader(io.StringIO(res.text))
                next(reader)
                db = SessionLocal()
                try:
                    for parts in reader:
                        if not parts:
                            continue
                        contract_id_str = parts[-1].strip()
                        if not contract_id_str.isdigit():
                            continue
                        contract_id = int(contract_id_str)
                        contract = db.query(Contract).filter(
                            Contract.id == contract_id,
                            Contract.tenant_signed_at == None
                        ).first()
                        if contract:
                            contract.tenant_signed_at = datetime.utcnow()
                            db.commit()
                            logger.info("Auto-signed contract %d from Google Sheet", contract_id)
                finally:
                    db.close()
        except Exception as e:
            logger.error("Sheet polling error: %s", e)
        await asyncio.sleep(120)


async def send_daily_reminders():
    while True:
        try:
            today = date.today()
            db = SessionLocal()
            try:
                contract_months = db.query(ContractMonth).options(
                    joinedload(ContractMonth.payments),
                    joinedload(ContractMonth.contract).joinedload(Contract.tenant),
                    joinedload(ContractMonth.contract).joinedload(Contract.room).joinedload(Room.property),
                ).filter(
                    ContractMonth.year == today.year,
                    ContractMonth.month == today.month,
                ).all()

                for cm in contract_months:
                    contract = cm.contract
                    if not contract or contract.terminated_at:
                        continue

                    pay_day = effective_pay_day(contract.pay_day, today.year, today.month)
                    reminder_day = max(1, pay_day - 3)
                    if today.day < reminder_day:
                        continue

                    total_paid = round(sum(float(p.amount) for p in cm.payments), 2)
                    amount_due = round(float(contract.amount), 2)
                    if total_paid >= amount_due:
                        continue

                    if cm.reminder_sent_at:
                        last = cm.reminder_sent_at
                        if hasattr(last, 'date'):
                            last = last.date()
                        if last >= today:
                            continue

                    room = contract.room
                    prop = room.property
                    tenant = contract.tenant
                    owner = db.query(User).filter(User.id == prop.owner_id).first()
                    if not prop or not tenant or not owner:
                        continue

                    remaining = amount_due - total_paid
                    month_name = datetime(today.year, today.month, 1).strftime("%B %Y")

                    html = f"""
                        <p>Hi,</p>
                        <p>Rent is due for <strong>{room.name}</strong> at <strong>{prop.name}</strong>.</p>
                        <table style="border-collapse:collapse;margin-top:1rem;">
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Tenant</td><td><strong>{tenant.username}</strong></td></tr>
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Room</td><td><strong>{room.name}</strong></td></tr>
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Month</td><td><strong>{month_name}</strong></td></tr>
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Due date</td><td><strong>{pay_day} {month_name}</strong></td></tr>
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Amount due</td><td><strong>${amount_due:.2f}</strong></td></tr>
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Paid so far</td><td><strong>${total_paid:.2f}</strong></td></tr>
                            <tr><td style="padding:4px 16px 4px 0;color:#888;">Remaining</td><td><strong>${remaining:.2f}</strong></td></tr>
                        </table>
                        <p style="margin-top:1rem;color:#888;font-size:12px;">
                            This reminder will stop once the owner marks the payment as received.
                        </p>
                    """

                    recipients = [r.email for r in [tenant, owner] if r and r.email]
                    sent = send_email(recipients, f"Rent due — {room.name} at {prop.name} — {month_name}", html)
                    if sent:
                        cm.reminder_sent_at = datetime.utcnow()
                        db.commit()

            finally:
                db.close()

        except Exception as e:
            logger.error("Daily reminder error: %s", e)

        now = datetime.utcnow()
        next_run = datetime(now.year, now.month, now.day, 9, 0, 0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info("Next reminder run in %.1f hours", wait_seconds / 3600)
        await asyncio.sleep(wait_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(poll_google_sheet())
    asyncio.create_task(send_daily_reminders())
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.include_router(users_router)
app.include_router(properties_router)
app.include_router(rooms_router)
app.include_router(contracts_router)


@app.get("/")
def read_root():
    return {"message": "mi_calli running"}


@app.get("/health/db")
def db_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        return {"database": "disconnected", "error": str(e)}


@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/uploads/{file.filename}"}


@app.post("/import_xlsx")
async def import_xlsx_endpoint(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),       # FIX: was True — now defaults to live run
    db: Session = Depends(get_db),     # FIX: use FastAPI's session (inside Docker)
):
    if not file.filename.endswith((".xlsx", ".xls")):
        return {"error": "Only .xlsx / .xls files are accepted"}

    contents = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        df = pd.read_excel(tmp_path)
    except Exception as e:
        return {"error": f"Could not parse file: {e}"}
    finally:
        os.unlink(tmp_path)

    try:
        result = run_import(df, db, dry_run=dry_run)   # FIX: pass db directly
    except Exception as e:
        import traceback
        logger.error("Import error: %s", traceback.format_exc())
        db.rollback()
        return {"error": str(e)}

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return {
        "status": "ok",
        "dry_run": dry_run,
        "result": {
            "created": len(result["created"]),
            "unresolved": len(result["unresolved"]),
            "created_list": result["created"],
            "unresolved_list": result["unresolved"],
        },
    }