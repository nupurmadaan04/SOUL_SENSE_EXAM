from datetime import datetime, UTC, timedelta
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from ..models import (
    User, Achievement, UserAchievement, UserStreak, UserXP, 
    Challenge, UserChallenge, JournalEntry, Score
)

logger = logging.getLogger(__name__)

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

class GamificationService:
    @staticmethod
    async def award_xp(db: AsyncSession, user_id: int, amount: int, reason: str) -> UserXP:
        """Award XP (Async)."""
        """Award XP to a user and handle leveling up."""
        stmt = select(UserXP).filter(UserXP.user_id == user_id)
        result = await db.execute(stmt)
        user_xp = result.scalar_one_or_none()
        
        if not user_xp:
            user_xp = UserXP(user_id=user_id, total_xp=0, current_level=1, xp_to_next_level=500)
            db.add(user_xp)
            await db.flush()

        user_xp.total_xp += amount
        user_xp.last_xp_awarded_at = datetime.utcnow()

        while user_xp.total_xp >= user_xp.xp_to_next_level:
            user_xp.current_level += 1
            user_xp.xp_to_next_level = int(user_xp.xp_to_next_level * 1.2)
            logger.info(f"User {user_id} leveled up to {user_xp.current_level}!")

        await db.commit()
        return user_xp

    @staticmethod
    async def update_streak(db: AsyncSession, user_id: int, activity_type: str = "combined") -> UserStreak:
        """Update streak (Async)."""
        """Update user activity streak."""
        stmt = select(UserStreak).filter(
            UserStreak.user_id == user_id, 
            UserStreak.activity_type == activity_type
        )
        result = await db.execute(stmt)
        streak = result.scalar_one_or_none()

        now = datetime.now(UTC)
        today = now.date()

        if not streak:
            streak = UserStreak(
                user_id=user_id, activity_type=activity_type, 
                current_streak=1, longest_streak=1, last_activity_date=now
            )
            db.add(streak)
        else:
            last_date = streak.last_activity_date.date() if streak.last_activity_date else None
            if last_date == today:
                pass
            elif last_date == today - timedelta(days=1):
                streak.current_streak += 1
                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak
                streak.last_activity_date = now
            else:
                if streak.streak_freeze_count > 0:
                    streak.streak_freeze_count -= 1
                    streak.current_streak += 1
                    streak.last_activity_date = now
                else:
                    streak.current_streak = 1
                    streak.last_activity_date = now

        if streak.current_streak % 7 == 0:
            await GamificationService.award_xp(db, user_id, 200, f"{streak.current_streak} day streak")
        await db.commit()
        
        # Award XP for streak milestones (every 7 days)
        if streak.current_streak > 0 and streak.current_streak % 7 == 0:
            await GamificationService.award_xp(db, user_id, 200, f"{streak.current_streak} day streak milestone")
            
        return streak

    @staticmethod
    async def check_achievements(db: AsyncSession, user_id: int, activity: str) -> List[UserAchievement]:
        """Check achievements (Async)."""
        ua_stmt = select(UserAchievement).filter(
        """Check if any achievements are unlocked by the recent activity."""
        # Get all potential achievements for the category/activity
        ua_stmt = select(UserAchievement.achievement_id).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.unlocked == True
        )
        ua_result = await db.execute(ua_stmt)
        unlocked_ids = [ua.achievement_id for ua in ua_result.scalars().all()]
        
        ach_stmt = select(Achievement).filter(~Achievement.achievement_id.in_(unlocked_ids))
        ach_result = await db.execute(ach_stmt)
        potential_achievements = ach_result.scalars().all()
        
        new_unlocks = []
        unlocked_ids = list(ua_result.scalars().all())
        
        ach_stmt = select(Achievement).filter(
            ~Achievement.achievement_id.in_(unlocked_ids) if unlocked_ids else True
        )
        ach_result = await db.execute(ach_stmt)
        potential_achievements = list(ach_result.scalars().all())
        
        new_unlocks = []
        
        for ach in potential_achievements:
            met = False
            if ach.achievement_id == "FIRST_JOURNAL" and activity == "journal":
                met = True
            elif ach.achievement_id == "EQ_EXPLORER" and activity == "assessment":
                met = True
            elif ach.achievement_id == "MONTHLY_MASTER":
                thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat()
                count_stmt = select(func.count(JournalEntry.id)).filter(
                    JournalEntry.user_id == user_id,
                    JournalEntry.timestamp >= thirty_days_ago
                )
                count_result = await db.execute(count_stmt)
                if (count_result.scalar() or 0) >= 30:
                    met = True
            
            if met:
                stmt_lookup = select(UserAchievement).filter(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == ach.achievement_id
                )
                lookup_result = await db.execute(stmt_lookup)
                ua = lookup_result.scalar_one_or_none()
                # Check journal count in last 30 days
                thirty_days_ago = (datetime.now(UTC) - timedelta(days=30))
                journal_stmt = select(func.count(JournalEntry.id)).filter(
                    JournalEntry.user_id == user_id,
                    JournalEntry.timestamp >= thirty_days_ago,
                    JournalEntry.is_deleted == False
                )
                journal_res = await db.execute(journal_stmt)
                count = journal_res.scalar() or 0
                if count >= 30:
                    met = True
            
            if met:
                ua_check_stmt = select(UserAchievement).filter(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == ach.achievement_id
                )
                ua_check_res = await db.execute(ua_check_stmt)
                ua = ua_check_res.scalar_one_or_none()
                
                if not ua:
                    ua = UserAchievement(
                        user_id=user_id, achievement_id=ach.achievement_id,
                        progress=100, unlocked=True, unlocked_at=datetime.utcnow()
                    )
                    db.add(ua)
                else:
                    ua.progress = 100
                    ua.unlocked = True
                    ua.unlocked_at = datetime.utcnow()
                
                new_unlocks.append(ua)
                await GamificationService.award_xp(db, user_id, ach.points_reward, f"Unlocked {ach.name}")

                await GamificationService.award_xp(db, user_id, ach.points_reward, f"Unlocked achievement: {ach.name}")

        await db.commit()
        return new_unlocks

    @staticmethod
    async def get_user_summary(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """User summary (Async)."""
        stmt_xp = select(UserXP).filter(UserXP.user_id == user_id)
        result_xp = await db.execute(stmt_xp)
        xp = result_xp.scalar_one_or_none()
        """Get a summary of user gamification stats."""
        xp_stmt = select(UserXP).filter(UserXP.user_id == user_id)
        xp_res = await db.execute(xp_stmt)
        xp = xp_res.scalar_one_or_none()
        
        if not xp:
            xp = UserXP(user_id=user_id, total_xp=0, current_level=1, xp_to_next_level=500)
            db.add(xp)
            await db.commit()
            
        stmt_streaks = select(UserStreak).filter(UserStreak.user_id == user_id)
        result_streaks = await db.execute(stmt_streaks)
        streaks = result_streaks.scalars().all()
        
        stmt_ua = select(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.unlocked == True
        ).order_by(desc(UserAchievement.unlocked_at)).limit(5)
        result_ua = await db.execute(stmt_ua)
        recent_ua = result_ua.scalars().all()
        
        achievements = []
        for ua in recent_ua:
            stmt_ach = select(Achievement).filter(Achievement.achievement_id == ua.achievement_id)
            result_ach = await db.execute(stmt_ach)
            ach = result_ach.scalar_one_or_none()
        streak_stmt = select(UserStreak).filter(UserStreak.user_id == user_id)
        streak_res = await db.execute(streak_stmt)
        streaks = list(streak_res.scalars().all())
        
        # Recent achievements
        recent_ua_stmt = select(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.unlocked == True
        ).order_by(desc(UserAchievement.unlocked_at)).limit(5)
        
        recent_ua_res = await db.execute(recent_ua_stmt)
        recent_ua = list(recent_ua_res.scalars().all())
        
        achievements = []
        for ua in recent_ua:
            ach_stmt = select(Achievement).filter(Achievement.achievement_id == ua.achievement_id)
            ach_res = await db.execute(ach_stmt)
            ach = ach_res.scalar_one_or_none()
            if ach:
                achievements.append({
                    "name": ach.name,
                    "description": ach.description,
                    "icon": ach.icon,
                    "unlocked_at": ua.unlocked_at
                })
                
        return {
            "xp": {
                "total_xp": xp.total_xp,
                "current_level": xp.current_level,
                "level_progress": xp.total_xp / xp.xp_to_next_level if xp.xp_to_next_level > 0 else 1.0
            },
            "streaks": [
                {
                    "activity_type": s.activity_type,
                    "current_streak": s.current_streak,
                    "is_active_today": s.last_activity_date.date() == datetime.now(UTC).date() if s.last_activity_date else False
                } for s in streaks
            ],
            "recent_achievements": achievements
        }

    @staticmethod
    async def get_leaderboard(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the global anonymized leaderboard (Async)."""
        stmt = select(UserXP, User.username).join(User, UserXP.user_id == User.id).order_by(desc(UserXP.total_xp)).limit(limit)
        result = await db.execute(stmt)
        results = result.all()
        """Get the global anonymized leaderboard."""
        stmt = select(UserXP, User.username).join(User, UserXP.user_id == User.id).order_by(desc(UserXP.total_xp)).limit(limit)
        result = await db.execute(stmt)
        rows = result.all()
        
        leaderboard = []
        for i, (xp, username) in enumerate(rows):
            leaderboard.append({
                "rank": i + 1,
                "username": f"{username[:3]}***" if username else "Anonymous",
                "total_xp": xp.total_xp,
                "current_level": xp.current_level
            })
        return leaderboard

    @staticmethod
    async def seed_initial_achievements(db: AsyncSession):
        """Seed the database with initial achievements if they don't exist (Async)."""
        """Seed the database with initial achievements if they don't exist."""
        initial_achievements = [
            {
                "achievement_id": "FIRST_JOURNAL",
                "name": "First Journal",
                "description": "Write your first journal entry",
                "icon": "📝",
                "category": "consistency",
                "rarity": "common",
                "points_reward": 50
            },
            {
                "achievement_id": "WEEK_WARRIOR",
                "name": "Week Warrior",
                "description": "Journal for 7 consecutive days",
                "icon": "🛡️",
                "category": "consistency",
                "rarity": "rare",
                "points_reward": 200
            },
            {
                "achievement_id": "EQ_EXPLORER",
                "name": "EQ Explorer",
                "description": "Complete your first emotional assessment",
                "icon": "🔍",
                "category": "awareness",
                "rarity": "common",
                "points_reward": 100
            }
        ]
        
        for ach_data in initial_achievements:
            stmt = select(Achievement).filter(Achievement.achievement_id == ach_data["achievement_id"])
            result = await db.execute(stmt)
            exists = result.scalar_one_or_none()
            if not exists:
<<<<<<< HEAD
=======
            check_stmt = select(Achievement).filter(Achievement.achievement_id == ach_data["achievement_id"])
            check_res = await db.execute(check_stmt)
            if not check_res.scalar_one_or_none():
>>>>>>> aa71e7b (ISSUE-1318)
                ach = Achievement(**ach_data)
                db.add(ach)
        await db.commit()
