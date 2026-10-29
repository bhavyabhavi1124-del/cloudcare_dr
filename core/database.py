"""
Database Manager & Session Handler for Safeprog
Handles connections, schema migrations, SHA-256 state tracking, and portable data dumps/restorations.
"""

import io
import hashlib
from typing import Generator, List, Dict, Any, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from core.config import settings
from core.models import Base, CustomerAccount, AuditTransaction, BackupRecord, RecoveryAudit

# Engine initialization
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(target_engine=None) -> None:
    """Creates all defined database tables and handles lightweight schema migrations."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    inspector = inspect(eng)
    try:
        columns_acc = [c["name"] for c in inspector.get_columns("customer_accounts")]
        if "integrity_hash" not in columns_acc:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE customer_accounts ADD COLUMN integrity_hash VARCHAR(64)"))
    except Exception:
        pass

    try:
        columns_bak = [c["name"] for c in inspector.get_columns("backup_records")]
        if "state_sha256" not in columns_bak:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE backup_records ADD COLUMN state_sha256 VARCHAR(64)"))
    except Exception:
        pass

    # Backfill missing integrity hashes for existing customer records
    try:
        SessionCls = sessionmaker(bind=eng)
        with SessionCls() as session:
            accounts = session.query(CustomerAccount).filter(CustomerAccount.integrity_hash.is_(None)).all()
            if accounts:
                for acc in accounts:
                    acc.sign_integrity()
                session.commit()
    except Exception:
        pass

def get_db() -> Generator[Session, None, None]:
    """Dependency helper for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def compute_database_state_hash(db_session: Session) -> str:
    """
    Computes a deterministic collective SHA-256 state hash for all accounts and transactions.
    Any addition, deletion, or field modification in the database alters this state hash.
    """
    accounts = db_session.query(CustomerAccount).order_by(CustomerAccount.account_number).all()
    txs = db_session.query(AuditTransaction).order_by(AuditTransaction.tx_hash).all()

    if not accounts and not txs:
        return hashlib.sha256(b"EMPTY_SAFEPROG_DATABASE_STATE").hexdigest()

    hasher = hashlib.sha256()
    for acc in accounts:
        # Include current field values in hash
        hasher.update(acc.calculate_integrity_hash().encode("utf-8"))
    for tx in txs:
        tx_repr = f"{tx.tx_hash}:{tx.account_number}:{tx.amount_usd:.2f}:{tx.tx_type}"
        hasher.update(tx_repr.encode("utf-8"))

    return hasher.hexdigest()

def get_sync_status(db_session: Session) -> Dict[str, Any]:
    """
    Assesses data synchronization and cryptographic SHA-256 integrity:
    1. Computes live database state hash.
    2. Compares against the latest backup's state hash.
    3. Scans for any tampered / modified records where integrity checksum fails.
    """
    current_state_hash = compute_database_state_hash(db_session)
    latest_backup = db_session.query(BackupRecord).order_by(BackupRecord.created_at.desc()).first()

    # Integrity verification across all accounts
    accounts = db_session.query(CustomerAccount).all()
    tampered_accounts = [acc for acc in accounts if not acc.is_integrity_valid()]
    tampered_count = len(tampered_accounts)

    last_synced_hash = latest_backup.state_sha256 if latest_backup else None
    
    if tampered_count > 0:
        sync_status = "TAMPERED_MODIFIED"
        is_in_sync = False
        message = f"Data modification recognized! {tampered_count} record(s) failed SHA-256 integrity check."
    elif not latest_backup:
        sync_status = "NO_BACKUP"
        is_in_sync = False
        message = "No vault backup snapshot exists. Synchronization required."
    elif last_synced_hash == current_state_hash:
        sync_status = "IN_SYNC"
        is_in_sync = True
        message = "Live database and vault backup are 100% in sync with matching SHA-256 state hashes."
    else:
        sync_status = "DRIFT_DETECTED"
        is_in_sync = False
        message = "Live database state has drifted from the last backup. Synchronization required."

    return {
        "sync_status": sync_status,
        "is_in_sync": is_in_sync,
        "message": message,
        "current_state_hash": current_state_hash,
        "last_synced_hash": last_synced_hash,
        "latest_backup_id": latest_backup.backup_id if latest_backup else None,
        "latest_backup_at": latest_backup.created_at.isoformat() if latest_backup else None,
        "tampered_count": tampered_count,
        "tampered_accounts": [
            {
                "id": acc.id,
                "account_number": acc.account_number,
                "owner_name": acc.owner_name,
                "balance_usd": acc.balance_usd,
                "account_status": acc.account_status,
                "stored_hash": acc.integrity_hash,
                "calculated_hash": acc.calculate_integrity_hash()
            }
            for acc in tampered_accounts
        ]
    }

