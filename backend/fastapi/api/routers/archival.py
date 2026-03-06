import os
import uuid
import logging
from typing import Annotated
from datetime import datetime, timezone, timedelta
UTC = timezone.utc
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse

from ..services.db_service import get_db, AsyncSessionLocal
from ..services.data_archival_service import DataArchivalService
from ..schemas.archival import ArchiveRequest, ArchiveResponse, PurgeResponse, UndoPurgeResponse
from .auth import get_current_user, require_admin
from ..models import User, ExportRecord

router = APIRouter(tags=["GDPR Archival & Purge"])
logger = logging.getLogger("api.archival")

async def _background_archive_generation(
    user_id: int, 
    password: str, 
    include_pdf: bool,
    include_csv: bool,
    include_json: bool
):
    """
    Executes the ZIP archival asynchronously.
    """
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"Archival failed: User {user_id} not found.")
            return

        try:
            filepath, export_id = await DataArchivalService.generate_comprehensive_archive(
                db=db,
                user=user,
                password=password,
                include_pdf=include_pdf,
                include_csv=include_csv,
                include_json=include_json
            )
            # In a real system, we might trigger a WebSocket or push notification here.
            logger.info(f"Background archive complete for {user.username}. ID: {export_id}")
        except Exception as e:
            logger.error(f"Background archive failed for {user.username}: {e}")

@router.post("/archive/generate", response_model=ArchiveResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_personal_archive(
    req: ArchiveRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Request a comprehensive, password-protected ZIP archive of all personal data.
    The archive includes a high-fidelity PDF report, structured JSON, and tabular CSVs.
    Runs asynchronously in the background.
    """
    from api.services.background_task_service import BackgroundTaskService, TaskType
    from api.celery_tasks import generate_archive_task

    task = await BackgroundTaskService.create_task(
        db=db,
        user_id=current_user.id,
        task_type=TaskType.EXPORT_JSON,  # Treating as export/archival
        params={"type": "archival", "include_pdf": req.include_pdf, "include_csv": req.include_csv, "include_json": req.include_json}
    )
    job_id = task.job_id
    
    generate_archive_task.delay(
        job_id,
        current_user.id,
        req.password,
        req.include_pdf,
        req.include_csv,
        req.include_json
    )
    
    return ArchiveResponse(
        job_id=job_id,
        status="processing",
        message="Your archive is being generated. You will be notified when the secure download link is ready."
    )

@router.delete("/purge", response_model=PurgeResponse)
async def request_secure_purge(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Initiates a Secure Purge (Soft Delete) of all user data.
    Data will be permanently hard-deleted after a 30-day grace period.
    """
    try:
        purge_date = await DataArchivalService.initiate_secure_purge(db, current_user)
        can_undo_until = purge_date + timedelta(days=30)
        
        return PurgeResponse(
            message="Your account is scheduled for deletion. You have 30 days to undo this action.",
            purge_date=purge_date,
            can_undo_until=can_undo_until
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/purge/undo", response_model=UndoPurgeResponse)
async def undo_secure_purge(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Undo a previously requested Secure Purge, provided it is within the 30-day window.
    """
    try:
        await DataArchivalService.undo_secure_purge(db, current_user)
        return UndoPurgeResponse(
            message="Your account deletion request has been canceled.",
            status="restored"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/archive/{export_id}/download")
async def download_secure_archive(
    export_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Download a generated ZIP archive using its export_id.
    """
    from sqlalchemy import select
    stmt = select(ExportRecord).where(
        ExportRecord.export_id == export_id,
        ExportRecord.user_id == current_user.id
    )
    result = await db.execute(stmt)
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(status_code=404, detail="Archive not found.")
        
    if export.expires_at and export.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Secure download link expired.")
        
    if not os.path.exists(export.file_path):
        raise HTTPException(status_code=404, detail="File no longer exists on the server.")
        
    return FileResponse(
        path=export.file_path, 
        filename=os.path.basename(export.file_path),
        media_type="application/zip"
    )

@router.post("/purge/scrub", dependencies=[Depends(require_admin)])
async def trigger_scrub_worker(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Manually triggers the GDPR hard-purge worker.
    Purges all users whose 30-day grace period has expired across SQL, S3, and Vector stores.
    Admin only.
    """
    count = await DataArchivalService.execute_hard_purges(db)
    return {"message": f"Scrubbing complete. {count} users permanently purged.", "count": count}
