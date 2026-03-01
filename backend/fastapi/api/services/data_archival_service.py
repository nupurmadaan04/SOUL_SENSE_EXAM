import os
import io
import json
import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

try:
    import pyzipper
except ImportError:
    pyzipper = None

from .export_service_v2 import ExportServiceV2
from ..models import (
    User, ExportRecord, Score, JournalEntry, UserSettings,
    PersonalProfile, MedicalProfile, UserStrengths,
    UserEmotionalPatterns, SatisfactionRecord,
    AssessmentResult, Response, UserSession
)
from ..utils.file_validation import sanitize_filename

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
                # We need to temporarily write PDF to disk or buffer
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf_path = tmp_pdf.name
                
                try:
                    ExportServiceV2._write_pdf(tmp_pdf_path, data, user)
                    with open(tmp_pdf_path, 'rb') as pdf_f:
                        zf.writestr(f"{user.username}_report.pdf", pdf_f.read())
                except Exception as e:
                    logger.error(f"Failed to include PDF in archive: {e}")
                finally:
                    if os.path.exists(tmp_pdf_path):
                        os.remove(tmp_pdf_path)

            # --- Add CSV Bundle ---
            if include_csv:
                from .export_service_v2 import csv
                def _add_csv(filename: str, rows: list):
                    if not rows: return
                    buffer = io.StringIO()
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

        # Write to disk
        with open(filepath, 'wb') as f:
            f.write(zip_buffer.getvalue())

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
        Background worker function to permanently delete users whose 30-day grace period has expired.
        Returns the number of users purged.
        """
        threshold_date = datetime.now(UTC) - timedelta(days=30)
        
        stmt = select(User).where(
            User.is_deleted == True,
            User.deleted_at <= threshold_date
        )
        result = await db.execute(stmt)
        users_to_purge = result.scalars().all()
        
        count = 0
        for user in users_to_purge:
            # SQLAlchemy will handle cascade="all, delete-orphan" for related objects
            # defined in the relationships. For any unmapped/manual orphaned blobs
            # (e.g. S3 objects, local files) we would add cleanup code here.
            
            # Example: Clean up pending exports on disk
            export_stmt = select(ExportRecord).where(ExportRecord.user_id == user.id)
            exp_res = await db.execute(export_stmt)
            exports = exp_res.scalars().all()
            for exp in exports:
                if os.path.exists(exp.file_path):
                    try:
                        os.remove(exp.file_path)
                    except: pass
            
            await db.delete(user)
            count += 1
            
        await db.commit()
        return count

    @staticmethod
    async def archive_stale_journals(db: AsyncSession) -> int:
        """
        Automated Cold Storage Archival Pipeline (#1125).
        Moves 2+ year old journals to S3.
        """
        from ..config import get_settings_instance
        from .storage_service import get_storage_service
        
        settings = get_settings_instance()
        storage = get_storage_service()
        threshold = datetime.now(UTC) - timedelta(days=settings.archival_threshold_years * 365)
        
        # We fetch 50 entries at a time to avoid overwhelming the worker or database
        stmt = select(JournalEntry).filter(
            JournalEntry.is_deleted == False,
            JournalEntry.archive_pointer == None
        ).limit(50)
        
        res = await db.execute(stmt)
        entries = res.scalars().all()
        
        archived_count = 0
        for entry in entries:
            try:
                # Parse timestamp (SQLite stores as ISO String)
                ts = entry.timestamp
                if not ts: continue
                entry_date = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                
                if entry_date > threshold:
                    continue
                
                # 1. Transmit encrypted ciphertext to S3
                key = f"archives/journals/{entry.tenant_id or 'global'}/{entry.user_id}/{entry.id}.enc"
                metadata = {
                    "user_id": str(entry.user_id),
                    "tenant_id": str(entry.tenant_id),
                    "archived_at": datetime.now(UTC).isoformat()
                }
                
                pointer = storage.upload_encrypted_content(
                    key=key,
                    content=entry.content, # Preserves ENC: ciphertext
                    metadata=metadata
                )
                
                # 2. Update DB: Store pointer and clear hot content
                entry.archive_pointer = pointer
                entry.content = None 
                archived_count += 1
                
            except Exception as e:
                logger.error(f"Failed to archive journal {entry.id}: {e}")
                
        if archived_count > 0:
            await db.commit()
            logger.info(f"Archival Pipeline: Successfully moved {archived_count} journals to cold storage.")
        
        return archived_count
