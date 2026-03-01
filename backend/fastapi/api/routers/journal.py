"""
Journal Router

Provides authenticated API endpoints for journal management:
- Full CRUD operations
- Sentiment analysis (automatic on create/update)
- Tag management
- Search and filtering
- Analytics and trends
- Export functionality
- AI Journaling prompts
"""

from datetime import datetime, UTC
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, status, Request, BackgroundTasks
from fastapi.responses import Response as FastApiResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import (
    JournalCreate,
    JournalUpdate,
    JournalResponse,
    JournalCursorResponse,
    JournalAnalytics,
    # JournalSearchParams,
    JournalPromptsResponse,
    JournalPrompt,
    SmartPromptsResponse,
    SmartPrompt
)
from ..services.journal_service import JournalService, get_journal_prompts
from ..services.smart_prompt_service import SmartPromptService
from ..services.db_service import get_db
from ..routers.auth import get_current_user
from ..models import User
from ..utils.limiter import limiter

router = APIRouter(tags=["Journal"])


async def get_journal_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get JournalService."""
    return JournalService(db)


# ============================================================================
# Journal CRUD Endpoints
# ============================================================================

@router.post("/", response_model=JournalResponse, status_code=status.HTTP_202_ACCEPTED, summary="Create Journal Entry")
@limiter.limit("10/minute")
async def create_journal(
    request: Request,
    journal_data: JournalCreate,
    background_tasks: Annotated[BackgroundTasks, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Create a new journal entry. AI sentiment analysis starts asynchronously via gRPC.
    """
    return await journal_service.create_entry(
        current_user=current_user,
        content=journal_data.content,
        background_tasks=background_tasks,
        tags=journal_data.tags,
        privacy_level=journal_data.privacy_level,
        sleep_hours=journal_data.sleep_hours,
        sleep_quality=journal_data.sleep_quality,
        energy_level=journal_data.energy_level,
        work_hours=journal_data.work_hours,
        screen_time_mins=journal_data.screen_time_mins,
        stress_level=journal_data.stress_level,
        stress_triggers=journal_data.stress_triggers,
        daily_schedule=journal_data.daily_schedule
    )


@router.get("/", response_model=JournalCursorResponse, summary="List Journal Entries")
@router.get("/", response_model=JournalListResponse, summary="List Journal Entries")
@limiter.limit("100/minute")
async def list_journals(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)],
    cursor: Optional[str] = Query(None, description="ISO format date or timestamp|id tie-breaker"),
    limit: int = Query(25, ge=1, le=100),
    start_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD")
):
    """
    List user's journal entries with pagination and date filtering.
    """
    entries, total = await journal_service.get_entries(
        current_user=current_user,
        cursor=cursor,
        limit=limit,
        start_date=start_date,
        end_date=end_date
    )
    
    return JournalCursorResponse(
        data=[JournalResponse.model_validate(e) for e in entries],
        next_cursor=next_cursor,
        has_more=has_more
    )


# ============================================================================
# Advanced Features 
# ============================================================================

@router.get("/prompts", response_model=JournalPromptsResponse, summary="Get AI Prompts")
async def list_prompts(
    category: Optional[str] = Query(None, pattern="^(gratitude|reflection|goals|emotions|creativity)$")
):
    """
    Get AI-generated journaling prompts to inspire writing.
    """
    prompts = get_journal_prompts(category)
    return JournalPromptsResponse(
        prompts=[JournalPrompt(**p) for p in prompts],
        category=category
    )


@router.get("/smart-prompts", response_model=SmartPromptsResponse, summary="Get Smart AI Prompts")
async def get_smart_prompts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    count: int = Query(3, ge=1, le=5, description="Number of prompts to return")
):
    """
    Get AI-personalized journal prompts based on user's emotional context.
    """
    smart_service = SmartPromptService(db)
    result = await smart_service.get_smart_prompts(
        user_id=current_user.id,
        count=count
    )
    
    return SmartPromptsResponse(
        prompts=[SmartPrompt(**p) for p in result["prompts"]],
        user_mood=result["user_mood"],
        detected_patterns=result["detected_patterns"],
        sentiment_avg=result["sentiment_avg"]
    )


@router.get("/search", response_model=JournalListResponse, summary="Search Journal Entries")
async def search_journals(
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)],
    query: Optional[str] = Query(None, min_length=2),
    tags: Optional[List[str]] = Query(None),
    sentiment_category: Optional[str] = Query(None, pattern="^(positive|neutral|negative)$", description="Filter by category"),
    min_sentiment: Optional[float] = Query(None, ge=0, le=100),
    max_sentiment: Optional[float] = Query(None, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search across journal content, tags, and sentiment scores.
    """
    entries, total = await journal_service.search_entries(
        current_user=current_user,
        query=query,
        tags=tags,
        sentiment_category=sentiment_category,
        min_sentiment=min_sentiment,
        max_sentiment=max_sentiment,
        skip=skip,
        limit=limit
    )
    
    return JournalListResponse(
        total=total,
        entries=[JournalResponse.model_validate(e) for e in entries],
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/analytics", response_model=JournalAnalytics, summary="Get Journal Analytics")
async def get_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Detailed analytics on journaling patterns.
    """
    return await journal_service.get_analytics(current_user)


@router.get("/export", summary="Export Journal Entries")
async def export_journals(
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)],
    format: str = Query("json", pattern="^(json|txt)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Export all journal entries in JSON or TXT format.
    """
    content = await journal_service.export_entries(
        current_user=current_user,
        format=format,
        start_date=start_date,
        end_date=end_date
    )
    
    media_type = "application/json" if format == "json" else "text/plain"
    return FastApiResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=journal_export_{datetime.now(UTC).strftime('%Y%m%d')}.{format}"}
    )


# ============================================================================
# Journal CRUD Endpoints (Dynamic Routes)
# ============================================================================

@router.get("/{journal_id}", response_model=JournalResponse, summary="Get Journal Entry")
async def get_journal(
    journal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Retrieve a specific journal entry by ID.
    """
    return await journal_service.get_entry_by_id(journal_id, current_user)


@router.put("/{journal_id}", response_model=JournalResponse, summary="Update Journal Entry")
async def update_journal(
    journal_id: int,
    journal_data: JournalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Update an existing journal entry.
    """
    return await journal_service.update_entry(
        entry_id=journal_id,
        current_user=current_user,
        **journal_data.model_dump(exclude_unset=True)
    )


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Journal Entry")
async def delete_journal(
    journal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Mark a journal entry as deleted.
    """
    await journal_service.delete_entry(journal_id, current_user)
    return None
