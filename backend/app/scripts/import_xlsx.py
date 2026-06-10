#!/usr/bin/env python3
"""Import transactions from an XLSX ledger into the DB.

This is a full bootstrap importer: it will create Properties, Rooms, Users, and Contracts 
from the ledger data, then populate Payments and HouseExpenses.

Usage:
    python import_xlsx.py --file uploads/Ambar.xlsx           # live run (commits)
    python import_xlsx.py --file uploads/Ambar.xlsx --dry-run # validate only
"""
from __future__ import annotations

import argparse
import csv
import os
import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime

import pandas as pd
import bcrypt

from app.db.database import SessionLocal
from app.models.property import Property, HouseExpense
from app.models.room import Room
from app.models.contract import Contract, ContractMonth, Payment
from app.models.user import User


def normalize_col(c: str) -> str:
    return c.strip().lower()


def get_or_create_property(db, name: str, owner_id: int) -> Optional[Property]:
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


def get_or_create_room(db, property_id: int, estudio_name: str) -> Optional[Room]:
    if property_id is None or pd.isna(estudio_name):
        return None
    s = str(int(estudio_name)) if (isinstance(estudio_name, (int, float)) and not pd.isna(estudio_name)) else str(estudio_name).strip()
    room = db.query(Room).filter(Room.property_id == property_id, Room.name.ilike(s)).first()
    if room:
        return room
    room = Room(property_id=property_id, name=s)
    db.add(room)
    db.flush()
    return room


def get_or_create_user(db, name: str, email: Optional[str] = None) -> User:
    uname = str(name).strip()[:32] if name and not pd.isna(name) else f'user_{uuid.uuid4().hex[:8]}'

    if email and not pd.isna(email):
        user = db.query(User).filter(User.email == email.strip()).first()
        if user:
            return user

    user = db.query(User).filter(User.username == uname).first()
    if user:
        return user

    base = uname
    i = 1
    while db.query(User).filter(User.username == uname).first():
        uname = f"{base}_{i}"
        i += 1

    placeholder_email = email if (email and not pd.isna(email)) else f"import+{uuid.uuid4().hex}@noemail.local"
    pwd = uuid.uuid4().hex[:32]
    pwd_hash = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(username=uname, email=placeholder_email, password_hash=pwd_hash, role="tenant")
    db.add(user)
    db.flush()
    return user


def get_or_create_contract(db, room_id: int, tenant_id: int, start_year: int, start_month: int, amount: Decimal) -> Contract:
    contract = db.query(Contract).filter(
        Contract.room_id == room_id,
        Contract.tenant_id == tenant_id,
        Contract.start_year == start_year,
        Contract.start_month == start_month,
    ).first()
    if contract:
        return contract
    contract = Contract(
        room_id=room_id,
        tenant_id=tenant_id,
        start_year=start_year,
        start_month=start_month,
        duration_months=12,
        pay_day=1,
        amount=amount,
    )
    db.add(contract)
    db.flush()
    return contract


def get_or_create_contract_month(db, contract: Contract, year: int, month: int) -> ContractMonth:
    cm = db.query(ContractMonth).filter(
        ContractMonth.contract_id == contract.id,
        ContractMonth.year == year,
        ContractMonth.month == month
    ).first()
    if cm:
        return cm
    cm = ContractMonth(contract_id=contract.id, year=year, month=month)
    db.add(cm)
    db.flush()
    return cm


