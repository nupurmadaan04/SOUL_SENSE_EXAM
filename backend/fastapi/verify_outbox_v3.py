import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
UTC = timezone.utc
from unittest.mock import MagicMock, patch

# Add relevant paths
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.services.db_service import AsyncSessionLocal
from api.models import OutboxEvent, User
from api.services.journal_service import JournalService
from api.services.outbox_relay_service import OutboxRelayService
from sqlalchemy import select, delete

async def verify_outbox_reliability():
    print("=== SEARCH INDEX OUTBOX RELIABILITY VERIFICATION (#1146) ===")
    
    # 1. Setup Data
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
             print("No user.")
             return
        
        user_id = user.id
        username = user.username

        await db.execute(delete(OutboxEvent).where(OutboxEvent.topic == "search_indexing"))
        await db.commit()
    
    # 2. Trigger Event
    async with AsyncSessionLocal() as db:
        # Re-fetch user to avoid detachment
        user = await db.get(User, user_id)
        journal_service = JournalService(db)
        entry = await journal_service.create_entry(
            current_user=user,
            content="Eventual consistency test content."
        )
        print(f"Created journal {entry.id} for user {username}")

    # 3. Test Relay Failure
    async with AsyncSessionLocal() as db:
        print("\n--- SIMULATING ELASTICSEARCH FAILURE ---")
        with patch('api.services.outbox_relay_service.get_es_service') as mock_es_factory:
            mock_es = MagicMock()
            mock_es.index_document.side_effect = Exception("ES Timeout")
            mock_es_factory.return_value = mock_es
            
            await OutboxRelayService.process_pending_indexing_events(db)

        # Refresh state
        stmt = select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing")
        event = (await db.execute(stmt)).scalars().first()
        print(f"Captured Failure -> Status: {event.status}, Retries: {event.retry_count}")
        print(f"Wait Time: {event.next_retry_at}")
        
        # Prepare for recovery test (move next_retry_at to past)
        event.next_retry_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

    # 4. Test Recovery
    async with AsyncSessionLocal() as db:
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
        print(f"Captured Success -> Status: {event.status}, Processed At: {event.processed_at}")
        
        if event.status == "processed" and event.processed_at:
            print("\n=== VERIFICATION SUCCESSFUL ===")
        else:
            print("\n=== VERIFICATION FAILED ===")

if __name__ == "__main__":
    asyncio.run(verify_outbox_reliability())
