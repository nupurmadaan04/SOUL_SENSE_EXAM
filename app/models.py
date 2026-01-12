from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Index, func, event, text, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timedelta
import logging

# Create Base
Base = declarative_base()

class UserProfile:
    def __init__(self):
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
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    last_login = Column(String, nullable=True)

    scores = relationship("Score", back_populates="user", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="user", cascade="all, delete-orphan")
    satisfaction_records = relationship("WorkStudySatisfaction", back_populates="user", cascade="all, delete-orphan")
    # ADDED: satisfaction_records relationship

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
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat(), index=True)  # Added timestamp and index

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
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat(), index=True)  # Added index
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
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

class QuestionCategory(Base):
    __tablename__ = 'question_category'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

class JournalEntry(Base):
    __tablename__ = 'journal_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    entry_date = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    content = Column(Text)
    sentiment_score = Column(Float)
    emotional_patterns = Column(Text)

# ==================== WORK/STUDY SATISFACTION MODEL ====================

class WorkStudySatisfaction(Base):
    __tablename__ = 'work_study_satisfaction'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Core satisfaction scores (1-5 scale)
    motivation_score = Column(Integer, nullable=False)  # How motivated are you?
    engagement_score = Column(Integer, nullable=False)  # How engaged do you feel?
    progress_score = Column(Integer, nullable=False)    # Satisfaction with progress
    environment_score = Column(Integer, nullable=False) # Satisfaction with environment
    balance_score = Column(Integer, nullable=False)     # Work-study-life balance
    
    # Calculated scores
    overall_score = Column(Float, index=True)  # 0-100 scale
    weighted_average = Column(Float)           # Weighted average (1-5 scale)
    
    # Context
    context_type = Column(String, default="work")  # "work", "study", or "both"
    occupation = Column(String, nullable=True)     # Job title/student status
    tenure_months = Column(Integer, nullable=True) # Months in current role/study
    
    # Interpretation and recommendations
    interpretation = Column(String, nullable=False)
    recommendations = Column(JSON)  # Structured recommendations
    insights = Column(Text)         # Free-text insights
    
    # Metadata
    assessment_date = Column(String, default=lambda: datetime.utcnow().isoformat())
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), 
                       onupdate=lambda: datetime.utcnow().isoformat())
    
    # Relationship
    user = relationship("User", back_populates="satisfaction_records")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_satisfaction_user_date', 'user_id', 'assessment_date'),
        Index('idx_satisfaction_score_range', 'overall_score'),
        Index('idx_satisfaction_context', 'context_type', 'overall_score'),
        Index('idx_satisfaction_occupation', 'occupation', 'overall_score'),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'domain_scores': {
                'motivation': {
                    'raw': self.motivation_score,
                    'interpretation': self._interpret_domain_score(self.motivation_score)
                },
                'engagement': {
                    'raw': self.engagement_score,
                    'interpretation': self._interpret_domain_score(self.engagement_score)
                },
                'progress': {
                    'raw': self.progress_score,
                    'interpretation': self._interpret_domain_score(self.progress_score)
                },
                'environment': {
                    'raw': self.environment_score,
                    'interpretation': self._interpret_domain_score(self.environment_score)
                },
                'balance': {
                    'raw': self.balance_score,
                    'interpretation': self._interpret_domain_score(self.balance_score)
                }
            },
            'overall': {
                'score': self.overall_score,
                'weighted_average': self.weighted_average,
                'interpretation': self.interpretation
            },
            'context': {
                'type': self.context_type,
                'occupation': self.occupation,
                'tenure_months': self.tenure_months
            },
            'recommendations': self.recommendations or [],
            'insights': self.insights,
            'timestamps': {
                'assessment_date': self.assessment_date,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
        }
    
    def _interpret_domain_score(self, score: int) -> str:
        """Interpret individual domain scores (1-5 scale)"""
        interpretations = {
            1: "Very Low - Significant concerns",
            2: "Low - Needs improvement",
            3: "Moderate - Room for growth",
            4: "High - Generally positive",
            5: "Very High - Excellent"
        }
        return interpretations.get(score, "Unknown")
    
    def calculate_overall_score(self):
        """Calculate overall satisfaction score (0-100 scale)"""
        weights = {
            'motivation': 0.3,
            'engagement': 0.25,
            'progress': 0.2,
            'environment': 0.15,
            'balance': 0.1
        }
        
        weighted_sum = (
            self.motivation_score * weights['motivation'] +
            self.engagement_score * weights['engagement'] +
            self.progress_score * weights['progress'] +
            self.environment_score * weights['environment'] +
            self.balance_score * weights['balance']
        )
        
        # Convert from 1-5 weighted average to 0-100 scale
        self.weighted_average = weighted_sum
        self.overall_score = round(weighted_sum * 20, 1)  # (1-5) * 20 = (0-100)
        
        return self.overall_score
    
    def generate_interpretation(self):
        """Generate interpretation based on overall score"""
        if self.overall_score >= 80:
            self.interpretation = "High Satisfaction"
        elif self.overall_score >= 60:
            self.interpretation = "Moderate Satisfaction"
        elif self.overall_score >= 40:
            self.interpretation = "Low Satisfaction"
        else:
            self.interpretation = "Critical Dissatisfaction"

# ==================== SATISFACTION TREND ANALYSIS ====================

