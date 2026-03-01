import asyncio
import logging
import json
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OutboxEvent, JournalEntry
from .es_service import get_es_service

logger = logging.getLogger(__name__)

class OutboxRelayService:
    """
    Relay Service for the Outbox Pattern.
    Ensures that transactional outbox events are reliably pushed to external systems
    like Elasticsearch, providing At-Least-Once delivery guarantees.
    """

    @staticmethod
    async def process_pending_indexing_events(db: AsyncSession) -> int:
        """
        Poll pending search index events from the outbox and push to ES.
        Processes in strict order (by ID) to ensure sequential updates.
        Implements Exponential Backoff for failed attempts (#1146).
        """
        from sqlalchemy import and_, or_
        now = datetime.now(UTC)
        
        # 1. Fetch pending events for the 'search_indexing' topic
        # Only fetch those that are NOT 'failed' AND (next_retry_at IS NULL OR next_retry_at < NOW)
        stmt = select(OutboxEvent).filter(
            OutboxEvent.topic == "search_indexing",
            OutboxEvent.status == "pending",
            or_(
                OutboxEvent.next_retry_at == None,
                OutboxEvent.next_retry_at <= now
            )
        ).order_by(OutboxEvent.id).limit(50)
        
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        if not events:
            return 0
            
        es_service = get_es_service()
        processed_count = 0
        
        for event in events:
            try:
                payload = event.payload
                journal_id = payload.get("journal_id")
                action = payload.get("action")
                
                # RECOVERY CHECK: Get latest journal state for atomicity
                journal_stmt = select(JournalEntry).filter(JournalEntry.id == journal_id)
                journal_res = await db.execute(journal_stmt)
                journal = journal_res.scalar_one_or_none()

                if action == "upsert":
                    if journal and not journal.is_deleted:
                        # Push most recent content to Elasticsearch
                        await es_service.index_document(
                            entity="journal",
                            doc_id=journal.id,
                            data={
                                "user_id": journal.user_id,
                                "tenant_id": str(journal.tenant_id) if journal.tenant_id else None,
                                "content": journal.content,
                                "timestamp": journal.timestamp
                            }
                        )
                        logger.debug(f"Relayed UPSERT for journal {journal_id}")
                    elif journal and journal.is_deleted:
                        # Corner case: journal soft-deleted between outbox write and relay
                        await es_service.delete_document("journal", journal_id)
                
                elif action == "delete":
                    # Explicit removal
                    await es_service.delete_document("journal", journal_id)
                    logger.debug(f"Relayed DELETE for journal {journal_id}")
                
                # 2. Success: Mark as processed or delete to save space
                event.status = "processed"
                event.processed_at = now
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to relay OutboxEvent {event.id}: {str(e)}")
                # 3. FAILURE: Exponential Backoff (30s, 1m, 2m, 4m, 8m...)
                event.retry_count = (event.retry_count or 0) + 1
                event.error_message = str(e)
                
                if event.retry_count >= 10:
                    event.status = "failed"
                    logger.critical(f"Aborting OutboxEvent {event.id} permanently after 10 retries.")
                else:
                    delay_seconds = 30 * (2 ** (event.retry_count - 1))
                    from datetime import timedelta
                    event.next_retry_at = now + timedelta(seconds=delay_seconds)
                    logger.warning(f"Retrying OutboxEvent {event.id} in {delay_seconds}s (Attempt {event.retry_count})")
        
        # 4. Final Batch Commit
        await db.commit()
        return processed_count

    @classmethod
    async def start_relay_worker(cls, async_session_factory, interval_seconds: int = 2):
        """
        Background worker loop to continuously process outbox events.
        Usually started as a dedicated process or as part of app startup.
        """
        logger.info("Search Index Outbox Relay Worker started.")
        while True:
            try:
                async with async_session_factory() as db:
                    count = await cls.process_pending_indexing_events(db)
                    if count > 0:
                        logger.info(f"Successfully relayed {count} indexing events to Elasticsearch.")
            except Exception as e:
                logger.error(f"Critical error in Outbox Relay Worker: {e}", exc_info=True)
            
            # Use small sleep to allow for near real-time indexing while avoiding CPU hogging
            await asyncio.sleep(interval_seconds)
