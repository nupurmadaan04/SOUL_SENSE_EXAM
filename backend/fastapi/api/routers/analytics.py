"""Analytics API router - Aggregated, non-sensitive data only."""
from fastapi import APIRouter, Depends, status, Request, Response, BackgroundTasks, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import logging
from ..services.db_router import get_db
from ..services.analytics_service import AnalyticsService
from ..services.user_analytics_service import UserAnalyticsService
from app.core import AuthorizationError, InternalServerError
from fastapi_cache.decorator import cache
from ..schemas import (
    AnalyticsSummary,
    TrendAnalytics,
    BenchmarkComparison,
    PopulationInsights,
    AnalyticsEventCreate,
    DashboardStatisticsResponse,
    ConversionRateKPI,
    RetentionKPI,
    ARPUKPI,
    KPISummary,
    UserAnalyticsSummary,
    UserTrendsResponse
)
from ..middleware.rate_limiter import rate_limit_analytics
from .auth import get_current_user, require_admin
from ..models import User
from ..utils.network import get_real_ip

logger = logging.getLogger("api.analytics")
router = APIRouter(tags=["Analytics"])


@router.post("/events", status_code=201, dependencies=[Depends(rate_limit_analytics)])
async def track_event(
    event: AnalyticsEventCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Log a tracking event."""
    await AnalyticsService.log_event(db, event.model_dump(), ip_address=get_real_ip(request))
    return {"status": "ok"}


@router.get("/summary", response_model=AnalyticsSummary, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=3600)
async def get_analytics_summary(
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get overall analytics summary (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    summary = await AnalyticsService.get_overall_summary(db, environment=environment)
    return AnalyticsSummary(**summary)


@router.get("/trends", response_model=TrendAnalytics, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=1800)
async def get_trend_analytics(
    period: str = Query('monthly', pattern='^(daily|weekly|monthly)$'),
    limit: int = Query(12, ge=1, le=24),
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get trend analytics over time (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    trends = await AnalyticsService.get_trend_analytics(db, period_type=period, limit=limit, environment=environment)
    return TrendAnalytics(**trends)


@router.get("/benchmarks", response_model=List[BenchmarkComparison], dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=3600)
async def get_benchmark_comparison(
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get benchmark comparison data (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    benchmarks = await AnalyticsService.get_benchmark_comparison(db, environment=environment)
    return [BenchmarkComparison(**b) for b in benchmarks]


@router.get("/insights", response_model=PopulationInsights, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=3600)
async def get_population_insights(
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get population-level insights (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    insights = await AnalyticsService.get_population_insights(db, environment=environment)
    return PopulationInsights(**insights)


@router.get("/me/summary", response_model=UserAnalyticsSummary)
async def get_user_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get personalized analytics summary for the current user."""
    return await UserAnalyticsService.get_dashboard_summary(db, current_user.id)


@router.get("/me/trends", response_model=UserTrendsResponse)
async def get_user_analytics_trends(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get time-series data for user charts."""
    eq_scores = await UserAnalyticsService.get_eq_trends(db, current_user.id, days)
    wellbeing = await UserAnalyticsService.get_wellbeing_trends(db, current_user.id, days)
    
    return UserTrendsResponse(
        eq_scores=eq_scores,
        wellbeing=wellbeing
    )


@router.get("/statistics", response_model=DashboardStatisticsResponse, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=1800)
async def get_dashboard_statistics(
    timeframe: str = Query('30d', pattern='^(7d|30d|90d)$'),
    exam_type: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None, pattern='^(positive|neutral|negative)$'),
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics with historical trends (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    trends = await AnalyticsService.get_dashboard_statistics(
        db, timeframe=timeframe, exam_type=exam_type, sentiment=sentiment, environment=environment
    )
    return DashboardStatisticsResponse(historical_trends=trends)


@router.get("/age-groups", dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
async def get_age_group_statistics(
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed statistics by age group (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    stats = await AnalyticsService.get_age_group_statistics(db, environment=environment)
    return {"age_group_statistics": stats, "environment": environment or get_current_environment()}


@router.get("/distribution", dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
async def get_score_distribution(
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get score distribution across ranges (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    distribution = await AnalyticsService.get_score_distribution(db, environment=environment)
    return {"score_distribution": distribution, "environment": environment or get_current_environment()}


@router.get("/kpis/conversion-rate", response_model=ConversionRateKPI, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=3600)
async def get_conversion_rate_kpi(
    period_days: int = Query(30, ge=1, le=365),
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get Conversion Rate KPI (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    return await AnalyticsService.calculate_conversion_rate(db, period_days, environment=environment)


@router.get("/kpis/retention-rate", response_model=RetentionKPI, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=3600)
async def get_retention_rate_kpi(
    period_days: int = Query(7, ge=1, le=90),
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get Retention Rate KPI (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    return await AnalyticsService.calculate_retention_rate(db, period_days, environment=environment)


@router.get("/kpis/arpu", response_model=ARPUKPI, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=3600)
async def get_arpu_kpi(
    period_days: int = Query(30, ge=1, le=365),
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get ARPU KPI (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    return await AnalyticsService.calculate_arpu(db, period_days, environment=environment)


@router.get("/kpis/summary", response_model=KPISummary, dependencies=[Depends(rate_limit_analytics), Depends(require_admin)])
@cache(expire=1800)
async def get_kpi_summary(
    conversion_period: int = Query(30, ge=1, le=365),
    retention_period: int = Query(7, ge=1, le=90),
    arpu_period: int = Query(30, ge=1, le=365),
    environment: Optional[str] = Query(None, description="Filter by environment (defaults to current)"),
    db: AsyncSession = Depends(get_db)
):
    """Get combined KPI summary (Admin only).
    
    Supports cross-environment queries for admin users to compare data across environments.
    """
    kpi_summary = await AnalyticsService.get_kpi_summary(
        db,
        conversion_period,
        retention_period,
        arpu_period,
        environment=environment
    )
    return KPISummary(**kpi_summary)
