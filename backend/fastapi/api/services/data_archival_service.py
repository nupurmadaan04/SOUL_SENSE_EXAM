import os
import io
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

try:
    import pyzipper
except ImportError:
    pyzipper = None

from .storage_service import get_storage_service
from ..models import (
    User, ExportRecord, Score, JournalEntry, UserSettings,
    PersonalProfile, MedicalProfile, UserStrengths,
    UserEmotionalPatterns, SatisfactionRecord,
    AssessmentResult, Response, UserSession
)
from ..utils.file_validation import sanitize_filename
from .scrubber_service import scrubber_service

logger = logging.getLogger("api.archival")

class DataArchivalService:
    """
    Handles GDPR-compliant comprehensive data portability and secure archival.
    Creates password-protected ZIP archives containing PDF, CSV, and JSON representations.
    Manages the Secure Purge (Soft Delete with 30-day Undo -> Hard Delete) lifecycle.
    """

    @staticmethod
    async def generate_comprehensive_archive(
        db: AsyncSession, 
        user: User, 
        password: str,
        include_pdf: bool = True,
        include_csv: bool = True,
        include_json: bool = True
    ) -> Tuple[str, str]:
        """
        Generates a comprehensive export (JSON, CSV, PDF) and bundles them into a password-protected ZIP.
        Returns the (filepath, export_id).
        """
        if pyzipper is None:
            raise RuntimeError("pyzipper is required for password-protected archives. Install it via pip.")

        export_id = uuid.uuid4().hex
        timestamp = datetime.now(UTC)
        
        # 1. Fetch comprehensive user data
        options = {"data_types": list(ExportServiceV2.DATA_TYPES)}
        data = await ExportServiceV2._fetch_export_data(db, user, options)
        metadata = ExportServiceV2._build_metadata(user, export_id, "zip_archive", options, timestamp)
        data['_export_metadata'] = metadata

        # 2. Setup file paths
        ext = "zip"
        filepath = ExportServiceV2._get_safe_filepath(user.username, ext)

        # 3. Create the password-protected ZIP using pyzipper
        zip_buffer = io.BytesIO()
        try:
            with pyzipper.AESZipFile(
                zip_buffer, 
                'w', 
                compression=pyzipper.ZIP_DEFLATED, 
                encryption=pyzipper.WZ_AES
            ) as zf:
                zf.setpassword(password.encode('utf-8'))

                # --- Add JSON ---
                if include_json:
                    json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
                    zf.writestr(f"{user.username}_data.json", json_str.encode('utf-8'))

                # --- Add PDF ---
                if include_pdf:
                    import tempfile
                    import aiofiles
                    tmp_fd, tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(tmp_fd)
                    
                    try:
                        # Note: _write_pdf is currently sync, but we read it back async
                        ExportServiceV2._write_pdf(tmp_pdf_path, data, user)
                        
                        # Requirement #1233: Use Async Context Manager for file reading
                        async with aiofiles.open(tmp_pdf_path, mode='rb') as pdf_f:
                            pdf_content = await pdf_f.read()
                            zf.writestr(f"{user.username}_report.pdf", pdf_content)
                        
                        from ..utils.fd_guard import FDGuard
                        FDGuard.check_fd_usage("archive_pdf_read_async")
                    except Exception as e:
                        logger.error(f"Failed to include PDF in archive for user {user.id}: {e}")
                    finally:
                        if os.path.exists(tmp_pdf_path):
                            try:
                                os.remove(tmp_pdf_path)
                            except Exception as e:
                                logger.warning(f"Failed to remove temp PDF '{tmp_pdf_path}': {e}")

                # --- Add CSV Bundle ---
                if include_csv:
                    from .export_service_v2 import csv
                    def _add_csv(filename: str, rows: list):
                        if not rows: return
                        with io.StringIO() as buffer:
                            fieldnames = set()
                            for row in rows: fieldnames.update(row.keys())
                            writer = csv.DictWriter(buffer, fieldnames=sorted(list(fieldnames)))
                            writer.writeheader()
                            for row in rows:
                                safe = {k: ExportServiceV2._sanitize_csv_field(v) for k, v in row.items()}
                                writer.writerow(safe)
                            zf.writestr(f"csv_data/{filename}", buffer.getvalue().encode('utf-8-sig'))

                    for key, value in data.items():
                        if key == '_export_metadata': continue
                        if isinstance(value, list):
                            _add_csv(f'{key}.csv', value)
                        elif isinstance(value, dict):
                            _add_csv(f'{key}.csv', [value])

            # Requirement #1233: Use Async Context Manager for final storage write
            import aiofiles
            async with aiofiles.open(filepath, mode='wb') as f:
                await f.write(zip_buffer.getvalue())
            
            from ..utils.fd_guard import FDGuard
            FDGuard.check_fd_usage("archive_zip_write_async")

        except Exception as e:
            logger.error(f"Failed to generate or write ZIP archive: {e}")
            raise RuntimeError(f"Storage write failure: {e}")
        finally:
            zip_buffer.close()

        # 4. Record Export in DB
        record = ExportRecord(
            export_id=export_id,
            user_id=user.id,
            file_path=filepath,
            format="zip_archive",
            status="completed",
            created_at=timestamp,
            expires_at=timestamp + timedelta(days=7), # Archive available for 7 days
            is_encrypted=True
        )
        db.add(record)
        await db.commit()

        return filepath, export_id

    @staticmethod
    async def archive_stale_journals(db: AsyncSession) -> int:
        """
        Archives stale journals to cold storage.
        Moves content older than archival_threshold_years to S3 and sets archive_pointer.
        Returns the number of entries archived.
        """
        from ..config import get_settings_instance
        settings = get_settings_instance()
        storage = get_storage_service()

        # Calculate threshold date
        threshold_date = datetime.now(UTC) - timedelta(days=settings.archival_threshold_years * 365)

        # Find stale entries that haven't been archived yet
        stmt = select(JournalEntry).where(
            JournalEntry.timestamp <= threshold_date,
            JournalEntry.content.isnot(None),  # Has content
            JournalEntry.archive_pointer.is_(None),  # Not already archived
            JournalEntry.is_deleted == False
        )
        result = await db.execute(stmt)
        stale_entries = result.scalars().all()

        archived_count = 0
        for entry in stale_entries:
            try:
                # Generate S3 key
                import uuid
                s3_key = f"journals/{entry.user_id}/{entry.id}_{uuid.uuid4().hex[:8]}.json"

                # Prepare content for storage
                content_data = {
                    "id": entry.id,
                    "user_id": entry.user_id,
                    "username": entry.username,
                    "title": entry.title,
                    "content": entry.content,
                    "timestamp": entry.timestamp,
                    "is_deleted": entry.is_deleted,
                    "tags": entry.tags,
                    "sentiment_score": entry.sentiment_score,
                    "emotional_patterns": entry.emotional_patterns,
                    "embedding": entry.embedding,
                    "archived_at": datetime.now(UTC).isoformat()
                }
                content_json = json.dumps(content_data, ensure_ascii=False, default=str)

                # Store in cold storage
                archive_uri = await storage.store_content(content_json, s3_key)
                if archive_uri:
                    # Update database: clear content and set archive pointer
                    entry.content = None
                    entry.archive_pointer = archive_uri
                    logger.info(f"Archived journal {entry.id} to {archive_uri}")
                    archived_count += 1
                else:
                    logger.error(f"Failed to archive journal {entry.id} to cold storage")

            except Exception as e:
                logger.error(f"Error archiving journal {entry.id}: {e}")
                continue

        # Commit all changes
        if archived_count > 0:
            await db.commit()

        logger.info(f"Archived {archived_count} stale journals to cold storage")
        return archived_count

    @staticmethod
    async def initiate_secure_purge(db: AsyncSession, user: User) -> datetime:
        """
        Initiates a secure purge (Soft Delete). Sets the timer for 30 days.
        """
        if user.is_deleted:
            raise ValueError("Account is already scheduled for deletion.")
            
        now = datetime.now(UTC)
        user.is_deleted = True
        user.deleted_at = now
        # We could also invalidate all sessions / refresh tokens here
        # to forcefully log them out of all devices.
        
        await db.commit()
        return now

    @staticmethod
    async def undo_secure_purge(db: AsyncSession, user: User) -> None:
        """
        Reverts the Secure Purge if within the 30-day window.
        """
        if not user.is_deleted:
            raise ValueError("Account is not scheduled for deletion.")
            
        user.is_deleted = False
        user.deleted_at = None
        
        await db.commit()

    @staticmethod
    async def execute_hard_purges(db: AsyncSession) -> int:
        """
        Idempotent worker factor:
        1. Find new users past the 30-day grace period and start their saga.
        2. Find and resume any 'PENDING', 'ASSETS_DELETED', or 'FAILED' sagas.
        """
        # --- PHASE 1: Start new sagas for expired users ---
        threshold_date = datetime.now(UTC) - timedelta(days=30)
        stmt = select(User.id).where(
            User.is_deleted == True,
            User.deleted_at <= threshold_date
        )
        result = await db.execute(stmt)
        user_ids = result.scalars().all()
        
        # --- PHASE 2: Re-fetch user_ids from incomplete sagas to ensure progress ---
        saga_stmt = select(GDPRScrubLog.user_id).where(
            GDPRScrubLog.status.in_(['PENDING', 'ASSETS_DELETED', 'FAILED'])
        )
        saga_res = await db.execute(saga_stmt)
        pending_ids = saga_res.scalars().all()
        
        # Combine and deduplicate
        all_ids_to_process = list(set(user_ids) | set(pending_ids))
        
        count = 0
        for user_id in all_ids_to_process:
            try:
                # scrub_user is now idempotent and saga-based
                await scrubber_service.scrub_user(db, user_id)
                
                # Check if it actually completed to count it
                status = await scrubber_service.get_scrub_status_by_user(db, user_id)
                if status == 'COMPLETED':
                    count += 1
                    logger.info(f"GDPR: Hard purge completed for user {user_id}")
            except Exception as e:
                logger.error(f"GDPR: Saga execution failed for user {user_id}: {e}")
                continue
            
        return count

    @staticmethod
    async def get_scrub_status_by_user(db: AsyncSession, user_id: int) -> Optional[str]:
        """Helper to get status by user_id."""
        from ..models import GDPRScrubLog
        stmt = select(GDPRScrubLog.status).where(GDPRScrubLog.user_id == user_id).order_by(GDPRScrubLog.updated_at.desc())
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
