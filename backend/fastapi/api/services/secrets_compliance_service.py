"""
Secrets Age & Rotation Compliance Service (#1246)

Provides automated detection and alerting for stale secrets that exceed
rotation policy thresholds. Integrates with Celery for scheduled checks
and Redis for metrics storage.
"""

import logging
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ..models import RefreshToken, User
from ..config import get_settings_instance
import redis

logger = logging.getLogger(__name__)


class SecretsComplianceService:
    """
    Service for managing secrets age and rotation compliance.

    Handles automated detection of stale secrets, alerting, and metrics
    collection for dashboard monitoring.
    """

    # Age thresholds in days
    ROTATION_THRESHOLDS = {
        'warning': 30,    # Alert at 30 days
        'critical': 60,  # Critical alert at 60 days
        'max_age': 90    # Maximum allowed age before forced rotation
    }

    def __init__(self):
        self.settings = get_settings_instance()
        self.redis_client = redis.from_url(self.settings.redis_url)

    async def check_compliance(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Check all active refresh tokens for compliance violations.

        Returns comprehensive compliance report with violations and statistics.

        Args:
            db: Database session

        Returns:
            Dict containing compliance statistics and violation details
        """
        now = datetime.now(UTC)

        # Query active refresh tokens with age information
        stmt = select(
            RefreshToken.id,
            RefreshToken.user_id,
            RefreshToken.created_at,
            RefreshToken.expires_at,
            RefreshToken.is_revoked,
            User.username,
            User.email,
            (now - RefreshToken.created_at).label('age_seconds')
        ).join(
            User, RefreshToken.user_id == User.id
        ).where(
            and_(
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > now  # Not yet expired
            )
        )

        result = await db.execute(stmt)
        tokens = result.fetchall()

        # Initialize compliance report
        report = {
            'total_active_tokens': len(tokens),
            'compliant_tokens': 0,
            'warning_violations': 0,
            'critical_violations': 0,
            'expired_tokens': 0,
            'violations': [],
            'checked_at': now.isoformat(),
            'compliance_rate': 0.0
        }

        for token in tokens:
            age_days = token.age_seconds.days

            violation = {
                'token_id': token.id,
                'user_id': token.user_id,
                'username': token.username,
                'email': token.email,
                'age_days': age_days,
                'created_at': token.created_at.isoformat(),
                'expires_at': token.expires_at.isoformat()
            }

            if age_days >= self.ROTATION_THRESHOLDS['max_age']:
                # Token has exceeded maximum allowed age
                report['expired_tokens'] += 1
                violation['severity'] = 'expired'
                violation['recommendation'] = 'Immediate revocation required'
                report['violations'].append(violation)

            elif age_days >= self.ROTATION_THRESHOLDS['critical']:
                # Token is in critical violation zone
                report['critical_violations'] += 1
                violation['severity'] = 'critical'
                violation['recommendation'] = 'Rotate within 24 hours'
                report['violations'].append(violation)

            elif age_days >= self.ROTATION_THRESHOLDS['warning']:
                # Token is in warning zone
                report['warning_violations'] += 1
                violation['severity'] = 'warning'
                violation['recommendation'] = 'Rotate within 7 days'
                report['violations'].append(violation)

            else:
                # Token is compliant
                report['compliant_tokens'] += 1

        # Calculate compliance rate
        if report['total_active_tokens'] > 0:
            report['compliance_rate'] = (
                report['compliant_tokens'] / report['total_active_tokens'] * 100
            )

        return report

    async def get_compliance_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve current compliance metrics from Redis cache.

        Returns:
            Current compliance metrics or None if not available
        """
        try:
            metrics_data = self.redis_client.get("secrets_compliance:metrics")
            if metrics_data:
                return json.loads(metrics_data)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve compliance metrics: {e}")
            return None

    async def update_metrics(self, report: Dict[str, Any]) -> bool:
        """
        Update compliance metrics in Redis cache.

        Args:
            report: Compliance report to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            # Store full report with 24-hour expiration
            self.redis_client.setex(
                "secrets_compliance:metrics",
                86400,  # 24 hours
                json.dumps(report)
            )

            # Store individual metrics for easier dashboard queries
            self.redis_client.setex("secrets_compliance:total_active", 86400, report['total_active_tokens'])
            self.redis_client.setex("secrets_compliance:compliant", 86400, report['compliant_tokens'])
            self.redis_client.setex("secrets_compliance:warnings", 86400, report['warning_violations'])
            self.redis_client.setex("secrets_compliance:critical", 86400, report['critical_violations'])
            self.redis_client.setex("secrets_compliance:expired", 86400, report['expired_tokens'])
            self.redis_client.setex("secrets_compliance:rate", 86400, report['compliance_rate'])

            logger.debug(f"Updated compliance metrics: {report}")
            return True

        except Exception as e:
            logger.error(f"Failed to update compliance metrics: {e}")
            return False

    async def get_tokens_needing_rotation(self, db: AsyncSession, severity: str = 'warning') -> List[Dict[str, Any]]:
        """
        Get list of tokens that need rotation based on severity level.

        Args:
            db: Database session
            severity: Minimum severity level ('warning', 'critical', 'expired')

        Returns:
            List of tokens needing rotation
        """
        severity_levels = {
            'warning': self.ROTATION_THRESHOLDS['warning'],
            'critical': self.ROTATION_THRESHOLDS['critical'],
            'expired': self.ROTATION_THRESHOLDS['max_age']
        }

        min_age_days = severity_levels.get(severity, self.ROTATION_THRESHOLDS['warning'])
        now = datetime.now(UTC)

        stmt = select(
            RefreshToken.id,
            RefreshToken.user_id,
            RefreshToken.created_at,
            RefreshToken.expires_at,
            User.username,
            User.email,
            (now - RefreshToken.created_at).label('age_days')
        ).join(
            User, RefreshToken.user_id == User.id
        ).where(
            and_(
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > now,
                func.extract('epoch', now - RefreshToken.created_at) / 86400 >= min_age_days
            )
        )

        result = await db.execute(stmt)
        tokens = result.fetchall()

        return [{
            'token_id': token.id,
            'user_id': token.user_id,
            'username': token.username,
            'email': token.email,
            'age_days': int(token.age_days.days),
            'created_at': token.created_at.isoformat(),
            'expires_at': token.expires_at.isoformat()
        } for token in tokens]

    async def force_rotate_expired_tokens(self, db: AsyncSession) -> int:
        """
        Force rotation of tokens that have exceeded maximum age.

        This is a safety mechanism to automatically revoke tokens that
        are dangerously old, even if not manually rotated.

        Args:
            db: Database session

        Returns:
            Number of tokens revoked
        """
        max_age_threshold = datetime.now(UTC) - timedelta(days=self.ROTATION_THRESHOLDS['max_age'])

        # Mark expired tokens as revoked
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.is_revoked == False,
                RefreshToken.created_at < max_age_threshold
            )
        )

        result = await db.execute(stmt)
        expired_tokens = result.scalars().all()

        revoked_count = 0
        for token in expired_tokens:
            token.is_revoked = True
            revoked_count += 1

        if revoked_count > 0:
            await db.commit()
            logger.warning(f"Force revoked {revoked_count} tokens exceeding maximum age")

        return revoked_count

    def get_rotation_thresholds(self) -> Dict[str, int]:
        """
        Get current rotation threshold configuration.

        Returns:
            Dictionary of threshold values in days
        """
        return self.ROTATION_THRESHOLDS.copy()

    async def simulate_secret_aging(self, db: AsyncSession, days_to_add: int) -> Dict[str, Any]:
        """
        Simulate secret aging for testing purposes.

        Temporarily adjusts token creation dates to simulate aging.
        WARNING: This modifies database state for testing only.

        Args:
            db: Database session
            days_to_add: Number of days to add to token ages

        Returns:
            Compliance report with simulated aging
        """
        # This is for testing only - would modify created_at timestamps
        # Implementation would depend on test requirements
        logger.warning("Simulated aging requested - this modifies database state")
        # Implementation would go here for testing scenarios
        return await self.check_compliance(db)


# Global service instance
secrets_compliance_service = SecretsComplianceService()