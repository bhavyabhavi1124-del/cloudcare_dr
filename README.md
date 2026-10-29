# Safeprog — Resilient Local & Cloud-Gated Data Platform
## With Real-Time Synchronization & SHA-256 Data Integrity Engine

Safeprog is a local-first, disaster-recovery-driven relational data platform built under a **Strict AWS Free Credits and Spending-Limit Policy**.

It provides a minimal, robust local architecture with:
- **Aesthetic & Simple Web Interface**: Modern, responsive dark-mode dashboard with frosted glassmorphic UI, live tabs, toast notifications, and interactive verification controls.
- **SHA-256 Data Integrity Engine**: Cryptographic signatures per record and collective Merkle-style database state hashing. Any direct record modification or tampering is instantly recognized and visually flagged.
- **Real-Time Synchronization Resolver**: Detects database drift between live records and backup snapshots, and resolves synchronization drift with 1-click verified snapshot creation.
- **Local Relational Engine**: Embedded SQLite / PostgreSQL abstraction for customer accounts and audit ledgers.
- **Local Storage Vault**: Gzip-compressed backups with cryptographic SHA-256 integrity catalogs and retention pruning.
- **Disaster Recovery (DR) Sandbox Suite**: Automated drill runner that restores backups in temporary isolated environments, measures **Recovery Time Objective (RTO)** and **Recovery Point Objective (RPO)**, validates row parity and SHA-256 integrity, and disposes cleanly.
- **Strict AWS Approval Gate**: Programmatic lock on all cloud resources. AWS S3 and RDS are modular, optional adapters disabled by default to guarantee $0.00 unapproved spending.

---

## Strict AWS Credit & Spending-Limit Policy

This project strictly adheres to the non-negotiable credit and spending rules:
1. **Never exceed approved budget**: Default approved cloud budget is **$0.00**.
2. **Mandatory Approval Gate**: Before provisioning any cloud resource, the 7-point disclosure card must be presented:
   - Service & resource type
   - AWS region
   - Expected runtime and storage
   - Estimated cost before credits
   - Credit eligibility status
   - Possible costs not covered by credits
   - Safe shutdown and cleanup instructions
3. **No Unplanned Commitments**: No subscriptions, Savings Plans, Reserved Instances, or paid support plans.
4. **No Auto-Upgrades or Hidden Cost Traps**: Avoids NAT gateways, Application Load Balancers, public IPv4 addresses, and unmonitored stopped RDS instances (which continue billing for gp3 storage).
5. **Local Fallback Guaranteed**: The entire application, database, backup suite, and dashboard function 100% offline without requiring any cloud resources or credentials.

---

## Quickstart (Local Environment)

### Prerequisites
- Python 3.12+ (Installed in `.venv` or `venv`)

### 1. Run the Web Dashboard
```powershell
# Option A: Run with Streamlit (Interactive Healthcare DR Dashboard)
.\venv\Scripts\python.exe run.py --streamlit
# or: .\venv\Scripts\streamlit.exe run streamlit_app.py

# Option B: Run with FastAPI / Uvicorn Server
.\venv\Scripts\python.exe run.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

### 2. Command Line Operations (CLI)

Safeprog includes a full CLI controller in `run.py`:

```powershell
# Check real-time database, sync status, and SHA-256 state hashes
.\venv\Scripts\python.exe run.py --status

# Audit cryptographic SHA-256 data integrity across all customer records
.\venv\Scripts\python.exe run.py --verify

# Solve synchronization drift by creating a verified snapshot
.\venv\Scripts\python.exe run.py --sync

# Generate synthetic customer and ledger records
.\venv\Scripts\python.exe run.py --seed 50

# Create an immediate compressed SQL backup with SHA-256
.\venv\Scripts\python.exe run.py --backup

# Execute an automated sandbox disaster recovery drill
.\venv\Scripts\python.exe run.py --drill
```

### 3. Run Test Suite
```powershell
.\venv\Scripts\python.exe -m pytest tests/
```

---

## Architecture Overview

```
Safeprog/
│
├── core/
│   ├── config.py             # App configuration & budget limits
│   ├── policy.py             # Programmatic enforcement of credit policy & approval gates
│   ├── database.py           # SQLAlchemy manager, SHA-256 state hashing & sync diagnosis
│   ├── models.py             # Models with SHA-256 integrity signatures & verification
│   └── synthetic.py          # Synthetic dataset generator with automatic cryptographic signing
│
├── storage/
│   ├── base.py               # Pluggable StorageProvider interface
│   ├── local_storage.py      # Local filesystem vault with retention pruning & SHA-256 sidecars
│   └── s3_storage.py         # Optional AWS S3 adapter (locked by policy gate)
│
├── backup/
│   ├── manager.py            # Gzip compression, SHA-256 state snapshotting, and cataloging
│   └── recovery.py           # Disaster recovery runner (sandbox restore, RTO/RPO calculation)
│
├── cloud/
│   ├── approval_gate.py      # 7-point disclosure card builder
│   └── budget_estimator.py   # Free Tier & promotional credit eligibility verifier
│
├── dashboard/
│   ├── app.py                # FastAPI dashboard server & REST API (Sync, Integrity, Accounts)
│   └── templates/
│       └── index.html        # Simple & aesthetic Tailwind web interface with glassmorphism
│
├── data/                     # Local data directory
│   ├── local.db              # Primary relational SQLite database
│   └── storage_vault/        # Local simulated S3 backup vault
│
├── tests/
│   ├── test_safeprog.py      # Core unit & integration test suite
│   └── test_api.py           # Web API & synchronization verification tests
│
├── docker-compose.yml        # Multi-container setup (PostgreSQL + MinIO + App)
├── Dockerfile                # Production container spec
├── requirements.txt          # Python dependencies
└── run.py                    # Unified CLI & server launcher
```

---

## Docker Compose Setup (Optional)

When Docker Desktop or a container engine is available, Safeprog can be run with multi-container PostgreSQL and MinIO:

```bash
docker compose up -d
```
- **PostgreSQL 16**: Port `5432`
- **MinIO (Local S3)**: Port `9000` (API) / `9001` (Web Console)
- **Safeprog Dashboard**: Port `8000`
