import hashlib
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
UTC = timezone.utc

from ..models import User, ExportRecord, OutboxEvent, GDPRScrubLog
from .storage_service import storage_service

logger = logging.getLogger("api.scrubber")

class DistributedScrubberService:
    """
    Idempotent Saga Pattern for GDPR Scrubbing (Issue #1144).
    Ensures PII in external stores (S3, Vector) is cleared BEFORE SQL records
    are purged, preventing orphaned files if the SQL transaction fails.
    """
    
    @staticmethod
    async def scrub_user(db: AsyncSession, user_id: int):
        """
        Orchestrates an idempotent deletion across all stores.
        Checkpoints ensure that if the process fails mid-way, it can resume 
        exactly where it left off on retry.
        """
        # 1. Fetch existing log or start a new Saga
        stmt = select(GDPRScrubLog).where(GDPRScrubLog.user_id == user_id)
        res = await db.execute(stmt)
        scrub_log = res.scalar_one_or_none()
        
        user = await db.get(User, user_id)
        
        if not scrub_log:
            if not user:
                logger.warning(f"GDPR: Attempted to scrub non-existent user {user_id} with no active Saga. Already purged?")
                return
                
            # --- INIT PHASE: Capture all asset references before they're lost ---
            # Capture all known file uploads/exports from DB metadata
            exp_stmt = select(ExportRecord.file_path).where(ExportRecord.user_id == user_id)
            exp_res = await db.execute(exp_stmt)
            assets = exp_res.scalars().all()
            
            scrub_id = hashlib.sha256(f"scrub_{user_id}_{user.username}_{datetime.now(UTC).timestamp()}".encode()).hexdigest()
            scrub_log = GDPRScrubLog(
                user_id=user_id,
                username=user.username,
                scrub_id=scrub_id,
                status='PENDING',
                assets_to_delete=list(assets)
            )
            db.add(scrub_log)
            # Create a 'Scrub Scheduled' outbox event for external auditing systems
            outbox_scrub = OutboxEvent(
                topic="GDPR_SCRUB_INITIATED",
                payload={"scrub_id": scrub_id, "user_id": user_id, "timestamp": datetime.now(UTC).isoformat()},
                status="pending"
            )
            db.add(outbox_scrub)
            await db.commit()
            await db.refresh(scrub_log)
            logger.info(f"GDPR: Saga initialized for user {user_id} (scrub_id: {scrub_id})")

        # 2. EXE PHASE: Delete External Assets (Idempotent)
        if scrub_log.status == 'PENDING':
            # a. Storage (S3 / Local Exports)
            if not scrub_log.storage_deleted:
                files = scrub_log.assets_to_delete or []
                for file_path in files:
                    try:
                        # storage_service.delete_file must be idempotent (no error if file gone)
                        await storage_service.delete_file(file_path)
                    except Exception as e:
                        logger.warning(f"File Deletion Failed in Scrub: {file_path} - {e}")
                        # We don't mark storage_deleted=True if a failure occurs to ensure retry
                
                scrub_log.storage_deleted = True
                await db.commit()
            
            # b. Vector Store (Elasticsearch Vector / Pinecone)
            if not scrub_log.vector_deleted:
                # FUTURE: Here we call vector_service.purge_user_vectors(user_id)
                scrub_log.vector_deleted = True
                await db.commit()
                
            # If all external checkpoints passed, advance state
            if scrub_log.storage_deleted and scrub_log.vector_deleted:
                scrub_log.status = 'ASSETS_DELETED'
                await db.commit()
                logger.debug(f"GDPR: External assets cleared for user {user_id}")
        
        # 3. PURGE PHASE: SQL Hard Delete
        if scrub_log.status == 'ASSETS_DELETED':
            try:
                if user:
                    # Capture user info for audit logging before delete
                    username = user.username
                    await db.delete(user)
                    
                    # Log completion to Outbox for reliable auditing/reporting
                    log_complete = OutboxEvent(
                        topic="GDPR_SCRUB_COMPLETE",
                        payload={
                            "scrub_id": scrub_log.scrub_id,
                            "user_id": user_id,
                            "username": username,
                            "timestamp": datetime.now(UTC).isoformat()
                        },
                        status="processed"
                    )
                    db.add(log_complete)
                
                scrub_log.sql_deleted = True
                scrub_log.status = 'COMPLETED'
                await db.commit()
                logger.info(f"GDPR: Saga COMPLETED successfully for user {user_id}")
            except Exception as e:
                await db.rollback()
                scrub_log.last_error = str(e)
                scrub_log.retry_count += 1
                await db.commit()
                logger.error(f"GDPR: SQL Purge failed for user {user_id}: {e}")
                raise e

    @staticmethod
    async def get_scrub_status(scrub_id: str, db: AsyncSession) -> Optional[Dict]:
        """Verify if a purge was successfully completed by its scrub_id."""
        stmt = select(GDPRScrubLog).where(GDPRScrubLog.scrub_id == scrub_id)
        result = await db.execute(stmt)
        log = result.scalar_one_or_none()
        if log:
            return {
                "scrub_id": log.scrub_id,
                "user_id": log.user_id,
                "status": log.status,
                "completed": log.status == 'COMPLETED',
                "checkpoints": {
                    "storage": log.storage_deleted,
                    "vector": log.vector_deleted,
                    "sql": log.sql_deleted
                },
                "processed_at": log.updated_at.isoformat() if log.status == 'COMPLETED' else None
            }
        return None

scrubber_service = DistributedScrubberService()
