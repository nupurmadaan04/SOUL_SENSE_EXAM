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
    JournalListResponse,
    # JournalSearchParams,
    JournalPromptsResponse,
    JournalPrompt,
    SmartPromptsResponse,
    SmartPrompt,
    EmotionFilterRequest,
    JournalFilterResponse,
    FilterOptionsResponse
)
from ..services.journal_service import JournalService, get_journal_prompts
from ..services.smart_prompt_service import SmartPromptService
from ..services.db_service import get_db
from ..routers.auth import get_current_user
from ..models import User
from ..utils.limiter import limiter

router = APIRouter(tags=["Journal"])


from sqlalchemy.ext.asyncio import AsyncSession

def get_journal_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get JournalService."""
    return JournalService(db)

@router.post("/", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/", response_model=JournalListResponse, summary="List Journal Entries")
@limiter.limit("100/minute")
async def list_journals(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)],
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List user's journal entries with pagination and date filtering.
    """
    entries, total = await journal_service.get_entries(
        current_user=current_user,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date
    )
    return JournalListResponse(
        total=total,
        entries=[JournalResponse.model_validate(e) for e in entries],
        page=skip // limit + 1,
        page_size=limit
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


@router.get("/search", response_model=JournalListResponse, summary="Search Journal Entries")
@limiter.limit("100/minute")
async def search_journals(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)],
    query: Optional[str] = Query(None, min_length=2),
    tags: Optional[List[str]] = Query(None),
    sentiment_category: Optional[str] = Query(None, pattern="^(positive|neutral|negative)$"),
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


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal(
    journal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    return await journal_service.get_entry_by_id(journal_id, current_user)

@router.put("/{journal_id}", response_model=JournalResponse)
async def update_journal(
    journal_id: int,
    journal_data: JournalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    return await journal_service.update_entry(
        entry_id=journal_id,
        current_user=current_user,
        **journal_data.model_dump(exclude_unset=True)
    )

@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal(
    journal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    await journal_service.delete_entry(journal_id, current_user)
    return None


@router.get("/analytics", response_model=JournalAnalytics, summary="Get Journal Analytics")
@limiter.limit("50/minute")
async def get_analytics(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Detailed analytics on journaling patterns.
    """
    return await journal_service.get_analytics(current_user)


@router.get("/export", summary="Export Journal Entries")
@limiter.limit("10/minute")
async def export_journals(
    request: Request,
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
# Emotion Filtering Endpoints (Issue #1325)
# ============================================================================

@router.get("/filters/options", response_model=FilterOptionsResponse, summary="Get Available Filter Options")
@limiter.limit("50/minute")
async def get_filter_options(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Get available filter options and ranges based on user's journal data.
    
    Useful for populating filter UI controls (dropdowns, range sliders, checkboxes).
    Returns min/max values for each dimension and unique values.
    """
    options = await journal_service.get_filter_options(current_user)
    return FilterOptionsResponse(**options)


@router.post("/filtered", response_model=JournalFilterResponse, summary="Advanced Emotion Filtering")
@limiter.limit("100/minute")
async def get_filtered_entries(
    request: Request,
    filter_params: EmotionFilterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    journal_service: Annotated[JournalService, Depends(get_journal_service)]
):
    """
    Get journal entries with advanced multi-dimensional filtering (Issue #1325).
    
    **Supported Filters:**
    - **Date Range**: start_date, end_date (YYYY-MM-DD format)
    - **Emotion Types**: anxiety, sadness, joy, frustration, fatigue, hope, positivity, negative
    - **Sentiment Intensity**: min/max sentiment (0-100)
    - **Mood**: min/max mood score (1-10)
    - **Stress Level**: min/max stress (1-10)
    - **Energy Level**: min/max energy (1-10)
    - **Sleep Quality**: min/max sleep quality (1-10)
    - **Category**: specific category filter
    - **Tags**: multiple tags (matches any tag)
    
    **Multiple filters are combined with AND logic.**
    Emotion types within filter are combined with OR logic (matches any emotion).
    Tags within filter are combined with OR logic (matches any tag).
    
    **Returns:**
    - entries: List of matching journal entries
    - total: Total count of entries matching all filters
    - filters_applied: Echo of the filter request
    - has_more: Whether pagination has more results
    - empty_state_message: Helpful message when no results found
    """
    # Execute filtered search
    entries, total = await journal_service.search_entries(
        current_user=current_user,
        query=None,  # Emotion filtering endpoint doesn't use text search
        tags=filter_params.tags,
        emotion_types=filter_params.emotion_types,
        category=filter_params.category,
        start_date=filter_params.start_date,
        end_date=filter_params.end_date,
        min_sentiment=filter_params.min_sentiment,
        max_sentiment=filter_params.max_sentiment,
        min_mood=filter_params.min_mood,
        max_mood=filter_params.max_mood,
        min_stress=filter_params.min_stress,
        max_stress=filter_params.max_stress,
        min_energy=filter_params.min_energy,
        max_energy=filter_params.max_energy,
        min_sleep_quality=filter_params.min_sleep_quality,
        max_sleep_quality=filter_params.max_sleep_quality,
        skip=filter_params.skip,
        limit=filter_params.limit
    )
    
    # Generate empty state message when no results  
    empty_state = None
    if total == 0:
        active_filters = []
        
        if filter_params.emotion_types:
            active_filters.append(f"emotions: {', '.join(filter_params.emotion_types)}")
        if filter_params.category:
            active_filters.append(f"category: {filter_params.category}")
        if filter_params.tags:
            active_filters.append(f"tags: {', '.join(filter_params.tags)}")
        if filter_params.start_date:
            active_filters.append(f"from {filter_params.start_date}")
        if filter_params.end_date:
            active_filters.append(f"until {filter_params.end_date}")
        if filter_params.min_sentiment is not None or filter_params.max_sentiment is not None:
            sent_range = f"{filter_params.min_sentiment or 0}-{filter_params.max_sentiment or 100}"
            active_filters.append(f"sentiment: {sent_range}")
        if filter_params.min_mood is not None or filter_params.max_mood is not None:
            mood_range = f"{filter_params.min_mood or 1}-{filter_params.max_mood or 10}"
            active_filters.append(f"mood: {mood_range}")
        if filter_params.min_stress is not None or filter_params.max_stress is not None:
            stress_range = f"{filter_params.min_stress or 1}-{filter_params.max_stress or 10}"
            active_filters.append(f"stress: {stress_range}")
        if filter_params.min_energy is not None or filter_params.max_energy is not None:
            energy_range = f"{filter_params.min_energy or 1}-{filter_params.max_energy or 10}"
            active_filters.append(f"energy: {energy_range}")
        if filter_params.min_sleep_quality is not None or filter_params.max_sleep_quality is not None:
            sleep_range = f"{filter_params.min_sleep_quality or 1}-{filter_params.max_sleep_quality or 10}"
            active_filters.append(f"sleep: {sleep_range}")
        
        filter_desc = "; ".join(active_filters) if active_filters else "your criteria"
        empty_state = f"No journal entries found matching {filter_desc}. Try adjusting your filters to see more results."
    
    return JournalFilterResponse(
        entries=[JournalResponse.model_validate(e) for e in entries],
        total=total,
        filters_applied=filter_params,
        has_more=(filter_params.skip + filter_params.limit) < total,
        empty_state_message=empty_state
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
