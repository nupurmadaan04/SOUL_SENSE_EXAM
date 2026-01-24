from typing import Any, Dict, List, Optional
from datetime import datetime

import json
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class HealthResponse(BaseModel):
    status: str


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for decoded token data."""
    username: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response (excludes password)."""
    id: int
    username: str
    created_at: str
    last_login: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Assessment Schemas for API Router
# ============================================================================

class AssessmentResponse(BaseModel):
    """Schema for a single assessment response."""
    id: int
    username: str
    total_score: int
    sentiment_score: float
    age: Optional[int]
    detailed_age_group: Optional[str]
    timestamp: str
    
    model_config = ConfigDict(from_attributes=True)


class AssessmentListResponse(BaseModel):
    """Schema for paginated assessment list."""
    total: int
    assessments: List[AssessmentResponse]
    page: int
    page_size: int


class AssessmentDetailResponse(BaseModel):
    """Schema for detailed assessment information."""
    id: int
    username: str
    total_score: int
    sentiment_score: float
    reflection_text: Optional[str]
    is_rushed: bool
    is_inconsistent: bool
    age: Optional[int]
    detailed_age_group: Optional[str]
    timestamp: str
    responses_count: int


class AssessmentStatsResponse(BaseModel):
    """Schema for assessment statistics."""
    total_assessments: int
    average_score: float
    highest_score: int
    lowest_score: int
    average_sentiment: float
    age_group_distribution: Dict[str, int]


# ============================================================================
# Question Schemas for API Router
# ============================================================================

class QuestionResponse(BaseModel):
    """Schema for a single question response."""
    id: int
    question_text: str
    category_id: Optional[int] = None
    difficulty: Optional[int] = None
    is_active: Optional[int] = 1
    min_age: Optional[int] = 0
    max_age: Optional[int] = 120
    weight: Optional[float] = 1.0
    tooltip: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuestionListResponse(BaseModel):
    """Schema for paginated question list."""
    total: int
    questions: List[QuestionResponse]
    page: int
    page_size: int


class QuestionCategoryResponse(BaseModel):
    """Schema for question category."""
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# User CRUD Schemas
# ============================================================================

