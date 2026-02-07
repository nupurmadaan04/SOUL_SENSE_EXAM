# app/models.py
"""
Compatibility layer for tests and legacy imports.
Core models have been refactored elsewhere.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, create_engine, event, Index, text, DateTime
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy.engine import Engine, Connection
from typing import List, Optional, Any, Dict, Tuple, Union
from datetime import datetime, timedelta, UTC
import logging

# Define Base
Base = declarative_base()

class UserProfile:
    def __init__(self) -> None:
        self.occupation = ""
        self.workload = 0 # 1-10
        self.stressors = [] # ["exams", "deadlines"]
        self.health_concerns = []
        self.preferred_tone = "empathetic" # or "direct"
        self.language = "English"
        
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    last_login = Column(String, nullable=True)
    
    # PR 1: Security & Lifecycle Fields
    is_active = Column(Boolean, default=True, nullable=False)
    otp_secret = Column(String, nullable=True) # TOTP Secret
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    last_activity = Column(String, nullable=True) # Track idle time

    scores = relationship("Score", back_populates="user", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", uselist=False, back_populates="user", cascade="all, delete-orphan")
    medical_profile = relationship("MedicalProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    personal_profile = relationship("PersonalProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    strengths = relationship("UserStrengths", uselist=False, back_populates="user", cascade="all, delete-orphan")
    emotional_patterns = relationship("UserEmotionalPatterns", uselist=False, back_populates="user", cascade="all, delete-orphan")
    sync_settings = relationship("UserSyncSetting", back_populates="user", cascade="all, delete-orphan")
    password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class LoginAttempt(Base):
    """
    Track login attempts for security auditing and persistent locking.
    Replaces in-memory 'failed_attempts' dictionary.
    """
    __tablename__ = 'login_attempts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_successful = Column(Boolean)
    
    # PR 1: Audit Auditing
    user_agent = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)

class AuditLog(Base):
    """
    Audit Log for tracking security-critical user actions.
    Separated from LoginAttempt to provide a user-facing history.
    """
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    action = Column(String, nullable=False) # LOGIN, LOGOUT, 2FA_UPDATE, PASSWORD_CHANGE
    ip_address = Column(String, nullable=True, default="SYSTEM")
    user_agent = Column(String, nullable=True) # Truncated to 255 chars
    details = Column(Text, nullable=True) # JSON string for additional context (allow-listed fields only)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")

class OTP(Base):
    """
    One-Time Passwords for Password Reset and 2FA challenges.
    """
    __tablename__ = 'otp_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    code_hash = Column(String, nullable=False)
    type = Column(String, nullable=False) # 'RESET_PASSWORD', 'LOGIN_CHALLENGE'
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)

    user = relationship("User")


class PasswordHistory(Base):
    """
    Stores hashed previous passwords to prevent reuse.
    Configurable via PASSWORD_HISTORY_LIMIT in security_config.
    """
    __tablename__ = 'password_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="password_history")

class RefreshToken(Base):
    """
    Persistent storage for JWT refresh tokens.
    Enables long-lived sessions with high security via:
    - Token Rotation: New refresh token issued on every use.
    - Revocation: Ability to kill sessions remotely.
    """
    __tablename__ = 'refresh_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="refresh_tokens")


class UserSession(Base):
    """Track user login sessions with unique session IDs"""
    __tablename__ = 'user_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    username = Column(String, nullable=False, index=True)  # Denormalized for quick lookups
    created_at = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    last_accessed = Column(String, default=lambda: datetime.now(UTC).isoformat())
    ip_address = Column(String, nullable=True)  # Optional: track IP for security
    user_agent = Column(String, nullable=True)  # Optional: track user agent
    is_active = Column(Boolean, default=True, index=True)
    logged_out_at = Column(String, nullable=True)

    user = relationship("User", back_populates="sessions")

    # Composite indexes for performance
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_username_active', 'username', 'is_active'),
        Index('idx_session_created', 'created_at'),
    )


class UserSyncSetting(Base):
    """Store user-specific sync settings as key-value pairs with version control for conflict detection."""
    __tablename__ = 'user_sync_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)  # JSON-serialized value
    version = Column(Integer, default=1, nullable=False)  # For optimistic locking
    created_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    updated_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    
    user = relationship("User", back_populates="sync_settings")
    
    __table_args__ = (
        Index('idx_sync_user_key', 'user_id', 'key', unique=True),
    )

class UserSettings(Base):
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    theme = Column(String, default='light')
    question_count = Column(Integer, default=10)
    sound_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True) # Web-ready
    language = Column(String, default='en') # Web-ready
    updated_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    
    # Wave 2 Phase 2.3 & 2.4: Calibration & Safety
    decision_making_style = Column(String, nullable=True) # Analytical/Intuitive/etc.
    risk_tolerance = Column(Integer, nullable=True)     # 1-10 slider
    readiness_for_change = Column(Integer, nullable=True) # 1-10 scale
    advice_frequency = Column(String, nullable=True)     # Daily/Weekly/Rarely
    reminder_style = Column(String, default='Gentle')    # Gentle/Motivational
    advice_boundaries = Column(Text, default="[]")       # JSON multi-select
    ai_trust_level = Column(Integer, nullable=True)      # 1-10 slider
    
    data_usage_consent = Column(Boolean, default=False)
    emergency_disclaimer_accepted = Column(Boolean, default=False)
    crisis_support_preference = Column(Boolean, default=True)
    
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())

    user = relationship("User", back_populates="settings")

class MedicalProfile(Base):
    __tablename__ = 'medical_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    
    blood_type = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)        # Store as JSON string or plain text
    medications = Column(Text, nullable=True)      # Store as JSON string or plain text
    medical_conditions = Column(Text, nullable=True) # Store as JSON string or plain text
    
    # New fields for PR #5 (Issues #258, #263)
    surgeries = Column(Text, nullable=True)        # History of surgeries
    therapy_history = Column(Text, nullable=True)  # Past counselling/therapy
    ongoing_health_issues = Column(Text, nullable=True) # Issue #262: Ongoing health issues
    
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    
    last_updated = Column(String, default=lambda: datetime.now(UTC).isoformat())

    user = relationship("User", back_populates="medical_profile")

class PersonalProfile(Base):
    __tablename__ = 'personal_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    
    # Basic Info
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    education = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    hobbies = Column(Text, nullable=True)     # Store as JSON string or comma-separated
    bio = Column(Text, nullable=True)
    life_events = Column(Text, nullable=True) # JSON: [{date, title, description, impact}]
    
    # Contact Info (Phase 53: Profile Redesign)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)  # Format: YYYY-MM-DD
    gender = Column(String, nullable=True)         # Male/Female/Other/Prefer not to say
    address = Column(Text, nullable=True)
    
    # Existing fields from PR #5 (Issues #261, #260)
    society_contribution = Column(Text, nullable=True) # How user contributes to community
    life_pov = Column(Text, nullable=True)             # User's philosophy/perspective
    high_pressure_events = Column(Text, nullable=True) # Issue #275: Recent high-pressure events
    
    avatar_path = Column(String, nullable=True) # Path to local image file
    age = Column(Integer, nullable=True)
    
    last_updated = Column(String, default=lambda: datetime.now(UTC).isoformat())
    # Wave 2 Phase 2.1: Lifestyle & Health
    support_system = Column(Text, nullable=True)     # friends/family/colleagues
    social_interaction_freq = Column(String, nullable=True) # Daily/Weekly/Rarely
    exercise_freq = Column(String, nullable=True)     # Daily/Weekly/Monthly/None
    dietary_patterns = Column(String, nullable=True)  # Balanced/Unbalanced/Vegetarian/etc.
    
    last_updated = Column(String, default=lambda: datetime.utcnow().isoformat())

    user = relationship("User", back_populates="personal_profile")

class UserStrengths(Base):
    __tablename__ = 'user_strengths'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    
    # JSON Lists for Tags
    top_strengths = Column(Text, default="[]") # e.g. ["Creativity", "Empathy"]
    areas_for_improvement = Column(Text, default="[]") # e.g. ["Public Speaking"]
    current_challenges = Column(Text, default="[]") # Issue #271: New field
    
    # Preferences
    learning_style = Column(String, nullable=True) # Visual, Auditory, etc.
    communication_preference = Column(String, nullable=True) # Direct, Supportive
    
    # New field for PR #5 (Issue #266)
    comm_style = Column(Text, nullable=True) # Detailed communication style
    
    # Boundaries & Goals
    sharing_boundaries = Column(Text, default="[]") # JSON List
    goals = Column(Text, nullable=True)
    
    last_updated = Column(String, default=lambda: datetime.now(UTC).isoformat())
    # Wave 2 Phase 2.2: Goals & Vision
    short_term_goals = Column(Text, nullable=True)
    long_term_vision = Column(Text, nullable=True)
    primary_help_area = Column(String, nullable=True)

    # Wave 2 Phase 2.1: Calibration
    relationship_stress = Column(Integer, nullable=True) # 1-10 slider
    
    last_updated = Column(String, default=lambda: datetime.utcnow().isoformat())

    user = relationship("User", back_populates="strengths")


class UserEmotionalPatterns(Base):
    """Store user-defined emotional patterns for empathetic AI responses (Issue #269)."""
    __tablename__ = 'user_emotional_patterns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    
    # Common emotional states (JSON array)
    common_emotions = Column(Text, default="[]")  # e.g., ["anxiety", "calmness", "overthinking"]
    
    # Emotional triggers (what causes these emotions)
    emotional_triggers = Column(Text, nullable=True)
    
    # User's coping strategies
    coping_strategies = Column(Text, nullable=True)
    
    # Preferred support style during distress
    preferred_support = Column(String, nullable=True)  # "Encouraging", "Problem-solving", "Just listen"
    
    last_updated = Column(String, default=lambda: datetime.now(UTC).isoformat())
    
    user = relationship("User", back_populates="emotional_patterns")


class Score(Base):
    __tablename__ = 'scores'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)  # Added index
    total_score = Column(Integer, index=True)  # Added index
    sentiment_score = Column(Float, default=0.0)  # New: NLTK Sentiment Score
    reflection_text = Column(Text, nullable=True) # New: Open-ended response
    is_rushed = Column(Boolean, default=False) # Behavioral pattern: Rushed answering
    is_inconsistent = Column(Boolean, default=False) # Behavioral pattern: Inconsistent answering
    age = Column(Integer, index=True)  # Added index
    detailed_age_group = Column(String, index=True)  # Added index
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Added index
    session_id = Column(String, index=True, nullable=True) # PR 6.1: API Session ID
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)  # Added timestamp and index

    user = relationship("User", back_populates="scores")

    # Composite indexes for performance
    __table_args__ = (
        Index('idx_score_username_timestamp', 'username', 'timestamp'),
        Index('idx_score_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_score_age_score', 'age', 'total_score'),
        Index('idx_score_agegroup_score', 'detailed_age_group', 'total_score'),
    )

