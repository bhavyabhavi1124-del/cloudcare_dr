"""
SQLAlchemy Data Models for Safeprog
Represents synthetic business entities and backup/recovery audit registries
with SHA-256 data integrity and modification recognition.
"""

from datetime import datetime, timezone
import hashlib
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def compute_account_sha256(account_number: str, owner_name: str, email: str, balance_usd: float, account_status: str) -> str:
    """Computes a deterministic SHA-256 data integrity hash for account data."""
    payload = f"{account_number.strip()}|{owner_name.strip()}|{email.strip().lower()}|{balance_usd:.2f}|{account_status.strip().upper()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

class CustomerAccount(Base):
    """Synthetic customer entity with cryptographic SHA-256 integrity verification."""
    __tablename__ = "customer_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_number = Column(String(64), unique=True, nullable=False, index=True)
    owner_name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    balance_usd = Column(Float, default=0.0, nullable=False)
    account_status = Column(String(32), default="ACTIVE", nullable=False)
    integrity_hash = Column(String(64), nullable=True)  # SHA-256 integrity baseline
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def calculate_integrity_hash(self) -> str:
        """Calculates current SHA-256 hash of the record's mutable data fields."""
        return compute_account_sha256(
            self.account_number,
            self.owner_name,
            self.email,
            self.balance_usd,
            self.account_status
        )

    def is_integrity_valid(self) -> bool:
        """Returns True if current data fields match the registered SHA-256 integrity baseline."""
        if not self.integrity_hash:
            return False
        return self.calculate_integrity_hash() == self.integrity_hash

    def sign_integrity(self) -> str:
        """Recalculates and stamps the integrity_hash with current data."""
        self.integrity_hash = self.calculate_integrity_hash()
        return self.integrity_hash

class AuditTransaction(Base):
    """Synthetic ledger/audit transaction records."""
    __tablename__ = "audit_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(String(64), unique=True, nullable=False, index=True)
    account_number = Column(String(64), nullable=False, index=True)
    amount_usd = Column(Float, nullable=False)
    tx_type = Column(String(32), nullable=False)  # CREDIT, DEBIT, TRANSFER
    memo = Column(String(256), nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

class BackupRecord(Base):
    """Tracks backup artifacts created, their checksums, sizes, and locations."""
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    backup_id = Column(String(64), unique=True, nullable=False, index=True)
    storage_provider = Column(String(32), nullable=False)  # LOCAL or S3
    file_path = Column(String(512), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    state_sha256 = Column(String(64), nullable=True)  # Database state SHA-256 at snapshot time
    total_records = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(String(32), default="COMPLETED", nullable=False)
    verified = Column(Boolean, default=False, nullable=False)

class RecoveryAudit(Base):
    """Tracks disaster recovery tests, restore performance (RTO/RPO), and integrity checks."""
    __tablename__ = "recovery_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(64), unique=True, nullable=False, index=True)
    backup_id = Column(String(64), nullable=False)
    test_timestamp = Column(DateTime, default=utc_now, nullable=False)
    rto_seconds = Column(Float, nullable=False)  # Recovery Time Objective (duration)
    records_restored = Column(Integer, nullable=False)
    integrity_verified = Column(Boolean, nullable=False)
    details = Column(Text, nullable=True)
