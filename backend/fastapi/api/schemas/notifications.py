from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class NotificationPreferenceBase(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    marketing_alerts: Optional[bool] = None
    security_alerts: Optional[bool] = None
    insight_alerts: Optional[bool] = None
    reminder_alerts: Optional[bool] = None
    
    # Daily reminder settings (Issue #1328)
    daily_reminder_enabled: Optional[bool] = None
    reminder_time: Optional[str] = None  # HH:MM format
    reminder_frequency: Optional[str] = None  # daily, weekly, custom
    reminder_days: Optional[List[str]] = None  # ["Mon", "Tue", ...]
    reminder_message: Optional[str] = None

class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: int
    user_id: int

class NotificationReminderCreate(BaseModel):
    """Create a new notification reminder."""
    reminder_type: str = "emotion_logging"
    reminder_title: str = "Time to log your emotions"
    reminder_body: Optional[str] = None
    delivery_channel: str = "push"

class NotificationReminderUpdate(BaseModel):
    """Update an existing notification reminder."""
    reminder_title: Optional[str] = None
    reminder_body: Optional[str] = None
    status: Optional[str] = None  # active, paused, disabled
    delivery_channel: Optional[str] = None

class NotificationReminderResponse(BaseModel):
    """Response model for notification reminders."""
    id: int
    user_id: int
    preference_id: int
    scheduled_time: datetime
    last_sent_at: Optional[datetime] = None
    status: str
    reminder_type: str
    reminder_title: str
    reminder_body: Optional[str] = None
    is_sent: bool
    delivery_channel: str
    delivery_attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ReminderSettingsUpdate(BaseModel):
    """Update user's reminder settings (Issue #1328)."""
    daily_reminder_enabled: bool
    reminder_time: str  # HH:MM format
    reminder_frequency: str = "daily"  # daily, weekly, custom
    reminder_days: Optional[List[str]] = None
    reminder_message: Optional[str] = None

class NotificationTemplateCreate(BaseModel):
    name: str
    subject_template: str
    body_html_template: Optional[str] = None
    body_text_template: Optional[str] = None
    language: str = "en"
    is_active: bool = True

class NotificationTemplateResponse(NotificationTemplateCreate):
    id: int

class NotificationSendRequest(BaseModel):
    user_id: int
    template_name: str
    context: Dict[str, Any] = {}
    force_channels: Optional[List[str]] = None

class NotificationLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    template_name: str
    channel: str
    status: str
    error_message: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
