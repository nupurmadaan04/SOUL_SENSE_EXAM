"""
Tests for Emotion Comparison Service.
"""

import pytest
from datetime import datetime, timedelta
from backend.fastapi.api.services.emotion_comparison_service import EmotionComparisonService


@pytest.mark.asyncio
async def test_compare_periods(async_db, test_user):
    """Test comparing two time periods."""
    now = datetime.now()
    period1_start = now - timedelta(days=14)
    period1_end = now - timedelta(days=7)
    period2_start = now - timedelta(days=7)
    period2_end = now
    
    result = await EmotionComparisonService.compare_periods(
        db=async_db,
        user_id=test_user.id,
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end
    )
    
    assert 'period1' in result
    assert 'period2' in result
    assert 'comparison' in result
    assert 'metrics' in result['period1']
    assert 'metrics' in result['period2']


@pytest.mark.asyncio
async def test_calculate_changes():
    """Test percentage change calculations."""
    period1 = {
        'avg_sentiment': 0.5,
        'avg_mood': 5.0,
        'avg_stress': 3.0,
        'journal_entries': 10,
        'avg_eq_score': 75.0
    }
    
    period2 = {
        'avg_sentiment': 0.6,
        'avg_mood': 6.0,
        'avg_stress': 2.5,
        'journal_entries': 15,
        'avg_eq_score': 80.0
    }
    
    changes = EmotionComparisonService._calculate_changes(period1, period2)
    
    assert changes['sentiment']['direction'] == 'up'
    assert changes['sentiment']['percentage'] == 20.0
    assert changes['mood']['direction'] == 'up'
    assert changes['stress']['direction'] == 'down'


def test_calculate_changes_zero_baseline():
    """Test change calculation with zero baseline."""
    period1 = {'avg_sentiment': 0, 'avg_mood': 0, 'avg_stress': 0, 'journal_entries': 0, 'avg_eq_score': 0}
    period2 = {'avg_sentiment': 0.5, 'avg_mood': 5.0, 'avg_stress': 3.0, 'journal_entries': 10, 'avg_eq_score': 75.0}
    
    changes = EmotionComparisonService._calculate_changes(period1, period2)
    
    assert changes['sentiment']['percentage'] == 0
    assert changes['sentiment']['direction'] == 'neutral'
