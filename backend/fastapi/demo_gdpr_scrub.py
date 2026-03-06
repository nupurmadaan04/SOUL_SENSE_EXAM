import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
UTC = timezone.utc

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Mock environment variables
os.environ.setdefault("APP_ENV", "development")

from unittest.mock import MagicMock, AsyncMock
from api.services.db_service import AsyncSessionLocal, engine
from api.models import Base, User, ExportRecord, JournalEntry, OutboxEvent
from api.services.encryption_service import current_dek, current_user_id
from api.services.data_archival_service import DataArchivalService
from api.services.scrubber_service import scrubber_service
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Setup file-based DB for logic testing
import uuid
DB_PATH = f"gdpr_test_{uuid.uuid4().hex[:8]}.db"
test_engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def run_demo():
    print("=== Testing GDPR 'Right to be Forgotten' & Data Scrubbing (#1134) ===")
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Set DEK context for encrypted content (Journal entries)
    current_dek.set(b'\0' * 32)

    async with TestSession() as db:
        # 1. Register a Test User
        user = User(username="gdpr_victim", password_hash="dummy")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # SAVE ID LOCALLY to avoid lazy-loading on deleted/expired objects
        user_id = user.id
        
        current_user_id.set(user_id)
        print(f"[OK] Registered User: {user.username} (ID: {user_id})")
        
        # 2. Add some trace data
        entry = JournalEntry(user_id=user_id, content="This is private data that must be scrubbed.", entry_date="2026-03-01")
        export = ExportRecord(user_id=user_id, file_path="exports/gdpr_victim_data.zip", export_id="EXP-123", format="zip")
        db.add(entry)
        db.add(export)
        await db.commit()
        print("[OK] Created trace data: 1 Journal Entry, 1 Export Record")
        
        # Create a dummy file for the export
        os.makedirs("exports", exist_ok=True)
        with open("exports/gdpr_victim_data.zip", "w") as f:
            f.write("sensitive_archive_data")
        print(f"[OK] Created dummy export file: exports/gdpr_victim_data.zip")

        # 3. Initiate Secure Purge (Soft Delete)
        print("\n--- Initiating Secure Purge (Step 1/2) ---")
        await db.refresh(user) # Ensure object is not expired
        purge_date = await DataArchivalService.initiate_secure_purge(db, user)
        print(f"[OK] User marked is_deleted=True at {purge_date}")
        
        # 4. Simulate 31 days passing
        print("Simulating 31-day grace period expiration...")
        stmt = update(User).where(User.id == user_id).values(deleted_at=datetime.now(UTC) - timedelta(days=31))
        await db.execute(stmt)
        await db.commit()
        
        # 5. Execute Hard Scrub
        print("\n--- Executing Distributed Scrub (Step 2/2) ---")
        # In a real environment, the Celery task calls execute_hard_purges
        await DataArchivalService.execute_hard_purges(db)
        
        # 6. VERIFICATION
        print("\n--- Final Verification ---")
        
        # SQL Check using the SAVED user_id
        user_res = await db.get(User, user_id)
        if user_res is None:
            print("[SUCCESS] SQL user record purged.")
        else:
            print("[FAILURE] User record still exists in SQL.")
            
        entry_res = await db.execute(select(JournalEntry).where(JournalEntry.user_id == user_id))
        if entry_res.scalar_one_or_none() is None:
            print("[SUCCESS] Related journal entries purged via cascading.")
            
        # File System Check
        if not os.path.exists("exports/gdpr_victim_data.zip"):
            print("[SUCCESS] S3/Local S3 export archive scrubbed from disk.")
        else:
            print("[FAILURE] Export file still exists on disk.")

        # Deletion Log (Outbox) Check
        scrub_hash = hashlib.sha256(str(user_id).encode()).hexdigest()
        log_res = await scrubber_service.get_scrub_status(scrub_hash, db)
        if log_res:
            print(f"[SUCCESS] Content-addressable deletion log verified (Scrub Status: {log_res['status']})")
        else:
            print("[FAILURE] Deletion log missing.")

import hashlib
if __name__ == "__main__":
    asyncio.run(run_demo())