class Response(Base):
    __tablename__ = 'responses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)  # Added index
    question_id = Column(Integer, index=True)  # Added index
    response_value = Column(Integer, index=True)  # Added index
    age_group = Column(String, index=True)  # Added index
    detailed_age_group = Column(String, index=True)  # Added index
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)  # Added index
    session_id = Column(String, index=True, nullable=True) # PR 6.1: API Session ID
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Added index

    user = relationship("User", back_populates="responses")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_response_user_question', 'user_id', 'question_id'),
        Index('idx_response_username_timestamp', 'username', 'timestamp'),
        Index('idx_response_question_timestamp', 'question_id', 'timestamp'),
        Index('idx_response_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_response_agegroup_timestamp', 'detailed_age_group', 'timestamp'),
    )

class Question(Base):
    __tablename__ = 'question_bank'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(String)
    category_id = Column(Integer)
    difficulty = Column(Integer)
    is_active = Column(Integer, default=1)
    min_age = Column(Integer, default=0)
    max_age = Column(Integer, default=120)
    weight = Column(Float, default=1.0)
    tooltip = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.now(UTC).isoformat())

class QuestionCategory(Base):
    __tablename__ = 'question_category'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

class JournalEntry(Base):
    __tablename__ = 'journal_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    entry_date = Column(String, default=lambda: datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
    content = Column(Text)
    sentiment_score = Column(Float)
    emotional_patterns = Column(Text)
    
    # New fields for daily wellbeing tracking (Issues #255, #267, #272)
    sleep_hours = Column(Float, nullable=True)     # Range: 0-24
    sleep_quality = Column(Integer, nullable=True) # Range: 1-10
    energy_level = Column(Integer, nullable=True)  # Range: 1-10
    work_hours = Column(Float, nullable=True)      # Range: 0-24

    # PR #6: Expanded Daily Metrics (Issues #254, #259, #268, #253)
    screen_time_mins = Column(Integer, nullable=True)  # Minutes of screen time
    stress_level = Column(Integer, nullable=True)      # Range: 1-10
    stress_triggers = Column(Text, nullable=True)      # What triggered stress
    daily_schedule = Column(Text, nullable=True)       # Daily routine/schedule

    # Enhanced Journal Extensions: Tagging system
    tags = Column(Text, nullable=True)  # JSON list of tags like ["stress", "gratitude", "relationships"]
    
    # Soft delete and status (PR #8)
    is_deleted = Column(Boolean, default=False)
    privacy_level = Column(String, default="private") # private, shared, public
    word_count = Column(Integer, default=0)

