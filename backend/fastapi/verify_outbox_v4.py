import asyncio
import sys
import os
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

# Add relevant paths
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.services.db_service import AsyncSessionLocal
from api.models import OutboxEvent, User
from api.services.journal_service import JournalService
from api.services.outbox_relay_service import OutboxRelayService
from sqlalchemy import select, delete

async def verify_outbox_v4():
    print("=== SEARCH INDEX OUTBOX RELIABILITY VERIFICATION (#1146) ===")
    
    async with AsyncSessionLocal() as db:
        # 1. CLEANUP
        await db.execute(delete(OutboxEvent).where(OutboxEvent.topic == "search_indexing"))
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if not user:
             print("No user.")
             return
        user_id = user.id
        await db.commit()
    
    async with AsyncSessionLocal() as db:
        # 2. TRIGGER
        user = await db.get(User, user_id)
        service = JournalService(db)
        # Mock gamification to avoid side-effect errors in verification script
        with patch('api.services.gamification_service.GamificationService.award_xp', return_value=None):
            with patch('api.services.gamification_service.GamificationService.update_streak', return_value=None):
                with patch('api.services.gamification_service.GamificationService.check_achievements', return_value=None):
                    entry = await service.create_entry(current_user=user, content="Eventual Consistency Test")
                    print(f"Created Journal ID: {entry.id}")

    async with AsyncSessionLocal() as db:
        # 3. RELAY FAILURE
        print("\n--- SIMULATING RELAY FAILURE (ES Down) ---")
        with patch('api.services.outbox_relay_service.get_es_service') as mock_es_factory:
            mock_es = MagicMock()
            mock_es.index_document.side_effect = Exception("Elasticsearch unreachable")
            mock_es_factory.return_value = mock_es
            
            await OutboxRelayService.process_pending_indexing_events(db)

        # CHECK
        stmt = select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing")
        event = (await db.execute(stmt)).scalars().first()
        print(f"Failure Recorded -> Status: {event.status}, Retries: {event.retry_count}")
        
        # Prepare for recovery
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
        
        # CHECK
        stmt = select(OutboxEvent).filter(OutboxEvent.topic == "search_indexing")
        event = (await db.execute(stmt)).scalars().first()
        print(f"Success Recorded -> Status: {event.status}, Processed At: {event.processed_at}")
        
        if event.status == "processed":
            print("\n=== VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    asyncio.run(verify_outbox_v4())
