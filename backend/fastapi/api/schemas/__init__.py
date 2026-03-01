from typing import Any, Dict, List, Optional
from datetime import datetime

import json
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator

from ..utils.sanitization import sanitize_string, clean_identifier


class ServiceStatus(BaseModel):
    """Status of an individual service."""
    status: str = Field(description="healthy, degraded, or unhealthy")
    latency_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    message: Optional[str] = Field(None, description="Optional status message")


class HealthResponse(BaseModel):
    """Response schema for health and readiness endpoints."""
    status: str = Field(description="healthy or unhealthy")
    timestamp: str = Field(description="ISO 8601 timestamp")
    version: str = Field(description="Application version")
    services: Optional[Dict[str, ServiceStatus]] = Field(None, description="Status of dependent services")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional diagnostics (when ?full=true)")


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    username: str = Field(..., min_length=3, max_length=20, description="Unique username")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=50, description="User's last name")
    age: Optional[int] = Field(None, ge=13, le=120, description="User's age")
    gender: Optional[str] = Field(None, description="User's gender")

    @field_validator('username', 'email', mode='before')
    @classmethod
    def sanitize_identifiers(cls, v: str) -> str:
        if isinstance(v, str):
            return clean_identifier(v)
        return v

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError('Username must start with a letter and contain only alphanumeric characters and underscores')
        
        reserved = {'admin', 'root', 'support', 'soulsense', 'system', 'official'}
        if v in reserved:
            raise ValueError('This username is reserved')
        return v

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        import re
        from ..utils.weak_passwords import WEAK_PASSWORDS
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        if v.lower() in WEAK_PASSWORDS:
            raise ValueError('This password is too common. Please choose a stronger password.')
        return v

    @field_validator('first_name', 'last_name', mode='before')
    @classmethod
    def sanitize_personal_info(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return sanitize_string(v)
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str

    @field_validator('username', mode='before')
    @classmethod
    def sanitize_username(cls, v: str) -> str:
        if isinstance(v, str):
            return clean_identifier(v)
        return v


class TwoFactorLoginRequest(BaseModel):
    """Schema for 2FA verification."""
    pre_auth_token: str = Field(..., description="Temporary token from step 1")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class TwoFactorAuthRequiredResponse(BaseModel):
    """Response when 2FA is required."""
    message: str = "2FA Verification Required"
    require_2fa: bool = True
    pre_auth_token: str


class TwoFactorConfirmRequest(BaseModel):
    """Schema for enabling 2FA with verification code."""
    code: str = Field(..., min_length=6, max_length=6)


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset."""
    email: EmailStr = Field(..., description="User's registered email")

    @field_validator('email', mode='before')
    @classmethod
    def sanitize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return clean_identifier(v)
        return v


class UsernameAvailabilityResponse(BaseModel):
    """Response for username availability check."""
    available: bool
    message: str


class PasswordResetComplete(BaseModel):
    """Schema for completing password reset."""
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('email', mode='before')
    @classmethod
    def sanitize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return clean_identifier(v)
        return v

    @field_validator('new_password')
    @classmethod
    def validate_new_password_complexity(cls, v: str) -> str:
        import re
        from ..utils.weak_passwords import WEAK_PASSWORDS
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        if v.lower() in WEAK_PASSWORDS:
            raise ValueError('This password is too common. Please choose a stronger password.')
        return v


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    warnings: Optional[List[Dict[str, str]]] = None
    onboarding_completed: Optional[bool] = None
    is_admin: Optional[bool] = None


class CaptchaResponse(BaseModel):
    """Schema for CAPTCHA generation response."""
    captcha_code: str = Field(..., description="The CAPTCHA code to display")
    session_id: str = Field(..., description="Session ID for CAPTCHA validation")


class LoginRequest(BaseModel):
    """Schema for login request with CAPTCHA."""
    identifier: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")
    captcha_input: str = Field(..., description="User's CAPTCHA input")
    session_id: str = Field(..., description="Session ID from CAPTCHA generation")


class TokenData(BaseModel):
    """Schema for decoded token data."""
    username: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response (excludes password)."""
    id: int
    username: str
    created_at: datetime
    last_login: Optional[str] = None
    onboarding_completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class AvatarUploadResponse(BaseModel):
    """Schema for avatar upload response."""
    message: str
    avatar_path: str


class FieldError(BaseModel):
    """Schema for individual field validation errors."""
    field: str
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized error response for the entire API."""
    code: str = Field(..., description="Machine-readable error code (e.g., AUTH001)")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context or debugging info")
    fields: Optional[List[FieldError]] = Field(None, description="Granular field-level errors for forms")


# ============================================================================
# Exam Submission Schemas (Issue 6.5 — API Answer Validation)
# ============================================================================

class AnswerSubmit(BaseModel):
    """Schema for a single answer item within an exam submission payload."""
    question_id: int = Field(
        ...,
        ge=1,
        description="ID of the question being answered",
    )
    value: int = Field(
        ...,
        ge=1,
        le=5,
        description="Likert scale answer value (1-5)",
    )


class ExamSubmit(BaseModel):
    """Schema for a batch exam submission payload.

    Validates structural geometry of the answers array:
    - Duplicate question_id values are rejected immediately with a 422.
    - Completeness against expected question count is enforced in the router
      after a DB lookup so that async context issues are avoided cleanly.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        description="Active exam session identifier",
    )
    answers: List[AnswerSubmit] = Field(
        ...,
        min_length=1,
        description="List of question/answer pairs — must be non-empty and duplicate-free",
    )
    is_draft: bool = Field(
        default=False,
        description="When True, completeness validation is skipped (draft saves are allowed)",
    )

    @model_validator(mode="after")
    def check_question_uniqueness(self) -> "ExamSubmit":
        """Reject payloads that submit the same question_id more than once.

        A hacker submitting question_id=5 twenty times must receive a 422 before
        any database write occurs.  Draft status does NOT exempt this check because
        duplicate IDs are always a structural error regardless of draft vs. final.
        """
        question_ids = [a.question_id for a in self.answers]
        if len(question_ids) != len(set(question_ids)):
            from collections import Counter
            dupes = [qid for qid, count in Counter(question_ids).items() if count > 1]
            raise ValueError(
                f"Submitted payload contains duplicate question answers for "
                f"question_id(s): {dupes}.  Each question may only be answered once."
            )
        return self


