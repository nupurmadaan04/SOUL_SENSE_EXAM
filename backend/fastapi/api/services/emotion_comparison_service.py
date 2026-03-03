"""
Emotion Comparison Service for side-by-side date range analysis.

Allows users to compare emotional patterns across different time periods.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import logging

from ..models import JournalEntry, Score

logger = logging.getLogger(__name__)


class EmotionComparisonService:
    """Service for comparing emotions across different time periods."""
    
    @staticmethod
    async def compare_periods(
        db: AsyncSession,
        user_id: int,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime
    ) -> Dict:
        """
        Compare emotional metrics between two time periods.
        
        Returns comparative analytics including:
        - Average sentiment scores
        - Mood trends
        - Entry counts
        - Change percentages
        """
        # Get period 1 data
        period1_data = await EmotionComparisonService._get_period_data(
            db, user_id, period1_start, period1_end
        )
        
        # Get period 2 data
        period2_data = await EmotionComparisonService._get_period_data(
            db, user_id, period2_start, period2_end
        )
        
        # Calculate comparisons
        comparison = {
            'period1': {
                'start': period1_start.isoformat(),
                'end': period1_end.isoformat(),
                'metrics': period1_data
            },
            'period2': {
                'start': period2_start.isoformat(),
                'end': period2_end.isoformat(),
                'metrics': period2_data
            },
            'comparison': EmotionComparisonService._calculate_changes(
                period1_data, period2_data
            )
        }
        
        return comparison
    
    @staticmethod
    async def _get_period_data(
        db: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get emotional metrics for a specific period."""
        
        # Journal entries
        journal_stmt = select(
            func.count(JournalEntry.id).label('count'),
            func.avg(JournalEntry.sentiment_score).label('avg_sentiment'),
            func.avg(JournalEntry.mood_score).label('avg_mood'),
            func.avg(JournalEntry.stress_level).label('avg_stress')
        ).filter(
            and_(
                JournalEntry.user_id == user_id,
                JournalEntry.timestamp >= start_date.isoformat(),
                JournalEntry.timestamp <= end_date.isoformat(),
                JournalEntry.is_deleted == False
            )
        )
        
        journal_result = await db.execute(journal_stmt)
        journal_data = journal_result.first()
        
        # Assessment scores
        score_stmt = select(
            func.count(Score.id).label('count'),
            func.avg(Score.total_score).label('avg_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        ).filter(
            and_(
                Score.user_id == user_id,
                Score.timestamp >= start_date.isoformat(),
                Score.timestamp <= end_date.isoformat()
            )
        )
        
        score_result = await db.execute(score_stmt)
        score_data = score_result.first()
        
        return {
            'journal_entries': journal_data.count or 0,
            'avg_sentiment': float(journal_data.avg_sentiment or 0),
            'avg_mood': float(journal_data.avg_mood or 0),
            'avg_stress': float(journal_data.avg_stress or 0),
            'assessments': score_data.count or 0,
            'avg_eq_score': float(score_data.avg_score or 0)
        }
    
    @staticmethod
    def _calculate_changes(period1: Dict, period2: Dict) -> Dict:
        """Calculate percentage changes between periods."""
        
        def calc_change(val1: float, val2: float) -> Dict:
            if val1 == 0:
                return {'change': 0, 'percentage': 0, 'direction': 'neutral'}
            
            change = val2 - val1
            percentage = (change / val1) * 100
            direction = 'up' if change > 0 else 'down' if change < 0 else 'neutral'
            
            return {
                'change': round(change, 2),
                'percentage': round(percentage, 2),
                'direction': direction
            }
        
        return {
            'sentiment': calc_change(
                period1['avg_sentiment'],
                period2['avg_sentiment']
            ),
            'mood': calc_change(
                period1['avg_mood'],
                period2['avg_mood']
            ),
            'stress': calc_change(
                period1['avg_stress'],
                period2['avg_stress']
            ),
            'eq_score': calc_change(
                period1['avg_eq_score'],
                period2['avg_eq_score']
            ),
            'journal_activity': calc_change(
                period1['journal_entries'],
                period2['journal_entries']
            )
        }
