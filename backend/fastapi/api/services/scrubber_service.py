import logging
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .data_archival_service import DataArchivalService
from .kafka_producer import get_kafka_producer
from ..models import User, ExportRecord, OutboxEvent

logger = logging.getLogger("api.scrubber")

class DistributedScrubberService:
    """
    Orchestrates the permanent deletion of user data across all distributed systems:
    SQL, S3 (via StorageService), Elasticsearch, and Kafka.
    """

    @staticmethod
    async def scrub_user(db: AsyncSession, user_id: int) -> dict:
        """
        Main orchestration method to scrub a single user.
        Follows a 'Source of Truth Last' approach:
        1. Scrub external/read models first (ES, S3).
        2. Emit final purge event to Kafka.
        3. Finally, hard-delete from the main SQL database.
        """
        report = {
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "steps": {}
        }
        
        try:
            # Fetch user to ensure existence and log progress
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Attempted to scrub non-existent user ID {user_id}")
                return {"status": "skipped", "reason": "user_not_found"}

            logger.info(f"Starting distributed scrub for user {user.username} (ID: {user_id})")

            # --- Step 1: Scrub S3 Blobs (Exports, Archives) ---
            try:
                # We will implement StorageService in the next step
                # For now, we use a placeholder or dummy implementation
                from .storage_service import StorageService
                count = await StorageService.hard_delete_user_blobs(user_id)
                report["steps"]["s3"] = {"status": "success", "objects_deleted": count}
            except Exception as e:
                logger.error(f"S3 scrub failed for user {user_id}: {e}")
                report["steps"]["s3"] = {"status": "failed", "error": str(e)}

            # --- Step 2: Scrub Elasticsearch Indices ---
            try:
                from .es_service import get_es_service
                es_service = get_es_service()
                await es_service.delete_user_data(user_id)
                report["steps"]["elasticsearch"] = {"status": "success"}
            except Exception as e:
                logger.error(f"Elasticsearch scrub failed for user {user_id}: {e}")
                report["steps"]["elasticsearch"] = {"status": "failed", "error": str(e)}

            # --- Step 3: Emit Kafka Purge Event ---
            try:
                producer = get_kafka_producer()
                await producer.send_message("user_purged", {
                    "user_id": user_id,
                    "scrub_id": user.username,
                    "purged_at": datetime.now(UTC).isoformat()
                })
                report["steps"]["kafka"] = {"status": "success"}
            except Exception as e:
                logger.error(f"Kafka event emission failed for user {user_id}: {e}")
                report["steps"]["kafka"] = {"status": "failed", "error": str(e)}

            # --- Step 4: Final SQL Hard Delete ---
            try:
                # We perform the actual SQL delete here
                # cascading relationships defined in the model will handle most tables
                await db.delete(user)
                await db.commit()
                report["steps"]["sql"] = {"status": "success"}
                logger.info(f"User {user_id} hard-purged successfully from all systems.")
            except Exception as e:
                await db.rollback()
                logger.error(f"SQL Hard Delete failed for user {user_id}: {e}")
                report["steps"]["sql"] = {"status": "failed", "error": str(e)}

        except Exception as e:
            logger.critical(f"Scrubber orchestrator crashed for user {user_id}: {e}")
            report["status"] = "error"
            report["error"] = str(e)
            
        return report

    @staticmethod
    async def schedule_purge_event(db: AsyncSession, user_id: int):
        """
        Adds a purge event to the Outbox table for background processing.
        This provides a Deletion Log (Outbox Pattern) to track pending purges.
        """
        event = OutboxEvent(
            topic="data_purge",
            payload={
                "action": "SCRUB_USER",
                "user_id": user_id,
                "scheduled_at": datetime.now(UTC).isoformat()
            },
            status="pending"
        )
        db.add(event)
        await db.commit()
        logger.info(f"Purge event scheduled in Outbox for user {user_id}")
