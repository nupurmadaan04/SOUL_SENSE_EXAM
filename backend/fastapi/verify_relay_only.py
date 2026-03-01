import asyncio
import sys
import os
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

# Add relevant paths
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.services.db_service import AsyncSessionLocal
from api.models import OutboxEvent, User, JournalEntry
from api.services.outbox_relay_service import OutboxRelayService
from sqlalchemy import select, delete

async def verify_relay_only():
    print("=== SEARCH INDEX OUTBOX RELAY VERIFICATION (CORE LOGIC) ===")
    
    async with AsyncSessionLocal() as db:
        # 1. CLEANUP
        await db.execute(delete(OutboxEvent).where(OutboxEvent.topic == "search_indexing"))
        
        # Ensure we have a journal to index
        journal = (await db.execute(select(JournalEntry).limit(1))).scalar_one_or_none()
        if not journal:
             print("No journal found to index.")
             return
        
        # 2. SEED PENDING EVENT
        print(f"Seeding outbox event for journal {journal.id}...")
        event = OutboxEvent(
            topic="search_indexing",
            payload={"journal_id": journal.id, "action": "upsert"},
            status="pending"
        )
        db.add(event)
        await db.commit()
    
    async with AsyncSessionLocal() as db:
        # 3. RELAY FAILURE
        print("\n--- SIMULATING RELAY FAILURE (ES Down) ---")
        with patch('api.services.outbox_relay_service.get_es_service') as mock_es_factory:
            mock_es = MagicMock()
            mock_es.index_document.side_effect = Exception("Elasticsearch Error")
            mock_es_factory.return_value = mock_es
            
            await OutboxRelayService.process_pending_indexing_events(db)

        # RE-FETCH
        res = await db.execute(select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing"))
        event = res.scalars().first()
        print(f"Captured Failure -> Status: {event.status}, Retries: {event.retry_count}")
        print(f"Wait Time: {event.next_retry_at}")
        
        # Move next_retry_at to past for recovery test
        event.next_retry_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

    async with AsyncSessionLocal() as db:
        # 4. RECOVERY
        print("\n--- SIMULATING RELAY RECOVERY (ES Up) ---")
        with patch('api.services.outbox_relay_service.get_es_service') as mock_es_factory:
            mock_es = MagicMock()
            async def mock_ok(*args, **kwargs): pass
            mock_es.index_document = mock_ok
            mock_es_factory.return_value = mock_es
            
            await OutboxRelayService.process_pending_indexing_events(db)

        # RE-FETCH
        res = await db.execute(select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing"))
        event = res.scalars().first()
        print(f"Captured Success -> Status: {event.status}, Processed At: {event.processed_at}")
        
        if event.status == "processed":
            print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    asyncio.run(verify_relay_only())