def verify_all_records_integrity(db_session: Session) -> Dict[str, Any]:
    """Scans all customer accounts and tests cryptographic SHA-256 checksums."""
    accounts = db_session.query(CustomerAccount).order_by(CustomerAccount.id.asc()).all()
    total = len(accounts)
    valid = 0
    tampered = []

    for acc in accounts:
        if acc.is_integrity_valid():
            valid += 1
        else:
            tampered.append({
                "id": acc.id,
                "account_number": acc.account_number,
                "owner_name": acc.owner_name,
                "email": acc.email,
                "balance_usd": acc.balance_usd,
                "account_status": acc.account_status,
                "stored_hash": acc.integrity_hash,
                "calculated_hash": acc.calculate_integrity_hash(),
                "integrity_valid": False
            })

    rate = 100.0 if total == 0 else round((valid / total) * 100, 1)

    return {
        "total_records": total,
        "valid_records": valid,
        "tampered_records_count": len(tampered),
        "integrity_rate_pct": rate,
        "tampered_records": tampered
    }

def export_portable_sql_dump(db_session: Session) -> str:
    """
    Exports a clean, dialect-agnostic portable SQL dump containing schema definitions
    and all data for CustomerAccount and AuditTransaction tables, including SHA-256 checksums.
    """
    output = io.StringIO()
    output.write("-- Safeprog Portable Database Dump\n")
    output.write(f"-- Generated: {settings.PROJECT_NAME}\n\n")

    # 1. Accounts
    accounts = db_session.query(CustomerAccount).all()
    output.write(f"-- Table: customer_accounts ({len(accounts)} rows)\n")
    for acc in accounts:
        name_esc = acc.owner_name.replace("'", "''")
        email_esc = acc.email.replace("'", "''")
        dt_str = acc.created_at.isoformat()
        hash_val = f"'{acc.integrity_hash}'" if acc.integrity_hash else "NULL"
        output.write(
            f"INSERT INTO customer_accounts (account_number, owner_name, email, balance_usd, account_status, integrity_hash, created_at) "
            f"VALUES ('{acc.account_number}', '{name_esc}', '{email_esc}', {acc.balance_usd}, '{acc.account_status}', {hash_val}, '{dt_str}');\n"
        )
    output.write("\n")

    # 2. Transactions
    transactions = db_session.query(AuditTransaction).all()
    output.write(f"-- Table: audit_transactions ({len(transactions)} rows)\n")
    for tx in transactions:
        if tx.memo:
            escaped_memo = tx.memo.replace("'", "''")
            memo_val = f"'{escaped_memo}'"
        else:
            memo_val = "NULL"
        dt_str = tx.timestamp.isoformat()
        output.write(
            f"INSERT INTO audit_transactions (tx_hash, account_number, amount_usd, tx_type, memo, timestamp) "
            f"VALUES ('{tx.tx_hash}', '{tx.account_number}', {tx.amount_usd}, '{tx.tx_type}', {memo_val}, '{dt_str}');\n"
        )
    output.write("\n")

    return output.getvalue()

def get_database_metrics(db_session: Session) -> Dict[str, Any]:
    """Returns real-time metrics on database records, synchronization state, and operational health."""
    account_count = db_session.query(CustomerAccount).count()
    tx_count = db_session.query(AuditTransaction).count()
    backup_count = db_session.query(BackupRecord).count()
    audit_count = db_session.query(RecoveryAudit).count()
    
    sync_info = get_sync_status(db_session)

    # Calculate approximate size
    db_size_kb = 0.0
    if "sqlite" in settings.DATABASE_URL:
        db_file = settings.DATA_DIR / "local.db"
        if db_file.exists():
            db_size_kb = round(db_file.stat().st_size / 1024, 2)
    
    return {
        "engine": "SQLite (Local Simulation)" if "sqlite" in settings.DATABASE_URL else "PostgreSQL",
        "url_masked": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
        "customer_accounts_count": account_count,
        "audit_transactions_count": tx_count,
        "backups_recorded": backup_count,
        "dr_tests_recorded": audit_count,
        "total_records": account_count + tx_count,
        "database_size_kb": db_size_kb,
        "sync_status": sync_info["sync_status"],
        "is_in_sync": sync_info["is_in_sync"],
        "sync_message": sync_info["message"],
        "current_state_hash": sync_info["current_state_hash"],
        "last_synced_hash": sync_info["last_synced_hash"],
        "tampered_count": sync_info["tampered_count"]
    }
