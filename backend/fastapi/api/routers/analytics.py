"""Analytics API router - Aggregated, non-sensitive data only."""
from typing import Optional, List, Dict, Any
import logging
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_router import get_db
from ..services.analytics_service import AnalyticsService
from ..services.user_analytics_service import UserAnalyticsService
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
from .auth import get_current_user, require_admin
from ..models import User
from ..utils.network import get_real_ip

logger = logging.getLogger("api.analytics")
router = APIRouter(tags=["Analytics"])


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def track_event(
    event: AnalyticsEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Log a tracking event without PII."""
    try:
        await AnalyticsService.log_event(db, event.model_dump(), ip_address=get_real_ip(request))
    except Exception as e:
        logger.debug(f"Event logging failed: {e}")
    return {"status": "ok"}


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get overall aggregate analytics summary (Admin only)."""
    summary = await AnalyticsService.get_overall_summary(db, environment=environment)
    return AnalyticsSummary(**summary)


@router.get("/trends", response_model=TrendAnalytics)
async def get_trend_analytics(
    period: str = Query('monthly', pattern='^(daily|weekly|monthly)$', description="Time period type"),
    limit: int = Query(12, ge=1, le=24, description="Number of periods to return"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get trend analytics over time (Admin only)."""
    trends = await AnalyticsService.get_trend_analytics(db, period_type=period, limit=limit, environment=environment)
    return TrendAnalytics(**trends)


@router.get("/benchmarks", response_model=List[BenchmarkComparison])
async def get_benchmark_comparison(
    category_id: Optional[int] = Query(None),
    environment: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get benchmark comparison data with percentiles (Admin only)."""
    benchmarks = await AnalyticsService.get_benchmarks(db, category_id=category_id, environment=environment)
    return [BenchmarkComparison(**b) for b in benchmarks]


@router.get("/user/summary", response_model=UserAnalyticsSummary)
async def get_user_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user dashboard summary metrics for authenticated user."""
    return await UserAnalyticsService.get_dashboard_summary(db, current_user.id)


@router.get("/user/trends", response_model=UserTrendsResponse)
async def get_user_trends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get individual user trends for dashboard charts."""
    return await UserAnalyticsService.get_user_trends(db, current_user.id)


@router.get("/statistics", response_model=DashboardStatisticsResponse)
async def get_dashboard_statistics(
    timeframe: str = Query('30d', pattern='^(7d|30d|90d)$'),
    exam_type: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None, pattern='^(positive|neutral|negative)$'),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregate dashboard statistics with historical trends (Admin only)."""
    trends = await AnalyticsService.get_dashboard_statistics(
        db, timeframe=timeframe, exam_type=exam_type, sentiment=sentiment, environment=environment
    )
    return DashboardStatisticsResponse(historical_trends=trends)


@router.get("/kpis/summary", response_model=KPISummary)
async def get_kpi_summary(
    conversion_period: int = Query(30, ge=1, le=365),
    retention_period: int = Query(7, ge=1, le=90),
    arpu_period: int = Query(30, ge=1, le=365),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get combined KPI summary (Admin only)."""
    kpi_summary = await AnalyticsService.get_kpi_summary(
        db,
        conversion_period,
        retention_period,
        arpu_period,
        environment=environment
    )
    return KPISummary(**kpi_summary)
