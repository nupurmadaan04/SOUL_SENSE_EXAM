import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from backend.fastapi.api.models import Goal, User
from backend.fastapi.api.services.goal_service import GoalService
from backend.fastapi.api.schemas import GoalCreate, GoalUpdate

@pytest.mark.asyncio
async def test_create_goal(db_session: AsyncSession):
    # Setup test user
    user = User(username="testuser", password_hash="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    service = GoalService(db_session)
    goal_data = GoalCreate(
        title="Journaling",
        category="Reflection",
        target_value=30.0,
        unit="days"
    )
    
    goal = await service.create_goal(user.id, goal_data)
    
    assert goal.title == "Journaling"
    assert goal.user_id == user.id
    assert goal.status == "active"
    assert goal.current_value == 0.0

@pytest.mark.asyncio
async def test_update_goal_progress_and_completion(db_session: AsyncSession):
    # Setup test user and goal
    user = User(username="testuser2", password_hash="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    service = GoalService(db_session)
    goal = Goal(
        user_id=user.id,
        title="Sleep Improvement",
        category="Health",
        target_value=7.0,
        current_value=0.0,
        status="active"
    )
    db_session.add(goal)
    await db_session.commit()
    await db_session.refresh(goal)
    
    # Update progress
    await service.update_goal(goal.id, user.id, GoalUpdate(current_value=4.0))
    await db_session.refresh(goal)
    assert goal.current_value == 4.0
    assert goal.status == "active"
    
    # Complete goal
    await service.update_goal(goal.id, user.id, GoalUpdate(current_value=7.0))
    await db_session.refresh(goal)
    assert goal.current_value == 7.0
    assert goal.status == "completed"
