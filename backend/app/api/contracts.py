from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
import os
import calendar
from datetime import datetime
import uuid
import logging
import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.db.database import SessionLocal
from app.models import User, Property, Room, Contract, ContractMonth, Payment
from app.schemas.contract import ContractCreate, ContractResponse, PaymentCreate, PaymentResponse
from sqlalchemy.exc import ProgrammingError

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def is_admin(db: Session, admin_id: int) -> bool:
    admin = db.query(User).filter(User.id == admin_id).first()
    return bool(admin and admin.role == "admin")


def effective_pay_day(pay_day: int, year: int, month: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    return min(pay_day, last_day)


def send_email(to_emails: list, subject: str, html: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_password:
        logger.warning("SMTP not configured, skipping email")
        return False

    success = True
    for recipient in to_emails:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = recipient
            msg.add_alternative(html, subtype="html")
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_password)
                s.send_message(msg)
            logger.info("Email sent to %s", recipient)
        except Exception as e:
            logger.error("Failed to send email to %s: %s", recipient, e)
            success = False
    return success


def generate_month_pdf(contract_month: ContractMonth, contract: Contract, tenant: User, room: Room, prop: Property) -> str:
    uploads_dir = os.path.abspath("uploads/contracts")
    os.makedirs(uploads_dir, exist_ok=True)
    filename = f"contract_{contract.id}_month_{contract_month.year}_{contract_month.month}.pdf"
    file_path = os.path.join(uploads_dir, filename)

    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("RENTAL CONTRACT", styles['Title']))
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"Property: {prop.name}", styles['Normal']))
    story.append(Paragraph(f"Address: {prop.address}", styles['Normal']))
    story.append(Paragraph(f"Room: {room.name}", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Tenant: {tenant.username}", styles['Normal']))
    story.append(Paragraph(f"Email: {tenant.email}", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Month: {contract_month.month}/{contract_month.year}", styles['Normal']))
    story.append(Paragraph(f"Pay day: {contract.pay_day} of each month", styles['Normal']))
    story.append(Paragraph(f"Amount due: ${contract.amount}", styles['Normal']))
    story.append(Spacer(1, 12))
    if contract.inventory:
        story.append(Paragraph(f"Inventory: {contract.inventory}", styles['Normal']))
        story.append(Spacer(1, 12))
    story.append(Paragraph(
        "By submitting the signing form, the tenant agrees to the terms above.",
        styles['Normal']
    ))

    doc.build(story)
    return f"/uploads/contracts/{filename}"


def create_contract_months(contract: Contract, db: Session, tenant: User, room: Room, prop: Property):
    """Create all ContractMonth rows for the contract duration."""
    year = contract.start_year
    month = contract.start_month
    for i in range(contract.duration_months):
        cm = ContractMonth(
            contract_id=contract.id,
            year=year,
            month=month,
        )
        db.add(cm)
        db.flush()
        cm.file_path = generate_month_pdf(cm, contract, tenant, room, prop)
        db.add(cm)
        # Advance month
        month += 1
        if month > 12:
            month = 1
            year += 1


@router.post("/contracts", response_model=ContractResponse)
def create_contract(data: ContractCreate):
    db: Session = SessionLocal()
    room = db.query(Room).filter(Room.id == data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="room not found")
    prop = db.query(Property).filter(Property.id == room.property_id).first()
    tenant = db.query(User).filter(User.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")
    if tenant.role != "tenant":
        raise HTTPException(status_code=400, detail="user is not a tenant")

    # Check room not already occupied
    active = db.query(Contract).filter(
        Contract.room_id == data.room_id,
        Contract.terminated_at == None
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="room already has an active contract")

    contract = Contract(
        room_id=data.room_id,
        tenant_id=data.tenant_id,
        start_year=data.start_year,
        start_month=data.start_month,
        duration_months=data.duration_months,
        pay_day=data.pay_day,
        amount=data.amount,
        inventory=data.inventory,
    )
    db.add(contract)
    db.flush()
    create_contract_months(contract, db, tenant, room, prop)
    db.commit()
    db.refresh(contract)
    db.close()
    return contract


@router.get("/contracts", response_model=list[ContractResponse])
def get_contracts(room_id: int | None = None):
    db: Session = SessionLocal()
    query = db.query(Contract)
    if room_id:
        query = query.filter(Contract.room_id == room_id)
    contracts = query.all()
    db.close()
    return contracts


@router.post("/contracts/{contract_id}/terminate")
def terminate_contract(contract_id: int, payload: dict):
    admin_id = payload.get("admin_id")
    db: Session = SessionLocal()
    if not admin_id or not is_admin(db, int(admin_id)):
        db.close()
        raise HTTPException(status_code=403, detail="admin privileges required")
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        db.close()
        raise HTTPException(status_code=404, detail="contract not found")

    today = datetime.utcnow()
    contract.terminated_at = today

    # Delete future unpaid months
    for cm in contract.months:
        if (cm.year, cm.month) > (today.year, today.month):
            db.delete(cm)
        elif cm.year == today.year and cm.month == today.month:
            # Keep current month
            pass

    # Notify tenant and owner
    room = contract.room
    prop = db.query(Property).filter(Property.id == room.property_id).first()
    tenant = contract.tenant
    owner = db.query(User).filter(User.id == prop.owner_id).first()
    recipients = [r.email for r in [tenant, owner] if r and r.email]
    send_email(
        recipients,
        f"Contract terminated — {prop.name} / {room.name}",
        f"""
        <p>Hi,</p>
        <p>The rental contract for <strong>{room.name}</strong> at <strong>{prop.name}</strong> has been terminated.</p>
        <p>Tenant: <strong>{tenant.username}</strong></p>
        <p>Termination date: <strong>{today.strftime('%B %d, %Y')}</strong></p>
        """
    )

    db.commit()
    db.close()
    return {"terminated": True}


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
    return {"signed": True}


@router.post("/contracts/{contract_id}/generate_token")
def generate_token(contract_id: int, payload: dict):
    admin_id = payload.get("admin_id")
    db: Session = SessionLocal()
    if not admin_id or not is_admin(db, int(admin_id)):
        db.close()
        raise HTTPException(status_code=403, detail="admin privileges required")
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        db.close()
        raise HTTPException(status_code=404, detail="contract not found")
    token = uuid.uuid4().hex
    contract.tenant_token = token if hasattr(contract, 'tenant_token') else None

    # Send email with first month PDF
    first_month = contract.months[0] if contract.months else None
    form_url = os.getenv("GOOGLE_FORM_URL", "")
    base = os.getenv("APP_BASE_URL", "http://localhost")
    pdf_url = f"{base}{first_month.file_path}" if first_month and first_month.file_path else ""

    sent = send_email(
        [contract.tenant.email],
        "Please sign your rent contract",
        f"""
        <p>Hello {contract.tenant.username},</p>
        <p>Your rental contract is ready.</p>
        <ol>
            <li><a href='{pdf_url}'>View your contract (PDF)</a></li>
            <li><a href='{form_url}'>Sign the contract</a></li>
        </ol>
        <p>Your Contract ID is: <strong>{contract.id}</strong></p>
        """
    )
    db.close()
    return {"emailed": bool(sent), "contract_id": contract.id}


@router.post("/contracts/sign/confirm")
def sign_confirm(payload: dict):
    contract_id = payload.get("contract_id")
    if not contract_id:
        raise HTTPException(status_code=400, detail="contract_id required")
    db: Session = SessionLocal()
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        db.close()
        raise HTTPException(status_code=404, detail="contract not found")
    contract.tenant_signed_at = datetime.utcnow()
    db.add(contract)
    db.commit()
    db.close()
    return {"signed": True}


@router.post("/contract_months/{month_id}/mark_paid", response_model=PaymentResponse)
def mark_paid(month_id: int, payload: PaymentCreate):
    db: Session = SessionLocal()
    cm = db.query(ContractMonth).filter(ContractMonth.id == month_id).first()
    if not cm:
        raise HTTPException(status_code=404, detail="contract month not found")
    payment = Payment(
        contract_month_id=month_id,
        amount=float(payload.amount),
        recorded_by=payload.recorded_by,
        receipt_url=payload.receipt_url,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.close()
    return payment


@router.get("/admin/year/{year}")
def year_summary(year: int):
    db: Session = SessionLocal()
    try:
        months = db.query(ContractMonth).filter(ContractMonth.year == year).all()
    except ProgrammingError:
        db.close()
        raise HTTPException(status_code=503, detail="Database tables missing")

    result = {}
    for cm in months:
        contract = cm.contract
        if contract.terminated_at:
            continue
        room = contract.room
        prop = db.query(Property).filter(Property.id == room.property_id).first()
        pid = str(prop.id)
        if pid not in result:
            result[pid] = {"property_id": prop.id, "property": prop.name, "months": {}}
        paid = round(sum(float(p.amount) for p in cm.payments), 2)
        amount = round(float(contract.amount), 2)
        month_key = str(cm.month)
        if month_key not in result[pid]["months"]:
            result[pid]["months"][month_key] = []
        result[pid]["months"][month_key].append({
            "contract_month_id": cm.id,
            "contract_id": contract.id,
            "room": room.name,
            "tenant": contract.tenant.username,
            "tenant_id": contract.tenant_id,
            "amount": amount,
            "paid": paid,
            "paid_full": paid >= amount,
            "admin_signed": contract.admin_signed_at is not None,
            "tenant_signed": contract.tenant_signed_at is not None,
            "pay_day": contract.pay_day,
            "expires": f"{contract.start_month + contract.duration_months - 1 if contract.start_month + contract.duration_months - 1 <= 12 else (contract.start_month + contract.duration_months - 1) % 12}/{contract.start_year + (contract.start_month + contract.duration_months - 2) // 12}",
            "file": cm.file_path,
        })
    db.close()
    return result