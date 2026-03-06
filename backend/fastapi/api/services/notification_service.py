import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
UTC = timezone.utc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from jinja2 import Environment, DictLoader, select_autoescape

from ..models import User, NotificationTemplate, NotificationLog, NotificationPreference

logger = logging.getLogger("api.notifications")

class NotificationOrchestrator:
    """
    Central service for rendering and dispatching notifications.
    Combines Jinja2 Template rendering with Multi-channel async dispatch based on User preferences.
    """
    
    _jinja_env = Environment(autoescape=select_autoescape(['html', 'xml']))

    @classmethod
    async def render_template(cls, db: AsyncSession, template_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Fetch template from DB and render with context."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.name == template_name,
            NotificationTemplate.is_active == True
        )
        res = await db.execute(stmt)
        template = res.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template '{template_name}' not found or inactive.")
            
        render_result = {}
        
        # We temporarily add templates to Jinja env to compile them safely
        loader_dict = {
            f"{template_name}_subject": template.subject_template,
        }
        if template.body_html_template:
            loader_dict[f"{template_name}_html"] = template.body_html_template
        if template.body_text_template:
            loader_dict[f"{template_name}_text"] = template.body_text_template
            
        cls._jinja_env.loader = DictLoader(loader_dict)
        
        try:
            render_result['subject'] = cls._jinja_env.get_template(f"{template_name}_subject").render(**context)
            if template.body_html_template:
                render_result['html'] = cls._jinja_env.get_template(f"{template_name}_html").render(**context)
            if template.body_text_template:
                render_result['text'] = cls._jinja_env.get_template(f"{template_name}_text").render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise ValueError(f"Template rendering error: {str(e)}")
            
        return render_result

    @classmethod
    async def dispatch_notification(
        cls, 
        db: AsyncSession, 
        user: User, 
        template_name: str, 
        context: Dict[str, Any],
        force_channels: Optional[List[str]] = None
    ) -> List[int]:
        """
        Orchestrates rendering and dispatching based on user preferences.
        Returns a list of NotificationLog IDs created.
        """
        # Render Content
        content = await cls.render_template(db, template_name, context)
        
        # Determine channels based on preferences or force_channels
        channels_to_send = []
        if force_channels:
            channels_to_send = force_channels
        else:
            # Check DB for User preferences
            stmt = select(NotificationPreference).where(NotificationPreference.user_id == user.id)
            res = await db.execute(stmt)
            pref = res.scalar_one_or_none()
            
            # Default logic if no explicit preferences set: send email and in-app
            if not pref:
                channels_to_send = ['email', 'in_app']
            else:
                if pref.email_enabled: channels_to_send.append('email')
                if pref.push_enabled: channels_to_send.append('push')
                if pref.in_app_enabled: channels_to_send.append('in_app')
                
        from api.celery_tasks import send_notification_task
        
        # For each channel, create a pending log and attempt send
        log_ids = []
        for channel in channels_to_send:
            log = NotificationLog(
                user_id=user.id,
                template_name=template_name,
                channel=channel,
                status="pending"
            )
            db.add(log)
            await db.commit() # Commit to get ID
            await db.refresh(log)
            log_ids.append(log.id)
            
            # Use Celery for async dispatch
            send_notification_task.delay(log.id, channel, user.id, content)
            
        return log_ids

    @classmethod
    async def _async_send(cls, db_session: AsyncSession, log_id: int, channel: str, user: User, content: Dict[str, str]):
        """
        Mock background worker simulating SMTP or APNS/FCM calls. 
        Requires a new session since it's backgrounded.
        """
        from ..services.db_service import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            stmt = select(NotificationLog).where(NotificationLog.id == log_id)
            res = await db.execute(stmt)
            log = res.scalar_one_or_none()
            
            if not log: return
            
            try:
                # MOCK: Simulate network latency for SMTP / Push providers
                await asyncio.sleep(1.0)
                
                # MOCK Send logic
                if channel == 'email':
                    # email_service.send(user.email, content['subject'], content['html'] or content['text'])
                    pass
                elif channel == 'push':
                    # push_service.send(user.device_token, content['subject'], content['text'])
                    pass
                elif channel == 'in_app':
                    # in_app_service.create_alert(...)
                    pass
                    
                log.status = "sent"
                log.sent_at = datetime.now(UTC)
                
            except Exception as e:
                log.status = "failed"
                log.error_message = str(e)
                logger.error(f"Failed to send notification {log_id} via {channel}: {e}")
                
            finally:
                await db.commit()

    @staticmethod
    async def seed_default_templates(db: AsyncSession):
        """Seed common templates into DB."""
        templates = [
            {
                "name": "welcome_email",
                "subject_template": "Welcome to Soul Sense, {{ username }}!",
                "body_html_template": "<h1>Welcome, {{ username }}!</h1><p>We are glad you are here.</p>",
                "body_text_template": "Welcome, {{ username }}! We are glad you are here."
            },
            {
                "name": "weekly_insight",
                "subject_template": "Your weekly emotional recap is ready",
                "body_html_template": "<h2>Your Insights</h2><p>Your average score was {{ avg_score }}.</p>",
                "body_text_template": "Your weekly average score was {{ avg_score }}."
            }
        ]
        
        for t in templates:
            existing = await db.execute(select(NotificationTemplate).where(NotificationTemplate.name == t['name']))
            if not existing.scalar_one_or_none():
                db.add(NotificationTemplate(**t))
        await db.commit()