class SatisfactionRecord(Base):
    __tablename__ = 'satisfaction_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=True)
    username = Column(String, index=True)
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    
    # Core satisfaction metrics
    satisfaction_score = Column(Integer, index=True)  # 1-10 scale
    satisfaction_category = Column(String, index=True)  # 'work', 'academic', 'both', 'other'
    
    # Detailed factors (JSON encoded for flexibility)
    positive_factors = Column(Text, nullable=True)  # JSON list
    negative_factors = Column(Text, nullable=True)  # JSON list
    improvement_suggestions = Column(Text, nullable=True)
    
    # Context information
    context = Column(String, nullable=True)  # 'workplace', 'school', 'university', 'remote', 'hybrid'
    duration_months = Column(Integer, nullable=True)  # How long in current role/studies
    
    # Optional: Link to EQ test if taken around same time
    eq_score_id = Column(Integer, ForeignKey('scores.id'), nullable=True, index=True)
    
    # Composite indexes
    __table_args__ = (
        Index('idx_satisfaction_user_time', 'user_id', 'timestamp'),
        Index('idx_satisfaction_category_score', 'satisfaction_category', 'satisfaction_score'),
        Index('idx_satisfaction_context', 'context', 'satisfaction_score'),
    )

class SatisfactionHistory(Base):
    """Track satisfaction trends over time"""
    __tablename__ = 'satisfaction_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    month_year = Column(String, index=True)  # Format: 'YYYY-MM'
    avg_satisfaction = Column(Float)
    trend = Column(String)  # 'improving', 'declining', 'stable'
    insights = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_satisfaction_history_user_month', 'user_id', 'month_year'),
    )

