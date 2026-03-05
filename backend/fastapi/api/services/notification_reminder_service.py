"""
Notification Reminder Service for managing scheduled emotion logging reminders.
Handles creation, update, deletion, and scheduling of daily reminders.

Issue #1328: Push Notification Reminder System
- Schedule local push notifications
- Add reminder toggle in settings
- Notifications trigger on schedule
- User can disable anytime
"""

from datetime import datetime, timedelta, time
from typing import Optional, List
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models import NotificationReminder, NotificationPreference, User, NotificationLog
from ..schemas.notifications import (
    NotificationReminderCreate,
    NotificationReminderUpdate,
    NotificationReminderResponse,
)


class NotificationReminderService:
    """Service for managing notification reminders."""
    
    @staticmethod
    def create_reminder(
        db: Session,
        user_id: int,
        reminder_data: NotificationReminderCreate,
    ) -> NotificationReminder:
        """
        Create a new notification reminder for a user.
        
        Args:
            db: Database session
            user_id: User ID
            reminder_data: Reminder creation data
            
        Returns:
            Created NotificationReminder instance
        """
        # Get or create user's notification preference
        pref = db.query(NotificationPreference).filter_by(user_id=user_id).first()
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.add(pref)
            db.flush()
        
        # Calculate next scheduled time
        scheduled_time = NotificationReminderService._calculate_next_reminder_time(
            user_id, reminder_data.reminder_time, db
        )
        
        reminder = NotificationReminder(
            user_id=user_id,
            preference_id=pref.id,
            scheduled_time=scheduled_time,
            reminder_type=reminder_data.reminder_type,
            reminder_title=reminder_data.reminder_title,
            reminder_body=reminder_data.reminder_body,
            delivery_channel=reminder_data.delivery_channel,
            status="active",
        )
        
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        
        return reminder
    
    @staticmethod
    def update_reminder(
        db: Session,
        reminder_id: int,
        reminder_data: NotificationReminderUpdate,
    ) -> Optional[NotificationReminder]:
        """
        Update an existing notification reminder.
        
        Args:
            db: Database session
            reminder_id: Reminder ID
            reminder_data: Update data
            
        Returns:
            Updated NotificationReminder or None if not found
        """
        reminder = db.query(NotificationReminder).filter_by(id=reminder_id).first()
        if not reminder:
            return None
        
        # Update allowed fields
        if reminder_data.reminder_title is not None:
            reminder.reminder_title = reminder_data.reminder_title
        if reminder_data.reminder_body is not None:
            reminder.reminder_body = reminder_data.reminder_body
        if reminder_data.status is not None:
            reminder.status = reminder_data.status
        if reminder_data.delivery_channel is not None:
            reminder.delivery_channel = reminder_data.delivery_channel
        
        reminder.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(reminder)
        
        return reminder
    
    @staticmethod
    def update_preference_settings(
        db: Session,
        user_id: int,
        daily_reminder_enabled: bool,
        reminder_time: str,
        reminder_frequency: str = "daily",
        reminder_days: Optional[List[str]] = None,
        reminder_message: Optional[str] = None,
    ) -> NotificationPreference:
        """
        Update user's reminder preference settings.
        
        Args:
            db: Database session
            user_id: User ID
            daily_reminder_enabled: Enable/disable daily reminders
            reminder_time: Time in HH:MM format (user's timezone)
            reminder_frequency: daily, weekly, or custom
            reminder_days: Days for weekly reminders
            reminder_message: Custom message
            
        Returns:
            Updated NotificationPreference
        """
        pref = db.query(NotificationPreference).filter_by(user_id=user_id).first()
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.add(pref)
        
        pref.daily_reminder_enabled = daily_reminder_enabled
        pref.reminder_time = reminder_time
        pref.reminder_frequency = reminder_frequency
        pref.reminder_days = reminder_days
        pref.reminder_message = reminder_message
        
        db.commit()
        db.refresh(pref)
        
        # Schedule reminders if enabling
        if daily_reminder_enabled:
            NotificationReminderService._schedule_reminders(db, user_id, pref)
        else:
            # Disable all active reminders
            db.query(NotificationReminder).filter(
                and_(
                    NotificationReminder.user_id == user_id,
                    NotificationReminder.status == "active"
                )
            ).update({"status": "disabled"})
            db.commit()
        
        return pref
    
    @staticmethod
    def get_reminders_by_user(
        db: Session,
        user_id: int,
        status: Optional[str] = None,
    ) -> List[NotificationReminder]:
        """
        Get reminders for a specific user.
        
        Args:
            db: Database session
            user_id: User ID
            status: Filter by status (active, paused, disabled)
            
        Returns:
            List of NotificationReminder instances
        """
        query = db.query(NotificationReminder).filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(NotificationReminder.scheduled_time).all()
    
    @staticmethod
    def get_pending_reminders(
        db: Session,
        cutoff_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[NotificationReminder]:
        """
        Get pending reminders that should be sent.
        
        Args:
            db: Database session
            cutoff_time: Only get reminders before this time
            limit: Max reminders to fetch
            
        Returns:
            List of pending NotificationReminder instances
        """
        if cutoff_time is None:
            cutoff_time = datetime.utcnow()
        
        return db.query(NotificationReminder).filter(
            and_(
                NotificationReminder.status == "active",
                NotificationReminder.is_sent == False,
                NotificationReminder.scheduled_time <= cutoff_time,
            )
        ).order_by(NotificationReminder.scheduled_time).limit(limit).all()
    
    @staticmethod
    def mark_reminder_sent(
        db: Session,
        reminder_id: int,
        channel: str = "push",
    ) -> Optional[NotificationReminder]:
        """
        Mark a reminder as sent.
        
        Args:
            db: Database session
            reminder_id: Reminder ID
            channel: Channel used for delivery
            
        Returns:
            Updated NotificationReminder or None if not found
        """
        reminder = db.query(NotificationReminder).filter_by(id=reminder_id).first()
        if not reminder:
            return None
        
        reminder.is_sent = True
        reminder.last_sent_at = datetime.utcnow()
        reminder.delivery_channel = channel
        reminder.delivery_attempts += 1
        reminder.last_error = None
        reminder.updated_at = datetime.utcnow()
        
        # Schedule next reminder
        reminder.scheduled_time = NotificationReminderService._calculate_next_reminder_time(
            reminder.user_id,
            reminder.preference.reminder_time if reminder.preference else "09:00",
            db,
        )
        reminder.is_sent = False
        
        db.commit()
        db.refresh(reminder)
        
        return reminder
    
    @staticmethod
    def mark_reminder_failed(
        db: Session,
        reminder_id: int,
        error_message: str,
    ) -> Optional[NotificationReminder]:
        """
        Mark a reminder as failed.
        
        Args:
            db: Database session
            reminder_id: Reminder ID
            error_message: Error details
            
        Returns:
            Updated NotificationReminder or None if not found
        """
        reminder = db.query(NotificationReminder).filter_by(id=reminder_id).first()
        if not reminder:
            return None
        
        reminder.delivery_attempts += 1
        reminder.last_error = error_message
        reminder.updated_at = datetime.utcnow()
        
        # Disable after 5 failed attempts
        if reminder.delivery_attempts >= 5:
            reminder.status = "disabled"
        
        db.commit()
        db.refresh(reminder)
        
        return reminder
    
    @staticmethod
    def delete_reminder(db: Session, reminder_id: int) -> bool:
        """
        Delete a notification reminder.
        
        Args:
            db: Database session
            reminder_id: Reminder ID
            
        Returns:
            True if deleted, False if not found
        """
        reminder = db.query(NotificationReminder).filter_by(id=reminder_id).first()
        if not reminder:
            return False
        
        db.delete(reminder)
        db.commit()
        
        return True
    
    @staticmethod
    def _calculate_next_reminder_time(
        user_id: int,
        reminder_time: str,
        db: Session,
    ) -> datetime:
        """
        Calculate the next reminder time based on user's timezone and preference.
        
        Args:
            user_id: User ID
            reminder_time: Time in HH:MM format
            db: Database session
            
        Returns:
            Next reminder time in UTC
        """
        # Get user's timezone (default to UTC)
        user = db.query(User).filter_by(id=user_id).first()
        user_tz_str = "UTC"
        
        if user and hasattr(user, 'settings') and user.settings:
            user_tz_str = user.settings.timezone or "UTC"
        
        try:
            user_tz = pytz.timezone(user_tz_str)
        except:
            user_tz = pytz.UTC
        
        # Parse reminder time
        try:
            hour, minute = map(int, reminder_time.split(':'))
        except:
            hour, minute = 9, 0  # Default to 9 AM
        
        # Get current time in user's timezone
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        now_user = now_utc.astimezone(user_tz)
        
        # Create reminder time for today in user's timezone
        reminder_dt = now_user.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If time has passed, use tomorrow
        if reminder_dt <= now_user:
            reminder_dt += timedelta(days=1)
        
        # Convert back to UTC
        reminder_utc = reminder_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        
        return reminder_utc
    
    @staticmethod
    def _schedule_reminders(
        db: Session,
        user_id: int,
        preference: NotificationPreference,
    ) -> None:
        """
        Schedule reminders based on user preferences.
        
        Args:
            db: Database session
            user_id: User ID
            preference: NotificationPreference instance
        """
        # Delete existing reminders for this preference
        db.query(NotificationReminder).filter(
            NotificationReminder.preference_id == preference.id
        ).delete()
        
        # Calculate frequency
        if preference.reminder_frequency == "daily":
            days_to_schedule = 30  # Schedule next 30 days
        elif preference.reminder_frequency == "weekly":
            days_to_schedule = 90  # Schedule 3 months
        else:
            days_to_schedule = 30
        
        # Create reminder for each day (or specific days if weekly)
        reminder_days = preference.reminder_days or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for i in range(days_to_schedule):
            current_date = datetime.utcnow() + timedelta(days=i)
            day_name = day_names[current_date.weekday()]
            
            # Skip if not in reminder_days for weekly reminders
            if preference.reminder_frequency == "weekly" and day_name not in reminder_days:
                continue
            
            scheduled_time = NotificationReminderService._calculate_next_reminder_time(
                user_id, preference.reminder_time, db
            )
            
            # Offset by i days
            scheduled_time += timedelta(days=i)
            
            reminder = NotificationReminder(
                user_id=user_id,
                preference_id=preference.id,
                scheduled_time=scheduled_time,
                reminder_type="emotion_logging",
                reminder_title=preference.reminder_message or "Time to log your emotions",
                delivery_channel="push",
                status="active",
            )
            
            db.add(reminder)
        
        db.commit()
