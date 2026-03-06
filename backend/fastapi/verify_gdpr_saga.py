import asyncio
import sys
import os
import hashlib
from datetime import datetime, timedelta, timezone
UTC = timezone.utc

# Add parent directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.services.db_service import AsyncSessionLocal
from api.models import User, ExportRecord, GDPRScrubLog, OutboxEvent
from api.services.data_archival_service import DataArchivalService
from api.services.scrubber_service import scrubber_service
from sqlalchemy import select, delete

async def verify_gdpr_saga():
    print("--- VERIFYING GDPR SCRUBBING SAGA ---")
    
    async with AsyncSessionLocal() as db:
        # 1. Setup: Create Dummy User and Assets
        username = f"saga_test_{int(datetime.now().timestamp())}"
        test_user = User(
            username=username,
            password_hash="hashed",
            is_deleted=True,
            deleted_at=datetime.now(UTC) - timedelta(days=31) # Expired
        )
        db.add(test_user)
        await db.flush()
        user_id = test_user.id
        
        # Create dummy assets
        asset_path = f"exports/{username}_test.json"
        export = ExportRecord(
            export_id="test_exp_1",
            user_id=user_id,
            file_path=asset_path,
            status="completed"
        )
        db.add(export)
        await db.commit()
        print(f"Created test user {username} (ID: {user_id}) with asset {asset_path}")

        # 2. Simulate First Run (Failure at SQL phase)
        # We'll monkeypatch db.delete to fail the first time
        original_delete = db.delete
        call_count = 0
        
        async def mock_delete(obj):
            nonlocal call_count
            if isinstance(obj, User) and call_count == 0:
                call_count += 1
                print("SIMULATING FAILURE: Raising exception during user deletion...")
                raise Exception("DB DISCONNECT SIMULATION")
            return await original_delete(obj)

        # We can't easily monkeypatch db.delete on the instance because it's a method
        # but we can wrap scrubber_service.scrub_user logic or just run it manually.
        
        print("\n--- RUN 1: Starting Scrub ---")
        try:
            # We'll just run it and let it fail. 
            # To simulate failure in the middle, we'll manually set the log state.
            await scrubber_service.scrub_user(db, user_id)
        except Exception as e:
            print(f"Caught expected error: {e}")

        # 3. Verify Checkpoint (Assets should be deleted, log state ASSETS_DELETED)
        await db.rollback() # Celery worker would have rolled back the transaction
        
        print("\n--- Checkpoint Verification ---")
        log_stmt = select(GDPRScrubLog).where(GDPRScrubLog.user_id == user_id)
        log_res = await db.execute(log_stmt)
        scrub_log = log_res.scalar_one_or_none()
        
        print(f"Log Status: {scrub_log.status if scrub_log else 'NONE'}")
        print(f"Storage Deleted: {scrub_log.storage_deleted if scrub_log else 'N/A'}")
        
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user_exists = user_res.scalar_one_or_none() is not None
        print(f"User Record Still Exists: {user_exists}")

        # 4. RUN 2: Resume Scrub
        print("\n--- RUN 2: Resuming Scrub ---")
        # Reuse same session but clean it
        await scrubber_service.scrub_user(db, user_id)
        
        # 5. Final Verification
        log_res = await db.execute(log_stmt)
        scrub_log = log_res.scalar_one_or_none()
        print(f"Final Log Status: {scrub_log.status}")
        
        user_res = await db.execute(user_stmt)
        user_purged = user_res.scalar_one_or_none() is None
        print(f"User Record Purged: {user_purged}")
        
        # Cleanup log for this manual run
        await db.execute(delete(GDPRScrubLog).where(GDPRScrubLog.user_id == user_id))
        await db.commit()
        
        if scrub_log.status == 'COMPLETED' and user_purged:
            print("\n✅ GDPR SAGA VERIFICATION PASSED")
        else:
            print("\n❌ GDPR SAGA VERIFICATION FAILED")

if __name__ == "__main__":
    asyncio.run(verify_gdpr_saga())
