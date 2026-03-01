"""Analytics service for aggregated, non-sensitive data analysis."""
from sqlalchemy import func, case, distinct, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta, UTC

from ..models import Score, User, AnalyticsEvent
from ..utils.environment_context import get_current_environment


class AnalyticsService:
    """Service for generating aggregated analytics data.
    
    This service ONLY provides aggregated data and never exposes
    individual user information or raw sensitive data.
    
    Environment Separation:
        All analytics queries are automatically filtered by the current environment
        to prevent staging data from mixing with production data (Issue #979).
    """
    
    @staticmethod
    async def log_event(db: AsyncSession, event_data: dict, ip_address: Optional[str] = None) -> AnalyticsEvent:
        """Log a user behavior event with environment tracking."""
        import json
        
        data_payload = json.dumps(event_data.get('event_data', {}))
        environment = get_current_environment()
        
        event = AnalyticsEvent(
            anonymous_id=event_data['anonymous_id'],
            event_type=event_data.get('event_type', 'unknown'),
            event_name=event_data['event_name'],
            event_data=data_payload,
            ip_address=ip_address,
            timestamp=datetime.now(UTC),
            environment=environment
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def get_age_group_statistics(db: AsyncSession) -> List[Dict]:
        """Get pre-computed statistics by age group using CQRS (#1124)."""
        from ..models import CQRSAgeGroupStats
        
        stmt = select(CQRSAgeGroupStats).order_by(CQRSAgeGroupStats.age_group)
        result = await db.execute(stmt)
        stats = result.scalars().all()
        
        return [
            {
                'age_group': s.age_group,
                'total_assessments': s.total_assessments,
                'average_score': round(s.average_score, 2),
                'min_score': s.min_score,
                'max_score': s.max_score,
                'average_sentiment': round(s.average_sentiment, 3)
            }
            for s in stats
        ]
    
    @staticmethod
    async def get_score_distribution(db: AsyncSession) -> List[Dict]:
        """Get score distribution across ranges using CQRS (#1124)."""
        from ..models import CQRSDistributionStats
        
        total_stmt = select(func.sum(CQRSDistributionStats.count))
        total_res = await db.execute(total_stmt)
        total_count = total_res.scalar() or 0
        
        stmt = select(CQRSDistributionStats).order_by(CQRSDistributionStats.score_range)
        result = await db.execute(stmt)
        stats = result.scalars().all()
        
        return [
            {
                'score_range': s.score_range,
                'count': s.count,
                'percentage': round((s.count / total_count * 100) if total_count > 0 else 0, 2)
            }
            for s in stats
        ]
    
    @staticmethod
    async def get_overall_summary(db: AsyncSession) -> Dict:
        """Get overall analytics summary utilizing CQRS Read Models (#1124)."""
        from ..models import CQRSGlobalStats
        
        # Read from the pre-computed fast CQRS table instead of heavy aggregates
        stmt = select(CQRSGlobalStats).order_by(desc(CQRSGlobalStats.last_updated)).limit(1)
        res = await db.execute(stmt)
        stats = res.scalar_one_or_none()
        
        if not stats:
            # Fallback for empty DBs
            return {
                'total_assessments': 0, 'unique_users': 0, 'global_average_score': 0,
                'global_average_sentiment': 0, 'age_group_stats': [], 'score_distribution': [],
                'assessment_quality_metrics': {'rushed_assessments': 0, 'inconsistent_assessments': 0}
            }
            
        age_group_stats = await AnalyticsService.get_age_group_statistics(db)
        score_dist = await AnalyticsService.get_score_distribution(db)
        
        return {
            'total_assessments': stats.total_assessments,
            'unique_users': stats.unique_users,
            'global_average_score': round(stats.global_average_score, 2),
            'global_average_sentiment': round(stats.global_average_sentiment, 3),
            'age_group_stats': age_group_stats,
            'score_distribution': score_dist,
            'assessment_quality_metrics': {
                'rushed_assessments': stats.rushed_assessments,
                'inconsistent_assessments': stats.inconsistent_assessments
            }
        }
    
    @staticmethod
    async def get_trend_analytics(
        db: AsyncSession,
        period_type: str = 'monthly',
        limit: int = 12,
        environment: Optional[str] = None
    ) -> Dict:
        """Get trend analytics over time utilizing CQRS Read Models (#1124)."""
        from ..models import CQRSTrendAnalytics
        
        # Read from the pre-computed fast CQRS table instead of heavy aggregates
        stmt = select(CQRSTrendAnalytics).order_by(desc(CQRSTrendAnalytics.period)).limit(limit)
        
        result = await db.execute(stmt)
        trends = result.scalars().all()
        
        data_points = [
            {
                'period': t.period,
                'average_score': round(t.avg_score or 0, 2),
                'assessment_count': t.count
            }
            for t in reversed(trends)
        ]
        
        if len(data_points) >= 2:
            first_avg = data_points[0]['average_score']
            last_avg = data_points[-1]['average_score']
            
            if last_avg > first_avg + 1:
                trend_direction = 'increasing'
            elif last_avg < first_avg - 1:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        return {
            'period_type': period_type,
            'data_points': data_points,
            'trend_direction': trend_direction,
            'environment': environment
        }
    
    @staticmethod
    async def get_benchmark_comparison(db: AsyncSession) -> List[Dict]:
        """Get benchmark comparison using CQRS (#1124)."""
        from ..models import CQRSGlobalStats
        
        stmt = select(CQRSGlobalStats).order_by(desc(CQRSGlobalStats.last_updated)).limit(1)
        res = await db.execute(stmt)
        stats = res.scalar_one_or_none()
        
        if not stats:
            return [{
                'category': 'Overall',
                'global_average': 0,
                'percentile_25': 0,
                'percentile_50': 0,
                'percentile_75': 0,
                'percentile_90': 0
            }]
            
        return [{
            'category': 'Overall',
            'global_average': round(stats.global_average_score, 2),
            'percentile_25': round(stats.p25_score, 2),
            'percentile_50': round(stats.p50_score, 2),
            'percentile_75': round(stats.p75_score, 2),
            'percentile_90': round(stats.p90_score, 2)
        }]
    
    @staticmethod
    async def get_population_insights(db: AsyncSession) -> Dict:
        """Get population-level insights using CQRS (#1124)."""
        from ..models import CQRSGlobalStats, CQRSAgeGroupStats
        
        # 1. Most common age group
        common_stmt = select(CQRSAgeGroupStats).order_by(desc(CQRSAgeGroupStats.total_assessments)).limit(1)
        common_res = await db.execute(common_stmt)
        most_common = common_res.scalar_one_or_none()
        
        # 2. Highest performing age group
        perf_stmt = select(CQRSAgeGroupStats).order_by(desc(CQRSAgeGroupStats.average_score)).limit(1)
        perf_res = await db.execute(perf_stmt)
        highest_performing = perf_res.scalar_one_or_none()
        
        # 3. Overall stats from global read model
        global_stmt = select(CQRSGlobalStats).order_by(desc(CQRSGlobalStats.last_updated)).limit(1)
        global_res = await db.execute(global_stmt)
        global_stats = global_res.scalar_one_or_none()
        
        if not global_stats:
            return {
                'most_common_age_group': 'Unknown',
                'highest_performing_age_group': 'Unknown',
                'total_population_size': 0,
                'assessment_completion_rate': 0
            }
        
        return {
            'most_common_age_group': most_common.age_group if most_common else 'Unknown',
            'highest_performing_age_group': highest_performing.age_group if highest_performing else 'Unknown',
            'total_population_size': global_stats.unique_users,
            'assessment_completion_rate': 100.0 if global_stats.total_assessments > 0 else 0
        }
    
    @staticmethod
    async def get_dashboard_statistics(
        db: AsyncSession,
        timeframe: str = '30d',
        exam_type: Optional[str] = None,
        sentiment: Optional[str] = None,
        environment: Optional[str] = None
    ) -> List[Dict]:
        """Get dashboard statistics with historical trends.
        
        Args:
            db: Database session
            timeframe: Time period for statistics (7d, 30d, 90d)
            exam_type: Optional exam type filter
            sentiment: Optional sentiment filter
            environment: Optional environment filter (defaults to current environment)
        """
        if environment is None:
            environment = get_current_environment()
            
        now = datetime.now(UTC)
        if timeframe == '7d':
            start_date = now - timedelta(days=7)
        elif timeframe == '30d':
            start_date = now - timedelta(days=30)
        elif timeframe == '90d':
            start_date = now - timedelta(days=90)
        else:
            start_date = now - timedelta(days=30)
        
        stmt = select(
            Score.id,
            Score.timestamp,
            Score.total_score,
            Score.sentiment_score
        ).filter(
            Score.timestamp >= start_date,
            Score.environment == environment
        )
        
        if sentiment:
            if sentiment == 'positive':
                stmt = stmt.filter(Score.sentiment_score >= 0.6)
            elif sentiment == 'neutral':
                stmt = stmt.filter(Score.sentiment_score.between(0.4, 0.6))
            elif sentiment == 'negative':
                stmt = stmt.filter(Score.sentiment_score < 0.4)
        
        stmt = stmt.order_by(desc(Score.timestamp)).limit(100)
        result = await db.execute(stmt)
        scores = result.all()
        
        trends = []
        for score in reversed(scores):
            trends.append({
                'id': score.id,
                'timestamp': score.timestamp.isoformat(),
                'total_score': score.total_score,
                'sentiment_score': score.sentiment_score
            })
        
        return trends

    @staticmethod
    async def calculate_conversion_rate(
        db: AsyncSession,
        period_days: int = 30,
        environment: Optional[str] = None
    ) -> Dict:
        """Calculate Conversion Rate KPI.
        
        Args:
            db: Database session
            period_days: Number of days to look back
            environment: Optional environment filter (defaults to current environment)
        """
        if environment is None:
            environment = get_current_environment()
            
        cutoff_date = datetime.now(UTC) - timedelta(days=period_days)

        started_stmt = select(func.count(AnalyticsEvent.id)).filter(
            AnalyticsEvent.event_name == 'signup_start',
            AnalyticsEvent.timestamp >= cutoff_date,
            AnalyticsEvent.environment == environment
        )
        started_res = await db.execute(started_stmt)
        signup_started = started_res.scalar() or 0

        completed_stmt = select(func.count(AnalyticsEvent.id)).filter(
            AnalyticsEvent.event_name == 'signup_success',
            AnalyticsEvent.timestamp >= cutoff_date,
            AnalyticsEvent.environment == environment
        )
        completed_res = await db.execute(completed_stmt)
        signup_completed = completed_res.scalar() or 0

        conversion_rate = (signup_completed / signup_started * 100) if signup_started > 0 else 0

        return {
            'signup_started': signup_started,
            'signup_completed': signup_completed,
            'conversion_rate': round(conversion_rate, 2),
            'period': f'last_{period_days}_days',
            'environment': environment
        }

    @staticmethod
    async def calculate_retention_rate(
        db: AsyncSession,
        period_days: int = 7,
        environment: Optional[str] = None
    ) -> Dict:
        """Calculate Retention Rate KPI.
        
        Args:
            db: Database session
            period_days: Number of days for retention calculation
            environment: Optional environment filter (defaults to current environment)
        """
        if environment is None:
            environment = get_current_environment()
            
        today = datetime.now(UTC).date()
        day_0 = today - timedelta(days=period_days)
        day_n = today

        day0_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
            AnalyticsEvent.user_id.isnot(None),
            func.date(AnalyticsEvent.timestamp) == day_0,
            AnalyticsEvent.environment == environment
        )
        day0_res = await db.execute(day0_stmt)
        day_0_users = day0_res.scalar() or 0

        dayn_subq = select(func.distinct(AnalyticsEvent.user_id)).filter(
            func.date(AnalyticsEvent.timestamp) == day_n,
            AnalyticsEvent.environment == environment
        ).subquery()
        
        dayn_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
            AnalyticsEvent.user_id.isnot(None),
            func.date(AnalyticsEvent.timestamp) == day_0,
            AnalyticsEvent.user_id.in_(select(dayn_subq)),
            AnalyticsEvent.environment == environment
        )
        dayn_res = await db.execute(dayn_stmt)
        day_n_active_users = dayn_res.scalar() or 0

        retention_rate = (day_n_active_users / day_0_users * 100) if day_0_users > 0 else 0

        return {
            'day_0_users': day_0_users,
            'day_n_active_users': day_n_active_users,
            'retention_rate': round(retention_rate, 2),
            'period_days': period_days,
            'period': f'{period_days}_day_retention',
            'environment': environment
        }

    @staticmethod
    async def calculate_arpu(
        db: AsyncSession,
        period_days: int = 30,
        environment: Optional[str] = None
    ) -> Dict:
        """Calculate ARPU KPI.
        
        Args:
            db: Database session
            period_days: Number of days to look back
            environment: Optional environment filter (defaults to current environment)
        """
        if environment is None:
            environment = get_current_environment()
            
        cutoff_date = datetime.now(UTC) - timedelta(days=period_days)

        active_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
            AnalyticsEvent.user_id.isnot(None),
            AnalyticsEvent.timestamp >= cutoff_date,
            AnalyticsEvent.environment == environment
        )
        active_res = await db.execute(active_stmt)
        total_active_users = active_res.scalar() or 0

        total_revenue = 0.0
        arpu = (total_revenue / total_active_users) if total_active_users > 0 else 0

        return {
            'total_revenue': total_revenue,
            'total_active_users': total_active_users,
            'arpu': round(arpu, 2),
            'period': f'last_{period_days}_days',
            'currency': 'USD',
            'environment': environment
        }

    @staticmethod
    async def get_kpi_summary(
        db: AsyncSession,
        conversion_period_days: int = 30,
        retention_period_days: int = 7,
        arpu_period_days: int = 30,
        environment: Optional[str] = None
    ) -> Dict:
        """Get combined KPI summary.
        
        Args:
            db: Database session
            conversion_period_days: Period for conversion rate calculation
            retention_period_days: Period for retention rate calculation
            arpu_period_days: Period for ARPU calculation
            environment: Optional environment filter (defaults to current environment)
        """
        if environment is None:
            environment = get_current_environment()
            
        conversion_rate = await AnalyticsService.calculate_conversion_rate(
            db, conversion_period_days, environment
        )
        retention_rate = await AnalyticsService.calculate_retention_rate(
            db, retention_period_days, environment
        )
        arpu = await AnalyticsService.calculate_arpu(db, arpu_period_days, environment)

        return {
            'conversion_rate': conversion_rate,
            'retention_rate': retention_rate,
            'arpu': arpu,
            'calculated_at': datetime.now(UTC).isoformat(),
            'period': f'conversion_{conversion_period_days}d_retention_{retention_period_days}d_arpu_{arpu_period_days}d',
            'environment': environment
        }


