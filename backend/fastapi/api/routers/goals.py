"""
Goals Router (Async Version)

Provides authenticated endpoints for creating, tracking, 
and managing emotional growth goals.
"""

from typing import Annotated, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalListResponse
)
from ..services.goal_service import GoalService
from ..routers.auth import get_current_user
from ..services.db_service import get_db
from ..models import User

router = APIRouter(tags=["Goals"])

async def get_goal_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get GoalService with async database session."""
    return GoalService(db)

@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, summary="Create Emotional Goal")
async def create_goal(
    goal_data: GoalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)]
):
    """
    Create a new structured emotional goal for the authenticated user.
    """
    return await goal_service.create_goal(current_user.id, goal_data)

@router.get("/", response_model=GoalListResponse, summary="List My Goals")
async def list_my_goals(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """
    Retrieve a paginated list of goals for the current user.
    Optional filter by status (active, completed, abandoned, paused).
    """
    skip = (page - 1) * page_size
    goals, total = await goal_service.get_user_goals(
        user_id=current_user.id,
        status_filter=status,
        skip=skip,
        limit=page_size
    )
    
    return GoalListResponse(
        total=total,
        goals=goals,
        page=page,
        page_size=page_size
    )

@router.get("/stats", summary="Get Goal Statistics")
async def get_goal_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)]
):
    """
    Get a summary of goal progress and success rates for the current user.
    """
    return await goal_service.get_goal_stats(current_user.id)

@router.get("/{goal_id}", response_model=GoalResponse, summary="Get Goal Details")
async def get_goal_details(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)]
):
    """
    Retrieve details for a specific goal.
    """
    return await goal_service.get_goal_by_id(goal_id, current_user.id)

@router.patch("/{goal_id}", response_model=GoalResponse, summary="Update Goal Progress")
async def update_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)]
):
    """
    Update an existing goal's details or report progress.
    If current_value reaches target_value, status is automatically set to 'completed'.
    """
    return await goal_service.update_goal(goal_id, current_user.id, goal_update)

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Goal")
async def delete_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)]
):
    """
    Permanently remove a goal.
    """
    await goal_service.delete_goal(goal_id, current_user.id)
    return None