# ============================================================================
# Assessment Schemas for API Router
# ============================================================================

class AssessmentResponse(BaseModel):
    """Schema for a single assessment response."""
    id: int
    username: Optional[str] = None
    total_score: int
    sentiment_score: Optional[float] = 0.0
    age: Optional[int] = None
    detailed_age_group: Optional[str] = None
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
    sentiment_score: Optional[float] = 0.0
    reflection_text: Optional[str]
    is_rushed: Optional[bool] = Field(default=False)
    is_inconsistent: Optional[bool] = Field(default=False)
    age: Optional[int]
    detailed_age_group: Optional[str]
    timestamp: str
    responses_count: int
    
    model_config = ConfigDict(from_attributes=True)


class CategoryScore(BaseModel):
    """Score breakdown for a specific question category."""
    category_name: str
    score: float
    max_score: float
    percentage: float


class Recommendation(BaseModel):
    """Personalized recommendation based on category performance."""
    category_name: str
    message: str
    priority: str  # 'high', 'medium', 'low'


class DetailedExamResult(BaseModel):
    """Comprehensive exam result breakdown."""
    assessment_id: int
    total_score: float
    max_possible_score: float
    overall_percentage: float
    timestamp: str
    category_breakdown: List[CategoryScore]
    recommendations: List[Recommendation]

    model_config = ConfigDict(from_attributes=True)


class AssessmentStatsResponse(BaseModel):
    """Schema for assessment statistics."""
    total_assessments: int
    average_score: float
    highest_score: int
    lowest_score: int
    average_sentiment: float
    age_group_distribution: Dict[str, int]


class ExamResponseCreate(BaseModel):
    """Schema for saving a single question response (click)."""
    question_id: int
    value: int = Field(..., ge=1, le=5, description="Likert Scale metric (1-5)")
    age_group: Optional[str] = Field(None, description="Age group context")
    session_id: Optional[str] = Field(None, description="Exam session ID")