# ============================================================================
# Privacy & Consent Methods (Issue #982)
# ============================================================================

    @staticmethod
    def track_consent_event(
        db: Session,
        anonymous_id: str,
        event_type: str,
        consent_type: str,
        consent_version: str,
        event_data: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AnalyticsEvent:
        """
        Track a consent event (consent_given or consent_revoked).

        Args:
            db: Database session
            anonymous_id: Client-generated anonymous ID
            event_type: 'consent_given' or 'consent_revoked'
            consent_type: Type of consent (analytics, marketing, research)
            consent_version: Version of consent terms
            event_data: Additional metadata
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created ConsentEvent
        """
        import json

        # Serialize event_data to JSON
        data_payload = json.dumps(event_data) if event_data else None

        event = AnalyticsEvent(
            anonymous_id=anonymous_id,
            event_type=event_type,
            event_name=f"consent_{consent_type}_{event_type}",
            event_data=data_payload,
            ip_address=ip_address,
            environment=get_current_environment(),
            timestamp=datetime.utcnow()
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        # Update or create user consent status
        AnalyticsService._update_user_consent_status(
            db, anonymous_id, event_type, consent_type, consent_version,
            ip_address, user_agent
        )

        return event

    @staticmethod
    def _update_user_consent_status(
        db: Session,
        anonymous_id: str,
        event_type: str,
        consent_type: str,
        consent_version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Update the user's current consent status based on consent event.

        Args:
            db: Database session
            anonymous_id: Client-generated anonymous ID
            event_type: 'consent_given' or 'consent_revoked'
            consent_type: Type of consent
            consent_version: Version of consent terms
            ip_address: Client IP address
            user_agent: Client user agent
        """
        # Find existing consent record
        consent = db.query(UserConsent).filter(
            UserConsent.anonymous_id == anonymous_id,
            UserConsent.consent_type == consent_type
        ).first()

        now = datetime.utcnow()
        consent_granted = (event_type == 'consent_given')

        if consent:
            # Update existing record
            consent.consent_granted = consent_granted
            consent.consent_version = consent_version
            if consent_granted:
                consent.granted_at = now
                consent.revoked_at = None
            else:
                consent.revoked_at = now
            consent.ip_address = ip_address
            consent.user_agent = user_agent
            consent.updated_at = now
        else:
            # Create new consent record
            consent = UserConsent(
                anonymous_id=anonymous_id,
                consent_type=consent_type,
                consent_granted=consent_granted,
                consent_version=consent_version,
                granted_at=now if consent_granted else None,
                revoked_at=now if not consent_granted else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(consent)

        db.commit()

    @staticmethod
    def check_analytics_consent(db: Session, anonymous_id: str) -> Dict[str, Any]:
        """
        Check if user has consented to analytics tracking.

        Args:
            db: Database session
            anonymous_id: Client-generated anonymous ID

        Returns:
            Dictionary with consent status information
        """
        consent = db.query(UserConsent).filter(
            UserConsent.anonymous_id == anonymous_id,
            UserConsent.consent_type == 'analytics',
            UserConsent.consent_granted == True
        ).first()

        if consent:
            return {
                'analytics_consent_given': True,
                'consent_version': consent.consent_version,
                'last_updated': consent.updated_at.isoformat() if consent.updated_at else None
            }
        else:
            return {
                'analytics_consent_given': False,
                'consent_version': None,
                'last_updated': None
            }

    @staticmethod
    def get_consent_status(db: Session, anonymous_id: str) -> Dict:
        """
        Get comprehensive consent status for a user.

        Args:
            db: Database session
            anonymous_id: Client-generated anonymous ID

        Returns:
            Dictionary with current consent status and history
        """
        # Get current consent statuses
        consents = db.query(UserConsent).filter(
            UserConsent.anonymous_id == anonymous_id
        ).all()

        consent_status = {
            'analytics_consent': False,
            'marketing_consent': False,
            'research_consent': False,
            'consent_version': '1.0',  # Default version
            'last_updated': None
        }

        for consent in consents:
            if consent.consent_type == 'analytics':
                consent_status['analytics_consent'] = consent.consent_granted
            elif consent.consent_type == 'marketing':
                consent_status['marketing_consent'] = consent.consent_granted
            elif consent.consent_type == 'research':
                consent_status['research_consent'] = consent.consent_granted

            # Update version and last_updated if more recent
            if consent.updated_at and (
                consent_status['last_updated'] is None or
                consent.updated_at > consent_status['last_updated']
            ):
                consent_status['consent_version'] = consent.consent_version
                consent_status['last_updated'] = consent.updated_at

        # Get consent event history
        events = db.query(ConsentEvent).filter(
            ConsentEvent.anonymous_id == anonymous_id
        ).order_by(ConsentEvent.timestamp.desc()).limit(50).all()

        consent_status['consent_history'] = [event.to_dict() for event in events]

        # Set default last_updated if no consents exist
        if consent_status['last_updated'] is None:
            consent_status['last_updated'] = datetime.utcnow().isoformat()
        else:
            consent_status['last_updated'] = consent_status['last_updated'].isoformat()

        return consent_status

    @staticmethod
    def update_consent_preferences(
        db: Session,
        anonymous_id: str,
        analytics_consent: Optional[bool] = None,
        marketing_consent: Optional[bool] = None,
        research_consent: Optional[bool] = None,
        consent_version: str = '1.0',
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Update user consent preferences.

        Args:
            db: Database session
            anonymous_id: Client-generated anonymous ID
            analytics_consent: New analytics consent status
            marketing_consent: New marketing consent status
            research_consent: New research consent status
            consent_version: Version of consent terms
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Updated consent status
        """
        consent_updates = []

        if analytics_consent is not None:
            event_type = 'consent_given' if analytics_consent else 'consent_revoked'
            AnalyticsService.track_consent_event(
                db, anonymous_id, event_type, 'analytics', consent_version,
                None, ip_address, user_agent
            )
            consent_updates.append(('analytics', analytics_consent))

        if marketing_consent is not None:
            event_type = 'consent_given' if marketing_consent else 'consent_revoked'
            AnalyticsService.track_consent_event(
                db, anonymous_id, event_type, 'marketing', consent_version,
                None, ip_address, user_agent
            )
            consent_updates.append(('marketing', marketing_consent))

        if research_consent is not None:
            event_type = 'consent_given' if research_consent else 'consent_revoked'
            AnalyticsService.track_consent_event(
                db, anonymous_id, event_type, 'research', consent_version,
                None, ip_address, user_agent
            )
            consent_updates.append(('research', research_consent))

        return AnalyticsService.get_consent_status(db, anonymous_id)
