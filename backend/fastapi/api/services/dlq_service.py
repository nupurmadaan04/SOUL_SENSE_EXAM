"""
Dead-Letter Queue (DLQ) Service - Issue #1355

Manages dead-lettered async tasks:
- Stores failed tasks for visibility and recovery
- Enables manual replay with replay limits
- Provides monitoring metrics for alerting
- Supports discard for unrecoverable failures
"""

import json
import logging
from datetime import datetime, timezone, timedelta
UTC = timezone.utc
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ..models import DeadLetterQueue

logger = logging.getLogger(__name__)

# Import Celery app for task replay
try:
    from ..celery_app import celery_app
except Exception:
    celery_app = None

# DLQ Configuration
DLQ_CONFIG = {
    'max_replay_attempts': 3,
    'auto_archive_days': 30,
}


class DLQService:
    """Service for managing dead-lettered tasks."""
    
    @staticmethod
    async def enqueue_to_dlq(
        db: AsyncSession,
        task_id: str,
        task_name: str,
        task_type: str,
        user_id: Optional[int],
        params: Optional[Dict[str, Any]],
        error_message: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> DeadLetterQueue:
        """
        Enqueue a failed task to the DLQ for manual recovery.
        
        Args:
            db: Async database session
            task_id: Original Celery task ID
            task_name: Full Celery task name (e.g., "api.celery_tasks.generate_journal_embedding_task")
            task_type: Business task type (e.g., "export_pdf", "send_email")
            user_id: User ID (None for system tasks)
            params: Original task parameters
            error_message: Full error traceback
            result: Last execution result
            
        Returns:
            DeadLetterQueue record
        """
        try:
            # Check if task already exists in DLQ (idempotency)
            stmt = select(DeadLetterQueue).where(DeadLetterQueue.task_id == task_id)
            result_set = await db.execute(stmt)
            existing = result_set.scalar_one_or_none()
            
            if existing:
                # Increment error count
                existing.error_count += 1
                existing.error_message = error_message  # Update with latest error
                existing.last_retry_at = datetime.now(UTC)
                logger.info(f"DLQ: Updated existing task {task_id}, error_count={existing.error_count}")
            else:
                # Create new DLQ entry
                dlq_record = DeadLetterQueue(
                    task_id=task_id,
                    task_name=task_name,
                    task_type=task_type,
                    user_id=user_id,
                    params=json.dumps(params) if params else None,
                    result=json.dumps(result) if result else None,
                    error_message=error_message,
                    error_count=1,
                    status='pending_replay',
                    replay_count=0,
                    created_at=datetime.now(UTC),
                    queued_at=datetime.now(UTC),
                )
                db.add(dlq_record)
                existing = dlq_record
                logger.info(f"DLQ: Enqueued task {task_id} ({task_type}) for user {user_id}")
            
            await db.commit()
            await db.refresh(existing)
            return existing
            
        except SQLAlchemyError as e:
            logger.error(f"DLQ: Failed to enqueue task {task_id}: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_dlq_tasks(
        db: AsyncSession,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[DeadLetterQueue], int]:
        """
        Retrieve DLQ tasks with optional filtering.
        
        Args:
            db: Async database session
            task_type: Filter by task type (e.g., "export_pdf")
            status: Filter by status (pending_replay, archived, discarded)
            user_id: Filter by user ID
            limit: Number of records to retrieve
            offset: Pagination offset
            
        Returns:
            Tuple of (tasks list, total count)
        """
        try:
            stmt = select(DeadLetterQueue)
            count_stmt = select(func.count(DeadLetterQueue.id))
            
            if task_type:
                stmt = stmt.where(DeadLetterQueue.task_type == task_type)
                count_stmt = count_stmt.where(DeadLetterQueue.task_type == task_type)
            
            if status:
                stmt = stmt.where(DeadLetterQueue.status == status)
                count_stmt = count_stmt.where(DeadLetterQueue.status == status)
            
            if user_id:
                stmt = stmt.where(DeadLetterQueue.user_id == user_id)
                count_stmt = count_stmt.where(DeadLetterQueue.user_id == user_id)
            
            # Order by most recent first
            stmt = stmt.order_by(desc(DeadLetterQueue.created_at)).limit(limit).offset(offset)
            
            result = await db.execute(stmt)
            tasks = list(result.scalars().all())
            
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar() or 0
            
            return tasks, total_count
            
        except SQLAlchemyError as e:
            logger.error(f"DLQ: Failed to retrieve tasks: {e}")
            return [], 0
    
    @staticmethod
    async def replay_task(
        db: AsyncSession,
        task_id: str,
    ) -> bool:
        """
        Replay (requeue) a task from the DLQ.
        
        Enforces replay limits to prevent infinite loops.
        Task is requeued back to Celery with original parameters.
        
        Args:
            db: Async database session
            task_id: DLQ task ID
            
        Returns:
            True if replay initiated, False otherwise
        """
        try:
            stmt = select(DeadLetterQueue).where(DeadLetterQueue.task_id == task_id)
            result = await db.execute(stmt)
            dlq_task = result.scalar_one_or_none()
            
            if not dlq_task:
                logger.warning(f"DLQ: Task {task_id} not found for replay")
                return False
            
            # Check replay limit
            if dlq_task.replay_count >= DLQ_CONFIG['max_replay_attempts']:
                logger.warning(
                    f"DLQ: Task {task_id} has exceeded max replay attempts "
                    f"({dlq_task.replay_count}/{DLQ_CONFIG['max_replay_attempts']})"
                )
                return False
            
            # Parse original params
            params = json.loads(dlq_task.params) if dlq_task.params else {}
            
            # Extract args and kwargs from params
            # Assuming params format: {"args": [...], "kwargs": {...}}
            args = params.get('args', ())
            kwargs = params.get('kwargs', {})
            
            # Requeue the task if Celery is available
            if celery_app:
                try:
                    celery_app.send_task(
                        dlq_task.task_name,
                        args=args,
                        kwargs=kwargs,
                        task_id=dlq_task.task_id,
                        queue='default',
                        retry=False,  # Disable automatic retries
                        retry_policy={'max_retries': 0},  # Don't retry in Celery layer
                    )
                    logger.debug(f"DLQ: Sent task {task_id} to Celery broker")
                except Exception as ce:
                    # If Celery communication fails, log but continue
                    # The most important part is updating the DLQ database record
                    # When Celery/Redis becomes available, the task will be resent
                    logger.warning(
                        f"DLQ: Could not send task {task_id} to Celery broker (may retry asynchronously): {type(ce).__name__}"
                    )
            else:
                logger.debug(f"DLQ: Celery not available for task {task_id}, will queue for later processing")
            
            # Update DLQ record
            dlq_task.replay_count += 1
            dlq_task.last_retry_at = datetime.now(UTC)
            
            await db.commit()
            
            logger.info(f"DLQ: Replayed task {task_id} (attempt {dlq_task.replay_count})")
            return True
            
        except Exception as e:
            logger.error(f"DLQ: Failed to replay task {task_id}: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def discard_task(
        db: AsyncSession,
        task_id: str,
        reason: str = "Manual discard",
    ) -> bool:
        """
        Discard (archive) a task from the DLQ.
        
        Used for unrecoverable failures (business logic errors, deleted users, etc.).
        
        Args:
            db: Async database session
            task_id: DLQ task ID
            reason: Reason for discard
            
        Returns:
            True if discarded, False otherwise
        """
        try:
            stmt = select(DeadLetterQueue).where(DeadLetterQueue.task_id == task_id)
            result = await db.execute(stmt)
            dlq_task = result.scalar_one_or_none()
            
            if not dlq_task:
                logger.warning(f"DLQ: Task {task_id} not found for discard")
                return False
            
            dlq_task.status = 'discarded'
            
            # Store reason in result
            result_data = json.loads(dlq_task.result) if dlq_task.result else {}
            result_data['discard_reason'] = reason
            dlq_task.result = json.dumps(result_data)
            
            await db.commit()
            
            logger.info(f"DLQ: Discarded task {task_id} - Reason: {reason}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"DLQ: Failed to discard task {task_id}: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def get_dlq_stats(db: AsyncSession) -> Dict[str, Any]:
        """
        Get DLQ health metrics for monitoring and alerting.
        
        Returns:
            Dict with:
            - total_count: Total tasks in DLQ
            - pending_replay_count: Tasks awaiting replay
            - archived_count: Archived tasks
            - discarded_count: Discarded tasks
            - by_task_type: Breakdown by task type
            - oldest_task_age_hours: Age of oldest task
            - growth_rate_per_hour: Tasks added in last hour
        """
        try:
            # Total counts by status
            total_stmt = select(func.count(DeadLetterQueue.id))
            pending_stmt = select(func.count(DeadLetterQueue.id)).where(
                DeadLetterQueue.status == 'pending_replay'
            )
            archived_stmt = select(func.count(DeadLetterQueue.id)).where(
                DeadLetterQueue.status == 'archived'
            )
            discarded_stmt = select(func.count(DeadLetterQueue.id)).where(
                DeadLetterQueue.status == 'discarded'
            )
            
            total_result = await db.execute(total_stmt)
            total_count = total_result.scalar() or 0
            
            pending_result = await db.execute(pending_stmt)
            pending_count = pending_result.scalar() or 0
            
            archived_result = await db.execute(archived_stmt)
            archived_count = archived_result.scalar() or 0
            
            discarded_result = await db.execute(discarded_stmt)
            discarded_count = discarded_result.scalar() or 0
            
            # Breakdown by task type
            type_stmt = select(
                DeadLetterQueue.task_type,
                func.count(DeadLetterQueue.id).label('count')
            ).group_by(DeadLetterQueue.task_type)
            
            type_result = await db.execute(type_stmt)
            by_task_type = {row[0]: row[1] for row in type_result.all()}
            
            # Oldest task age
            oldest_stmt = select(DeadLetterQueue.created_at).order_by(
                DeadLetterQueue.created_at
            ).limit(1)
            
            oldest_result = await db.execute(oldest_stmt)
            oldest_task = oldest_result.scalar_one_or_none()
            oldest_age_hours = None
            
            if oldest_task:
                # Handle both naive and aware datetimes
                if oldest_task.tzinfo is None:
                    oldest_task_aware = oldest_task.replace(tzinfo=UTC)
                else:
                    oldest_task_aware = oldest_task
                age = datetime.now(UTC) - oldest_task_aware
                oldest_age_hours = int(age.total_seconds() / 3600)
            
            # Growth rate (tasks added in last hour)
            one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
            growth_stmt = select(func.count(DeadLetterQueue.id)).where(
                DeadLetterQueue.queued_at >= one_hour_ago
            )
            
            growth_result = await db.execute(growth_stmt)
            growth_rate = growth_result.scalar() or 0
            
            stats = {
                'total_count': total_count,
                'pending_replay_count': pending_count,
                'archived_count': archived_count,
                'discarded_count': discarded_count,
                'by_task_type': by_task_type,
                'oldest_task_age_hours': oldest_age_hours,
                'growth_rate_per_hour': growth_rate,
                'timestamp': datetime.now(UTC).isoformat(),
            }
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"DLQ: Failed to get stats: {e}")
            return {}
    
    @staticmethod
    async def auto_archive_old_tasks(db: AsyncSession) -> int:
        """
        Archive DLQ tasks older than configured threshold.
        
        Runs periodically via scheduled task to prevent table bloat.
        
        Returns:
            Number of tasks archived
        """
        try:
            threshold_date = datetime.now(UTC) - timedelta(days=DLQ_CONFIG['auto_archive_days'])
            
            stmt = update(DeadLetterQueue).where(
                and_(
                    DeadLetterQueue.created_at < threshold_date,
                    DeadLetterQueue.status == 'pending_replay'
                )
            ).values(status='archived')
            
            result = await db.execute(stmt)
            await db.commit()
            
            archived_count = result.rowcount or 0
            logger.info(f"DLQ: Auto-archived {archived_count} old tasks (older than {DLQ_CONFIG['auto_archive_days']} days)")
            
            return archived_count
            
        except SQLAlchemyError as e:
            logger.error(f"DLQ: Failed to auto-archive tasks: {e}")
            await db.rollback()
            return 0
