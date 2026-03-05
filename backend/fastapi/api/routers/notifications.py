import uuid
import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..services.db_service import get_db
from ..services.notification_service import NotificationOrchestrator
from ..services.notification_reminder_service import NotificationReminderService
from ..schemas.notifications import (
    NotificationPreferenceResponse, NotificationPreferenceBase,
    NotificationTemplateCreate, NotificationTemplateResponse,
    NotificationSendRequest, NotificationLogResponse,
    NotificationReminderCreate, NotificationReminderUpdate, NotificationReminderResponse,
    ReminderSettingsUpdate
)
from .auth import get_current_user, require_admin
from ..models import User, NotificationTemplate, NotificationLog, NotificationPreference, NotificationReminder

router = APIRouter(tags=["Notifications"])
logger = logging.getLogger("api.notifications")

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_my_notification_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Retrieve the current user's notification channel and alert preferences."""
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    
    if not pref:
        # Create default preferences
        pref = NotificationPreference(
            user_id=current_user.id,
            email_enabled=True,
            push_enabled=False,
            in_app_enabled=True,
            marketing_alerts=False,
            security_alerts=True,
            insight_alerts=True,
            reminder_alerts=True
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        
    return pref

@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_my_notification_preferences(
    req: NotificationPreferenceBase,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Update notification preferences."""
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    
    if not pref:
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
        
    update_data = req.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(pref, key, val)
        
    await db.commit()
    await db.refresh(pref)
    return pref

@router.get("/logs", response_model=List[NotificationLogResponse])
async def get_my_notification_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 20
):
    """Retrieve a history of notifications sent to the current user."""
    stmt = select(NotificationLog).where(
        NotificationLog.user_id == current_user.id
    ).order_by(NotificationLog.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return logs

# =====================================================================
# ADMIN ENDPOINTS: TEMPLATES & TESTING
# =====================================================================

@router.post("/admin/templates", response_model=NotificationTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    req: NotificationTemplateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):
    """(Admin) Create a new Jinja2 notification template."""
    stmt = select(NotificationTemplate).where(NotificationTemplate.name == req.name)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Template with this name already exists")
        
    template = NotificationTemplate(**req.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.get("/admin/templates", response_model=List[NotificationTemplateResponse])
async def list_templates(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):
    """(Admin) List all templates."""
    res = await db.execute(select(NotificationTemplate))
    return res.scalars().all()

@router.post("/admin/send", status_code=status.HTTP_202_ACCEPTED)
async def trigger_test_notification(
    req: NotificationSendRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):
    """
    (Admin) Dispatch a test notification securely to a target user.
    Uses Celery/AsyncOrchestrator to queue and execute template rendering & delivery.
    """
    stmt = select(User).where(User.id == req.user_id)
    target_user = (await db.execute(stmt)).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
        
    # Validates template syntax synchronously before enqueueing 
    try:
        await NotificationOrchestrator.render_template(db, req.template_name, req.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Dispatch Background Tasks (this handles multi-channel fanout)
    background_tasks.add_task(
        NotificationOrchestrator.dispatch_notification,
        db=db,
        user=target_user,
        template_name=req.template_name,
        context=req.context,
        force_channels=req.force_channels
    )
    
    return {"message": f"Successfully queued notification to user {req.user_id}"}


# =====================================================================
# REMINDER ENDPOINTS: Issue #1328 - Push Notification Reminder System
# =====================================================================

@router.get("/reminders/settings", response_model=NotificationPreferenceResponse)
async def get_reminder_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get the current user's reminder settings."""
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    
    if not pref:
        # Create default preferences
        pref = NotificationPreference(user_id=current_user.id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        
    return pref

@router.put("/reminders/settings", response_model=NotificationPreferenceResponse)
async def update_reminder_settings(
    req: ReminderSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Update the current user's reminder settings.
    Automatically schedules reminders when enabled.
    """
    pref = NotificationReminderService.update_preference_settings(
        db=db,
        user_id=current_user.id,
        daily_reminder_enabled=req.daily_reminder_enabled,
        reminder_time=req.reminder_time,
        reminder_frequency=req.reminder_frequency,
        reminder_days=req.reminder_days,
        reminder_message=req.reminder_message,
    )
    
    return pref

@router.get("/reminders", response_model=List[NotificationReminderResponse])
async def get_my_reminders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: Optional[str] = None
):
    """Get the current user's scheduled reminders."""
    reminders = NotificationReminderService.get_reminders_by_user(
        db=db,
        user_id=current_user.id,
        status=status
    )
    
    return reminders

@router.post("/reminders", response_model=NotificationReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    req: NotificationReminderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Create a new reminder for the current user."""
    reminder = NotificationReminderService.create_reminder(
        db=db,
        user_id=current_user.id,
        reminder_data=req,
    )
    
    return reminder

@router.put("/reminders/{reminder_id}", response_model=NotificationReminderResponse)
async def update_reminder(
    reminder_id: int,
    req: NotificationReminderUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Update a specific reminder."""
    # Verify ownership
    stmt = select(NotificationReminder).where(NotificationReminder.id == reminder_id)
    reminder = (await db.execute(stmt)).scalar_one_or_none()
    
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    updated = NotificationReminderService.update_reminder(
        db=db,
        reminder_id=reminder_id,
        reminder_data=req,
    )
    
    return updated

@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Delete a specific reminder."""
    # Verify ownership
    stmt = select(NotificationReminder).where(NotificationReminder.id == reminder_id)
    reminder = (await db.execute(stmt)).scalar_one_or_none()
    
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    success = NotificationReminderService.delete_reminder(db=db, reminder_id=reminder_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return None

