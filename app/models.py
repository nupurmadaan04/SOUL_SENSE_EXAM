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
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Mock Vector for non-postgres environments
    class Vector(Text):
        def __init__(self, dim):
            self.dim = dim
            super().__init__()

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
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True) # Timestamp of soft delete
    otp_secret = Column(String, nullable=True) # TOTP Secret
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    last_activity = Column(String, nullable=True) # Track idle time
    
    # Onboarding Status (Issue #933)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    # RBAC Roles
    is_admin = Column(Boolean, default=False, nullable=False)
    
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
    
    # Gamification Relationships
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    streaks = relationship("UserStreak", back_populates="user", cascade="all, delete-orphan")
    xp_stats = relationship("UserXP", uselist=False, back_populates="user", cascade="all, delete-orphan")

    # Advanced Analytics Relationships
    # Note: Analytics tables use username (string) instead of user_id for privacy
    # No foreign key relationships to avoid coupling

class LoginAttempt(Base):
    """Track login attempts for security auditing and persistent locking.
    Replaces in-memory 'failed_attempts' dictionary.
    """
    __tablename__ = 'login_attempts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_successful = Column(Boolean)
    user_agent = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)

class AuditLog(Base):
    """Comprehensive audit log for tracking all user actions, admin operations, and system events.
    Enhanced for security monitoring, compliance, and forensic analysis.
    """
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(36), unique=True, index=True)  # UUID for event uniqueness
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(100), index=True)  # e.g., 'auth', 'data_access', 'admin', 'system'
    severity = Column(String(20), default='info')  # 'info', 'warning', 'error', 'critical'

    # Actor information
    username = Column(String(100), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(Text)

    # Event details
    resource_type = Column(String(50))  # 'user', 'assessment', 'journal', 'system', etc.
    resource_id = Column(String(100))   # ID of the affected resource
    action = Column(String(100))        # 'login', 'view', 'create', 'update', 'delete', etc.
    outcome = Column(String(20))        # 'success', 'failure', 'denied'

    # Additional context
    details = Column(Text, nullable=True)  # JSON string with additional details
    error_message = Column(Text, nullable=True)

    # Compliance and retention
    retention_until = Column(DateTime, nullable=True)
    archived = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index('idx_audit_logs_timestamp_event_type', 'timestamp', 'event_type'),
        Index('idx_audit_logs_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
    )

class AnalyticsEvent(Base):
    """Track user behavior events (e.g., signup drop-off).
    Uses anonymous_id for pre-signup tracking.
    """
    __tablename__ = 'analytics_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    anonymous_id = Column(String, nullable=True, index=True)
    event_name = Column(String, nullable=False, index=True)
    event_data = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String, nullable=True)
    user = relationship("User")

class OTP(Base):
    """One-Time Passwords for Password Reset and 2FA challenges."""
    __tablename__ = 'otp_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    purpose = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    is_locked = Column(Boolean, default=False)
    user = relationship("User")

class PasswordHistory(Base):
    """Stores hashed previous passwords to prevent reuse.
    Configurable via PASSWORD_HISTORY_LIMIT in security_config.
    """
    __tablename__ = 'password_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user = relationship("User", back_populates="password_history")

class RefreshToken(Base):
    """Persistent storage for JWT refresh tokens.
    Enables long-lived sessions with high security via:
    - Token Rotation: New refresh token issued on every use.
    - Revocation: Ability to kill sessions remotely.
    """
    __tablename__ = 'refresh_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, index=True)
    user = relationship("User", back_populates="refresh_tokens")

class UserSession(Base):
    """Track user login sessions with unique session IDs"""
    __tablename__ = 'user_sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_username_active', 'username', 'is_active'),
        Index('idx_session_created', 'created_at'),
    )