class UserUpdate(BaseModel):
    """Schema for updating user information."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=8)


class UserDetail(BaseModel):
    """Detailed user information including relationships."""
    id: int
    username: str
    created_at: str
    last_login: Optional[str] = None
    has_settings: bool = False
    has_medical_profile: bool = False
    has_personal_profile: bool = False
    has_strengths: bool = False
    has_emotional_patterns: bool = False
    total_assessments: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Profile Schemas - User Settings
# ============================================================================

class UserSettingsCreate(BaseModel):
    """Schema for creating user settings."""
    theme: str = Field(default='light', pattern='^(light|dark)$')
    question_count: int = Field(default=10, ge=5, le=50)
    sound_enabled: bool = True
    notifications_enabled: bool = True
    language: str = Field(default='en', min_length=2, max_length=5)


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""
    theme: Optional[str] = Field(None, pattern='^(light|dark)$')
    question_count: Optional[int] = Field(None, ge=5, le=50)
    sound_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    language: Optional[str] = Field(None, min_length=2, max_length=5)


class UserSettingsResponse(BaseModel):
    """Schema for user settings response."""
    id: int
    user_id: int
    theme: str
    question_count: int
    sound_enabled: bool
    notifications_enabled: bool
    language: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Profile Schemas - Medical Profile
# ============================================================================

class MedicalProfileCreate(BaseModel):
    """Schema for creating medical profile."""
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[str] = None
    medical_conditions: Optional[str] = None
    surgeries: Optional[str] = None
    therapy_history: Optional[str] = None
    ongoing_health_issues: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class MedicalProfileUpdate(BaseModel):
    """Schema for updating medical profile."""
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[str] = None
    medical_conditions: Optional[str] = None
    surgeries: Optional[str] = None
    therapy_history: Optional[str] = None
    ongoing_health_issues: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class MedicalProfileResponse(BaseModel):
    """Schema for medical profile response."""
    id: int
    user_id: int
    blood_type: Optional[str]
    allergies: Optional[str]
    medications: Optional[str]
    medical_conditions: Optional[str]
    surgeries: Optional[str]
    therapy_history: Optional[str]
    ongoing_health_issues: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    last_updated: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Profile Schemas - Personal Profile
# ============================================================================

class PersonalProfileCreate(BaseModel):
    """Schema for creating personal profile."""
    occupation: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = None
    hobbies: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=1000)
    life_events: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    society_contribution: Optional[str] = None
    life_pov: Optional[str] = None
    high_pressure_events: Optional[str] = None
    avatar_path: Optional[str] = None


class PersonalProfileUpdate(BaseModel):
    """Schema for updating personal profile."""
    occupation: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = None
    hobbies: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=1000)
    life_events: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    society_contribution: Optional[str] = None
    life_pov: Optional[str] = None
    high_pressure_events: Optional[str] = None
    avatar_path: Optional[str] = None


class PersonalProfileResponse(BaseModel):
    """Schema for personal profile response."""
    id: int
    user_id: int
    occupation: Optional[str]
    education: Optional[str]
    marital_status: Optional[str]
    hobbies: Optional[str]
    bio: Optional[str]
    life_events: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    address: Optional[str]
    society_contribution: Optional[str]
    life_pov: Optional[str]
    high_pressure_events: Optional[str]
    avatar_path: Optional[str]
    last_updated: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Profile Schemas - User Strengths
# ============================================================================

class UserStrengthsCreate(BaseModel):
    """Schema for creating user strengths."""
    top_strengths: str = "[]"
    areas_for_improvement: str = "[]"
    current_challenges: str = "[]"
    learning_style: Optional[str] = None
    communication_preference: Optional[str] = None
    comm_style: Optional[str] = None
    sharing_boundaries: str = "[]"
    goals: Optional[str] = None


class UserStrengthsUpdate(BaseModel):
    """Schema for updating user strengths."""
    top_strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    current_challenges: Optional[str] = None
    learning_style: Optional[str] = None
    communication_preference: Optional[str] = None
    comm_style: Optional[str] = None
    sharing_boundaries: Optional[str] = None
    goals: Optional[str] = None


class UserStrengthsResponse(BaseModel):
    """Schema for user strengths response."""
    id: int
    user_id: int
    top_strengths: str
    areas_for_improvement: str
    current_challenges: str
    learning_style: Optional[str]
    communication_preference: Optional[str]
    comm_style: Optional[str]
    sharing_boundaries: str
    goals: Optional[str]
    last_updated: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Profile Schemas - Emotional Patterns
# ============================================================================

class UserEmotionalPatternsCreate(BaseModel):
    """Schema for creating emotional patterns."""
    common_emotions: str = "[]"
    emotional_triggers: Optional[str] = None
    coping_strategies: Optional[str] = None
    preferred_support: Optional[str] = None


class UserEmotionalPatternsUpdate(BaseModel):
    """Schema for updating emotional patterns."""
    common_emotions: Optional[str] = None
    emotional_triggers: Optional[str] = None
    coping_strategies: Optional[str] = None
    preferred_support: Optional[str] = None


class UserEmotionalPatternsResponse(BaseModel):
    """Schema for emotional patterns response."""
    id: int
    user_id: int
    common_emotions: str
    emotional_triggers: Optional[str]
    coping_strategies: Optional[str]
    preferred_support: Optional[str]
    last_updated: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Comprehensive Profile Response
# ============================================================================

class CompleteProfileResponse(BaseModel):
    """Complete user profile with all sub-profiles."""
    user: UserResponse
    settings: Optional[UserSettingsResponse] = None
    medical_profile: Optional[MedicalProfileResponse] = None
    personal_profile: Optional[PersonalProfileResponse] = None
    strengths: Optional[UserStrengthsResponse] = None
    emotional_patterns: Optional[UserEmotionalPatternsResponse] = None


# ============================================================================
# Analytics Schemas
# ============================================================================

class AgeGroupStats(BaseModel):
    """Aggregated statistics by age group"""
    age_group: str
    total_assessments: int
    average_score: float
    min_score: int
    max_score: int
    average_sentiment: float


class ScoreDistribution(BaseModel):
    """Score distribution for analytics"""
    score_range: str
    count: int
    percentage: float


class TrendDataPoint(BaseModel):
    """Time-series data point"""
    period: str
    average_score: float
    assessment_count: int


class AnalyticsSummary(BaseModel):
    """Overall analytics summary - aggregated data only"""
    total_assessments: int = Field(description="Total number of assessments")
    unique_users: int = Field(description="Number of unique users")
    global_average_score: float = Field(description="Overall average score")
    global_average_sentiment: float = Field(description="Overall sentiment score")
    age_group_stats: List[AgeGroupStats] = Field(description="Stats by age group")
    score_distribution: List[ScoreDistribution] = Field(description="Score distribution")
    assessment_quality_metrics: Dict[str, int] = Field(
        description="Quality metrics (rushed, inconsistent counts)"
    )


class TrendAnalytics(BaseModel):
    """Trend analytics over time"""
    period_type: str = Field(description="Time period type (daily, weekly, monthly)")
    data_points: List[TrendDataPoint] = Field(description="Time series data")
    trend_direction: str = Field(description="Overall trend (increasing, decreasing, stable)")


class BenchmarkComparison(BaseModel):
    """Benchmark comparison data"""
    category: str
    global_average: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_90: float


class PopulationInsights(BaseModel):
    """Population-level insights - no individual data"""
    most_common_age_group: str
    highest_performing_age_group: str
    total_population_size: int
    assessment_completion_rate: Optional[float] = Field(
        default=None, 
        description="Percentage of started assessments that were completed"
    )


# ============================================================================
# Journal Schemas for API Router
# ============================================================================

class JournalCreate(BaseModel):
    """Schema for creating a new journal entry."""
    content: str = Field(
        ..., 
        min_length=10, 
        max_length=50000,
        description="Journal content (10-50,000 characters)"
    )
    tags: Optional[List[str]] = Field(
        default=[],
        max_length=20,
        description="Tags for organizing entries (max 20)"
    )
    privacy_level: str = Field(
        default="private",
        pattern="^(private|shared|public)$",
        description="Privacy level: private, shared, or public"
    )
    # Wellbeing metrics
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Hours of sleep (0-24)")
    sleep_quality: Optional[int] = Field(None, ge=1, le=10, description="Sleep quality (1-10)")
    energy_level: Optional[int] = Field(None, ge=1, le=10, description="Energy level (1-10)")
    work_hours: Optional[float] = Field(None, ge=0, le=24, description="Work hours (0-24)")
    screen_time_mins: Optional[int] = Field(None, ge=0, le=1440, description="Screen time in minutes")
    stress_level: Optional[int] = Field(None, ge=1, le=10, description="Stress level (1-10)")
    stress_triggers: Optional[str] = Field(None, max_length=500, description="What triggered stress")
    daily_schedule: Optional[str] = Field(None, max_length=1000, description="Daily routine/schedule")


class JournalUpdate(BaseModel):
    """Schema for updating a journal entry."""
    content: Optional[str] = Field(
        None, 
        min_length=10, 
        max_length=50000,
        description="Updated content"
    )
    tags: Optional[List[str]] = Field(None, max_length=20)
    privacy_level: Optional[str] = Field(None, pattern="^(private|shared|public)$")
    # Wellbeing metrics
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    sleep_quality: Optional[int] = Field(None, ge=1, le=10)
    energy_level: Optional[int] = Field(None, ge=1, le=10)
    work_hours: Optional[float] = Field(None, ge=0, le=24)
    screen_time_mins: Optional[int] = Field(None, ge=0, le=1440)
    stress_level: Optional[int] = Field(None, ge=1, le=10)
    stress_triggers: Optional[str] = Field(None, max_length=500)
    daily_schedule: Optional[str] = Field(None, max_length=1000)


class JournalResponse(BaseModel):
    """Schema for a single journal entry response."""
    id: int
    username: str
    content: str
    sentiment_score: Optional[float] = Field(None, description="AI sentiment score (0-100)")
    emotional_patterns: Optional[str] = None
    tags: Optional[List[str]] = []
    entry_date: str
    word_count: int = Field(default=0, description="Number of words in content")
    reading_time_mins: Optional[float] = Field(None, description="Estimated reading time in minutes")
    privacy_level: str = Field(default="private")
    # Wellbeing metrics
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    energy_level: Optional[int] = None
    work_hours: Optional[float] = None
    screen_time_mins: Optional[int] = None
    stress_level: Optional[int] = None
    stress_triggers: Optional[str] = None
    daily_schedule: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        """Decode JSON string from DB to List[str] for API."""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return []
        return v


class JournalListResponse(BaseModel):
    """Schema for paginated journal entry list."""
    total: int
    entries: List[JournalResponse]
    page: int
    page_size: int


class JournalAnalytics(BaseModel):
    """Schema for journal analytics."""
    total_entries: int
    average_sentiment: float
    sentiment_trend: str = Field(description="improving, declining, or stable")
    most_common_tags: List[str]
    average_stress_level: Optional[float] = None
    average_sleep_quality: Optional[float] = None
    entries_this_week: int
    entries_this_month: int


class JournalSearchParams(BaseModel):
    """Schema for journal search parameters."""
    query: Optional[str] = Field(None, max_length=200, description="Search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    min_sentiment: Optional[float] = Field(None, ge=0, le=100)
    max_sentiment: Optional[float] = Field(None, ge=0, le=100)


class JournalPrompt(BaseModel):
    """Schema for AI journal prompt."""
    id: int
    category: str = Field(description="gratitude, reflection, goals, emotions, creativity")
    prompt: str
    description: Optional[str] = None


class JournalPromptsResponse(BaseModel):
    """Schema for list of journal prompts."""
    prompts: List[JournalPrompt]
    category: Optional[str] = None


# ============================================================================
# Settings Synchronization Schemas (Issue #396)
# ============================================================================

class SyncSettingCreate(BaseModel):
    """Schema for creating/updating a sync setting."""
    key: str = Field(..., min_length=1, max_length=100, description="Setting key")
    value: Any = Field(..., description="Setting value (will be JSON serialized)")


class SyncSettingUpdate(BaseModel):
    """Schema for updating a sync setting with conflict detection."""
    value: Any = Field(..., description="New value")
    expected_version: Optional[int] = Field(None, description="Expected version for conflict detection")


class SyncSettingResponse(BaseModel):
    """Schema for sync setting response."""
    key: str
    value: Any
    version: int
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator('value', mode='before')
    @classmethod
    def parse_value(cls, v):
        """Decode JSON string from DB to Python object."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return v
        return v


class SyncSettingBatchRequest(BaseModel):
    """Schema for batch operations."""
    settings: List[SyncSettingCreate]


class SyncSettingBatchResponse(BaseModel):
    """Schema for batch response."""
    settings: List[SyncSettingResponse]
    conflicts: List[str] = Field(default=[], description="Keys that had conflicts")


class SyncSettingConflictResponse(BaseModel):
    """Schema for conflict response (409)."""
    detail: str = "Version conflict"
    key: str
    current_version: int
    current_value: Any

