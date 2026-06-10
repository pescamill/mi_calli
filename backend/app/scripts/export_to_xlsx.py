#!/usr/bin/env python3
"""Export database data to XLSX for testing."""

import pandas as pd
from datetime import datetime
from app.db.database import SessionLocal
from app.models.user import User
from app.models.property import Property
from app.models.room import Room
from app.models.contract import Contract, ContractMonth, Payment
from app.models.property import HouseExpense

def export():
    db = SessionLocal()
    
    # Get all data
    contracts = db.query(Contract).all()
    expenses = db.query(HouseExpense).all()
    
    # Build transaction rows
    rows = []
    
    # Export payments (rents)
    for contract in contracts:
        room = db.query(Room).filter(Room.id == contract.room_id).first()
        prop = db.query(Property).filter(Property.id == room.property_id).first()
        tenant = db.query(User).filter(User.id == contract.tenant_id).first()
        
        # Get contract months with payments
        contract_months = db.query(ContractMonth).filter(ContractMonth.contract_id == contract.id).all()
        for cm in contract_months:
            payment = db.query(Payment).filter(Payment.contract_month_id == cm.id).first()
            if payment:
                rows.append({
                    "Tenant Name": tenant.username,
                    "Tenant Email": tenant.email,
                    "Property": prop.name,
                    "Room": room.name,
                    "Type": "Rent",
                    "Amount": float(payment.amount),
                    "Year": cm.year,
                    "Month": cm.month,
                    "Date": payment.paid_at.strftime("%Y-%m-%d") if payment.paid_at else "",
                    "Description": f"Rent payment - Room {room.name}",
                })
    
    # Export house expenses
    for expense in expenses:
        prop = db.query(Property).filter(Property.id == expense.property_id).first()
        rows.append({
            "Tenant Name": "-",
            "Tenant Email": "-",
            "Property": prop.name,
            "Room": "-",
            "Type": "Expense",
            "Amount": float(expense.amount),
            "Year": expense.year,
            "Month": expense.month,
            "Date": expense.paid_at.strftime("%Y-%m-%d") if expense.paid_at else "",
            "Description": expense.description,
        })
    
    # Create DataFrame and export
    df = pd.DataFrame(rows)
    output_file = "uploads/test_transactions.xlsx"
    df.to_excel(output_file, index=False, sheet_name="Transactions")
    print(f"✓ Exported {len(rows)} transactions to {output_file}")
    
    db.close()

if __name__ == "__main__":
    export()