class AssessmentResult(Base):
    """
    Stores results for periodic/specialized assessments (PR #7).
    Supported types: 'career_clarity', 'work_satisfaction', 'strengths'.
    """
    __tablename__ = 'assessment_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    assessment_type = Column(String, nullable=False, index=True) # e.g. 'career_clarity'
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    
    total_score = Column(Integer, nullable=False) # 0-100 or similar scale
    details = Column(Text, nullable=False) # JSON string: {"q1": "yes", "q2": 5, "raw_score": 85}
    
    # Optional: Link to a specific Journal Entry if triggered by one
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=True)

    user = relationship("User")
    
    __table_args__ = (
        Index('idx_assessment_user_type', 'user_id', 'assessment_type'),
    )
    


# ==================== DATABASE PERFORMANCE OPTIMIZATIONS ====================

logger = logging.getLogger(__name__)

@event.listens_for(Base.metadata, 'before_create')
def receive_before_create(target: Any, connection: Connection, **kw: Any) -> None:
    """Optimize database settings before tables are created"""
    logger.info("Optimizing database settings...")
    
    # SQLite specific optimizations
    if connection.engine.name == 'sqlite':
        connection.execute(text('PRAGMA journal_mode = WAL'))  # Write-Ahead Logging for better concurrency
        connection.execute(text('PRAGMA synchronous = NORMAL'))  # Good balance of safety and performance
        connection.execute(text('PRAGMA cache_size = -2000'))  # 2MB cache
        connection.execute(text('PRAGMA temp_store = MEMORY'))  # Store temp tables in memory
        connection.execute(text('PRAGMA mmap_size = 268435456'))  # 256MB memory map
        connection.execute(text('PRAGMA foreign_keys = ON'))  # Enable foreign key constraints

