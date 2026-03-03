import logging
import json
import csv
import io
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from ..models import AuditLog, User

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for securely logging user actions and retrieving audit history.
    """

    # Allowed fields in details JSON to prevent PII leakage
    ALLOWED_DETAIL_FIELDS = {
        "status", "reason", "method", "device", "location",
        "changed_field", "old_value", "outcome"
    }

    @classmethod
    async def log_event(
        cls,
        user_id: int,
        action: str,
        ip_address: Optional[str] = "SYSTEM",
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None
    ) -> bool:
        """Log a security-critical event."""
        if not db_session:
            logger.error("AuditLog requires a db_session")
            return False

        try:
            safe_ua = (user_agent[:250] + "...") if user_agent and len(user_agent) > 250 else user_agent

            safe_details = "{}"
            if details:
                filtered = {k: v for k, v in details.items() if k in cls.ALLOWED_DETAIL_FIELDS}
                try:
                    safe_details = json.dumps(filtered)
                except Exception as e:
                    logger.warning(f"Failed to serialize audit details: {e}")

            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=safe_ua,
                details=safe_details,
                timestamp=datetime.now(UTC)
            )

            db_session.add(log_entry)
            await db_session.commit()

            logger.info(f"AUDIT LOG: User {user_id} performed {action} from {ip_address}")
            return True

        except Exception as e:
            logger.critical(f"AUDIT LOG FAILURE: User {user_id} performed {action}. Error: {e}")
            await db_session.rollback()
            return False

    @classmethod
    async def log_auth_event(
        cls,
        action: str,
        username: str,
        ip_address: Optional[str] = "SYSTEM",
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None
    ) -> bool:
        """Log an auth event by username (finds user_id first)."""
        if not db_session:
            return False

        stmt = select(User.id).filter(User.username == username)
        result = await db_session.execute(stmt)
        user_id = result.scalar()

        if not user_id:
            logger.warning(f"AuditLog: Could not find user_id for username {username}")
            return False

        return await cls.log_event(
            user_id=user_id,
            action=action.upper(),
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            db_session=db_session
        )

    @staticmethod
    async def get_user_logs(
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        db_session: Optional[AsyncSession] = None
    ) -> List[AuditLog]:
        """Retrieve audit logs for a specific user with pagination."""
        if not db_session:
            return []

        try:
            offset = (page - 1) * per_page
            stmt = (
                select(AuditLog)
                .filter(AuditLog.user_id == user_id)
                .order_by(AuditLog.timestamp.desc())
                .limit(per_page)
                .offset(offset)
            )
            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to fetch audit logs for user {user_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Called by audit router: GET /audit/logs (admin)
    # ------------------------------------------------------------------
    @staticmethod
    async def query_logs(
        filters: Dict[str, Any],
        page: int,
        per_page: int,
        db: AsyncSession
    ) -> Tuple[List[AuditLog], int]:
        """
        Retrieve audit logs with optional filters and pagination.

        Supported filter keys: action, user_id, start_date, end_date.
        (event_type / resource_type / outcome / severity are stored in the
        JSON `details` column and available as a best-effort substring match.)
        """
        stmt = select(AuditLog)

        if filters.get("action"):
            stmt = stmt.filter(AuditLog.action.ilike(f"%{filters['action']}%"))

        if filters.get("username"):
            # Join user to filter by username
            stmt = stmt.join(User, AuditLog.user_id == User.id, isouter=True).filter(
                User.username.ilike(f"%{filters['username']}%")
            )

        if filters.get("start_date"):
            stmt = stmt.filter(AuditLog.timestamp >= filters["start_date"])

        if filters.get("end_date"):
            stmt = stmt.filter(AuditLog.timestamp <= filters["end_date"])

        # Best-effort filter for JSON-encoded fields
        for json_key in ("event_type", "resource_type", "outcome", "severity"):
            if filters.get(json_key):
                stmt = stmt.filter(
                    AuditLog.details.ilike(f"%{filters[json_key]}%")
                )

        # Total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply ordering + pagination
        stmt = stmt.order_by(AuditLog.timestamp.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(stmt)
        logs = list(result.scalars().all())

        return logs, total

    # ------------------------------------------------------------------
    # Called by audit router: GET /audit/my-activity
    # ------------------------------------------------------------------
    @staticmethod
    async def get_user_activity(
        user_id: int,
        page: int,
        per_page: int,
        db: AsyncSession
    ) -> Tuple[List[AuditLog], int]:
        """Return the requesting user's own audit history with pagination."""
        stmt = select(AuditLog).filter(AuditLog.user_id == user_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            stmt.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    # ------------------------------------------------------------------
    # Called by audit router: POST /audit/archive
    # ------------------------------------------------------------------
    @staticmethod
    async def archive_old_logs(
        retention_days: int,
        db: AsyncSession
    ) -> int:
        """
        Soft-archive (delete) logs older than `retention_days`.

        In a production system this would move rows to a cold-storage table
        or an S3 archival pipeline. For now it deletes them from the hot
        table and returns the count so the caller can log the outcome.
        """
        try:
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            stmt = delete(AuditLog).filter(AuditLog.timestamp < cutoff)
            result = await db.execute(stmt)
            await db.commit()
            archived = result.rowcount
            logger.info(f"Archived (deleted) {archived} audit logs older than {retention_days} days.")
            return archived
        except Exception as e:
            await db.rollback()
            logger.error(f"Audit archive failed: {e}")
            return 0

    # ------------------------------------------------------------------
    # Called by audit router: POST /audit/cleanup
    # ------------------------------------------------------------------
    @staticmethod
    async def cleanup_expired_logs(db: AsyncSession, days: int = 90) -> int:
        """Delete logs older than the default retention period (90 days)."""
        try:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            stmt = delete(AuditLog).filter(AuditLog.timestamp < cutoff)
            result = await db.execute(stmt)
            await db.commit()
            deleted = result.rowcount
            logger.info(f"Cleaned up {deleted} expired audit logs.")
            return deleted
        except Exception as e:
            await db.rollback()
            logger.error(f"Audit cleanup failed: {e}")
            return 0

    # ------------------------------------------------------------------
    # Called by audit router: GET /audit/export
    # ------------------------------------------------------------------
    @staticmethod
    async def export_logs(
        filters: Dict[str, Any],
        fmt: str,
        db: AsyncSession
    ) -> Any:
        """
        Export audit logs in JSON or CSV format.

        Returns:
          - list[dict] for fmt == "json"
          - str (CSV text) for fmt == "csv"
        """
        # Reuse query_logs with a large page size for export
        logs, _ = await AuditService.query_logs(
            filters=filters,
            page=1,
            per_page=10_000,  # hard cap; in prod use streaming
            db=db
        )

        rows = [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "ip_address": getattr(log, "ip_address", None),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "details": log.details,
            }
            for log in logs
        ]

        if fmt.lower() == "csv":
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return output.getvalue()

        return rows  # default: JSON-serialisable list