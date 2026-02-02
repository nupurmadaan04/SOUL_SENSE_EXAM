"""
Test Fixtures for Database and ML Components (Issue #348)

This module provides standardized, reusable test data and fixtures for:
- Database entities (User, Score, Response, JournalEntry, etc.)
- ML components (clustering, feature extraction, risk prediction)
- Sample data factories for generating test data

Usage:
    from tests.fixtures import sample_user, sample_score, UserFactory
    
    # Use pytest fixtures
    def test_something(sample_user):
        assert sample_user.username == "test_user"
    
    # Use factories directly
    user = UserFactory.create(username="custom_user")
"""

import pytest
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, User, UserSettings, MedicalProfile, PersonalProfile,
    UserStrengths, UserEmotionalPatterns, Score, Response,
    Question, QuestionCategory, JournalEntry, SatisfactionRecord,
    AssessmentResult
)


# ==============================================================================
# SAMPLE DATA CONSTANTS
# ==============================================================================

SAMPLE_EMOTIONS = ["Anxiety", "Stress", "Calmness", "Joy", "Frustration", "Contentment"]
SAMPLE_TRIGGERS = ["Work deadlines", "Social situations", "Financial concerns", "Health issues"]
SAMPLE_COPING = ["Deep breathing", "Exercise", "Journaling", "Meditation", "Talking to friends"]
SAMPLE_SUPPORT_STYLES = [
    "Encouraging & Motivating",
    "Problem-Solving & Practical", 
    "Just Listen & Validate",
    "Distraction & Positivity"
]
SAMPLE_STRENGTHS = ["Empathy", "Creativity", "Resilience", "Communication", "Leadership"]
SAMPLE_IMPROVEMENTS = ["Public Speaking", "Time Management", "Assertiveness", "Patience"]
SAMPLE_BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SAMPLE_OCCUPATIONS = ["Student", "Engineer", "Teacher", "Healthcare Worker", "Artist", "Manager"]
SAMPLE_GENDERS = ["M", "F", "Non-binary", "Prefer not to say"]


# ==============================================================================
# DATABASE FIXTURE FACTORIES
# ==============================================================================

class UserFactory:
    """Factory for creating test User instances."""
    
    _counter = 0
    
    @classmethod
    def create(
        cls,
        session=None,
        username: Optional[str] = None,
        password_hash: str = "test_hash_bcrypt",
        commit: bool = True
    ) -> User:
        """Create a new test user.
        
        Args:
            session: Database session (optional, for persistence)
            username: Custom username (auto-generated if None)
            password_hash: Password hash string
            commit: Whether to commit to database
            
        Returns:
            User instance
        """
        cls._counter += 1
        user = User(
            username=username or f"test_user_{cls._counter}_{datetime.utcnow().timestamp():.0f}",
            password_hash=password_hash
        )
        
        if session:
            session.add(user)
            if commit:
                session.commit()
                
        return user
    
    @classmethod
    def create_with_profiles(
        cls,
        session,
        username: Optional[str] = None,
        include_settings: bool = True,
        include_medical: bool = True,
        include_personal: bool = True,
        include_strengths: bool = True,
        include_emotional: bool = True
    ) -> User:
        """Create a user with all associated profile records.
        
        Args:
            session: Database session (required)
            username: Custom username
            include_settings: Include UserSettings
            include_medical: Include MedicalProfile
            include_personal: Include PersonalProfile
            include_strengths: Include UserStrengths
            include_emotional: Include UserEmotionalPatterns
            
        Returns:
            User with all specified profiles attached
        """
        user = cls.create(session, username, commit=True)
        
        if include_settings:
            settings = UserSettings(
                user_id=user.id,
                theme="dark",
                question_count=15,
                sound_enabled=True,
                notifications_enabled=True,
                language="en"
            )
            session.add(settings)
        
        if include_medical:
            medical = MedicalProfile(
                user_id=user.id,
                blood_type="A+",
                allergies=json.dumps(["Pollen", "Dust"]),
                medications=json.dumps(["Vitamin D"]),
                medical_conditions=json.dumps([]),
                emergency_contact_name="Jane Doe",
                emergency_contact_phone="+1-555-0123"
            )
            session.add(medical)
        
        if include_personal:
            personal = PersonalProfile(
                user_id=user.id,
                occupation="Software Engineer",
                education="Bachelor's Degree",
                marital_status="Single",
                hobbies=json.dumps(["Reading", "Hiking", "Coding"]),
                bio="Test user bio for testing purposes.",
                email="testuser@example.com",
                phone="+1-555-0100",
                gender="Prefer not to say"
            )
            session.add(personal)
        
        if include_strengths:
            strengths = UserStrengths(
                user_id=user.id,
                top_strengths=json.dumps(["Empathy", "Creativity", "Problem-solving"]),
                areas_for_improvement=json.dumps(["Time Management"]),
                current_challenges=json.dumps(["Work-life balance"]),
                learning_style="Visual",
                communication_preference="Supportive"
            )
            session.add(strengths)
        
        if include_emotional:
            emotional = UserEmotionalPatterns(
                user_id=user.id,
                common_emotions=json.dumps(["Calmness", "Occasional Stress"]),
                emotional_triggers="Deadlines and unexpected changes",
                coping_strategies="Deep breathing, taking walks, journaling",
                preferred_support="Encouraging & Motivating"
            )
            session.add(emotional)
        
        session.commit()
        session.refresh(user)
        return user
    
    @classmethod
    def reset_counter(cls):
        """Reset the internal counter (useful between test modules)."""
        cls._counter = 0


