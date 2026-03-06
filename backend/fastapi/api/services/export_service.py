import os
import json
import csv
import uuid
import logging
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import User, Score, UserSession
from ..utils.file_validation import sanitize_filename, validate_file_path
from ..utils.atomic import atomic_write
from ..utils.distributed_lock import require_lock

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class ExportService:
    """
    Service for securely exporting user data (Async).
    """
    
    EXPORT_DIR = Path("exports")

    @classmethod
    def ensure_export_dir(cls):
        """Ensure export directory exists."""
        cls.EXPORT_DIR.mkdir(exist_ok=True)

    @staticmethod
    def _sanitize_csv_field(field: Any) -> str:
        """Sanitize CSV fields."""
        """Sanitize CSV fields to prevent formula injection attacks."""
        if not isinstance(field, str):
            return str(field) if field is not None else ""
        if field and field.startswith(('=', '+', '-', '@')):
            return f"'{field}"
        return field

    @classmethod
    def _get_safe_filepath(cls, username: str, ext: str) -> str:
        """Generate safe filepath."""
        cls.ensure_export_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        """Generate a safe, collision-resistant filepath."""
        cls.ensure_export_dir()
        
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:8]
        safe_username = sanitize_filename(username)
        filename = f"{safe_username}_{timestamp}_{short_id}.{ext}"
        full_path = str(cls.EXPORT_DIR / filename)
        return validate_file_path(full_path, allowed_extensions=[f".{ext}"], base_dir=str(cls.EXPORT_DIR.resolve()))

    @staticmethod
    async def _fetch_user_scores(db: AsyncSession, user_id: int) -> List[Score]:
        """Fetch all scores (Async)."""
        stmt = select(Score).filter(Score.user_id == user_id).order_by(Score.timestamp.desc())
        
        return validate_file_path(
            full_path, 
            allowed_extensions=[f".{ext}"],
            base_dir=str(cls.EXPORT_DIR.resolve())
        )

    @staticmethod
    async def _fetch_user_scores(db: AsyncSession, user_id: int) -> List[Score]:
        """Fetch all scores for a user."""
        stmt = select(Score).join(UserSession, Score.session_id == UserSession.session_id).filter(
            UserSession.user_id == user_id
        ).order_by(Score.timestamp.desc())
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def generate_export(cls, db: AsyncSession, user: User, format: str) -> Tuple[str, str]:
        """Generate export (Async)."""
    @require_lock(name="export_v1_{user.id}_{format}", timeout=60)
    async def generate_export(cls, db: AsyncSession, user: User, format: str) -> Tuple[str, str]:
        """Generates an export file for the given user in the specified format."""
        if format.lower() not in ('json', 'csv'):
            raise ValueError(f"Invalid format '{format}'")

        scores = await cls._fetch_user_scores(db, user.id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        job_id = uuid.uuid4().hex[:8]
        safe_username = sanitize_filename(user.username)
        ext = format.lower()
        filename = f"{safe_username}_{timestamp}_{job_id}.{ext}"
        
        cls.ensure_export_dir()
        full_path = str(cls.EXPORT_DIR / filename)
        filepath = validate_file_path(full_path, allowed_extensions=[f".{ext}"], base_dir=str(cls.EXPORT_DIR.resolve()))
        cls.ensure_export_dir()
        
        full_path = str(cls.EXPORT_DIR / filename)
        filepath = validate_file_path(
            full_path, 
            allowed_extensions=[f".{ext}"],
            base_dir=str(cls.EXPORT_DIR.resolve())
        )
        
        try:
            if format.lower() == 'json':
                cls._write_json(filepath, user, scores)
            else:
                cls._write_csv(filepath, user, scores)
            logger.info(f"Export generated for {user.username}: {filepath}")
            return filepath, job_id
        except Exception as e:
            logger.error(f"Failed to generate export for {user.username}: {e}")
            if os.path.exists(filepath):
                 try: os.remove(filepath)
                 except: pass
            raise e

    @classmethod
    def _write_json(cls, filepath: str, user: User, scores: List[Score]):
        """Write JSON."""
        data = {
            "metadata": {
                "username": user.username,
                "user_id": user.id,
                "exported_at": datetime.now(UTC).isoformat(),
                "record_count": len(scores),
                "version": "1.0"
            },
            "data": [
                {
                    "timestamp": s.timestamp.isoformat() if isinstance(s.timestamp, datetime) else s.timestamp,
                    "total_score": s.total_score,
                    "sentiment_score": s.sentiment_score,
                    "reflection_text": s.reflection_text,
                    "is_rushed": s.is_rushed,
                    "is_inconsistent": s.is_inconsistent,
                    "age_group_snapshot": s.detailed_age_group
                } for s in scores
            ]
        }
        with atomic_write(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def _write_csv(cls, filepath: str, user: User, scores: List[Score]):
        """Write CSV."""
        headers = ["Timestamp", "Total Score", "Sentiment Score", "Reflection", "Is Rushed", "Is Inconsistent", "Age Group"]
        with atomic_write(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for s in scores:
                ts = s.timestamp.isoformat() if isinstance(s.timestamp, datetime) else s.timestamp
                writer.writerow([
                    cls._sanitize_csv_field(s.timestamp), s.total_score, s.sentiment_score,
                    cls._sanitize_csv_field(s.reflection_text), s.is_rushed, s.is_inconsistent,
                    cls._sanitize_csv_field(ts),
                    s.total_score,
                    s.sentiment_score,
                    cls._sanitize_csv_field(s.reflection_text),
                    s.is_rushed,
                    s.is_inconsistent,
                    cls._sanitize_csv_field(s.detailed_age_group)
                ])

    @classmethod
    def validate_export_access(cls, user: User, filename: str) -> bool:
        """Verify access."""
        """Verify that a user is authorized to access the given filename."""
        safe_username = sanitize_filename(user.username)
        if not filename.startswith(f"{safe_username}_"):
            logger.warning(f"Access denied: User {user.username} tried to access {filename}")
            return False
        return True

    @classmethod
    def cleanup_old_exports(cls, max_age_hours: int = 24):
        """Cleanup."""
        try:
            if not cls.EXPORT_DIR.exists(): return
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            if not cls.EXPORT_DIR.exists():
                return
                
            cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
            
            for p in cls.EXPORT_DIR.glob("*"):
                if p.is_file():
                    try:
                        mtime = datetime.fromtimestamp(p.stat().st_mtime, UTC)
                        if mtime < cutoff:
                            p.unlink()
                            logger.info(f"Deleted old export: {p.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {p.name}: {e}")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
