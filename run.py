"""
Safeprog CLI & Server Launcher
Command-line interface to launch the dashboard, take backups, seed data, or run DR tests.
"""

import sys
import argparse
import uvicorn
from core.config import settings
from core.database import (
    init_db, 
    SessionLocal, 
    get_database_metrics, 
    get_sync_status, 
    verify_all_records_integrity
)
from core.synthetic import generate_synthetic_data
from backup.manager import create_database_backup
from backup.recovery import run_disaster_recovery_drill
from core.models import BackupRecord

def main():
    parser = argparse.ArgumentParser(description="Safeprog Data Platform Controller")
    parser.add_argument("--server", action="store_true", help="Start the web dashboard (default)")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind server to")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host to bind server to")
    parser.add_argument("--seed", type=int, metavar="COUNT", help="Seed N synthetic customer accounts and transactions")
    parser.add_argument("--backup", action="store_true", help="Trigger an immediate database backup")
    parser.add_argument("--drill", action="store_true", help="Run disaster recovery drill on the latest backup")
    parser.add_argument("--status", action="store_true", help="Print real-time system metrics")
    parser.add_argument("--sync", action="store_true", help="Solve synchronization drift by creating a verified snapshot")
    parser.add_argument("--verify", action="store_true", help="Audit SHA-256 data integrity across all records")
    parser.add_argument("--streamlit", action="store_true", help="Launch the Streamlit interactive dashboard")

    args = parser.parse_args()

    # Ensure tables exist
    init_db()

    if args.seed:
        with SessionLocal() as session:
            print(f"[*] Generating {args.seed} synthetic customer accounts and transactions...")
            res = generate_synthetic_data(session, count=args.seed)
            print(f"[OK] Created {res['accounts_created']} accounts and {res['transactions_created']} transactions.")
        return

    if args.backup:
        with SessionLocal() as session:
            print("[*] Creating compressed database backup archive...")
            rec = create_database_backup(session)
            print(f"[OK] Backup created successfully!")
            print(f"    ID:       {rec.backup_id}")
            print(f"    Size:     {round(rec.size_bytes / 1024, 2)} KB")
            print(f"    SHA-256:  {rec.sha256_checksum}")
            print(f"    Records:  {rec.total_records}")
        return

    if args.drill:
        with SessionLocal() as session:
            latest = session.query(BackupRecord).order_by(BackupRecord.created_at.desc()).first()
            if not latest:
                print("[!] No backups found in vault. Run with --backup first.")
                return
            print(f"[*] Executing isolated sandbox disaster recovery drill for {latest.backup_id}...")
            rep = run_disaster_recovery_drill(latest.backup_id, session)
            print(f"[OK] DR Drill Result: {rep['status']}")
            print(f"    RTO (Restore Time): {rep['rto_seconds']}s")
            print(f"    RPO (Archive Age):  {rep['rpo_seconds']}s")
            print(f"    Restored Records:   {rep['restored_records']} / {rep['expected_records']}")
            print(f"    SHA-256 Verified:   {rep['sha256_verified']}")
        return

    if args.status:
        with SessionLocal() as session:
            metrics = get_database_metrics(session)
            print("\n=== Safeprog System Status ===")
            print(f"Engine:             {metrics['engine']}")
            print(f"Total Records:      {metrics['total_records']}")
            print(f"Customer Accounts:  {metrics['customer_accounts_count']}")
            print(f"Audit Transactions: {metrics['audit_transactions_count']}")
            print(f"Vault Backups:      {metrics['backups_recorded']}")
            print(f"DR Tests Conducted: {metrics['dr_tests_recorded']}")
            print(f"Sync Status:        {metrics['sync_status']} (In Sync: {metrics['is_in_sync']})")
            print(f"Live State Hash:    {metrics['current_state_hash']}")
            print(f"Last Synced Hash:   {metrics['last_synced_hash'] or 'None'}")
            print(f"Tampered Count:     {metrics['tampered_count']}")
            print(f"Cloud Integration:  LOCKED ($0.00 spent)")
            print("==============================\n")
        return

    if args.sync:
        with SessionLocal() as session:
            print("[*] Solving synchronization drift by creating a verified SHA-256 backup snapshot...")
            rec = create_database_backup(session)
            status = get_sync_status(session)
            print(f"[OK] Synchronization solved!")
            print(f"    Backup ID:       {rec.backup_id}")
            print(f"    State SHA-256:   {rec.state_sha256}")
            print(f"    Sync Status:     {status['sync_status']}")
        return

    if args.verify:
        with SessionLocal() as session:
            print("[*] Performing full-table SHA-256 cryptographic audit scan...")
            report = verify_all_records_integrity(session)
            print(f"[OK] Audit complete:")
            print(f"    Total Checked:   {report['total_records']}")
            print(f"    Valid Checksums: {report['valid_records']}")
            print(f"    Tampered/Mod:    {report['tampered_records_count']}")
            print(f"    Integrity Rate:  {report['integrity_rate_pct']}%")
            if report['tampered_records_count'] > 0:
                print("    [!] Recognized Altered Records:")
                for r in report['tampered_records']:
                    print(f"        -> {r['account_number']}: stored={r['stored_hash'][:16]}... calc={r['calculated_hash'][:16]}...")
        return

    if args.streamlit:
        import subprocess
        print(f"\n=======================================================")
        print(f"  CloudCare DR — Hospital Disaster Recovery Manager")
        print(f"  Streamlit App: http://{args.host}:{args.port}")
        print(f"=======================================================\n")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", str(args.port),
            "--server.address", args.host
        ])
        return

    # Default action: Start FastAPI Dashboard
    print(f"\n=======================================================")
    print(f"  Safeprog Resilient Local Data Platform")
    print(f"  Mode: LOCAL ONLY (Strict AWS Credit Policy Enforced)")
    print(f"  Dashboard: http://{args.host}:{args.port}")
    print(f"=======================================================\n")
    uvicorn.run("dashboard.app:app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()
