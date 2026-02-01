"""Analytics API router - Aggregated, non-sensitive data only."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..services.db_service import get_db
from ..services.analytics_service import AnalyticsService
from ..schemas import (
    AnalyticsSummary,
    TrendAnalytics,
    BenchmarkComparison,
    PopulationInsights
)
from ..middleware.rate_limiter import rate_limit_analytics

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary, dependencies=[Depends(rate_limit_analytics)])
async def get_analytics_summary(db: Session = Depends(get_db)):
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
    summary = AnalyticsService.get_overall_summary(db)
    return AnalyticsSummary(**summary)


@router.get("/trends", response_model=TrendAnalytics, dependencies=[Depends(rate_limit_analytics)])
async def get_trend_analytics(
    period: str = Query('monthly', pattern='^(daily|weekly|monthly)$', description="Time period type"),
    limit: int = Query(12, ge=1, le=24, description="Number of periods to return"),
    db: Session = Depends(get_db)
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
    trends = AnalyticsService.get_trend_analytics(db, period_type=period, limit=limit)
    return TrendAnalytics(**trends)


@router.get("/benchmarks", response_model=list[BenchmarkComparison], dependencies=[Depends(rate_limit_analytics)])
async def get_benchmark_comparison(db: Session = Depends(get_db)):
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
    benchmarks = AnalyticsService.get_benchmark_comparison(db)
    return [BenchmarkComparison(**b) for b in benchmarks]


@router.get("/insights", response_model=PopulationInsights, dependencies=[Depends(rate_limit_analytics)])
async def get_population_insights(db: Session = Depends(get_db)):
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
    insights = AnalyticsService.get_population_insights(db)
    return PopulationInsights(**insights)


@router.get("/age-groups", dependencies=[Depends(rate_limit_analytics)])
async def get_age_group_statistics(db: Session = Depends(get_db)):
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
    stats = AnalyticsService.get_age_group_statistics(db)
    return {"age_group_statistics": stats}


@router.get("/distribution", dependencies=[Depends(rate_limit_analytics)])
async def get_score_distribution(db: Session = Depends(get_db)):
    """
    Get score distribution across ranges.
    
    **Rate Limited**: 30 requests per minute per IP
    
    **Data Privacy**: Returns distribution counts only.
    No individual scores or user information.
    
    Returns distribution of scores in ranges:
    - 0-10, 11-20, 21-30, 31-40
    - Count and percentage for each range
    """
    distribution = AnalyticsService.get_score_distribution(db)
    return {"score_distribution": distribution}
