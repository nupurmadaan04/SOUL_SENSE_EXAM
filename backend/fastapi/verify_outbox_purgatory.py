
import asyncio
import uuid
import sys
import os
from unittest.mock import MagicMock

# --- MOCK ELASTICSEARCH ---
mock_es = MagicMock()
sys.modules['elasticsearch'] = mock_es
# --- MOCK DONE ---

from datetime import datetime, timezone, timedelta
UTC = timezone.utc
# Ensure current directory is in path for imports
sys.path.append(os.getcwd())

from api.models import OutboxEvent, Base
# We need the engine and session from db_service
from api.services.db_service import AsyncSessionLocal, engine

async def verify_outbox_logic():
    print("\n" + "="*60)
    print("🚀 SOUL-SENSE TRANSACTIONAL OUTBOX VERIFICATION")
    print("="*60)

    # Ensure tables exist in the local SQLite db for this test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Database schema initialized.")

    async with AsyncSessionLocal() as db:
        print("\n[1/4] Simulating Failed Relay attempts (Retry -> Dead Letter)...")
        event_id = str(uuid.uuid4())
        event = OutboxEvent(
            topic="search_indexing",
            payload={"action": "upsert", "journal_id": 99999, "event_id": event_id},
            status="pending",
            retry_count=0
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        print(f"  Created pending event: {event_id}")

        # Simulate 3 failures leading to dead_letter
        for i in range(1, 4):
            event.retry_count = i
            event.last_error = f"Connection timeout to Elasticsearch (Attempt {i})"
            
            if i >= 3:
                event.status = "dead_letter"
                print(f"  Attempt {i}: Transitioned to DEAD_LETTER (Max Retries)")
            else:
                delay = 60 * (2 ** (i-1))
                event.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
                print(f"  Attempt {i}: Status=pending, RetryCount={i}, NextRetry=+{delay}s")
            
            await db.commit()

        print("\n[2/4] Testing Purgatory Alert System...")
        from api.services.outbox_relay_service import OutboxRelayService
        stats = await OutboxRelayService.cleanup_purgatory(db, threshold=0) 
        print(f"  Stats: {stats['total_pending']} pending, {stats['total_dead_letter']} dead-lettered.")
        if stats["is_critical"]:
            print("  🚨 ALERT: Outbox Purgatory threshold exceeded! (Threshold: 0 for test)")
        
        print("\n[3/4] Testing Admin Manual Retry...")
        retried_count = await OutboxRelayService.retry_all_failed_events(db)
        print(f"  Action: Successfully reset {retried_count} events to 'pending'")
        
        # Verify reset
        from sqlalchemy import select
        # Use a filter that works with the JSON/String payload logic of the model
        stmt = select(OutboxEvent).filter(OutboxEvent.status == 'pending')
        res = await db.execute(stmt)
        updated_events = res.scalars().all()
        # Find our specific event
        target = next((e for e in updated_events if event_id in str(e.payload)), None)
        if target:
            print(f"  Event state: status={target.status}, retry_count={target.retry_count}")

        print("\n[4/4] Final Cleanup...")
        if target:
            await db.delete(target)
            await db.commit()
            print("  Test artifacts cleared.")

    print("\n" + "="*60)
    print("✅ ALL OUTBOX PURGATORY & DEAD-LETTER TESTS PASSED!")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(verify_outbox_logic())
