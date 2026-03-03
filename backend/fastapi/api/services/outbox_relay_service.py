import asyncio
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OutboxEvent, JournalEntry
from .es_service import get_es_service

logger = logging.getLogger(__name__)


class OutboxRelayService:
    """
    Relay Service for the Transactional Outbox Pattern (#1176).

    Guarantees At-Least-Once delivery of search indexing events to Elasticsearch.
    Implements exponential backoff for failed delivery attempts.

    Idempotency contract:
      - Each outbox event payload carries a stable `event_id` (UUID).
      - Elasticsearch writes use doc_id-level upsert/delete which are inherently
        idempotent: re-sending the same event_id causes an overwrite with the
        same data, not a duplicate.
      - The relay fetches the LATEST journal state at relay-time (not at write-time),
        so stale payloads are automatically corrected (e.g., soft-delete race).
    """

    @staticmethod
    async def process_pending_indexing_events(db: AsyncSession) -> int:
        """
        Poll pending search index events from the outbox and push to ES.
        Processes in strict ID order to ensure sequential updates.

        Per-event timestamps are used (not a single shared `now`) to ensure
        accurate next_retry_at and processed_at values for each event,
        regardless of how long earlier events in the batch take to process.
        """
        from sqlalchemy import and_

        # Fetch pending events that are either new or past their retry window
        stmt = select(OutboxEvent).filter(
            OutboxEvent.topic == "search_indexing",
            OutboxEvent.status == "pending",
            or_(
                OutboxEvent.next_retry_at == None,
                OutboxEvent.next_retry_at <= datetime.now(UTC)
            )
        ).order_by(OutboxEvent.id).limit(50)

        result = await db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return 0

        es_service = get_es_service()
        processed_count = 0

        for event in events:
            # Per-event timestamp: avoids skew in next_retry_at / processed_at
            # for large batches where earlier events may take time (#1176 reviewer gap).
            event_now = datetime.now(UTC)

            try:
                payload = event.payload
                journal_id = payload.get("journal_id")
                action = payload.get("action")
                event_id = payload.get("event_id", str(event.id))  # Idempotency key

                # Re-fetch the latest journal state at relay-time.
                # This corrects stale payloads (e.g., soft-delete race between
                # outbox write and relay without extra coordination).
                journal_stmt = select(JournalEntry).filter(JournalEntry.id == journal_id)
                journal_res = await db.execute(journal_stmt)
                journal = journal_res.scalar_one_or_none()

                if action == "upsert":
                    if journal and not journal.is_deleted:
                        # ES index_document is idempotent: same doc_id overwrites in-place
                        await es_service.index_document(
                            entity="journal",
                            doc_id=journal.id,
                            data={
                                "event_id": event_id,  # Carried through for ES-side dedup if needed
                                "user_id": journal.user_id,
                                "tenant_id": str(journal.tenant_id) if journal.tenant_id else None,
                                "content": journal.content,
                                "timestamp": journal.timestamp
                            }
                        )
                        logger.debug(f"[Outbox] Relayed UPSERT journal={journal_id} event={event_id}")
                    elif journal and journal.is_deleted:
                        # Soft-delete race: journal was deleted after event was written
                        # Treat as delete to keep ES consistent
                        await es_service.delete_document("journal", journal_id)
                        logger.debug(
                            f"[Outbox] Upgraded UPSERT -> DELETE (soft-delete race) "
                            f"journal={journal_id} event={event_id}"
                        )
                    else:
                        # Journal not found at all — log and mark as processed to avoid infinite retry
                        logger.warning(
                            f"[Outbox] Journal {journal_id} not found; marking event {event.id} as processed."
                        )

                elif action == "delete":
                    # ES delete_document is idempotent: deleting a non-existent doc is a no-op
                    await es_service.delete_document("journal", journal_id)
                    logger.debug(f"[Outbox] Relayed DELETE journal={journal_id} event={event_id}")

                # Mark as processed using per-event timestamp
                event.status = "processed"
                event.processed_at = event_now
                processed_count += 1

            except Exception as e:
                logger.error(f"[Outbox] Failed to relay event {event.id}: {e}")

                # Exponential backoff with max 3 retries
                event.retry_count = (event.retry_count or 0) + 1
                event.last_error = str(e)

                if event.retry_count >= 3:
                    event.status = "dead_letter"
                    logger.critical(
                        f"[Outbox] Event {event.id} moved to DEAD_LETTER after {event.retry_count} failed attempts."
                    )
                else:
                    # Exponential backoff: 30s, 60s, 120s
                    delay_seconds = 30 * (2 ** (event.retry_count - 1))
                    event.next_retry_at = event_now + timedelta(seconds=delay_seconds)
                    logger.warning(
                        f"[Outbox] Retry scheduled for event {event.id} in {delay_seconds}s (attempt {event.retry_count}/3)"
                    )

        # Single batch commit after all events are processed
        await db.commit()
        return processed_count

    @classmethod
    async def start_relay_worker(cls, async_session_factory, interval_seconds: int = 2):
        """
        Background worker loop that continuously polls the outbox table.
        Intended to run as a dedicated process or be started at app startup.
        """
        logger.info("[Outbox] Search Index Relay Worker started.")
        while True:
            try:
                async with async_session_factory() as db:
                    count = await cls.process_pending_indexing_events(db)
                    if count > 0:
                        logger.info(f"[Outbox] Relayed {count} indexing events to Elasticsearch.")
            except Exception as e:
                logger.error(f"[Outbox] Critical worker error: {e}", exc_info=True)

            await asyncio.sleep(interval_seconds)

    @classmethod
    async def monitor_purgatory_volume(cls, async_session_factory):
        """
        Background task that monitors the outbox table for 'purgatory' risk.
        Alerts if the volume of pending/failed/dead-letter events exceeds 10,000.
        """
        from sqlalchemy import func
        logger.info("[Outbox] Purgatory Monitor Job started.")
        
        while True:
            try:
                async with async_session_factory() as db:
                    # Count pending, failed and dead_letter events
                    stmt = select(func.count(OutboxEvent.id)).filter(
                        OutboxEvent.status.in_(["pending", "failed", "dead_letter"])
                    )
                    result = await db.execute(stmt)
                    count = result.scalar() or 0
                    
                    if count >= 10000:
                        logger.critical(
                            f"[CRITICAL ALERT] Outbox Purgatory Threshold Exceeded! "
                            f"Current Volume: {count}. Admin intervention required."
                        )
                    elif count > 5000:
                        logger.warning(f"[Outbox] Volume warning: {count} events in purgatory.")
                    else:
                        logger.debug(f"[Outbox] Purgatory volume check: {count} events.")
                        
            except Exception as e:
                logger.error(f"[Outbox] Purgatory Monitor Error: {e}")
            
            # Check every 5 minutes
            await asyncio.sleep(300)