class TokenRevocation(Base):
    """Store revoked access tokens to prevent reuse until they expire."""
    __tablename__ = 'token_revocations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_str = Column(String, index=True, nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class UserSyncSetting(Base):
    """Store user-specific sync settings as key-value pairs with version control for conflict detection."""
    __tablename__ = 'user_sync_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    updated_at = Column(String, default=lambda: datetime.now(UTC).isoformat())
    user = relationship("User", back_populates="sync_settings")
    __table_args__ = (
        Index('idx_sync_user_key', 'user_id', 'key', unique=True),
    )

class UserSettings(Base):
    __tablename__ = 'user_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    theme = Column(String, default="light")
    question_count = Column(Integer, default=10)
    sound_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    language = Column(String, default="en")

    # Crisis support settings (Integration with emotional support features)
    crisis_support_preference = Column(Boolean, default=True)
    crisis_mode_enabled = Column(Boolean, default=False)  # Enable crisis intervention routing (Issue #930)

    # Advanced Analytics Privacy Settings (Feature #804)
    analytics_enabled = Column(Boolean, default=False)  # Master switch for analytics
    benchmark_sharing_enabled = Column(Boolean, default=False)  # Allow anonymized benchmark comparisons
    pattern_analysis_enabled = Column(Boolean, default=False)  # Allow pattern detection
    forecast_enabled = Column(Boolean, default=False)  # Allow mood forecasting
    correlation_analysis_enabled = Column(Boolean, default=False)  # Allow correlation analysis
    recommendation_engine_enabled = Column(Boolean, default=False)  # Allow personalized recommendations

    # Data Usage Consent Settings (Issue #929)
    consent_ml_training = Column(Boolean, default=False)  # Allow journal phrasing for ML training
    consent_aggregated_research = Column(Boolean, default=False)  # Allow sanitized scores in global dashboards

    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    user = relationship("User", back_populates="settings")

class MedicalProfile(Base):
    __tablename__ = 'medical_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    blood_type = Column(String, nullable=True)
    allergies = Column(Text, nullable=True) # JSON string
    medications = Column(Text, nullable=True) # JSON string
    medical_conditions = Column(Text, nullable=True) # JSON string
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    last_updated = Column(String, default=lambda: datetime.now(UTC).isoformat())
    user = relationship("User", back_populates="medical_profile")

