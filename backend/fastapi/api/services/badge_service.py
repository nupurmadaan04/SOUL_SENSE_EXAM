from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, UTC
from ..models import Badge, UserBadge, User, JournalEntry, Score, UserStreak
import logging

logger = logging.getLogger(__name__)

class BadgeService:
    """Service for badge unlock logic and milestone tracking."""

    BADGE_RULES = {
        "first_journal": {"type": "count", "table": "journal", "threshold": 1, "category": "journal"},
        "journal_streak_7": {"type": "streak", "table": "journal", "threshold": 7, "category": "journal"},
        "journal_streak_30": {"type": "streak", "table": "journal", "threshold": 30, "category": "journal"},
        "journal_100": {"type": "count", "table": "journal", "threshold": 100, "category": "journal"},
        "first_eq_test": {"type": "count", "table": "eq_test", "threshold": 1, "category": "eq_test"},
        "eq_master": {"type": "score", "table": "eq_test", "threshold": 90, "category": "eq_test"},
        "eq_improvement": {"type": "improvement", "table": "eq_test", "threshold": 20, "category": "growth"},
        "consistent_user": {"type": "streak", "table": "combined", "threshold": 14, "category": "streak"},
    }

    @classmethod
    async def check_and_unlock_badges(cls, user_id: int, db: AsyncSession) -> List[Badge]:
        """Check all badge rules and unlock eligible badges."""
        unlocked = []
        for badge_name, rule in cls.BADGE_RULES.items():
            badge = await cls._get_or_create_badge(badge_name, rule, db)
            user_badge = await cls._get_user_badge(user_id, badge.id, db)
            
            if not user_badge.unlocked:
                progress = await cls._calculate_progress(user_id, rule, db)
                user_badge.progress = progress
                
                if progress >= rule["threshold"]:
                    user_badge.unlocked = True
                    user_badge.earned_at = datetime.now(UTC)
                    unlocked.append(badge)
                    logger.info(f"Badge unlocked: {badge_name} for user {user_id}")
        
        await db.commit()
        return unlocked

    @classmethod
    async def _get_or_create_badge(cls, name: str, rule: Dict, db: AsyncSession) -> Badge:
        """Get or create badge definition."""
        stmt = select(Badge).filter(Badge.name == name)
        result = await db.execute(stmt)
        badge = result.scalar_one_or_none()
        
        if not badge:
            badge = Badge(
                name=name,
                description=cls._get_description(name),
                icon=cls._get_icon(name),
                category=rule["category"],
                milestone_type=rule["type"],
                milestone_value=rule["threshold"]
            )
            db.add(badge)
            await db.flush()
        return badge

    @classmethod
    async def _get_user_badge(cls, user_id: int, badge_id: int, db: AsyncSession) -> UserBadge:
        """Get or create user badge progress."""
        stmt = select(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.badge_id == badge_id
        )
        result = await db.execute(stmt)
        user_badge = result.scalar_one_or_none()
        
        if not user_badge:
            user_badge = UserBadge(user_id=user_id, badge_id=badge_id)
            db.add(user_badge)
            await db.flush()
        return user_badge

    @classmethod
    async def _calculate_progress(cls, user_id: int, rule: Dict, db: AsyncSession) -> int:
        """Calculate current progress toward milestone."""
        if rule["type"] == "count":
            if rule["table"] == "journal":
                stmt = select(func.count(JournalEntry.id)).filter(JournalEntry.user_id == user_id)
            elif rule["table"] == "eq_test":
                stmt = select(func.count(Score.id)).filter(Score.user_id == user_id)
            result = await db.execute(stmt)
            return result.scalar() or 0
        
        elif rule["type"] == "streak":
            stmt = select(UserStreak.current_streak).filter(
                UserStreak.user_id == user_id,
                UserStreak.activity_type == rule["table"]
            )
            result = await db.execute(stmt)
            return result.scalar() or 0
        
        elif rule["type"] == "score":
            stmt = select(func.max(Score.total_score)).filter(Score.user_id == user_id)
            result = await db.execute(stmt)
            return result.scalar() or 0
        
        elif rule["type"] == "improvement":
            stmt = select(Score.total_score).filter(Score.user_id == user_id).order_by(Score.timestamp)
            result = await db.execute(stmt)
            scores = result.scalars().all()
            if len(scores) >= 2:
                return max(0, scores[-1] - scores[0])
            return 0
        
        return 0

    @classmethod
    async def get_user_badges(cls, user_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all badges for a user with progress."""
        stmt = select(UserBadge, Badge).join(Badge).filter(UserBadge.user_id == user_id)
        result = await db.execute(stmt)
        
        badges = []
        for user_badge, badge in result:
            badges.append({
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "category": badge.category,
                "progress": user_badge.progress,
                "milestone": badge.milestone_value,
                "unlocked": user_badge.unlocked,
                "earned_at": user_badge.earned_at.isoformat() if user_badge.earned_at else None
            })
        return badges

    @staticmethod
    def _get_description(name: str) -> str:
        descriptions = {
            "first_journal": "Write your first journal entry",
            "journal_streak_7": "Maintain a 7-day journaling streak",
            "journal_streak_30": "Maintain a 30-day journaling streak",
            "journal_100": "Write 100 journal entries",
            "first_eq_test": "Complete your first EQ assessment",
            "eq_master": "Score 90+ on an EQ assessment",
            "eq_improvement": "Improve your EQ score by 20 points",
            "consistent_user": "Use the app for 14 consecutive days"
        }
        return descriptions.get(name, "Achievement unlocked")

    @staticmethod
    def _get_icon(name: str) -> str:
        icons = {
            "first_journal": "📝",
            "journal_streak_7": "🔥",
            "journal_streak_30": "🏆",
            "journal_100": "💯",
            "first_eq_test": "🎯",
            "eq_master": "👑",
            "eq_improvement": "📈",
            "consistent_user": "⭐"
        }
        return icons.get(name, "🎖️")
