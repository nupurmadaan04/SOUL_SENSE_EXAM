import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.db import safe_db_context
from app.models import AuditLog, User

logger = logging.getLogger(__name__)

class AuditService:
    """
    Comprehensive audit logging service for security monitoring, compliance, and forensic analysis.
    """

    # Event type categories
    EVENT_TYPES = {
        'auth': ['login', 'logout', 'password_change', 'password_reset', 'account_create', 'account_delete',
                'session_create', 'session_expire', 'token_refresh', 'mfa_enable', 'mfa_disable', 'suspicious_activity'],
        'data_access': ['assessment_view', 'assessment_create', 'assessment_update', 'assessment_delete',
                       'journal_view', 'journal_create', 'journal_update', 'journal_delete',
                       'profile_view', 'profile_update', 'data_export', 'settings_change', 'backup_create', 'backup_restore'],
        'admin': ['admin_login', 'user_management', 'config_change', 'db_schema_change', 'maintenance_start',
                 'maintenance_end', 'feature_flag_change', 'bulk_operation'],
        'system': ['app_startup', 'app_shutdown', 'db_connection_failure', 'api_error', 'performance_anomaly',
                  'security_event', 'config_reload']
    }

    # Severity levels
    SEVERITY_LEVELS = ['info', 'warning', 'error', 'critical']

    # Retention periods (days)
    RETENTION_ACTIVE = 90
    RETENTION_ARCHIVE = 365
    RETENTION_EXTENDED = 2555  # 7 years

    @classmethod
    def log_event(
        cls,
        event_type: str,
        username: str = None,
        user_id: int = None,
        action: str = None,
        resource_type: str = None,
        resource_id: str = None,
        outcome: str = 'success',
        severity: str = 'info',
        ip_address: str = None,
        user_agent: str = None,
        details: Dict[str, Any] = None,
        error_message: str = None,
        db_session: Optional[Session] = None
    ) -> bool:
        """Log a comprehensive audit event."""
        if db_session:
            return cls._log_event_impl(
                session=db_session,
                event_type=event_type,
                username=username,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                error_message=error_message
            )
        
        try:
            with safe_db_context() as session:
                return cls._log_event_impl(
                    session=session,
                    event_type=event_type,
                    username=username,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    outcome=outcome,
                    severity=severity,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=details,
                    error_message=error_message
                )
        except Exception as e:
            logger.critical(f"AUDIT LOG FAILURE: {e}")
            return False

    @classmethod
    def _log_event_impl(cls, session: Session, **kwargs) -> bool:
        """Internal implementation for log_event."""
        try:
            event_type = kwargs.get('event_type')
            severity = kwargs.get('severity', 'info')
            outcome = kwargs.get('outcome', 'success')
            user_agent = kwargs.get('user_agent')
            details = kwargs.get('details')
            error_message = kwargs.get('error_message')

            # Validate inputs
            if event_type not in cls.EVENT_TYPES:
                event_type = 'system'
            if severity not in cls.SEVERITY_LEVELS:
                severity = 'info'
            if outcome not in ['success', 'failure', 'denied']:
                outcome = 'success'

            # Sanitize inputs
            safe_ua = cls._sanitize_user_agent(user_agent)
            safe_details = cls._sanitize_metadata(details)
            safe_error = cls._sanitize_text(error_message, 1000)

            # Generate unique event ID
            event_id = str(uuid.uuid4())

            # Calculate retention date based on severity
            retention_days = cls._get_retention_days(severity)
            retention_until = datetime.now(UTC) + timedelta(days=retention_days)

            # Create audit log entry
            log_entry = AuditLog(
                event_id=event_id,
                timestamp=datetime.now(UTC),
                event_type=event_type,
                severity=severity,
                username=kwargs.get('username'),
                user_id=kwargs.get('user_id'),
                ip_address=kwargs.get('ip_address'),
                user_agent=safe_ua,
                resource_type=kwargs.get('resource_type'),
                resource_id=str(kwargs.get('resource_id')) if kwargs.get('resource_id') else None,
                action=kwargs.get('action'),
                outcome=outcome,
                details=safe_details,
                error_message=safe_error,
                retention_until=retention_until
            )

            session.add(log_entry)
            
            # Log to application logger
            log_level = getattr(logging, severity.upper(), logging.INFO)
            logger.log(log_level, f"AUDIT [{event_type}:{kwargs.get('action')}] User:{kwargs.get('username')} Resource:{kwargs.get('resource_type')}:{kwargs.get('resource_id')} Outcome:{outcome}")

            return True

        except Exception as e:
            logger.error(f"Audit processing failed: {e}")
            return False

    @classmethod
    def log_auth_event(cls, event_type: str, username: str, details: Dict[str, Any] = None,
                      ip_address: str = None, user_agent: str = None, db_session: Optional[Session] = None) -> bool:
        """Log authentication-related events."""
        return cls.log_event(
            event_type='auth',
            username=username,
            action=event_type,
            outcome=details.get('outcome', 'success') if details else 'success',
            severity=details.get('severity', 'info') if details else 'info',
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=details,
            db_session=db_session
        )

    @classmethod
    def log_data_access(cls, username: str, resource_type: str, resource_id: str, action: str,
                       outcome: str = 'success', details: Dict[str, Any] = None,
                       ip_address: str = None, db_session: Optional[Session] = None) -> bool:
        """Log data access events."""
        return cls.log_event(
            event_type='data_access',
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            ip_address=ip_address,
            details=details,
            db_session=db_session
        )

    @classmethod
    def log_admin_action(cls, admin_username: str, target_resource: str, target_id: str, action: str,
                        outcome: str = 'success', details: Dict[str, Any] = None,
                        ip_address: str = None, db_session: Optional[Session] = None) -> bool:
        """Log administrative actions."""
        return cls.log_event(
            event_type='admin',
            username=admin_username,
            resource_type=target_resource,
            resource_id=target_id,
            action=action,
            outcome=outcome,
            severity='warning',  # Admin actions are typically warnings or higher
            ip_address=ip_address,
            details=details,
            db_session=db_session
        )

    @classmethod
    def log_system_event(cls, event_type: str, details: Dict[str, Any] = None,
                        severity: str = 'info', db_session: Optional[Session] = None) -> bool:
        """Log system-level events."""
        return cls.log_event(
            event_type='system',
            action=event_type,
            severity=severity,
            details=details,
            db_session=db_session
        )

    @classmethod
    def query_logs(cls, filters: Dict[str, Any] = None, page: int = 1, per_page: int = 50,
                  db_session: Optional[Session] = None) -> Tuple[List[AuditLog], int]:
        """Query audit logs with filtering and pagination."""
        if db_session:
            return cls._query_logs_impl(db_session, filters, page, per_page)
        
        try:
            with safe_db_context() as session:
                return cls._query_logs_impl(session, filters, page, per_page)
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return [], 0

    @classmethod
    def _query_logs_impl(cls, session: Session, filters: Dict[str, Any], page: int, per_page: int) -> Tuple[List[AuditLog], int]:
        """Internal implementation for query_logs."""
        query = session.query(AuditLog)

        # Apply filters
        if filters:
            query = cls._apply_filters(query, filters)

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * per_page
        logs = query.order_by(desc(AuditLog.timestamp)).limit(per_page).offset(offset).all()

        return logs, total_count

    @classmethod
    def get_user_activity(cls, user_id: int, page: int = 1, per_page: int = 20,
                         db_session: Optional[Session] = None) -> Tuple[List[AuditLog], int]:
        """Get audit logs for a specific user (user can view their own activity)."""
        filters = {'user_id': user_id}
        return cls.query_logs(filters, page, per_page, db_session)

    @classmethod
    def export_logs(cls, filters: Dict[str, Any] = None, format: str = 'json',
                   db_session: Optional[Session] = None) -> str:
        """
        Export audit logs in specified format.

        Args:
            filters: Filter criteria
            format: Export format ('json', 'csv')
            db_session: Optional session

        Returns:
            Exported data as string
        """
        logs, _ = cls.query_logs(filters, page=1, per_page=10000, db_session=db_session)  # Reasonable limit

        if format.lower() == 'csv':
            return cls._export_csv(logs)
        else:
            return cls._export_json(logs)

    @classmethod
    def archive_old_logs(cls, retention_days: int = None, db_session: Optional[Session] = None) -> int:
        """Archive logs older than retention period."""
        if retention_days is None:
            retention_days = cls.RETENTION_ACTIVE

        if db_session:
            return cls._archive_old_logs_impl(db_session, retention_days)
        
        try:
            with safe_db_context() as session:
                return cls._archive_old_logs_impl(session, retention_days)
        except Exception as e:
            logger.error(f"Audit archive failed: {e}")
            return 0

    @classmethod
    def _archive_old_logs_impl(cls, session: Session, retention_days: int) -> int:
        """Internal implementation for archive_old_logs."""
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
        archived_count = session.query(AuditLog).filter(
            and_(
                AuditLog.timestamp < cutoff_date,
                AuditLog.archived == False
            )
        ).update({'archived': True})

        logger.info(f"Archived {archived_count} old audit logs")
        return archived_count

    @classmethod
    def cleanup_expired_logs(cls, db_session: Optional[Session] = None) -> int:
        """Permanently delete logs past their retention period."""
        if db_session:
            return cls._cleanup_expired_logs_impl(db_session)
        
        try:
            with safe_db_context() as session:
                return cls._cleanup_expired_logs_impl(session)
        except Exception as e:
            logger.error(f"Audit cleanup failed: {e}")
            return 0

    @classmethod
    def _cleanup_expired_logs_impl(cls, session: Session) -> int:
        """Internal implementation for cleanup_expired_logs."""
        cutoff_date = datetime.now(UTC)
        deleted_count = session.query(AuditLog).filter(
            and_(
                AuditLog.retention_until < cutoff_date,
                AuditLog.archived == True
            )
        ).delete()

        logger.info(f"Cleaned up {deleted_count} expired audit logs")
        return deleted_count

    # Helper methods
    @staticmethod
    def _sanitize_user_agent(user_agent: str) -> str:
        """Sanitize user agent string."""
        if not user_agent:
            return None
        return user_agent[:500] + "..." if len(user_agent) > 500 else user_agent

    @staticmethod
    def _sanitize_metadata(metadata: Dict[str, Any]) -> str:
        """Sanitize and serialize metadata."""
        if not metadata:
            return None
        try:
            # Filter out sensitive fields
            safe_metadata = {k: v for k, v in metadata.items() if not k.lower().startswith(('password', 'token', 'secret'))}
            return json.dumps(safe_metadata)
        except Exception:
            return None

    @staticmethod
    def _sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize text fields."""
        if not text:
            return None
        return text[:max_length] + "..." if len(text) > max_length else text

    @staticmethod
    def _get_retention_days(severity: str) -> int:
        """Get retention days based on severity."""
        if severity in ['error', 'critical']:
            return AuditService.RETENTION_EXTENDED
        elif severity == 'warning':
            return AuditService.RETENTION_ARCHIVE
        else:
            return AuditService.RETENTION_ACTIVE

    @staticmethod
    def _apply_filters(query, filters: Dict[str, Any]):
        """Apply filters to query."""
        if 'event_type' in filters:
            query = query.filter(AuditLog.event_type == filters['event_type'])
        if 'username' in filters:
            query = query.filter(AuditLog.username == filters['username'])
        if 'user_id' in filters:
            query = query.filter(AuditLog.user_id == filters['user_id'])
        if 'resource_type' in filters:
            query = query.filter(AuditLog.resource_type == filters['resource_type'])
        if 'action' in filters:
            query = query.filter(AuditLog.action == filters['action'])
        if 'outcome' in filters:
            query = query.filter(AuditLog.outcome == filters['outcome'])
        if 'severity' in filters:
            query = query.filter(AuditLog.severity == filters['severity'])
        if 'start_date' in filters:
            query = query.filter(AuditLog.timestamp >= filters['start_date'])
        if 'end_date' in filters:
            query = query.filter(AuditLog.timestamp <= filters['end_date'])
        if 'ip_address' in filters:
            query = query.filter(AuditLog.ip_address == filters['ip_address'])

        return query

    @staticmethod
    def _export_json(logs: List[AuditLog]) -> str:
        """Export logs as JSON."""
        data = []
        for log in logs:
            data.append({
                'event_id': log.event_id,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'event_type': log.event_type,
                'severity': log.severity,
                'username': log.username,
                'user_id': log.user_id,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'action': log.action,
                'outcome': log.outcome,
                'metadata': log.metadata,
                'error_message': log.error_message
            })
        return json.dumps(data, indent=2)

    @staticmethod
    def _export_csv(logs: List[AuditLog]) -> str:
        """Export logs as CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'event_id', 'timestamp', 'event_type', 'severity', 'username', 'user_id',
            'ip_address', 'resource_type', 'resource_id', 'action', 'outcome', 'error_message'
        ])

        # Data
        for log in logs:
            writer.writerow([
                log.event_id,
                log.timestamp.isoformat() if log.timestamp else '',
                log.event_type,
                log.severity,
                log.username,
                log.user_id,
                log.ip_address,
                log.resource_type,
                log.resource_id,
                log.action,
                log.outcome,
                log.error_message
            ])

        return output.getvalue()

    # Legacy compatibility methods
    @classmethod
    def log_event_legacy(cls, user_id: int, action: str, ip_address: Optional[str] = "SYSTEM",
                        user_agent: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
                        db_session: Optional[Session] = None) -> bool:
        """Legacy method for backward compatibility."""
        if db_session:
            return cls._log_event_legacy_impl(db_session, user_id, action, ip_address, user_agent, details)
        
        try:
            with safe_db_context() as session:
                return cls._log_event_legacy_impl(session, user_id, action, ip_address, user_agent, details)
        except Exception as e:
            logger.error(f"Legacy audit log failed: {e}")
            return False

    @classmethod
    def _log_event_legacy_impl(cls, session: Session, user_id: int, action: str, ip_address: str, 
                              user_agent: str, details: Dict[str, Any]) -> bool:
        """Internal implementation for log_event_legacy."""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            username = user.username if user else f"user_{user_id}"
        except Exception:
            username = f"user_{user_id}"

        # Map legacy action to new format
        event_type = 'auth' if action in ['LOGIN', 'PASSWORD_CHANGE', '2FA_ENABLE'] else 'system'
        severity = 'warning' if 'fail' in action.lower() else 'info'

        return cls.log_event(
            event_type=event_type,
            username=username,
            user_id=user_id,
            action=action.lower(),
            outcome='failure' if 'fail' in action.lower() else 'success',
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            db_session=session
        )

    @staticmethod
    def get_user_logs(user_id: int, page: int = 1, per_page: int = 20, db_session: Optional[Session] = None) -> List[AuditLog]:
        """Legacy method for backward compatibility."""
        logs, _ = AuditService.get_user_activity(user_id, page, per_page, db_session)
        return logs

    @staticmethod
    def cleanup_old_logs(days: int = 90) -> int:
        """Legacy method for backward compatibility."""
        return AuditService.archive_old_logs(days)
