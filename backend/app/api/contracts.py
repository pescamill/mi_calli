from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
import os
from datetime import datetime
import uuid
import resend
import logging


from app.db.database import SessionLocal
from app.models import User, Property, Contract, Payment
from app.schemas.contract import ContractCreate, ContractResponse
from app.schemas.payment import PaymentCreate, PaymentResponse
from sqlalchemy.exc import ProgrammingError

router = APIRouter()

logger = logging.getLogger("uvicorn.error")

def is_admin(db: Session, admin_id: int) -> bool:
    admin = db.query(User).filter(User.id == admin_id).first()
    return bool(admin and admin.role == "admin")

def send_signing_email(to_email: str, tenant_name: str, link: str):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return False
    resend.api_key = api_key
    try:
        resend.Emails.send({
            "from": os.getenv("SMTP_FROM", "onboarding@resend.dev"),
            "to": to_email,
            "subject": "Please sign your rent contract",
            "html": f"<p>Hello {tenant_name},</p><p>Please sign your contract by visiting: <a href='{link}'>{link}</a></p>",
        })
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False

@router.post("/contracts", response_model=ContractResponse)
def create_contract(contract_data: ContractCreate):
    db: Session = SessionLocal()
    prop = db.query(Property).filter(Property.id == contract_data.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="property not found")
    tenant = db.query(User).filter(User.id == contract_data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")
    if tenant.role != "tenant":
        raise HTTPException(status_code=400, detail="user is not a tenant")
    exists = db.query(Contract).filter(
        Contract.property_id == contract_data.property_id,
        Contract.tenant_id == contract_data.tenant_id,
        Contract.year == contract_data.year,
        Contract.month == contract_data.month,
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="contract already exists for this tenant/property/month")
    contract = Contract(
        property_id=contract_data.property_id,
        tenant_id=contract_data.tenant_id,
        year=contract_data.year,
        month=contract_data.month,
        amount=contract_data.amount,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    db.close()
    return contract

@router.post("/admin/generate_reminders")
def generate_reminders(payload: dict):
    year = payload.get("year") or datetime.utcnow().year
    month = payload.get("month") or datetime.utcnow().month
    admin_id = payload.get("admin_id")
    db: Session = SessionLocal()
    try:
        if not admin_id or not is_admin(db, int(admin_id)):
            raise HTTPException(status_code=403, detail="admin privileges required")
    except ProgrammingError:
        db.close()
        raise HTTPException(status_code=503, detail="Database tables missing; run migrations")
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    try:
        previous_contracts = db.query(Contract).filter(
            Contract.year == prev_year,
            Contract.month == prev_month
        ).all()
    except ProgrammingError:
        db.close()
        raise HTTPException(status_code=503, detail="Database tables missing; run migrations")
    if not previous_contracts:
        db.close()
        return {"created": 0, "message": "no contracts found for previous month to roll forward"}
    created = []
    for old_contract in previous_contracts:
        exists = db.query(Contract).filter(
            Contract.property_id == old_contract.property_id,
            Contract.tenant_id == old_contract.tenant_id,
            Contract.year == year,
            Contract.month == month,
        ).first()
        if exists:
            continue
        contract = Contract(
            property_id=old_contract.property_id,
            tenant_id=old_contract.tenant_id,
            year=year,
            month=month,
            amount=old_contract.amount,
        )
        db.add(contract)
        db.flush()
        uploads_dir = os.path.abspath("uploads/contracts")
        os.makedirs(uploads_dir, exist_ok=True)
        filename = f"contract_{contract.id}.html"
        file_path = os.path.join(uploads_dir, filename)
        tenant = db.query(User).filter(User.id == old_contract.tenant_id).first()
        prop = db.query(Property).filter(Property.id == old_contract.property_id).first()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                f"<html><body>"
                f"<h1>Contract for {prop.name}</h1>"
                f"<p>Tenant: {tenant.username} ({tenant.email})</p>"
                f"<p>Amount: {contract.amount}</p>"
                f"<p>Month: {month}/{year}</p>"
                f"</body></html>"
            )
        contract.file_path = f"/uploads/contracts/{filename}"
        db.add(contract)
        created.append(contract)
    db.commit()
    for c in created:
        db.refresh(c)
    db.close()
    return {"created": len(created)}

@router.post("/contracts/{contract_id}/admin_sign")
def admin_sign(contract_id: int, payload: dict):
    admin_id = payload.get("admin_id")
    db: Session = SessionLocal()
    if not admin_id or not is_admin(db, int(admin_id)):
        db.close()
        raise HTTPException(status_code=403, detail="admin privileges required")
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        db.close()
        raise HTTPException(status_code=404, detail="contract not found")
    contract.admin_signed_at = datetime.utcnow()
    db.add(contract)
    db.commit()
    db.refresh(contract)
    db.close()
    return {"signed": True, "contract_id": contract.id}

@router.get("/admin/year/{year}")
def year_summary(year: int):
    db: Session = SessionLocal()
    try:
        contracts = db.query(Contract).filter(Contract.year == year).all()
    except ProgrammingError:
        db.close()
        raise HTTPException(status_code=503, detail="Database tables missing; run migrations")
    result = {}
    for c in contracts:
        prop = c.property
        pid = str(prop.id)
        if pid not in result:
            result[pid] = {"property_id": prop.id, "property": prop.name, "months": {}}
        paid = sum(float(p.amount) for p in c.payments)
        month_key = str(c.month)
        if month_key not in result[pid]["months"]:
            result[pid]["months"][month_key] = []
        result[pid]["months"][month_key].append({
            "contract_id": c.id,
            "tenant": c.tenant.username,
            "tenant_id": c.tenant_id,
            "amount": float(c.amount),
            "paid": paid,
            "paid_full": paid >= float(c.amount),
            "admin_signed": c.admin_signed_at is not None,
            "tenant_signed": c.tenant_signed_at is not None,
            "file": c.file_path,
        })
    db.close()
    return result

@router.get("/admin/month/{year}/{month}")
def month_summary(year: int, month: int):
    db: Session = SessionLocal()
    try:
        contracts = db.query(Contract).filter(Contract.year == year, Contract.month == month).all()
    except ProgrammingError:
        db.close()
        raise HTTPException(status_code=503, detail="Database tables missing; run migrations")
    result = {}
    for c in contracts:
        prop = c.property
        prop_entry = result.setdefault(prop.id, {"property": prop.name, "tenants": []})
        paid = sum(float(p.amount) for p in c.payments)
        prop_entry["tenants"].append({
            "tenant": c.tenant.username,
            "amount": float(c.amount),
            "paid": paid,
            "paid_full": paid >= float(c.amount),
            "contract_id": c.id,
            "file": c.file_path,
        })
    for entry in result.values():
        entry["total_collected"] = sum(t["paid"] for t in entry["tenants"])
        entry["total_due"] = sum(t["amount"] for t in entry["tenants"])
    db.close()
    return result

@router.post("/contracts/{contract_id}/generate_token")
def generate_token(contract_id: int, payload: dict):
    admin_id = payload.get("admin_id")
    db: Session = SessionLocal()
    if not admin_id or not is_admin(db, int(admin_id)):
        raise HTTPException(status_code=403, detail="admin privileges required")
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="contract not found")
    token = uuid.uuid4().hex
    contract.tenant_token = token
    contract.token_generated_at = datetime.utcnow()
    db.add(contract)
    db.commit()
    db.refresh(contract)
    base = os.getenv("APP_BASE_URL", "http://localhost:8000")
    link = f"{base}/contracts/sign?token={token}"
    sent = False
    try:
        sent = send_signing_email(contract.tenant.email, contract.tenant.username, link)
        logger.info("Email sent=%s to=%s", sent, contract.tenant.email)
    except Exception as e:
        logger.error("Email exception: %s", e)
        sent = False
    db.close()
    return {"token": token, "link": link, "emailed": bool(sent)}

@router.get("/contracts/sign")
def sign_by_token(token: str):
    db: Session = SessionLocal()
    contract = db.query(Contract).filter(Contract.tenant_token == token).first()
    if not contract:
        raise HTTPException(status_code=404, detail="invalid token")
    contract.tenant_signed_at = datetime.utcnow()
    db.add(contract)
    db.commit()
    db.refresh(contract)
    db.close()
    return {"signed": True, "contract_id": contract.id}

@router.post("/contracts/{contract_id}/mark_paid", response_model=PaymentResponse)
def mark_paid(contract_id: int, payload: PaymentCreate):
    db: Session = SessionLocal()
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="contract not found")
    payment = Payment(
        contract_id=contract_id,
        amount=payload.amount,
        recorded_by=payload.recorded_by,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.close()
    return payment

@router.post("/contracts/{contract_id}/tenant_sign")
def tenant_sign(contract_id: int, payload: dict):
    tenant_id = payload.get("tenant_id")
    db: Session = SessionLocal()
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="contract not found")
    if tenant_id and int(tenant_id) != contract.tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    contract.tenant_signed_at = datetime.utcnow()
    db.add(contract)
    db.commit()
    db.refresh(contract)
    db.close()
    return {"signed": True}