class PersonalProfile(Base):
    __tablename__ = 'personal_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    occupation = Column(String, nullable=True)
    education = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    hobbies = Column(Text, nullable=True) # JSON string
    bio = Column(Text, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    avatar_path = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    street_address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    exercise_freq = Column(String, nullable=True)
    dietary_patterns = Column(String, nullable=True)
    has_therapist = Column(Boolean, nullable=True)
    support_network_size = Column(Integer, nullable=True)
    primary_support_type = Column(String, nullable=True)
    last_updated = Column(String, default=lambda: datetime.utcnow().isoformat())
    user = relationship("User", back_populates="personal_profile")

class UserStrengths(Base):
    __tablename__ = 'user_strengths'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    top_strengths = Column(Text, nullable=True) # JSON string
    areas_for_improvement = Column(Text, nullable=True) # JSON string
    current_challenges = Column(Text, nullable=True) # JSON string
    learning_style = Column(String, nullable=True)
    communication_preference = Column(String, nullable=True)
    primary_help_area = Column(String, nullable=True)
    relationship_stress = Column(Integer, nullable=True)
    primary_goal = Column(Text, nullable=True)
    focus_areas = Column(Text, nullable=True) # JSON array of strings
    last_updated = Column(String, default=lambda: datetime.utcnow().isoformat())
    user = relationship("User", back_populates="strengths")

class UserEmotionalPatterns(Base):
    """Store user-defined emotional patterns for empathetic AI responses (Issue #269)."""
    __tablename__ = 'user_emotional_patterns'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    common_emotions = Column(Text, nullable=True) # JSON list
    emotional_triggers = Column(Text, nullable=True)
    coping_strategies = Column(Text, nullable=True)
    preferred_support = Column(String, nullable=True)
    last_updated = Column(String, default=lambda: datetime.now(UTC).isoformat())
    user = relationship("User", back_populates="emotional_patterns")

class Score(Base):
    __tablename__ = 'scores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)
    total_score = Column(Integer, index=True)
    sentiment_score = Column(Float, default=0.0)
    age = Column(Integer, nullable=True)
    detailed_age_group = Column(String, nullable=True)
    is_rushed = Column(Boolean, default=False)
    is_inconsistent = Column(Boolean, default=False)
    reflection_text = Column(Text, nullable=True)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String, nullable=True)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat(), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Retake restriction fields (Issue #993)
    attempt_number = Column(Integer, default=1, nullable=False, index=True)
    status = Column(String, default="completed", nullable=False, index=True)  # "in_progress", "completed", "abandoned"
    
    user = relationship("User", back_populates="scores")
    
    __table_args__ = (
        Index('idx_score_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_score_age_score', 'age', 'total_score'),
        Index('idx_score_agegroup_score', 'detailed_age_group', 'total_score'),
        Index('idx_score_user_status', 'user_id', 'status'),  # For retake restriction queries
    )

class Response(Base):
    __tablename__ = 'responses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)
    question_id = Column(Integer, index=True)
    response_value = Column(Integer, index=True)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat(), index=True)
    age = Column(Integer, nullable=True)
    detailed_age_group = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    user = relationship("User", back_populates="responses")
    
    __table_args__ = (
        Index('idx_response_question_timestamp', 'question_id', 'timestamp'),
        Index('idx_response_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_response_agegroup_timestamp', 'detailed_age_group', 'timestamp'),
        Index('idx_response_user_question', 'user_id', 'question_id', unique=True),  # Unique constraint for user-question pairs
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
    username = Column(String, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    sentiment_score = Column(Float, default=0.0)
    emotional_patterns = Column(Text, nullable=True) # JSON list
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    entry_date = Column(String, nullable=True, index=True) # For legacy/charting
    category = Column(String, nullable=True, index=True)
    mood_score = Column(Integer, nullable=True) # 1-10
    sleep_hours = Column(Float, nullable=True)
    sleep_quality = Column(Integer, nullable=True)
    energy_level = Column(Integer, nullable=True)
    work_hours = Column(Float, nullable=True)
    stress_level = Column(Integer, nullable=True)
    screen_time_mins = Column(Integer, nullable=True)
    daily_schedule = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    privacy_level = Column(String, default="private", index=True)
    word_count = Column(Integer, default=0)
    embedding = Column(Vector(384), nullable=True) # Default dimension for all-MiniLM-L6-v2
    embedding_model = Column(String, nullable=True) # Track which model was used
    last_indexed_at = Column(DateTime, nullable=True)

class SatisfactionRecord(Base):
    __tablename__ = 'satisfaction_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=True)
    username = Column(String, index=True)
    satisfaction_category = Column(String, nullable=False) # e.g. 'work', 'social', 'health'
    satisfaction_score = Column(Integer, nullable=False) # 1-5
    context = Column(Text, nullable=True)
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat())
    
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
    month_year = Column(String, index=True)
    avg_satisfaction = Column(Float)
    trend = Column(String)
    insights = Column(Text, nullable=True)
    __table_args__ = (
        Index('idx_satisfaction_history_user_month', 'user_id', 'month_year'),
    )

class AssessmentResult(Base):
    """Stores results for periodic/specialized assessments (PR #7).
    Supported types: 'career_clarity', 'work_satisfaction', 'strengths'.
    """
    __tablename__ = 'assessment_results'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    assessment_type = Column(String, nullable=False, index=True)
    timestamp = Column(String, default=lambda: datetime.now(UTC).isoformat(), index=True)
    overall_score = Column(Float, nullable=True)
    details = Column(Text, nullable=False)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
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

class ExportRecord(Base):
    """Track user data exports for audit and GDPR compliance."""
    __tablename__ = 'export_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    export_id = Column(String, unique=True, nullable=False, index=True)
    format = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    data_types = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    status = Column(String, default='completed', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User")

# ==================== GAMIFICATION MODELS ====================

class Achievement(Base):
    __tablename__ = 'achievements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    achievement_id = Column(String(100), unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(500), nullable=True) # URL or emoji
    category = Column(String(50), nullable=False) # consistency, awareness, intelligence
    rarity = Column(String(20), default='common') # common, rare, epic, legendary
    requirements = Column(Text, nullable=True) # JSON string of requirements
    points_reward = Column(Integer, default=150)

class UserAchievement(Base):
    __tablename__ = 'user_achievements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    achievement_id = Column(String(100), ForeignKey('achievements.achievement_id'), nullable=False)
    progress = Column(Integer, default=0) # 0-100
    unlocked = Column(Boolean, default=False)
    unlocked_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")

class UserStreak(Base):
    __tablename__ = 'user_streaks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    activity_type = Column(String(50), default='combined')  # journal, assessment, combined
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    streak_freeze_count = Column(Integer, default=0)
    
    user = relationship("User", back_populates="streaks")

class UserXP(Base):
    __tablename__ = 'user_xp'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    total_xp = Column(Integer, default=0)
    current_level = Column(Integer, default=1)
    xp_to_next_level = Column(Integer, default=500)
    last_xp_awarded_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="xp_stats")

class Challenge(Base):
    """Weekly or Monthly Challenges for users to participate in."""
    __tablename__ = 'challenges'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    challenge_type = Column(String(50), index=True) # weekly, monthly, special
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    requirements = Column(Text) # JSON string
    reward_xp = Column(Integer, default=200)
    is_active = Column(Boolean, default=True, index=True)

class UserChallenge(Base):
    """Tracks user participation in challenges."""
    __tablename__ = 'user_challenges'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    challenge_id = Column(Integer, ForeignKey('challenges.id'), nullable=False)
    status = Column(String(20), default='joined') # joined, completed, failed
    progress = Column(Text) # JSON string
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User")
    challenge = relationship("Challenge")

class EmotionalPattern(Base):
    """Store detected emotional patterns for advanced analytics."""
    __tablename__ = 'emotional_patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    pattern_type = Column(String, nullable=False)  # temporal, correlation, trigger
    pattern_data = Column(Text, nullable=False)  # JSON string
    confidence_score = Column(Float, default=0.0)
    detected_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_emotional_patterns_user_type', 'username', 'pattern_type'),
        Index('idx_emotional_patterns_detected', 'detected_at'),
    )