@event.listens_for(Question.__table__, 'after_create')
def receive_after_create_question(target: Any, connection: Connection, **kw: Any) -> None:
    """Create additional indexes and optimizations after question table creation"""
    logger.info("Creating question search optimization indexes...")
    
    try:
        # Check if FTS5 extension is available
        connection.execute(text("SELECT fts5(?)"), ('test',))
        
        # Create virtual table for full-text search
        connection.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS question_search 
            USING fts5(id, question_text, content='question_bank', content_rowid='id')
        """))
        
        # Create triggers to keep the search index updated
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS question_ai AFTER INSERT ON question_bank BEGIN
                INSERT INTO question_search(rowid, question_text) VALUES (new.id, new.question_text);
            END;
        """))
        
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS question_ad AFTER DELETE ON question_bank BEGIN
                INSERT INTO question_search(question_search, rowid, question_text) VALUES('delete', old.id, old.question_text);
            END;
        """))
        
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS question_au AFTER UPDATE ON question_bank BEGIN
                INSERT INTO question_search(question_search, rowid, question_text) VALUES('delete', old.id, old.question_text);
                INSERT INTO question_search(rowid, question_text) VALUES (new.id, new.question_text);
            END;
        """))
        
        logger.info("Full-text search indexes created for questions")
    except:
        logger.warning("FTS5 not available, skipping full-text search optimization")

# ==================== CACHE AND PERFORMANCE TABLES ====================

class QuestionCache(Base):
    """Cache table for frequently accessed questions"""
    __tablename__ = 'question_cache'
    
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question_bank.id'), unique=True, index=True)
    question_text = Column(Text, nullable=False)
    category_id = Column(Integer, index=True)
    difficulty = Column(Integer, index=True)
    is_active = Column(Integer, default=1, index=True)
    min_age = Column(Integer, default=0)
    max_age = Column(Integer, default=120)
    tooltip = Column(Text, nullable=True)
    cached_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    access_count = Column(Integer, default=0, index=True)
    
    __table_args__ = (
        Index('idx_cache_active_difficulty', 'is_active', 'difficulty'),
        Index('idx_cache_category_active', 'category_id', 'is_active'),
        Index('idx_cache_access_time', 'access_count', 'cached_at'),
    )

class StatisticsCache(Base):
    """Cache for frequently calculated statistics"""
    __tablename__ = 'statistics_cache'
    
    id = Column(Integer, primary_key=True)
    stat_name = Column(String, unique=True, index=True)  # e.g., 'avg_score_global', 'question_count'
    stat_value = Column(Float)
    stat_json = Column(Text)  # For complex statistics
    calculated_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    valid_until = Column(String, index=True)
    
    __table_args__ = (
        Index('idx_stats_name_valid', 'stat_name', 'valid_until'),
    )

# ==================== PERFORMANCE HELPER FUNCTIONS ====================

