"""Analytics API router - Aggregated, non-sensitive data only."""
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
import logging
from ..services.db_service import get_db
from ..services.analytics_service import AnalyticsService
from ..schemas import (
    AnalyticsSummary,
    TrendAnalytics,
    BenchmarkComparison,
    PopulationInsights,
    AnalyticsEventCreate
)
from ..middleware.rate_limiter import rate_limit_analytics

logger = logging.getLogger("api.analytics")
router = APIRouter()


@router.post("/events", status_code=201, dependencies=[Depends(rate_limit_analytics)])
async def track_event(
    event: AnalyticsEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Log a tracking event (signup drop-off, etc).
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**:
    - No PII is logged (enforced by schema).
    - IP address is stored for security auditing.
    """
    await AnalyticsService.log_event(db, event.dict(), ip_address=request.client.host)
    return {"status": "ok"}


@router.get("/summary", response_model=AnalyticsSummary, dependencies=[Depends(rate_limit_analytics)])
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """
    Get overall analytics summary with aggregated data only.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: This endpoint returns ONLY aggregated statistics.
    No individual user data or raw sensitive information is exposed.
    
    Returns:
    - Total assessment count
    - Unique user count (anonymized)
    - Global average scores
    - Age group statistics (aggregated)
    - Score distribution (aggregated)
    - Quality metrics (counts only)
    """
    summary = await AnalyticsService.get_overall_summary(db)
    return AnalyticsSummary(**summary)


@router.get("/trends", response_model=TrendAnalytics, dependencies=[Depends(rate_limit_analytics)])
async def get_trend_analytics(
    period: str = Query('monthly', pattern='^(daily|weekly|monthly)$', description="Time period type"),
    limit: int = Query(12, ge=1, le=24, description="Number of periods to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trend analytics over time.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: Returns aggregated time-series data only.
    No individual assessment data or user information.
    
    - **period**: Type of period (daily, weekly, monthly)
    - **limit**: Number of periods to return (max 24)
    
    Returns time-series data with:
    - Average scores per period
    - Assessment counts per period
    - Overall trend direction
    """
    trends = await AnalyticsService.get_trend_analytics(db, period_type=period, limit=limit)
    return TrendAnalytics(**trends)


@router.get("/benchmarks", response_model=list[BenchmarkComparison], dependencies=[Depends(rate_limit_analytics)])
async def get_benchmark_comparison(db: AsyncSession = Depends(get_db)):
    """
    Get benchmark comparison data with percentiles.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: Returns percentile-based aggregations only.
    No individual scores or user data exposed.
    
    Returns:
    - Global average score
    - 25th, 50th, 75th, 90th percentiles
    - Useful for comparing against population benchmarks
    """
    benchmarks = await AnalyticsService.get_benchmark_comparison(db)
    return [BenchmarkComparison(**b) for b in benchmarks]


@router.get("/insights", response_model=PopulationInsights, dependencies=[Depends(rate_limit_analytics)])
async def get_population_insights(db: AsyncSession = Depends(get_db)):
    """
    Get population-level insights.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: Returns population-level aggregations only.
    No individual user data or sensitive information.
    
    Returns:
    - Most common age group
    - Highest performing age group (by average)
    - Total population size
    - Assessment completion rate
    """
    insights = await AnalyticsService.get_population_insights(db)
    return PopulationInsights(**insights)


@router.get("/age-groups", dependencies=[Depends(rate_limit_analytics)])
async def get_age_group_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get detailed statistics by age group.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: Returns aggregated statistics per age group.
    No individual assessment data.
    
    Returns for each age group:
    - Total assessments
    - Average score
    - Min/max scores
    - Average sentiment
    """
    stats = await AnalyticsService.get_age_group_statistics(db)
    return {"age_group_statistics": stats}


@router.get("/distribution", dependencies=[Depends(rate_limit_analytics)])
async def get_score_distribution(db: AsyncSession = Depends(get_db)):
    """
    Get score distribution across ranges.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: Returns distribution counts only.
    No individual scores or user information.
    
    Returns distribution of scores in ranges:
    - 0-10, 11-20, 21-30, 31-40
    - Count and percentage for each range
    """

    distribution = await AnalyticsService.get_score_distribution(db)
    return {"score_distribution": distribution}


# ============================================================================
# User Analytics Endpoints (PR 6.3)
# ============================================================================

from ..services.user_analytics_service import UserAnalyticsService
from ..schemas import UserAnalyticsSummary, UserTrendsResponse
from ..models import User
from .auth import get_current_user

@router.get("/me/summary", response_model=UserAnalyticsSummary)
async def get_user_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized analytics summary for the current user.
    
    Returns:
    - Total exams taken
    - Average score
    - Latest & Best scores
    - Trends and consistency analysis
    """
    return await UserAnalyticsService.get_dashboard_summary(db, current_user.id)


@router.get("/me/trends", response_model=UserTrendsResponse)
async def get_user_analytics_trends(
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get time-series data for user charts.
    
    Params:
    - days: Number of days to look back (default 30, max 365)
    
    Returns:
    - EQ Score history
    - Wellbeing metrics (Sleep, Stress, etc.)
    """
    eq_scores = await UserAnalyticsService.get_eq_trends(db, current_user.id, days)
    wellbeing = await UserAnalyticsService.get_wellbeing_trends(db, current_user.id, days)
    
    return UserTrendsResponse(
        eq_scores=eq_scores,
        wellbeing=wellbeing
    )


# ============================================================================
# Performance Monitoring Endpoints
# ============================================================================

class WebVitalsMetric(BaseModel):
    """Web Vitals metric model."""
    name: str
    value: float
    rating: str
    timestamp: int
    url: str
    user_agent: Optional[str] = None


class PerformanceSummary(BaseModel):
    """Performance summary for analytics."""
    url: str
    metrics: dict
    user_agent: Optional[str] = None


@router.post("/web-vitals", status_code=201)
async def track_web_vitals(
    metric: WebVitalsMetric,
    request: Request
):
    """
    Track Web Vitals metrics from the frontend.

    Args:
        metric: Web Vitals metric data

    Returns:
        Confirmation message

    Logs performance metrics without storing PII.
    In production, integrate with analytics service.
    """
    try:
        logger.info(
            f"Web Vitals - {metric.name}: {metric.value:.2f}ms "
            f"({metric.rating}) - {metric.url}"
        )

        return {
            "status": "success",
            "message": "Metric recorded",
            "metric": metric.name,
            "value": metric.value,
            "rating": metric.rating,
        }

    except Exception as e:
        logger.error(f"Error tracking Web Vitals: {e}")
        raise HTTPException(status_code=500, detail="Failed to track metric")


@router.post("/performance-summary", status_code=201)
async def track_performance_summary(
    summary: PerformanceSummary
):
    """
    Track performance summary from the frontend.

    Args:
        summary: Performance summary data

    Returns:
        Confirmation message
    """
    try:
        logger.info(f"Performance Summary for {summary.url}")
        logger.debug(f"Metrics: {summary.metrics}")

        return {
            "status": "success",
            "message": "Performance summary recorded",
        }

    except Exception as e:
        logger.error(f"Error tracking performance summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to track summary")
