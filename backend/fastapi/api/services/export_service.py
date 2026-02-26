import os
import json
import csv
import uuid
import logging
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..root_models import User, Score
from app.utils.file_validation import sanitize_filename, validate_file_path
from app.utils.atomic import atomic_write

logger = logging.getLogger(__name__)

class ExportService:
    """
    Service for securely exporting user data (Async).
    Handles data fetching, formatting, injection prevention, and safe file writing.
    """
    
    # Base directory for exports - relative to backend root or configured path
    EXPORT_DIR = Path("exports")

    @classmethod
    def ensure_export_dir(cls):
        """Ensure export directory exists."""
        cls.EXPORT_DIR.mkdir(exist_ok=True)

    @staticmethod
    def _sanitize_csv_field(field: Any) -> str:
        """
        Sanitize CSV fields to prevent formula injection attacks.
        Prepends ' to fields starting with =, +, -, or @.
        """
        if not isinstance(field, str):
            return str(field) if field is not None else ""
            
        if field and field.startswith(('=', '+', '-', '@')):
            return f"'{field}"
        return field

    @classmethod
    def _get_safe_filepath(cls, username: str, ext: str) -> str:
        """
        Generate a safe, collision-resistant filepath.
        Format: sanitize(username)_timestamp_shortuuid.ext
        """
        cls.ensure_export_dir()
        
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:8]
        safe_username = sanitize_filename(username)
        
        filename = f"{safe_username}_{timestamp}_{short_id}.{ext}"
        
        # Verify path using the strict validator
        full_path = str(cls.EXPORT_DIR / filename)
        
        # This will raise ValidationError if strict checks fail
        return validate_file_path(
            full_path, 
            allowed_extensions=[f".{ext}"],
            base_dir=str(cls.EXPORT_DIR.resolve())
        )

    @staticmethod
    async def _fetch_user_scores(db: AsyncSession, user_id: int) -> List[Score]:
        """Fetch all scores for a user."""
        stmt = select(Score).filter(Score.user_id == user_id).order_by(Score.timestamp.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def generate_export(cls, db: AsyncSession, user: User, format: str) -> Tuple[str, str]:
        """
        Generates an export file for the given user in the specified format.
        
        Args:
            db: Database session
            user: User object
            format: 'json' or 'csv'
            
        Returns:
            Tuple of (Absolute path to the generated file, job_id)
            
        Raises:
            ValueError: If format is invalid or other logical errors.
            IOError: If writing fails.
        """
        if format.lower() not in ('json', 'csv'):
            raise ValueError(f"Invalid format '{format}'. Supported: json, csv")

        scores = await cls._fetch_user_scores(db, user.id)
        
        # We use the short_id part of the filename as the Job ID for now
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        job_id = uuid.uuid4().hex[:8]
        safe_username = sanitize_filename(user.username)
        ext = format.lower()
        
        filename = f"{safe_username}_{timestamp}_{job_id}.{ext}"
        
        # Ensure dir
        cls.ensure_export_dir()
        
        # Verify path using the strict validator
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
            # Try to cleanup partial file if it exists (though atomic_write handles most cases)
            if os.path.exists(filepath):
                 try:
                     os.remove(filepath)
                 except:
                     pass
            raise e

    @classmethod
    def _write_json(cls, filepath: str, user: User, scores: List[Score]):
        """Write data to JSON file."""
        data = {
            "meta": {
                "username": user.username,
                "user_id": user.id,
                "exported_at": datetime.now(UTC).isoformat(),
                "record_count": len(scores),
                "version": "1.0"
            },
            "data": [
                {
                    "timestamp": s.timestamp,
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
        """Write data to CSV file with injection protection."""
        headers = [
            "Timestamp", "Total Score", "Sentiment Score", 
            "Reflection", "Is Rushed", "Is Inconsistent", "Age Group"
        ]
        
        with atomic_write(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for s in scores:
                writer.writerow([
                    cls._sanitize_csv_field(s.timestamp),
                    s.total_score,
                    s.sentiment_score,
                    cls._sanitize_csv_field(s.reflection_text),
                    s.is_rushed,
                    s.is_inconsistent,
                    cls._sanitize_csv_field(s.detailed_age_group)
                ])

    @classmethod
    def validate_export_access(cls, user: User, filename: str) -> bool:
        """
        Verify that a user is authorized to access the given filename.
        Strict ownership check based on filename convention: username_...
        """
        safe_username = sanitize_filename(user.username)
        # Check if filename starts with safe_username + "_"
        if not filename.startswith(f"{safe_username}_"):
            logger.warning(f"Access denied: User {user.username} tried to access {filename}")
            return False
            
        return True

    @classmethod
    def cleanup_old_exports(cls, max_age_hours: int = 24):
        """Delete export files older than max_age_hours."""
        try:
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
