#!/usr/bin/env python3
"""Seed test database with 10 tenants, 3 properties, 10 rooms, and monthly expenses."""

from datetime import datetime
from decimal import Decimal
import bcrypt
from app.db.database import SessionLocal
from app.models.user import User
from app.models.property import Property, HouseExpense
from app.models.room import Room
from app.models.contract import Contract, ContractMonth, Payment


def seed():
    db = SessionLocal()

    # Clear existing data
    db.query(Payment).delete()
    db.query(ContractMonth).delete()
    db.query(Contract).delete()
    db.query(HouseExpense).delete()
    db.query(Room).delete()
    db.query(Property).delete()
    db.query(User).delete()
    db.commit()

    # Create admin user
    pwd_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin = User(username="admin", email="admin@example.local", password_hash=pwd_hash, role="admin")
    db.add(admin)
    db.flush()

    # Create 10 tenants
    tenant_names = ["Juan", "Christian", "Pedro", "Diego", "Victoria", "Fernando", "Jhoana", "Elena", "Carlos", "Rosa"]
    tenants = []
    for i, name in enumerate(tenant_names):
        pwd_hash = bcrypt.hashpw(f"pass{i}123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(
            username=name.lower(),
            email=f"{name.lower()}@example.com",
            password_hash=pwd_hash,
            role="tenant",
        )
        db.add(user)
        db.flush()
        tenants.append(user)

    # Create 3 properties with 10 rooms total
    properties_data = [
        ("Ambar",   "Calle Principal 123",  8),
        ("Cabaña",  "Carretera 456",        1),
        ("Tapalpa", "Avenida Central 789",  1),
    ]

    properties = []
    for prop_name, address, num_rooms in properties_data:
        prop = Property(name=prop_name, address=address, owner_id=admin.id)
        db.add(prop)
        db.flush()
        properties.append(prop)

        for room_num in range(1, num_rooms + 1):
            room = Room(
                property_id=prop.id,
                name=str(room_num),
                default_amount=Decimal("6000.00") if prop_name == "Cabaña" else Decimal("8000.00"),
                default_pay_day=1,
                default_duration_months=12,
            )
            db.add(room)
        db.flush()

    rooms = db.query(Room).all()

    # Contracts start Jan 2026, run 12 months (Jan–Dec 2026)
    CONTRACT_START_YEAR  = 2026
    CONTRACT_START_MONTH = 1
    DURATION_MONTHS      = 12

    # Months that have passed and should show payments (up to May 2026)
    PAID_THROUGH = [(2026, m) for m in range(1, 6)]  # Jan–May

    contracts = []
    for i, room in enumerate(rooms):
        tenant = tenants[i % len(tenants)]
        contract = Contract(
            room_id=room.id,
            tenant_id=tenant.id,
            start_year=CONTRACT_START_YEAR,
            start_month=CONTRACT_START_MONTH,
            duration_months=DURATION_MONTHS,
            pay_day=5,
            amount=room.default_amount,
        )
        db.add(contract)
        db.flush()
        contracts.append(contract)

    # Create all 12 contract months; add payments only for months already past
    for contract in contracts:
        year, month = CONTRACT_START_YEAR, CONTRACT_START_MONTH
        for _ in range(DURATION_MONTHS):
            cm = ContractMonth(contract_id=contract.id, year=year, month=month)
            db.add(cm)
            db.flush()

            if (year, month) in PAID_THROUGH:
                # Simulate one room paying late (room index 3 → partial in April)
                room_idx = next(i for i, r in enumerate(rooms) if r.id == contract.room_id)
                if room_idx == 3 and (year, month) == (2026, 4):
                    # Partial payment
                    payment = Payment(
                        contract_month_id=cm.id,
                        amount=contract.amount / 2,
                        paid_at=datetime(year, month, 12),
                    )
                elif room_idx == 7 and (year, month) == (2026, 3):
                    # Late payment
                    payment = Payment(
                        contract_month_id=cm.id,
                        amount=contract.amount,
                        paid_at=datetime(year, month, 18),
                    )
                else:
                    payment = Payment(
                        contract_month_id=cm.id,
                        amount=contract.amount,
                        paid_at=datetime(year, month, 5),
                    )
                db.add(payment)

            month += 1
            if month > 12:
                month = 1
                year += 1

    # House expenses — realistic recurring + one-off items per property
    recurring_expenses = [
        ("CFE (electricidad)",     Decimal("420.00")),
        ("Agua potable",           Decimal("180.00")),
        ("Limpieza áreas comunes", Decimal("500.00")),
    ]
    one_off_expenses = {
        "Ambar": [
            ((2026, 1), "Reparación plomería cuarto 3",  Decimal("1800.00")),
            ((2026, 3), "Pintura pasillo",               Decimal("2200.00")),
            ((2026, 5), "Cambio chapa estudio 6",        Decimal("650.00")),
        ],
        "Cabaña": [
            ((2026, 2), "Mantenimiento calentador",      Decimal("900.00")),
        ],
        "Tapalpa": [
            ((2026, 4), "Reparación techo",              Decimal("3500.00")),
        ],
    }

    for prop in properties:
        # Recurring every month Jan–May
        for year, month in PAID_THROUGH:
            for desc, amount in recurring_expenses:
                db.add(HouseExpense(
                    property_id=prop.id,
                    description=desc,
                    amount=amount,
                    year=year,
                    month=month,
                    receipt_url="",
                ))
        # One-offs
        for (year, month), desc, amount in one_off_expenses.get(prop.name, []):
            db.add(HouseExpense(
                property_id=prop.id,
                description=desc,
                amount=amount,
                year=year,
                month=month,
                receipt_url="",
            ))

    db.commit()
    print("✓ Seeded: 10 tenants, 3 properties, 10 rooms")
    print("  Contracts: Jan–Dec 2026 (12 months each)")
    print("  Payments:  Jan–May 2026 (with one partial and one late for realism)")
    print("  Expenses:  recurring CFE/agua/limpieza + one-off repairs Jan–May 2026")
    db.close()


if __name__ == "__main__":
    seed()