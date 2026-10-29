import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

STORAGE_VAULT_DIR = DATA_DIR / "storage_vault"
STORAGE_VAULT_DIR.mkdir(exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "Safeprog - Resilient Local & Cloud-Gated Data Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    
    # Database Settings
    # Default to robust local SQLite; can switch to PostgreSQL URL when available
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{DATA_DIR / 'local.db'}"
    )
    RESTORE_TEST_DB_URL: str = os.getenv(
        "RESTORE_TEST_DB_URL",
        f"sqlite:///{DATA_DIR / 'test_restore.db'}"
    )
    
    # Storage Settings
    STORAGE_MODE: str = os.getenv("STORAGE_MODE", "LOCAL")  # "LOCAL" or "S3"
    LOCAL_STORAGE_PATH: Path = STORAGE_VAULT_DIR
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))
    
    # AWS Policy & Budget Guardrails
    AWS_POLICY_ENFORCED: bool = True
    AWS_PROVISIONING_LOCKED: bool = True
    AWS_APPROVED_BUDGET_USD: float = float(os.getenv("AWS_APPROVED_BUDGET_USD", "0.00"))
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME", "safeprog-backup-vault-unapproved")
    
    # Server Settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()
