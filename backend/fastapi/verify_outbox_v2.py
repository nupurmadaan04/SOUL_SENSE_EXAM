import asyncio
import sys
import os
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

# Add relevant paths
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.services.db_service import AsyncSessionLocal
from api.models import OutboxEvent, JournalEntry, User
from api.services.journal_service import JournalService
from api.services.outbox_relay_service import OutboxRelayService
from sqlalchemy import select, delete

async def verify_outbox_reliability():
    print("=== SEARCH INDEX OUTBOX RELIABILITY VERIFICATION (#1146) ===")
    
    # 1. Setup Data
    async with AsyncSessionLocal() as db:
        # Load user and KEEP session open
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
             print("No user.")
             return
        
        await db.execute(delete(OutboxEvent).where(OutboxEvent.topic == "search_indexing"))
        await db.commit()
        
        # We need to refresh the user after commit because it gets expired
        await db.refresh(user)

        journal_service = JournalService(db)
        entry = await journal_service.create_entry(
            current_user=user,
            content="Eventual consistency test content."
        )
        print(f"Created journal {entry.id}")

        # 2. Test Relay Failure
        print("\n--- SIMULATING ELASTICSEARCH FAILURE ---")
        with patch('api.services.outbox_relay_service.get_es_service') as mock_es_factory:
            mock_es = MagicMock()
            mock_es.index_document.side_effect = Exception("ES Timeout")
            mock_es_factory.return_value = mock_es
            
            await OutboxRelayService.process_pending_indexing_events(db)

        # Re-fetch from DB (within the same session, using fresh query)
        stmt = select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing")
        event = (await db.execute(stmt)).scalars().first()
        print(f"Event Status: {event.status}, Retries: {event.retry_count}")
        
        # Prepare for recovery test
        event.next_retry_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

        # 3. Test Recovery
        print("\n--- SIMULATING ELASTICSEARCH RECOVERY ---")
        with patch('api.services.outbox_relay_service.get_es_service') as mock_es_factory:
            mock_es = MagicMock()
            async def mock_ok(*args, **kwargs): pass
            mock_es.index_document = mock_ok
            mock_es_factory.return_value = mock_es
            
            await OutboxRelayService.process_pending_indexing_events(db)

        # Re-fetch
        stmt = select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing")
        event = (await db.execute(stmt)).scalars().first()
        print(f"Event Status: {event.status}, Processed At: {event.processed_at}")
        
        if event.status == "processed" and event.processed_at:
            print("\n=== VERIFICATION SUCCESSFUL ===")
        else:
            print("\n=== VERIFICATION FAILED ===")

if __name__ == "__main__":
    asyncio.run(verify_outbox_reliability())
