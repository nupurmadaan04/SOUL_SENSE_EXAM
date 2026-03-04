import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.fastapi.api.models import Base, User, Goal
from backend.fastapi.api.services.goal_service import GoalService
from backend.fastapi.api.schemas import GoalCreate
import os

DATABASE_URL = "sqlite+aiosqlite:///./test_goals.db"

async def test_goal_feature():
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db:
        # Create a test user
        user = User(username="goal_test_user", password_hash="hash")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        service = GoalService(db)
        
        # Test creation
        print("Creating goal...")
        goal_data = GoalCreate(
            title="Practice Empathy",
            description="Listen more, speak less",
            category="Empathy",
            target_value=10.0,
            unit="sessions"
        )
        goal = await service.create_goal(user.id, goal_data)
        print(f"Goal created: {goal.title} (ID: {goal.id})")
        
        # Test progression
        print("Updating progress...")
        from backend.fastapi.api.schemas import GoalUpdate
        await service.update_goal(goal.id, user.id, GoalUpdate(current_value=5.0))
        await db.refresh(goal)
        print(f"Progress: {goal.current_value}/{goal.target_value} ({goal.status})")
        
        # Test completion
        print("Completing goal...")
        await service.update_goal(goal.id, user.id, GoalUpdate(current_value=10.0))
        await db.refresh(goal)
        print(f"Status after completion: {goal.status}")
        
        # Test stats
        stats = await service.get_goal_stats(user.id)
        print(f"Stats: {stats}")

    await engine.dispose()
    if os.path.exists("./test_goals.db"):
        os.remove("./test_goals.db")

if __name__ == "__main__":
    asyncio.run(test_goal_feature())
