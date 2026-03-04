"""
Goal Service Layer (Async)

Handles business logic for structured emotional goal setting, 
tracking progress metrics, and managing goal lifecycles.
"""

from typing import Optional, List, Tuple, Any
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, case
from fastapi import HTTPException, status

from api.root_models import Goal, User
from ..schemas import GoalCreate, GoalUpdate

class GoalService:
    """Service for managing emotional goals and progress tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_goal(self, user_id: int, goal_data: GoalCreate) -> Goal:
        """Create a new emotional goal for a user."""
        new_goal = Goal(
            user_id=user_id,
            title=goal_data.title,
            description=goal_data.description,
            category=goal_data.category,
            target_value=goal_data.target_value,
            current_value=0.0,
            unit=goal_data.unit,
            deadline=goal_data.deadline,
            status='active',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        self.db.add(new_goal)
        try:
            await self.db.commit()
            await self.db.refresh(new_goal)
            return new_goal
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create goal: {str(e)}"
            )

    async def get_goal_by_id(self, goal_id: int, user_id: int) -> Goal:
        """Retrieve a specific goal by ID, ensuring it belongs to the user."""
        stmt = select(Goal).filter(and_(Goal.id == goal_id, Goal.user_id == user_id))
        result = await self.db.execute(stmt)
        goal = result.scalar_one_or_none()
        
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )
        return goal

    async def get_user_goals(
        self, 
        user_id: int, 
        status_filter: Optional[str] = None,
        skip: int = 0, 
        limit: int = 50
    ) -> Tuple[List[Goal], int]:
        """Retrieve all goals for a user with optional status filtering."""
        stmt = select(Goal).filter(Goal.user_id == user_id)
        
        if status_filter:
            stmt = stmt.filter(Goal.status == status_filter)
            
        # Get total count for pagination
        count_stmt = select(func.count(Goal.id)).filter(Goal.user_id == user_id)
        if status_filter:
            count_stmt = count_stmt.filter(Goal.status == status_filter)
            
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        stmt = stmt.order_by(Goal.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        goals = list(result.scalars().all())
        
        return goals, total

    async def update_goal(self, goal_id: int, user_id: int, goal_update: GoalUpdate) -> Goal:
        """Update goal details or progress."""
        goal = await self.get_goal_by_id(goal_id, user_id)
        
        update_data = goal_update.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(goal, key, value)
            
        # Auto-complete goal if current_value >= target_value
        if goal.current_value >= goal.target_value and goal.status == 'active':
            goal.status = 'completed'
            
        goal.updated_at = datetime.now(UTC)
        
        try:
            await self.db.commit()
            await self.db.refresh(goal)
            return goal
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update goal: {str(e)}"
            )

    async def delete_goal(self, goal_id: int, user_id: int) -> bool:
        """Delete a goal."""
        goal = await self.get_goal_by_id(goal_id, user_id)
        
        try:
            await self.db.delete(goal)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete goal: {str(e)}"
            )

    async def get_goal_stats(self, user_id: int) -> dict:
        """Get summary statistics for user goals."""
        stmt = select(
            func.count(Goal.id).label("total"),
            func.sum(case((Goal.status == 'completed', 1), else_=0)).label("completed"),
            func.sum(case((Goal.status == 'active', 1), else_=0)).label("active")
        ).filter(Goal.user_id == user_id)
        
        
        result = await self.db.execute(stmt)
        row = result.first()
        
        return {
            "total_goals": row.total or 0,
            "completed_goals": row.completed or 0,
            "active_goals": row.active or 0,
            "success_rate": (row.completed / row.total * 100) if row.total and row.total > 0 else 0
        }
