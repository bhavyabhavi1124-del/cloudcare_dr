"""
Synthetic Data Generator for Safeprog
Generates deterministic or random synthetic business entities to simulate workload.
"""

import uuid
import random
from datetime import timedelta
from sqlalchemy.orm import Session
from core.models import CustomerAccount, AuditTransaction, utc_now

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Evan", "Fiona", "George", "Hannah", "Ian", "Julia"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]
TX_TYPES = ["DEPOSIT", "WITHDRAWAL", "PAYMENT", "TRANSFER", "REFUND"]

def generate_synthetic_data(db_session: Session, count: int = 50) -> dict:
    """
    Generates synthetic customer accounts and corresponding audit transactions.
    """
    created_accounts = []
    for _ in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        acc_num = f"ACC-{uuid.uuid4().hex[:8].upper()}"
        email = f"{first.lower()}.{last.lower()}.{random.randint(100, 999)}@example.com"
        initial_balance = round(random.uniform(50.0, 15000.0), 2)
        created_date = utc_now() - timedelta(days=random.randint(1, 180))

        account = CustomerAccount(
            account_number=acc_num,
            owner_name=full_name,
            email=email,
            balance_usd=initial_balance,
            account_status="ACTIVE",
            created_at=created_date
        )
        account.sign_integrity()
        db_session.add(account)
        created_accounts.append(account)
    
    db_session.flush()

    # Generate 1 to 3 transactions for each created account
    created_txs = 0
    for acc in created_accounts:
        for _ in range(random.randint(1, 3)):
            amount = round(random.uniform(5.0, 1200.0), 2)
            tx_type = random.choice(TX_TYPES)
            tx = AuditTransaction(
                tx_hash=f"0x{uuid.uuid4().hex}",
                account_number=acc.account_number,
                amount_usd=amount,
                tx_type=tx_type,
                memo=f"Synthetic {tx_type.lower()} simulation batch",
                timestamp=acc.created_at + timedelta(hours=random.randint(1, 72))
            )
            db_session.add(tx)
            created_txs += 1

    db_session.commit()

    return {
        "accounts_created": len(created_accounts),
        "transactions_created": created_txs,
        "total_generated": len(created_accounts) + created_txs
    }

def clear_all_synthetic_data(db_session: Session) -> dict:
    """Clears customer data and transactions while preserving audit and backup logs."""
    tx_deleted = db_session.query(AuditTransaction).delete()
    acc_deleted = db_session.query(CustomerAccount).delete()
    db_session.commit()
    return {
        "accounts_deleted": acc_deleted,
        "transactions_deleted": tx_deleted
    }