class ExamResultCreate(BaseModel):
    """Schema for submitting a completed exam score."""
    total_score: int = Field(..., ge=0, le=100)
    sentiment_score: float
    reflection_text: Optional[str] = Field("", max_length=5000, description="User's reflection (will be encrypted)")
    is_rushed: bool = False
    is_inconsistent: bool = False
    age: int = Field(..., ge=10, le=120)
    age_group: str
    detailed_age_group: str
    session_id: Optional[str] = Field(None, description="Exam session ID")


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
    username: Optional[str] = Field(None, min_length=3, max_length=20)
    password: Optional[str] = Field(None, min_length=8)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError('Username must start with a letter and contain only alphanumeric characters and underscores')
        
        reserved = {'admin', 'root', 'support', 'soulsense', 'system', 'official'}
        if v in reserved:
            raise ValueError('This username is reserved')
        return v
    
    @field_validator('password', mode='before')
    @classmethod
    def trim_password(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            # We DON'T lowercase passwords, but trimming whitespace at ends is common
            return v.strip()
        return v

    @field_validator('password')
    @classmethod
    def reject_weak_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from ..utils.weak_passwords import WEAK_PASSWORDS
        if v.lower() in WEAK_PASSWORDS:
            raise ValueError('This password is too common. Please choose a stronger password.')
        return v


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
    onboarding_completed: bool = False

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
    
    # Wave 2 Phase 2.3 & 2.4
    decision_making_style: Optional[str] = None
    risk_tolerance: Optional[int] = Field(None, ge=1, le=10)
    readiness_for_change: Optional[int] = Field(None, ge=1, le=10)
    advice_frequency: Optional[str] = None
    reminder_style: Optional[str] = Field(default='Gentle', pattern='^(Gentle|Motivational)$')
    advice_boundaries: Optional[List[str]] = Field(default=[])
    ai_trust_level: Optional[int] = Field(None, ge=1, le=10)
    
    data_usage_consent: bool = False
    emergency_disclaimer_accepted: bool = False
    crisis_support_preference: bool = True
    crisis_mode_enabled: bool = False  # Enable crisis intervention routing (Issue #930)
    
    # Data Usage Consent (Issue #929)
    consent_ml_training: bool = False
    consent_aggregated_research: bool = False


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""
    theme: Optional[str] = Field(None, pattern='^(light|dark)$')
    question_count: Optional[int] = Field(None, ge=5, le=50)
    sound_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    language: Optional[str] = Field(None, min_length=2, max_length=5)
    
    # Wave 2 Phase 2.3 & 2.4
    decision_making_style: Optional[str] = None
    risk_tolerance: Optional[int] = Field(None, ge=1, le=10)
    readiness_for_change: Optional[int] = Field(None, ge=1, le=10)
    advice_frequency: Optional[str] = None
    reminder_style: Optional[str] = Field(None, pattern='^(Gentle|Motivational)$')
    advice_boundaries: Optional[List[str]] = None
    ai_trust_level: Optional[int] = Field(None, ge=1, le=10)
    
    data_usage_consent: Optional[bool] = None
    emergency_disclaimer_accepted: Optional[bool] = None
    crisis_support_preference: Optional[bool] = None
    crisis_mode_enabled: Optional[bool] = None  # Enable crisis intervention routing (Issue #930)
    
    # Data Usage Consent (Issue #929)
    consent_ml_training: Optional[bool] = None
    consent_aggregated_research: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    """Schema for user settings response."""
    id: int
    user_id: int
    theme: str
    question_count: int
    sound_enabled: bool
    notifications_enabled: bool
    language: str
    
    # Wave 2 Phase 2.3 & 2.4
    decision_making_style: Optional[str] = None
    risk_tolerance: Optional[int] = None
    readiness_for_change: Optional[int] = None
    advice_frequency: Optional[str] = None
    reminder_style: Optional[str] = None
    advice_boundaries: Optional[List[str]] = None
    ai_trust_level: Optional[int] = None
    
    data_usage_consent: Optional[bool] = None
    emergency_disclaimer_accepted: Optional[bool] = None
    crisis_support_preference: Optional[bool] = None
    crisis_mode_enabled: Optional[bool] = None  # Enable crisis intervention routing (Issue #930)
    
    # Data Usage Consent (Issue #929)
    consent_ml_training: Optional[bool] = None
    consent_aggregated_research: Optional[bool] = None
    
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Data Consent Schemas (Issue #929)
# ============================================================================

class DataConsentUpdate(BaseModel):
    """Schema for updating data consent settings."""
    consent_ml_training: Optional[bool] = None
    consent_aggregated_research: Optional[bool] = None


class DataConsentResponse(BaseModel):
    """Schema for data consent response."""
    consent_ml_training: bool
    consent_aggregated_research: bool


# ============================================================================
# Crisis Settings Schemas (Issue #930)
# ============================================================================

class CrisisSettingsUpdate(BaseModel):
    """Schema for updating crisis settings."""
    crisis_mode_enabled: bool


class CrisisSettingsResponse(BaseModel):
    """Schema for crisis settings response."""
    crisis_mode_enabled: bool


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
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[str] = None
    medical_conditions: Optional[str] = None
    surgeries: Optional[str] = None
    therapy_history: Optional[str] = None
    ongoing_health_issues: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    
    # Wave 2 Phase 2.1
    support_system: Optional[str] = None
    social_interaction_freq: Optional[str] = None
    exercise_freq: Optional[str] = None
    dietary_patterns: Optional[str] = None
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Average hours of sleep per night (0-24)")
    has_therapist: Optional[bool] = None
    support_network_size: Optional[int] = Field(None, ge=0, le=100, description="Number of people in support network (0-100)")
    primary_support_type: Optional[str] = None


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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    
    # Wave 2 Phase 2.1
    support_system: Optional[str] = None
    social_interaction_freq: Optional[str] = None
    exercise_freq: Optional[str] = None
    dietary_patterns: Optional[str] = None
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Average hours of sleep per night (0-24)")
    has_therapist: Optional[bool] = None
    support_network_size: Optional[int] = Field(None, ge=0, le=100, description="Number of people in support network (0-100)")
    primary_support_type: Optional[str] = None

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator('occupation', 'education', 'marital_status', 'hobbies', 'bio', 'life_events', 'phone', 'date_of_birth', 'gender', 'address', 'society_contribution', 'life_pov', 'high_pressure_events', mode='before')
    @classmethod
    def sanitize_profile_info(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return sanitize_string(v)
        return v


class PersonalProfileResponse(BaseModel):
    """Schema for personal profile response."""
    id: int
    user_id: int
    occupation: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = None
    hobbies: Optional[str] = None
    bio: Optional[str] = None
    life_events: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    society_contribution: Optional[str] = None
    life_pov: Optional[str] = None
    high_pressure_events: Optional[str] = None
    avatar_path: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    
    # Wave 2 Phase 2.1
    support_system: Optional[str] = None
    social_interaction_freq: Optional[str] = None
    exercise_freq: Optional[str] = None
    dietary_patterns: Optional[str] = None
    sleep_hours: Optional[float] = None
    has_therapist: Optional[bool] = None
    support_network_size: Optional[int] = None
    primary_support_type: Optional[str] = None
    
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
    
    # Wave 2 Phase 2.1 & 2.2
    relationship_stress: Optional[int] = Field(None, ge=1, le=10)
    short_term_goals: Optional[str] = None
    long_term_vision: Optional[str] = None
    primary_help_area: Optional[str] = None
    primary_goal: Optional[str] = Field(None, max_length=500)
    focus_areas: Optional[List[str]] = None


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
    
    # Wave 2 Phase 2.1 & 2.2
    relationship_stress: Optional[int] = Field(None, ge=1, le=10)
    short_term_goals: Optional[str] = None
    long_term_vision: Optional[str] = None
    primary_help_area: Optional[str] = None
    primary_goal: Optional[str] = Field(None, max_length=500)
    focus_areas: Optional[List[str]] = None


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
    
    # Wave 2 Phase 2.1 & 2.2
    relationship_stress: Optional[int] = None
    short_term_goals: Optional[str] = None
    long_term_vision: Optional[str] = None
    primary_help_area: Optional[str] = None
    primary_goal: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    
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
    emotional_triggers: Optional[str] = None
    coping_strategies: Optional[str] = None
    preferred_support: Optional[str] = None
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
    onboarding_completed: bool = False


# ============================================================================
# Onboarding Schemas (Issue #933)
# ============================================================================

class OnboardingData(BaseModel):
    """Schema for completing onboarding with all profile data."""
    # Step 1: Welcome & Vision (Goals)
    primary_goal: Optional[str] = Field(None, max_length=500)
    focus_areas: Optional[List[str]] = None
    
    # Step 2: Current Lifestyle
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    exercise_freq: Optional[str] = None
    dietary_patterns: Optional[str] = None
    
    # Step 3: Support System
    has_therapist: Optional[bool] = None
    support_network_size: Optional[int] = Field(None, ge=0, le=100)
    primary_support_type: Optional[str] = None


class OnboardingCompleteResponse(BaseModel):
    """Response after completing onboarding."""
    message: str = "Onboarding completed successfully"
    onboarding_completed: bool = True



# ============================================================================
# Core Analytics Schemas
# ============================================================================

class AnalyticsEventCreate(BaseModel):
    """Schema for tracking frontend events (signup drop-off, etc)."""
    anonymous_id: str = Field(..., min_length=10, description="Client-generated anonymous ID")
    event_type: str = Field(..., max_length=50)
    event_name: str = Field(..., max_length=100)
    event_data: Optional[Dict[str, Any]] = Field(None, description="Metadata (No PII)")

    @field_validator('event_data')
    @classmethod
    def validate_no_pii(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v:
            import json
            s = json.dumps(v).lower()
            # Only block absolutely critical items to avoid false positives in development
            forbidden = ['password', 'credit_card'] 
            for term in forbidden:
                if term in s:
                     raise ValueError(f"Potential PII detected: {term}")
        return v

# ============================================================================
# User Analytics Schemas (PR 6.3)
# ============================================================================

class UserAnalyticsSummary(BaseModel):
    """Headline stats for the user dashboard."""
    total_exams: int = Field(description="Total number of exams taken")
    average_score: float = Field(description="Average score across all exams")
    best_score: int = Field(description="Highest score achieved")
    latest_score: int = Field(description="Most recent score")
    sentiment_trend: str = Field(description="improving, declining, or stable")
    streak_days: int = Field(default=0, description="Consecutive days with activity")
    consistency_score: Optional[float] = Field(None, description="Coefficient of variation (lower is better)")


class EQScorePoint(BaseModel):
    """Single data point for EQ history charts."""
    id: int
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    total_score: int
    sentiment_score: Optional[float] = None


class WellbeingPoint(BaseModel):
    """Single data point for Wellbeing history (from Journal)."""
    date: str = Field(description="YYYY-MM-DD date")
    sleep_hours: Optional[float] = None
    stress_level: Optional[int] = None
    energy_level: Optional[int] = None
    screen_time_mins: Optional[int] = None


class UserTrendsResponse(BaseModel):
    """Combined trends to reduce API roundtrips."""
    eq_scores: List[EQScorePoint]
    wellbeing: List[WellbeingPoint]

# ============================================================================
# Deep Dive Schemas (PR 6.4)
# ============================================================================

class DeepDiveType(BaseModel):
    """Metadata about an available deep dive assessment."""
    id: str = Field(description="Unique identifier (e.g., 'career_clarity')")
    label: str = Field(description="Human-readable title")
    description: str = Field(description="Short description of purpose")
    icon: str = Field(description="Emoji or icon identifier")

class DeepDiveQuestion(BaseModel):
    """A single question for a deep dive."""
    id: int
    text: str

class DeepDiveSubmission(BaseModel):
    """User submission for a deep dive."""
    assessment_type: str
    responses: Dict[str, int] = Field(description="Map of Question Text -> Score (1-5)")

class DeepDiveResultResponse(BaseModel):
    """Result summary for a deep dive."""
    id: int
    assessment_type: str
    total_score: int
    normalized_score: int = Field(description="Score normalized to 0-100")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    details: Optional[Dict] = Field(None, description="Detailed breakdown if needed")

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
    timestamp: str
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
    similarity: Optional[float] = Field(None, description="Cosine similarity score for semantic search")

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


class JournalCursorResponse(BaseModel):
    """Schema for cursor-paginated journal entry list."""
    data: List[JournalResponse]
    next_cursor: Optional[str] = None
    has_more: bool


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
# Smart Journal Prompts Schemas (Issue #586)
# ============================================================================

class SmartPrompt(BaseModel):
    """Schema for a personalized AI journal prompt."""
    id: int
    prompt: str
    category: str = Field(description="Prompt category (anxiety, stress, gratitude, etc.)")
    context_reason: str = Field(description="Why this prompt was selected for the user")
    description: Optional[str] = Field(None, description="Brief description of prompt purpose")


class SmartPromptsResponse(BaseModel):
    """Response with AI-personalized journal prompts."""
    prompts: List[SmartPrompt] = Field(description="Personalized prompts (usually 3)")
    user_mood: str = Field(description="Detected mood: positive, neutral, or low")
    detected_patterns: List[str] = Field(
        default=[], 
        description="Emotional patterns detected from recent entries"
    )
    sentiment_avg: float = Field(description="Average sentiment from last 7 days")


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
    

# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Schema for individual audit log entry."""
    id: int
    action: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('details', mode='before')
    @classmethod
    def parse_details(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return None
        return v


# ============================================================================
# Gamification Schemas
# ============================================================================

class AchievementRequirement(BaseModel):
    type: str # 'count', 'streak', 'score', 'activity'
    target: str # 'journal', 'assessment', 'days', 'pattern'
    value: int

class AchievementResponse(BaseModel):
    achievement_id: str
    name: str
    description: str
    icon: Optional[str] = None
    category: str
    rarity: str
    points_reward: int
    unlocked: bool = False
    progress: int = 0
    unlocked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserXPResponse(BaseModel):
    total_xp: int
    current_level: int
    xp_to_next_level: int
    level_progress: float # 0.0 to 1.0

    model_config = ConfigDict(from_attributes=True)

class UserStreakResponse(BaseModel):
    activity_type: str
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[datetime] = None
    is_active_today: bool

    model_config = ConfigDict(from_attributes=True)

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_xp: int
    current_level: int
    avatar_path: Optional[str] = None

class ChallengeResponse(BaseModel):
    id: int
    title: str
    description: str
    challenge_type: str
    start_date: datetime
    end_date: datetime
    reward_xp: int
    status: str = "available" # available, joined, completed, failed
    progress: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class GamificationSummary(BaseModel):
    xp: UserXPResponse
    streaks: List[UserStreakResponse]
    recent_achievements: List[AchievementResponse]
    active_challenges: List[ChallengeResponse]


class DashboardStatisticsResponse(BaseModel):
    """Response for dashboard statistics with historical trends."""
    historical_trends: List[EQScorePoint]


# ============================================================================
# Audit Logging Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Response schema for individual audit log entries."""
    id: int
    event_id: str
    timestamp: datetime
    event_type: str
    severity: str
    username: Optional[str]
    user_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: Optional[str]
    outcome: str
    details: Optional[str]
    error_message: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class AuditLogListResponse(BaseModel):
    """Response schema for paginated audit log lists."""
    logs: List[AuditLogResponse]
    total_count: int
    page: int
    per_page: int

class AuditExportResponse(BaseModel):
    """Response schema for audit log exports."""
    data: str
    format: str
    timestamp: datetime

# ============================================================================
# OAuth Schemas
# ============================================================================

class OAuthAuthorizeRequest(BaseModel):
    """Request for OAuth authorization."""
    response_type: str = Field(..., description="Must be 'code'")
    client_id: str = Field(..., description="Client ID")
    redirect_uri: str = Field(..., description="Redirect URI")
    scope: Optional[str] = Field("openid profile email", description="Requested scopes")
    state: Optional[str] = Field(..., description="State parameter")
    code_challenge: str = Field(..., description="PKCE code challenge")
    code_challenge_method: str = Field("S256", description="PKCE method")

class OAuthTokenRequest(BaseModel):
    """Request for OAuth token exchange."""
    grant_type: str = Field(..., description="Must be 'authorization_code'")
    code: str = Field(..., description="Authorization code")
    redirect_uri: str = Field(..., description="Redirect URI")
    client_id: str = Field(..., description="Client ID")
    code_verifier: str = Field(..., description="PKCE code verifier")

class OAuthTokenResponse(BaseModel):
    """Response for OAuth token."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None

class OAuthUserInfo(BaseModel):
    """User info from OAuth."""
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


# ============================================================================
# KPI & Reporting Schemas (Issue #981)
# ============================================================================

class ConversionRateKPI(BaseModel):
    """Conversion Rate KPI: (signup_completed / signup_started) * 100"""
    signup_started: int = Field(description="Total number of signup attempts started")
    signup_completed: int = Field(description="Total number of successful signups")
    conversion_rate: float = Field(description="Conversion rate as percentage (0-100)")
    period: str = Field(description="Time period for the calculation")


class RetentionKPI(BaseModel):
    """Retention KPI: (day_n_active_users / day_0_users) * 100"""
    day_0_users: int = Field(description="Number of users active on day 0")
    day_n_active_users: int = Field(description="Number of users still active on day N")
    retention_rate: float = Field(description="Retention rate as percentage (0-100)")
    period_days: int = Field(description="Number of days for retention calculation")
    period: str = Field(description="Time period for the calculation")


class ARPUKPI(BaseModel):
    """ARPU KPI: (total_revenue / total_active_users)"""
    total_revenue: float = Field(description="Total revenue in the period")
    total_active_users: int = Field(description="Total active users in the period")
    arpu: float = Field(description="Average Revenue Per User")
    period: str = Field(description="Time period for the calculation")
    currency: str = Field(default="USD", description="Currency for revenue figures")


class KPISummary(BaseModel):
    """Combined KPI summary for dashboard reporting"""
    conversion_rate: ConversionRateKPI
    retention_rate: RetentionKPI
    arpu: ARPUKPI
    calculated_at: str = Field(description="ISO 8601 timestamp when KPIs were calculated")
    period: str = Field(description="Time period these KPIs cover")


# ============================================================================
# Privacy & Consent Schemas (Issue #982)
# ============================================================================

class ConsentEventCreate(BaseModel):
    """Schema for tracking consent events (consent_given, consent_revoked)."""
    anonymous_id: str = Field(..., min_length=10, description="Client-generated anonymous ID")
    event_type: str = Field(..., pattern="^(consent_given|consent_revoked)$", description="Type of consent event")
    consent_type: str = Field(..., description="Type of consent (analytics, marketing, research, etc.)")
    consent_version: str = Field(..., description="Version of consent terms")
    event_data: Optional[Dict[str, Any]] = Field(None, description="Additional consent metadata")


class ConsentStatusResponse(BaseModel):
    """Response schema for user's current consent status."""
    analytics_consent: bool = Field(description="Whether user has consented to analytics tracking")
    marketing_consent: bool = Field(description="Whether user has consented to marketing communications")
    research_consent: bool = Field(description="Whether user has consented to research data usage")
    consent_version: str = Field(description="Current version of consent terms")
    last_updated: str = Field(description="ISO 8601 timestamp of last consent update")
    consent_history: List[Dict[str, Any]] = Field(description="History of consent events")


class ConsentUpdateRequest(BaseModel):
    """Schema for updating user consent preferences."""
    analytics_consent: Optional[bool] = None
    marketing_consent: Optional[bool] = None
    research_consent: Optional[bool] = None


# ============================================================================
# Export Schemas (Issue #1057)
# ============================================================================

class ExportRequest(BaseModel):
    """Schema for basic export requests."""
    format: str = Field(
        default="json",
        pattern="^(json|csv|xml|html|pdf)$",
        description="Export format. Supported: json, csv, xml, html, pdf"
    )

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        supported_formats = {'json', 'csv', 'xml', 'html', 'pdf'}
        if v.lower() not in supported_formats:
            raise ValueError(f"Unsupported format: {v}. Supported formats: {', '.join(sorted(supported_formats))}")
        return v.lower()


class ExportOptions(BaseModel):
    """Schema for advanced export options."""
    data_types: Optional[List[str]] = Field(
        default=None,
        description="List of data types to include in export"
    )
    include_metadata: Optional[bool] = Field(
        default=True,
        description="Whether to include metadata in the export"
    )
    anonymize: Optional[bool] = Field(
        default=False,
        description="Whether to anonymize sensitive data"
    )

    @field_validator('data_types')
    @classmethod
    def validate_data_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        
        supported_data_types = {
            'profile', 'journal', 'assessments', 'scores',
            'satisfaction', 'settings', 'medical', 'strengths',
            'emotional_patterns', 'responses'
        }
        
        invalid_types = set(v) - supported_data_types
        if invalid_types:
            raise ValueError(f"Unsupported data types: {', '.join(sorted(invalid_types))}. Supported: {', '.join(sorted(supported_data_types))}")
        
        return v


class ExportV2Request(BaseModel):
    """Schema for V2 export requests with advanced options."""
    format: str = Field(
        ...,
        pattern="^(json|csv|xml|html|pdf)$",
        description="Export format. Supported: json, csv, xml, html, pdf"
    )
    options: Optional[ExportOptions] = Field(
        default=None,
        description="Advanced export options"
    )

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        supported_formats = {'json', 'csv', 'xml', 'html', 'pdf'}
        if v.lower() not in supported_formats:
            raise ValueError(f"Unsupported format: {v}. Supported formats: {', '.join(sorted(supported_formats))}")
        return v.lower()


class ExportResponse(BaseModel):
    """Schema for export operation responses."""
    job_id: Optional[str] = Field(None, description="Job ID for async exports")
    export_id: Optional[str] = Field(None, description="Export ID for completed exports")
    status: str = Field(..., description="Export status")
    format: str = Field(..., description="Export format used")
    filename: Optional[str] = Field(None, description="Generated filename")
    download_url: Optional[str] = Field(None, description="Download URL for the export")
    expires_at: Optional[str] = Field(None, description="ISO 8601 timestamp when export expires")
    message: Optional[str] = Field(None, description="Status message")


class AsyncExportRequest(BaseModel):
    """Schema for async export requests."""
    format: str = Field(
        ...,
        pattern="^(json|csv|xml|html|pdf)$",
        description="Export format. Supported: json, csv, xml, html, pdf"
    )
    options: Optional[ExportOptions] = Field(
        default=None,
        description="Advanced export options"
    )

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        supported_formats = {'json', 'csv', 'xml', 'html', 'pdf'}
        if v.lower() not in supported_formats:
            raise ValueError(f"Unsupported format: {v}. Supported formats: {', '.join(sorted(supported_formats))}")
        return v.lower()


class AsyncPDFExportRequest(BaseModel):
    """Schema for async PDF export requests."""
    include_charts: bool = Field(
        default=True,
        description="Whether to include charts in the PDF"
    )
    data_types: Optional[List[str]] = Field(
        default=None,
        description="List of data types to include"
    )

    @field_validator('data_types')
    @classmethod
    def validate_data_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        
        supported_data_types = {
            'profile', 'journal', 'assessments', 'scores',
            'satisfaction', 'settings', 'medical', 'strengths',
            'emotional_patterns', 'responses'
        }
        
        invalid_types = set(v) - supported_data_types
        if invalid_types:
            raise ValueError(f"Unsupported data types: {', '.join(sorted(invalid_types))}. Supported: {', '.join(sorted(supported_data_types))}")
        
        return v


class AsyncExportResponse(BaseModel):
    """Schema for async export operation responses."""
    job_id: str = Field(..., description="Job ID for the async export")
    status: str = Field(..., description="Export status")
    poll_url: str = Field(..., description="URL to poll for status")
    format: str = Field(..., description="Export format requested")