class ScoreFactory:
    """Factory for creating test Score instances."""
    
    @classmethod
    def create(
        cls,
        session=None,
        user: Optional[User] = None,
        username: str = "test_user",
        total_score: int = 75,
        sentiment_score: float = 0.5,
        age: int = 25,
        detailed_age_group: str = "Young Adult (18-25)",
        is_rushed: bool = False,
        is_inconsistent: bool = False,
        reflection_text: Optional[str] = None,
        timestamp: Optional[str] = None,
        commit: bool = True
    ) -> Score:
        """Create a test score record.
        
        Args:
            session: Database session
            user: Associated User (optional)
            username: Username string
            total_score: EQ score (0-100)
            sentiment_score: Sentiment analysis score (-1 to 1)
            age: User's age
            detailed_age_group: Age group classification
            is_rushed: Rushed answering flag
            is_inconsistent: Inconsistent answering flag
            reflection_text: Open-ended reflection
            timestamp: Custom timestamp (auto-generated if None)
            commit: Whether to commit
            
        Returns:
            Score instance
        """
        score = Score(
            username=user.username if user else username,
            user_id=user.id if user else None,
            total_score=total_score,
            sentiment_score=sentiment_score,
            age=age,
            detailed_age_group=detailed_age_group,
            is_rushed=is_rushed,
            is_inconsistent=is_inconsistent,
            reflection_text=reflection_text or "Test reflection text.",
            timestamp=timestamp or datetime.utcnow().isoformat()
        )
        
        if session:
            session.add(score)
            if commit:
                session.commit()
                
        return score
    
    @classmethod
    def create_batch(
        cls,
        session,
        user: User,
        count: int = 10,
        score_range: tuple = (50, 100),
        days_span: int = 30
    ) -> List[Score]:
        """Create multiple scores with realistic distributions.
        
        Args:
            session: Database session
            user: Associated User
            count: Number of scores to create
            score_range: (min, max) score range
            days_span: Number of days to spread scores over
            
        Returns:
            List of Score instances
        """
        scores = []
        np.random.seed(42)
        
        for i in range(count):
            days_ago = np.random.randint(0, days_span)
            timestamp = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
            total_score = np.random.randint(score_range[0], score_range[1])
            sentiment = np.random.uniform(-0.5, 1.0)
            
            score = cls.create(
                session=session,
                user=user,
                total_score=total_score,
                sentiment_score=sentiment,
                timestamp=timestamp,
                commit=False
            )
            scores.append(score)
        
        session.commit()
        return scores


