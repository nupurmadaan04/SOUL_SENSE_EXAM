"""
Pytest configuration and shared fixtures for SOUL_SENSE_EXAM tests.

This module provides core test infrastructure including:
- Database fixtures (temp_db for isolated testing)
- UI mocking fixtures (Tkinter variable mocks)
- Mock application controller

For additional fixtures including factory classes and ML mocks,
see tests/fixtures.py which provides:
- UserFactory, ScoreFactory, ResponseFactory, etc.
- FeatureDataFactory for ML feature datasets
- MockMLComponents for clustering and prediction mocks
- Pre-defined pytest fixtures (sample_user, sample_score, etc.)

Usage:
    # Use temp_db for database isolation
    def test_something(temp_db):
        user = User(username="test", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
    
    # Use factories from fixtures module
    from tests.fixtures import UserFactory, ScoreFactory
    def test_with_factory(temp_db):
        user = UserFactory.create_with_profiles(temp_db)
"""

import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
import tkinter as tk

# Import fixtures for re-export (allows using them without explicit import)
# These fixtures will be automatically available to all tests
from tests.fixtures import (
    # Database entity fixtures
    sample_user,
    sample_user_with_profiles,
    sample_score,
    sample_scores_batch,
    sample_responses,
    sample_journal_entry,
    sample_question_bank,
    # ML fixtures
    sample_user_features,
    sample_clustered_features,
    mock_score,
    mock_response,
    mock_clusterer,
    mock_feature_extractor,
    mock_risk_predictor,
    # Utility fixtures
    isolated_db,
    populated_db,
)

# --- DATABASE FIXTURES ---

@pytest.fixture(scope="function")
def temp_db(monkeypatch):
    """
    Creates a temporary in-memory database for each test.
    Patches app.db.SessionLocal and app.db.engine to use this isolate DB.
    """
    # Create valid in-memory DB URL for SQLite
    test_url = "sqlite:///:memory:"
    
    # Create engine and session
    test_engine = create_engine(test_url, echo=False)
    
    # Create tables (IMPORTANT: this verifies models are correct)
    Base.metadata.create_all(bind=test_engine)
    
    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Monkeypatch the REAL app.db objects
    monkeypatch.setattr("app.db.engine", test_engine)
    monkeypatch.setattr("app.db.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("app.db.get_session", lambda: TestSessionLocal())
    
    # Mock raw sqlite connection for legacy queries
    def mock_get_conn():
        return test_engine.raw_connection()
    monkeypatch.setattr("app.db.get_connection", mock_get_conn)
    
    # Patch get_session in consuming modules that used 'from app.db import get_session'
    try:
        monkeypatch.setattr("app.questions.get_session", lambda: TestSessionLocal())
    except Exception:
        pass
        
    try:
        monkeypatch.setattr("app.ml.clustering.get_session", lambda: TestSessionLocal())
    except Exception:
        pass
    
    # Clear application caches (memory + disk)
    from app.questions import clear_all_caches
    clear_all_caches()

    # Provide session to test
    session = TestSessionLocal()
    yield session
    
    # Cleanup
    session.close()
    test_engine.dispose()


# --- UI MOCKING FIXTURES ---

@pytest.fixture(scope="session", autouse=True)
def mock_tk_root():
    """
    Mock Tkinter root to prevent 'Display not found' errors in CI.
    autouse=True means this runs for ALL tests automatically.
    """
    if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
        pass

@pytest.fixture(autouse=True)
def mock_tk_variables(mocker):
    """
    Mock Tkinter variables (StringVar, IntVar) so they don't need a root window.
    This allows logic tests to run without Tcl/Tk.
    """
    class MockVar:
        def __init__(self, value=None):
            self._value = value
        def set(self, value):
            self._value = value
        def get(self):
            return self._value
            
    mocker.patch("tkinter.StringVar", side_effect=MockVar)
    mocker.patch("tkinter.IntVar", side_effect=MockVar)
    mocker.patch("tkinter.BooleanVar", side_effect=MockVar)
    mocker.patch("tkinter.DoubleVar", side_effect=MockVar)

@pytest.fixture
def mock_app(mocker):
    """
    Create a mock SoulSenseApp controller for UI tests.
    """
    # Create the mock object
    mock_app = mocker.MagicMock()
    
    # Configure attributes using configure_mock to ensure they are concrete values
    mock_app.configure_mock(
        current_question=0,
        responses=[],
        colors={
            "bg": "#ffffff", 
            "primary": "#000000", 
            "text_primary": "#000000",
            "surface": "#eeeeee"
        },
        fonts={
            "h1": ("Arial", 24, "bold"),
            "body": ("Arial", 12)
        },
        user_data={}
    )
    
    # Configure root as a separate mock
    mock_app.root = mocker.Mock()
    
@pytest.fixture(scope="session", autouse=True)
def ensure_nltk_data():
    """
    Ensure NLTK VADER lexicon is available for all tests.
    This prevents CI failures where the resource might be missing.
    """
    try:
        import nltk
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            print("Downloading NLTK VADER lexicon for tests...")
            nltk.download('vader_lexicon', quiet=True)
    except ImportError:
        pass  # NLTK not installed, tests should handle this
    except Exception as e:
        print(f"Warning: Failed to ensure NLTK data: {e}")
