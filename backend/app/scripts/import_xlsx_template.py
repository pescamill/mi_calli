"""Import transactions from a standard XLSX template.

The core logic accepts an injected SQLAlchemy session so it can be called
directly from a FastAPI endpoint (sharing the same DB connection/transaction).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional

import bcrypt
import pandas as pd
from sqlalchemy.orm import Session

from app.models.property import Property, HouseExpense
from app.models.room import Room
from app.models.contract import Contract, ContractMonth, Payment
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_property(db: Session, name: str, owner_id: int) -> Optional[Property]:
    if not name or pd.isna(name):
        return None
    name_clean = str(name).strip()
    prop = db.query(Property).filter(Property.name.ilike(name_clean)).first()
    if prop:
        return prop
    prop = Property(name=name_clean, address=f"Imported: {name_clean}", owner_id=owner_id)
    db.add(prop)
    db.flush()
    return prop


def _get_or_create_room(db: Session, property_id: int, room_name: str) -> Optional[Room]:
    if property_id is None or pd.isna(room_name):
        return None
    room_name_str = str(room_name).strip()
    room = db.query(Room).filter(
        Room.property_id == property_id,
        Room.name.ilike(room_name_str),
    ).first()
    if room:
        return room
    room = Room(property_id=property_id, name=room_name_str)
    db.add(room)
    db.flush()
    return room


def _get_or_create_user(db: Session, name: str, email: str) -> User:
    uname = str(name).strip()[:32] if (name and not pd.isna(name)) else f"user_{uuid.uuid4().hex[:8]}"

    if email and not pd.isna(email) and email != "-":
        user = db.query(User).filter(User.email == str(email).strip()).first()
        if user:
            return user

    user = db.query(User).filter(User.username == uname).first()
    if user:
        return user

    # Deduplicate username
    base, i = uname, 1
    while db.query(User).filter(User.username == uname).first():
        uname = f"{base}_{i}"
        i += 1

    email_val = (
        str(email).strip()
        if (email and not pd.isna(email) and email != "-")
        else f"import+{uuid.uuid4().hex}@noemail.local"
    )
    pwd_hash = bcrypt.hashpw(uuid.uuid4().hex[:32].encode(), bcrypt.gensalt()).decode()
    user = User(username=uname, email=email_val, password_hash=pwd_hash, role="tenant")
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# Main import function — accepts an injected session
# ---------------------------------------------------------------------------

def run_import(df: pd.DataFrame, db: Session, dry_run: bool = False) -> dict:
    """
    Process a DataFrame and write to the database using the provided session.
    Caller is responsible for commit/rollback.
    """
    created: list[dict] = []
    unresolved: list[dict] = []

    # Resolve owner
    owner = db.query(User).filter(User.role == "admin").first()
    if not owner:
        pwd_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        owner = User(username="admin", email="admin@example.local", password_hash=pwd_hash, role="admin")
        db.add(owner)
        db.flush()

    for idx, row in df.iterrows():
        raw = row.to_dict()
        try:
            tenant_name  = row.get("Tenant Name")
            tenant_email = row.get("Tenant Email")
            prop_name    = row.get("Property")
            room_name    = row.get("Room")
            tx_type      = str(row.get("Type") or "").strip().lower()
            amount       = row.get("Amount")
            year         = int(row.get("Year", 2024))
            month        = int(row.get("Month", 1))
            date_str     = row.get("Date")
            desc         = row.get("Description", "")

            if pd.isna(amount) or float(amount) == 0:
                unresolved.append({**raw, "reason": "no valid amount"})
                continue

            amount_dec = Decimal(str(amount))

            # Parse date
            if date_str and not pd.isna(date_str):
                try:
                    paid_at = pd.to_datetime(date_str).to_pydatetime()
                except Exception:
                    paid_at = datetime(year, month, 15)
            else:
                paid_at = datetime(year, month, 15)

            prop = _get_or_create_property(db, prop_name, owner.id)
            if not prop:
                unresolved.append({**raw, "reason": "could not create/find property"})
                continue

            if tx_type == "rent":
                if pd.isna(room_name) or room_name == "-":
                    unresolved.append({**raw, "reason": "rent requires room"})
                    continue

                room = _get_or_create_room(db, prop.id, room_name)
                if not room:
                    unresolved.append({**raw, "reason": "could not create/find room"})
                    continue

                user = _get_or_create_user(db, tenant_name, tenant_email)

                contract = db.query(Contract).filter(
                    Contract.room_id == room.id,
                    Contract.tenant_id == user.id,
                ).first()
                if not contract:
                    contract = Contract(
                        room_id=room.id,
                        tenant_id=user.id,
                        start_year=year,
                        start_month=month,
                        duration_months=12,
                        pay_day=1,
                        amount=amount_dec,
                    )
                    db.add(contract)
                    db.flush()

                cm = db.query(ContractMonth).filter(
                    ContractMonth.contract_id == contract.id,
                    ContractMonth.year == year,
                    ContractMonth.month == month,
                ).first()
                if not cm:
                    cm = ContractMonth(contract_id=contract.id, year=year, month=month)
                    db.add(cm)
                    db.flush()

                payment = Payment(contract_month_id=cm.id, amount=amount_dec, paid_at=paid_at)
                db.add(payment)
                db.flush()
                created.append({"type": "payment", "row": int(idx), "id": payment.id})

            elif tx_type == "expense":
                expense = HouseExpense(
                    property_id=prop.id,
                    description=str(desc),
                    amount=amount_dec,
                    year=year,
                    month=month,
                )
                db.add(expense)
                db.flush()
                created.append({"type": "expense", "row": int(idx), "id": expense.id})

            else:
                unresolved.append({**raw, "reason": f"unknown type: {tx_type}"})

        except Exception as row_err:
            unresolved.append({**raw, "reason": str(row_err)})
            # Flush failed — expire all pending state so the session stays usable
            db.expire_all()

    return {"created": created, "unresolved": unresolved}