class ResponseFactory:
    """Factory for creating test Response instances."""
    
    @classmethod
    def create(
        cls,
        session=None,
        user: Optional[User] = None,
        username: str = "test_user",
        question_id: int = 1,
        response_value: int = 3,
        age_group: str = "adult",
        detailed_age_group: str = "Young Adult (18-25)",
        timestamp: Optional[str] = None,
        commit: bool = True
    ) -> Response:
        """Create a test response record."""
        response = Response(
            username=user.username if user else username,
            user_id=user.id if user else None,
            question_id=question_id,
            response_value=response_value,
            age_group=age_group,
            detailed_age_group=detailed_age_group,
            timestamp=timestamp or datetime.utcnow().isoformat()
        )
        
        if session:
            session.add(response)
            if commit:
                session.commit()
                
        return response
    
    @classmethod
    def create_batch(
        cls,
        session,
        user: User,
        question_count: int = 10,
        response_pattern: str = "varied"
    ) -> List[Response]:
        """Create a batch of responses simulating a complete assessment.
        
        Args:
            session: Database session
            user: Associated User
            question_count: Number of questions answered
            response_pattern: "varied", "consistent_high", "consistent_low", "random"
            
        Returns:
            List of Response instances
        """
        responses = []
        np.random.seed(42)
        
        for q_id in range(1, question_count + 1):
            if response_pattern == "consistent_high":
                value = np.random.choice([4, 5])
            elif response_pattern == "consistent_low":
                value = np.random.choice([1, 2])
            elif response_pattern == "varied":
                value = np.random.choice([1, 2, 3, 4, 5], p=[0.1, 0.15, 0.3, 0.25, 0.2])
            else:  # random
                value = np.random.randint(1, 6)
            
            response = cls.create(
                session=session,
                user=user,
                question_id=q_id,
                response_value=value,
                commit=False
            )
            responses.append(response)
        
        session.commit()
        return responses


class JournalEntryFactory:
    """Factory for creating test JournalEntry instances."""
    
    SAMPLE_ENTRIES = [
        "Today was a productive day. I managed to complete all my tasks and even had time for a short walk.",
        "Feeling a bit overwhelmed with work lately. Need to find better ways to manage stress.",
        "Had a great conversation with a friend today. It really lifted my spirits.",
        "Struggling with sleep lately. Might need to adjust my evening routine.",
        "Made progress on my personal goals today. Small steps lead to big changes."
    ]
    
    @classmethod
    def create(
        cls,
        session=None,
        username: str = "test_user",
        content: Optional[str] = None,
        sentiment_score: float = 0.5,
        emotional_patterns: Optional[str] = None,
        sleep_hours: float = 7.0,
        sleep_quality: int = 7,
        energy_level: int = 6,
        stress_level: int = 4,
        entry_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        commit: bool = True
    ) -> JournalEntry:
        """Create a test journal entry."""
        entry = JournalEntry(
            username=username,
            content=content or np.random.choice(cls.SAMPLE_ENTRIES),
            sentiment_score=sentiment_score,
            emotional_patterns=emotional_patterns or json.dumps(["reflective", "hopeful"]),
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            energy_level=energy_level,
            stress_level=stress_level,
            entry_date=entry_date or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            tags=json.dumps(tags) if tags else json.dumps(["daily", "reflection"])
        )
        
        if session:
            session.add(entry)
            if commit:
                session.commit()
                
        return entry