class SatisfactionTrend(Base):
    __tablename__ = 'satisfaction_trends'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Trend metrics
    period_start = Column(String, nullable=False)  # e.g., "2024-01-01"
    period_end = Column(String, nullable=False)    # e.g., "2024-01-31"
    period_type = Column(String, nullable=False)   # "weekly", "monthly", "quarterly"
    
    # Averages for the period
    avg_motivation = Column(Float)
    avg_engagement = Column(Float)
    avg_progress = Column(Float)
    avg_environment = Column(Float)
    avg_balance = Column(Float)
    avg_overall = Column(Float)
    
    # Trend indicators
    trend_direction = Column(String)  # "improving", "declining", "stable"
    trend_magnitude = Column(Float)   # Percentage change
    
    # Calculated fields
    calculated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    # Indexes
    __table_args__ = (
        Index('idx_trend_user_period', 'user_id', 'period_start', 'period_end'),
        Index('idx_trend_direction', 'trend_direction', 'avg_overall'),
    )
    
    user = relationship("User")

# ==================== SATISFACTION BENCHMARKS ====================

class SatisfactionBenchmark(Base):
    __tablename__ = 'satisfaction_benchmarks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Benchmark grouping
    industry_sector = Column(String, index=True)  # e.g., "technology", "education", "healthcare"
    role_type = Column(String, index=True)        # e.g., "student", "professional", "manager"
    experience_level = Column(String, index=True) # e.g., "entry", "mid", "senior"
    
    # Benchmark scores (50th percentile)
    benchmark_motivation = Column(Float)
    benchmark_engagement = Column(Float)
    benchmark_progress = Column(Float)
    benchmark_environment = Column(Float)
    benchmark_balance = Column(Float)
    benchmark_overall = Column(Float)
    
    # Statistical data
    sample_size = Column(Integer)
    std_dev = Column(Float)
    
    # Metadata
    last_updated = Column(String, default=lambda: datetime.utcnow().isoformat())
    data_source = Column(String)  # e.g., "internal", "external_study"
    
    __table_args__ = (
        Index('idx_benchmark_sector_role', 'industry_sector', 'role_type'),
    )

# Simple function to get session (from upstream)
def get_session():
    from app.db import get_session as get_db_session
    return get_db_session()

# ==================== DATABASE PERFORMANCE OPTIMIZATIONS ====================

logger = logging.getLogger(__name__)

@event.listens_for(Base.metadata, 'before_create')
def receive_before_create(target, connection, **kw):
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
def receive_after_create_question(target, connection, **kw):
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
    cached_at = Column(String, default=lambda: datetime.utcnow().isoformat())
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
    calculated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    valid_until = Column(String, index=True)
    
    __table_args__ = (
        Index('idx_stats_name_valid', 'stat_name', 'valid_until'),
    )

# ==================== PERFORMANCE HELPER FUNCTIONS ====================

def create_performance_indexes(engine):
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
        
        # Create satisfaction-specific indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_satisfaction_overall_trend 
            ON work_study_satisfaction(user_id, overall_score, assessment_date)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_satisfaction_domain_analysis 
            ON work_study_satisfaction(
                motivation_score, engagement_score, progress_score, 
                environment_score, balance_score
            )
        """))
        
        # Optimize the database
        conn.execute(text('PRAGMA optimize'))
        
        logger.info("Performance indexes created and database optimized")

def preload_frequent_data(session):
    """Preload frequently accessed data into cache"""
    try:
        # Cache active questions
        active_questions = session.query(Question).filter(
            Question.is_active == 1
        ).order_by(Question.id).all()
        
        for question in active_questions:
            cache_entry = QuestionCache(
                question_id=question.id,
                question_text=question.question_text,
                category_id=question.category_id,
                difficulty=question.difficulty,
                is_active=question.is_active
            )
            session.merge(cache_entry)
        
        # Cache global statistics
        from sqlalchemy import func
        avg_score = session.query(func.avg(Score.total_score)).scalar() or 0
        question_count = session.query(func.count(Question.id)).filter(
            Question.is_active == 1
        ).scalar() or 0
        
        # Cache satisfaction statistics if table exists
        try:
            satisfaction_avg = session.query(func.avg(WorkStudySatisfaction.overall_score)).scalar() or 0
            satisfaction_count = session.query(func.count(WorkStudySatisfaction.id)).scalar() or 0
        except:
            satisfaction_avg = 0
            satisfaction_count = 0
        
        stats = [
            ('avg_score_global', avg_score, datetime.utcnow().isoformat()),
            ('question_count', question_count, datetime.utcnow().isoformat()),
            ('active_users', session.query(func.count(User.id)).scalar() or 0, 
             datetime.utcnow().isoformat()),
            ('satisfaction_avg', satisfaction_avg, datetime.utcnow().isoformat()),
            ('satisfaction_count', satisfaction_count, datetime.utcnow().isoformat())
        ]
        
        for stat_name, stat_value, calculated_at in stats:
            cache_entry = StatisticsCache(
                stat_name=stat_name,
                stat_value=stat_value,
                calculated_at=calculated_at,
                valid_until=(datetime.utcnow() + timedelta(hours=24)).isoformat()
            )
            session.merge(cache_entry)
        
        session.commit()
        logger.info("Frequent data preloaded into cache")
        
    except Exception as e:
        logger.error(f"Failed to preload data: {e}")
        session.rollback()

# ==================== QUERY OPTIMIZATION FUNCTIONS ====================

def get_active_questions_optimized(session, limit=None, offset=0):
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

def get_user_scores_optimized(session, username, limit=50):
    """Optimized query for user scores with pagination"""
    return session.query(Score).filter(
        Score.username == username
    ).order_by(
        Score.timestamp.desc()
    ).limit(limit).all()

def get_satisfaction_history_optimized(session, user_id, limit=20):
    """Optimized query for user's satisfaction history"""
    return session.query(WorkStudySatisfaction).filter(
        WorkStudySatisfaction.user_id == user_id
    ).order_by(
        WorkStudySatisfaction.assessment_date.desc()
    ).limit(limit).all()

# Initialize logger
logging.basicConfig(level=logging.INFO)