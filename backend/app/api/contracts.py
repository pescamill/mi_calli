from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
import os
from datetime import datetime

from app.db.database import SessionLocal
from app.models import User, Property, Contract, Payment
from app.schemas.contract import ContractCreate, ContractResponse
from app.schemas.payment import PaymentCreate, PaymentResponse

router = APIRouter()


@router.post("/admin/generate_reminders")
def generate_reminders(payload: dict):
    """Generate contracts for given year/month. Payload: {"year":2026,"month":5}
    If not provided, uses current month.
    """
    year = payload.get("year") or datetime.utcnow().year
    month = payload.get("month") or datetime.utcnow().month

    db: Session = SessionLocal()

    properties = db.query(Property).all()
    created = []
    for prop in properties:
        rent = getattr(prop, "rent_amount", None) or 6000
        tenants = db.query(User).filter(User.property_id == prop.id, User.role == "tenant").all()
        for tenant in tenants:
            exists = db.query(Contract).filter(
                Contract.property_id == prop.id,
                Contract.tenant_id == tenant.id,
                Contract.year == year,
                Contract.month == month,
            ).first()
            if exists:
                continue

            contract = Contract(
                property_id=prop.id,
                tenant_id=tenant.id,
                year=year,
                month=month,
                amount=rent,
            )
            db.add(contract)
            db.flush()

            # generate simple contract HTML
            uploads_dir = os.path.abspath("uploads/contracts")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = f"contract_{contract.id}.html"
            file_path = os.path.join(uploads_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"<html><body><h1>Contract for {prop.name}</h1><p>Tenant: {tenant.username} ({tenant.email})</p><p>Amount: {rent}</p><p>Month: {month}/{year}</p></body></html>")

            contract.file_path = f"/uploads/contracts/{filename}"
            db.add(contract)
            created.append(contract)

    db.commit()
    for c in created:
        db.refresh(c)
    db.close()

    return {"created": len(created)}


@router.get("/admin/month/{year}/{month}")
def month_summary(year: int, month: int):
    db: Session = SessionLocal()
    contracts = db.query(Contract).filter(Contract.year == year, Contract.month == month).all()
    result = {}
    for c in contracts:
        prop = c.property
        prop_entry = result.setdefault(prop.id, {"property": prop.name, "tenants": []})
        paid = sum([float(p.amount) for p in c.payments])
        prop_entry["tenants"].append({
            "tenant": c.tenant.username,
            "amount": float(c.amount),
            "paid": paid,
            "paid_full": paid >= float(c.amount),
            "contract_id": c.id,
            "file": c.file_path,
        })

    # compute totals per property
    for pid, entry in result.items():
        total_collected = sum(t["paid"] for t in entry["tenants"])
        total_due = sum(t["amount"] for t in entry["tenants"])
        entry["total_collected"] = total_collected
        entry["total_due"] = total_due

    db.close()
    return result


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
    # minimal signing: record tenant_signed_at when tenant provides their id (or token)
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