class QuestionFactory:
    """Factory for creating test Question instances."""
    
    SAMPLE_QUESTIONS = [
        ("I can easily identify my emotions as I experience them.", 1, 2),
        ("I remain calm under pressure.", 2, 3),
        ("I can understand how others are feeling.", 1, 2),
        ("I can motivate myself to complete tasks.", 3, 2),
        ("I handle criticism constructively.", 2, 3),
    ]
    
    @classmethod
    def create(
        cls,
        session=None,
        question_text: Optional[str] = None,
        category_id: int = 1,
        difficulty: int = 2,
        is_active: int = 1,
        min_age: int = 0,
        max_age: int = 120,
        weight: float = 1.0,
        tooltip: Optional[str] = None,
        commit: bool = True
    ) -> Question:
        """Create a test question."""
        question = Question(
            question_text=question_text or f"Test question {datetime.utcnow().timestamp():.0f}",
            category_id=category_id,
            difficulty=difficulty,
            is_active=is_active,
            min_age=min_age,
            max_age=max_age,
            weight=weight,
            tooltip=tooltip
        )
        
        if session:
            session.add(question)
            if commit:
                session.commit()
                
        return question
    
    @classmethod
    def create_question_bank(cls, session, count: int = 20) -> List[Question]:
        """Create a full question bank for testing."""
        questions = []
        
        for i in range(count):
            idx = i % len(cls.SAMPLE_QUESTIONS)
            text, cat, diff = cls.SAMPLE_QUESTIONS[idx]
            
            question = cls.create(
                session=session,
                question_text=f"{text} (Q{i+1})",
                category_id=cat,
                difficulty=diff,
                commit=False
            )
            questions.append(question)
        
        session.commit()
        return questions


# ==============================================================================
# ML FIXTURE FACTORIES
# ==============================================================================

class FeatureDataFactory:
    """Factory for creating ML feature datasets."""
    
    FEATURE_COLUMNS = [
        'username', 'avg_total_score', 'score_std', 'avg_sentiment',
        'sentiment_std', 'score_trend', 'response_consistency',
        'emotional_range', 'assessment_frequency', 'avg_response_value',
        'response_variance'
    ]
    
    @classmethod
    def create_user_features(
        cls,
        n_users: int = 50,
        random_state: int = 42
    ) -> pd.DataFrame:
        """Create a DataFrame of user features for clustering tests.
        
        Args:
            n_users: Number of users to generate
            random_state: Random seed for reproducibility
            
        Returns:
            DataFrame with user feature data
        """
        np.random.seed(random_state)
        
        data = {
            'username': [f'test_user_{i}' for i in range(n_users)],
            'avg_total_score': np.random.uniform(20, 100, n_users),
            'score_std': np.random.uniform(0, 20, n_users),
            'avg_sentiment': np.random.uniform(-1, 1, n_users),
            'sentiment_std': np.random.uniform(0, 0.5, n_users),
            'score_trend': np.random.uniform(-1, 1, n_users),
            'response_consistency': np.random.uniform(0, 1, n_users),
            'emotional_range': np.random.uniform(0, 50, n_users),
            'assessment_frequency': np.random.randint(1, 20, n_users),
            'avg_response_value': np.random.uniform(1, 5, n_users),
            'response_variance': np.random.uniform(0, 2, n_users)
        }
        
        return pd.DataFrame(data)
    
    @classmethod
    def create_clustered_features(
        cls,
        n_users_per_cluster: int = 10,
        n_clusters: int = 4,
        random_state: int = 42
    ) -> pd.DataFrame:
        """Create features with clear cluster separation for testing.
        
        Returns DataFrame where users naturally cluster into groups.
        """
        np.random.seed(random_state)
        all_data = []
        
        # Define cluster centers (representative profiles)
        cluster_profiles = [
            # Emotionally Resilient
            {'avg_total_score': 85, 'avg_sentiment': 0.7, 'response_consistency': 0.9},
            # Emotionally Developing  
            {'avg_total_score': 60, 'avg_sentiment': 0.3, 'response_consistency': 0.6},
            # Growth Seeker
            {'avg_total_score': 45, 'avg_sentiment': 0.0, 'response_consistency': 0.5},
            # Needs Support
            {'avg_total_score': 30, 'avg_sentiment': -0.3, 'response_consistency': 0.4},
        ]
        
        for cluster_id in range(n_clusters):
            profile = cluster_profiles[cluster_id % len(cluster_profiles)]
            
            for i in range(n_users_per_cluster):
                user_data = {
                    'username': f'cluster_{cluster_id}_user_{i}',
                    'avg_total_score': profile['avg_total_score'] + np.random.normal(0, 5),
                    'score_std': np.random.uniform(5, 15),
                    'avg_sentiment': profile['avg_sentiment'] + np.random.normal(0, 0.1),
                    'sentiment_std': np.random.uniform(0.1, 0.3),
                    'score_trend': np.random.uniform(-0.3, 0.3),
                    'response_consistency': profile['response_consistency'] + np.random.normal(0, 0.05),
                    'emotional_range': np.random.uniform(10, 30),
                    'assessment_frequency': np.random.randint(3, 15),
                    'avg_response_value': np.random.uniform(2, 4),
                    'response_variance': np.random.uniform(0.3, 1.5)
                }
                all_data.append(user_data)
        
        return pd.DataFrame(all_data)