class UserBenchmark(Base):
    """Store user benchmark comparisons for advanced analytics."""
    __tablename__ = 'user_benchmarks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    benchmark_type = Column(String, nullable=False)  # age_group, overall, etc.
    percentile = Column(Integer, nullable=False)  # 1-100
    comparison_group = Column(String, nullable=False)
    benchmark_data = Column(Text, nullable=True)  # JSON string with additional stats
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_user_benchmarks_user_type', 'username', 'benchmark_type'),
        Index('idx_user_benchmarks_created', 'created_at'),
    )

class AnalyticsInsight(Base):
    """Store generated insights and recommendations."""
    __tablename__ = 'analytics_insights'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    insight_type = Column(String, nullable=False)  # pattern, correlation, trigger, goal
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    priority = Column(String, default='medium')  # low, medium, high
    insight_data = Column(Text, nullable=True)  # JSON string with additional data
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_analytics_insights_user_type', 'username', 'insight_type'),
        Index('idx_analytics_insights_created', 'created_at'),
    )

class MoodForecast(Base):
    """Store mood forecast predictions."""
    __tablename__ = 'mood_forecasts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    forecast_date = Column(DateTime, nullable=False)
    predicted_score = Column(Float, nullable=False)
    confidence = Column(Float, default=0.0)
    forecast_basis = Column(Text, nullable=True)  # JSON string with basis data
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_mood_forecasts_user_date', 'username', 'forecast_date'),
        Index('idx_mood_forecasts_created', 'created_at'),
    )

# Initialize logger
logging.basicConfig(level=logging.INFO)
# End of models