def create_performance_indexes(engine: Engine) -> None:
    """Create additional performance indexes that might be needed"""
    with engine.connect() as conn:
        conn.commit() 
        # Create indexes that might not be in the model definitions
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_responses_composite 
            ON responses(username, question_id, response_value, timestamp)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_scores_composite 
            ON scores(username, total_score, age, timestamp)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_questions_quick_load 
            ON question_bank(is_active, id, question_text)
        """))
        
        # Optimize the database
        conn.execute(text('PRAGMA optimize'))
        
        logger.info("Performance indexes created and database optimized")

def preload_frequent_data(session: Session) -> None:
    """Preload frequently accessed data into cache (Optimized Bulk)."""
    try:
        # 1. OPTIMIZATION: Preserve access counts to restore them
        access_counts = {}
        try:
             # Fetch just ID/AccessCount to map
             cached_counts = session.query(QuestionCache.question_id, QuestionCache.access_count).all()
             access_counts = {qid: count for qid, count in cached_counts}
        except Exception:
             pass
        
        # 2. OPTIMIZATION: Clear Cache Table (Faster than N+1 merge checks)
        session.query(QuestionCache).delete()
        
        # 3. Cache active questions
        active_questions = session.query(Question).filter(
            Question.is_active == 1
        ).order_by(Question.id).all()
        
        new_entries = []
        for question in active_questions:
            new_entries.append(QuestionCache(
                question_id=question.id,
                question_text=question.question_text,
                category_id=question.category_id,
                difficulty=question.difficulty,
                is_active=question.is_active,
                access_count=access_counts.get(question.id, 0) # Restore count or 0
            ))
        
        # Bulk Insert
        if new_entries:
            session.add_all(new_entries)
        
        # Cache global statistics (Few items, merge is fine here)
        from sqlalchemy import func
        avg_score = session.query(func.avg(Score.total_score)).scalar() or 0
        question_count = session.query(func.count(Question.id)).filter(
            Question.is_active == 1
        ).scalar() or 0
        
        stats = [
            ('avg_score_global', avg_score, datetime.now(UTC).isoformat()),
            ('question_count', question_count, datetime.now(UTC).isoformat()),
            ('active_users', session.query(func.count(User.id)).scalar() or 0, 
             datetime.now(UTC).isoformat())
        ]
        
        for stat_name, stat_value, calculated_at in stats:
            cache_entry = StatisticsCache(
                stat_name=stat_name,
                stat_value=stat_value,
                calculated_at=calculated_at,
                valid_until=(datetime.now(UTC) + timedelta(hours=24)).isoformat()
            )
            session.merge(cache_entry)
        
        session.commit()
        logger.info("Frequent data preloaded into cache (Bulk Optimized)")
        
    except Exception as e:
        logger.error(f"Failed to preload data: {e}")
        session.rollback()

# ==================== QUERY OPTIMIZATION FUNCTIONS ====================

def get_active_questions_optimized(session: Session, limit: Optional[int] = None, offset: int = 0) -> List[Any]:
    """Optimized query for loading active questions"""
    # Try cache first
    cached = session.query(QuestionCache).filter(
        QuestionCache.is_active == 1
    ).order_by(QuestionCache.question_id)
    
    if limit:
        cached = cached.limit(limit)
    if offset:
        cached = cached.offset(offset)
    
    cached_results = cached.all()
    
    if cached_results:
        # Update access count
        for cache_entry in cached_results:
            cache_entry.access_count += 1
        session.commit()
        
        return [(c.question_id, c.question_text) for c in cached_results]
    
    # Fallback to direct query if cache misses
    query = session.query(Question.id, Question.question_text).filter(
        Question.is_active == 1
    ).order_by(Question.id)
    
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    
    return query.all()

def get_user_scores_optimized(session: Session, username: str, limit: int = 50) -> List["Score"]:
    """Optimized query for user scores with pagination"""
    return session.query(Score).filter(
        Score.username == username
    ).order_by(
        Score.timestamp.desc()
    ).limit(limit).all()

# Initialize logger
logging.basicConfig(level=logging.INFO)
# End of models