class MockMLComponents:
    """Factory for creating mock ML components."""
    
    @classmethod
    def create_mock_score(
        cls,
        total_score: int = 75,
        sentiment_score: float = 0.5,
        timestamp: Optional[str] = None
    ) -> Mock:
        """Create a mock Score object for ML tests."""
        score = Mock()
        score.total_score = total_score
        score.sentiment_score = sentiment_score
        score.timestamp = timestamp or datetime.utcnow().isoformat()
        return score
    
    @classmethod
    def create_mock_response(
        cls,
        response_value: int = 3,
        question_id: int = 1,
        timestamp: Optional[str] = None
    ) -> Mock:
        """Create a mock Response object for ML tests."""
        response = Mock()
        response.response_value = response_value
        response.question_id = question_id
        response.timestamp = timestamp or datetime.utcnow().isoformat()
        return response
    
    @classmethod
    def create_mock_clusterer(cls, n_clusters: int = 4) -> MagicMock:
        """Create a mock EmotionalProfileClusterer.
        
        Returns a mock clusterer that returns predictable results.
        """
        clusterer = MagicMock()
        clusterer.n_clusters = n_clusters
        clusterer.is_fitted = True
        clusterer.random_state = 42
        
        # Mock fit results
        clusterer.fit.return_value = {
            'n_users': 50,
            'n_clusters': n_clusters,
            'labels': [i % n_clusters for i in range(50)],
            'metrics': {
                'silhouette_score': 0.45,
                'calinski_harabasz': 120.5,
                'davies_bouldin': 0.8,
                'inertia': 500.0
            },
            'cluster_distribution': {i: 50 // n_clusters for i in range(n_clusters)}
        }
        
        # Mock predict results
        clusterer.predict.return_value = {
            'cluster_id': 0,
            'profile_name': 'Emotionally Resilient',
            'confidence': 0.85,
            'profile': {
                'name': 'Emotionally Resilient',
                'description': 'High emotional intelligence',
                'color': '#4CAF50',
                'emoji': '🌟'
            }
        }
        
        return clusterer
    
    @classmethod
    def create_mock_feature_extractor(cls) -> MagicMock:
        """Create a mock EmotionalFeatureExtractor."""
        extractor = MagicMock()
        extractor.feature_names = FeatureDataFactory.FEATURE_COLUMNS[1:]  # Exclude username
        
        # Mock extract_user_features
        extractor.extract_user_features.return_value = {
            'username': 'test_user',
            'avg_total_score': 75.0,
            'score_std': 10.0,
            'avg_sentiment': 0.5,
            'sentiment_std': 0.2,
            'score_trend': 0.1,
            'response_consistency': 0.8,
            'emotional_range': 25.0,
            'assessment_frequency': 5,
            'avg_response_value': 3.5,
            'response_variance': 0.8
        }
        
        return extractor
    
    @classmethod
    def create_mock_risk_predictor(cls) -> MagicMock:
        """Create a mock RiskPredictor."""
        predictor = MagicMock()
        predictor.model = MagicMock()
        predictor.model.predict.return_value = ["Low Risk"]
        predictor.model.predict_proba.return_value = [[0.85, 0.10, 0.05]]
        
        predictor.predict.return_value = "Low Risk"
        predictor.predict_with_explanation.return_value = {
            'prediction_label': 'Low Risk',
            'confidence': 0.85,
            'risk_factors': [],
            'protective_factors': ['High emotional awareness', 'Good support system']
        }
        
        return predictor


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================

@pytest.fixture
def sample_user(temp_db):
    """Create a basic test user."""
    return UserFactory.create(session=temp_db)


@pytest.fixture
def sample_user_with_profiles(temp_db):
    """Create a test user with all associated profiles."""
    return UserFactory.create_with_profiles(session=temp_db)


@pytest.fixture
def sample_score(temp_db, sample_user):
    """Create a test score for the sample user."""
    return ScoreFactory.create(session=temp_db, user=sample_user)


@pytest.fixture
def sample_scores_batch(temp_db, sample_user):
    """Create a batch of 10 test scores."""
    return ScoreFactory.create_batch(session=temp_db, user=sample_user, count=10)


@pytest.fixture
def sample_responses(temp_db, sample_user):
    """Create a batch of test responses."""
    return ResponseFactory.create_batch(session=temp_db, user=sample_user)


@pytest.fixture
def sample_journal_entry(temp_db, sample_user):
    """Create a test journal entry."""
    return JournalEntryFactory.create(session=temp_db, username=sample_user.username)


@pytest.fixture
def sample_question_bank(temp_db):
    """Create a test question bank with 20 questions."""
    return QuestionFactory.create_question_bank(session=temp_db, count=20)


@pytest.fixture
def sample_user_features():
    """Create sample user feature data for ML tests."""
    return FeatureDataFactory.create_user_features(n_users=50)


@pytest.fixture
def sample_clustered_features():
    """Create sample features with clear cluster separation."""
    return FeatureDataFactory.create_clustered_features()


@pytest.fixture
def mock_score():
    """Create a mock Score object for ML tests."""
    return MockMLComponents.create_mock_score()


@pytest.fixture
def mock_response():
    """Create a mock Response object for ML tests."""
    return MockMLComponents.create_mock_response()


@pytest.fixture
def mock_clusterer():
    """Create a mock EmotionalProfileClusterer."""
    return MockMLComponents.create_mock_clusterer()


@pytest.fixture
def mock_feature_extractor():
    """Create a mock EmotionalFeatureExtractor."""
    return MockMLComponents.create_mock_feature_extractor()


@pytest.fixture
def mock_risk_predictor():
    """Create a mock RiskPredictor."""
    return MockMLComponents.create_mock_risk_predictor()


# ==============================================================================
# UTILITY FIXTURES
# ==============================================================================

@pytest.fixture
def isolated_db():
    """Create a completely isolated in-memory database.
    
    This creates a fresh database for each test, independent of other fixtures.
    Useful when you need complete isolation without the temp_db patching.
    """
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def populated_db(isolated_db):
    """Create an isolated database with sample data pre-populated.
    
    Includes:
    - 3 users with full profiles
    - 10 scores per user
    - 10 responses per user
    - 5 journal entries per user
    - 20 questions
    """
    session = isolated_db
    
    # Create question bank first
    QuestionFactory.create_question_bank(session, count=20)
    
    # Create 3 users with full data
    for i in range(3):
        user = UserFactory.create_with_profiles(session, username=f"populated_user_{i}")
        ScoreFactory.create_batch(session, user, count=10)
        ResponseFactory.create_batch(session, user, question_count=10)
        
        for _ in range(5):
            JournalEntryFactory.create(session, username=user.username, commit=False)
    
    session.commit()
    yield session