def parse_and_import(path: str, dry_run: bool = False):
    df = pd.read_excel(path)
    df.columns = [normalize_col(c) for c in df.columns]

    unresolved = []
    created = []

    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.role == "admin").first()
        if not owner:
            pwd_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            owner = User(username="admin", email="admin@example.local", password_hash=pwd_hash, role="admin")
            db.add(owner)
            db.flush()

        for idx, row in df.iterrows():
            raw = row.to_dict()

            try:
                started = None
                if 'hora de inicio' in row.index:
                    try:
                        started = pd.to_datetime(row['hora de inicio'], dayfirst=False)
                    except Exception:
                        started = None

                correo = row.get('correo electrónico')
                nombre = row.get('operador')
                ubicacion = row.get('ubicacion')
                estudio = row.get('estudio no')
                concepto = str(row.get('concepto') or '').strip()
                ingreso = row.get('ingreso')
                egreso = row.get('egreso')
                observ = row.get('observaciones')

                amount = None
                is_income = False
                try:
                    if pd.notna(ingreso) and float(ingreso) != 0:
                        amount = Decimal(str(ingreso))
                        is_income = True
                    elif pd.notna(egreso) and float(egreso) != 0:
                        amount = Decimal(str(egreso))
                        is_income = False
                except (ValueError, TypeError):
                    pass

                if amount is None or amount == 0:
                    unresolved.append({**raw, 'reason': 'no valid amount'})
                    continue

                prop = get_or_create_property(db, ubicacion, owner.id)
                if not prop:
                    unresolved.append({**raw, 'reason': 'could not create/find property'})
                    continue

                estudio_str = str(estudio).strip().lower() if pd.notna(estudio) else ""
                PROPERTY_LEVEL_KEYWORDS = {
                    "general", "gral", "sueldo", "basura", "terraza",
                    "product limpieza para áreas comunes y estudios sucios",
                    "pago gas", "pago renta general", "sueldo limpieza",
                    "pago sueldo chris", "cerrajería estudio 16",
                }
                if estudio_str in PROPERTY_LEVEL_KEYWORDS:
                    room = None
                else:
                    room = get_or_create_room(db, prop.id, estudio)

                user = get_or_create_user(db, nombre, correo)
                concepto_lower = concepto.lower()

                if "renta" in concepto_lower:
                    if not room or not user:
                        unresolved.append({**raw, 'reason': 'no room or user for rent'})
                        continue

                    paid_at = started.to_pydatetime() if (started is not None and hasattr(started, 'to_pydatetime')) else (started if started else datetime.utcnow())
                    year = paid_at.year
                    month = paid_at.month

                    contract = get_or_create_contract(db, room.id, user.id, year, month, amount)
                    cm = get_or_create_contract_month(db, contract, year, month)
                    p = Payment(contract_month_id=cm.id, amount=amount, paid_at=paid_at)
                    db.add(p)
                    db.flush()
                    created.append({'type': 'payment', 'row': int(idx), 'id': p.id})

                elif "deposito" in concepto_lower or "apartado" in concepto_lower or "devolución" in concepto_lower:
                    y = started.year if started else 1
                    m = started.month if started else 1
                    he = HouseExpense(
                        property_id=prop.id,
                        description=f"{concepto} ({nombre})",
                        amount=amount if not is_income else -amount,
                        year=y,
                        month=m,
                        receipt_url=str(observ or ''),
                    )
                    db.add(he)
                    db.flush()
                    created.append({'type': 'house_expense_deposit', 'row': int(idx), 'id': he.id})

                elif any(kw in concepto_lower for kw in (
                    "mantenimiento", "servicios", "otros", "reparación", "herrero",
                    "madera", "pago", "cerrajería", "limpieza", "basura", "gas",
                    "pilas", "chapa",
                )):
                    y = started.year if started else 1
                    m = started.month if started else 1
                    he = HouseExpense(
                        property_id=prop.id,
                        description=f"{concepto} - {observ or ''}",
                        amount=amount,
                        year=y,
                        month=m,
                        receipt_url=str(row.get('destino') or ''),
                    )
                    db.add(he)
                    db.flush()
                    created.append({'type': 'house_expense', 'row': int(idx), 'id': he.id})

                else:
                    if not is_income and prop:
                        y = started.year if started else 1
                        m = started.month if started else 1
                        he = HouseExpense(
                            property_id=prop.id,
                            description=concepto,
                            amount=amount,
                            year=y,
                            month=m,
                            receipt_url=str(observ or ''),
                        )
                        db.add(he)
                        db.flush()
                        created.append({'type': 'house_expense_other', 'row': int(idx), 'id': he.id})
                    else:
                        unresolved.append({**raw, 'reason': f'unhandled concept: {concepto}'})

            except Exception as row_err:
                # Per-row error: log and continue instead of aborting the whole import
                unresolved.append({**raw, 'reason': f'row error: {row_err}'})
                db.rollback()  # Roll back only the failed flush, then continue

        if dry_run:
            print("DRY RUN — rolling back, nothing written.")
            db.rollback()
        else:
            db.commit()
            print("Committed to database.")

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

    success_path = 'import_created.csv'
    with open(success_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['type', 'row', 'id'])
        w.writeheader()
        for r in created:
            w.writerow(r)

    unresolved_path = 'import_unresolved.csv'
    if unresolved:
        keys = list(unresolved[0].keys())
        with open(unresolved_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in unresolved:
                w.writerow(r)

    result = {
        "created": len(created),
        "unresolved": len(unresolved),
        "created_csv": success_path,
        "unresolved_csv": unresolved_path,
    }
    print(f"Done. created={result['created']}, unresolved={result['unresolved']}")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', '-f', required=True, help='Path to XLSX file')
    # FIX: use store_true with default=False so omitting the flag means live run
    p.add_argument('--dry-run', action='store_true', default=False,
                   help='Validate only, do not commit (default: False)')
    args = p.parse_args()

    if not os.path.exists(args.file):
        print('file not found:', args.file)
        return

    parse_and_import(args.file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()