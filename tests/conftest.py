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
from sqlalchemy.pool import StaticPool
from app.models import Base
import backend.fastapi.api.root_models as backend_models

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
    
    # Create engine with StaticPool for in-memory DB in multi-threaded tests
    test_engine = create_engine(
        test_url, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create tables on both Base instances (if they differ due to importlib)
    Base.metadata.create_all(bind=test_engine)
    if hasattr(backend_models, "Base") and backend_models.Base is not Base:
        backend_models.Base.metadata.create_all(bind=test_engine)
    
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
    
    # Patch backend db_service (FastAPI)
    try:
        import backend.fastapi.api.services.db_service as backend_db
        monkeypatch.setattr(backend_db, "engine", test_engine)
        monkeypatch.setattr(backend_db, "SessionLocal", TestSessionLocal)
    except ImportError:
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
def mock_tk_variables(monkeypatch):
    """
    Mock Tkinter variables (StringVar, IntVar) so they don't need a root window.
    This allows logic tests to run without Tcl/Tk.
    """
    from unittest.mock import MagicMock
    
    class MockVar:
        def __init__(self, value=None):
            self._value = value
        def set(self, value):
            self._value = value
        def get(self):
            return self._value
            
    monkeypatch.setattr("tkinter.StringVar", MockVar)
    monkeypatch.setattr("tkinter.IntVar", MockVar)
    monkeypatch.setattr("tkinter.BooleanVar", MockVar)
    monkeypatch.setattr("tkinter.DoubleVar", MockVar)
    
    # Enhanced Mock Widget that supports cget and config
    class MockWidget(MagicMock):
        def __init__(self, master=None, **kwargs):
            super().__init__()
            self.master = master  # Explicitly set to prevent infinite mock chain
            self._config = {}
            self.master = master  # Explicitly set master to prevent infinite traversal
            # Add missing methods that are called during window operations
            self.transient = MagicMock()
            self.grab_set = MagicMock()
            self.geometry = MagicMock()
            self.title = MagicMock()
            self.resizable = MagicMock()
            self.protocol = MagicMock()
            self.focus_set = MagicMock()
            self.pack = MagicMock()
            self.grid = MagicMock()
            self.place = MagicMock()
            self.update_idletasks = MagicMock()
            
        def cget(self, key):
            return self._config.get(key, "")
            
        def configure(self, **kwargs):
            self._config.update(kwargs)
            return None
            
        def config(self, **kwargs):
            self.configure(**kwargs)
            return None
            
        def __getitem__(self, key):
             return self._config.get(key, "")

        def __setitem__(self, key, value):
            self._config[key] = value

    # Mock core Tk classes to prevent display connection
    mock_tk = MagicMock()
    mock_tk.return_value.winfo_screenwidth.return_value = 1920
    mock_tk.return_value.winfo_screenheight.return_value = 1080
    monkeypatch.setattr("tkinter.Tk", mock_tk)
    
    mock_toplevel = MagicMock()
    mock_toplevel.return_value.winfo_screenwidth.return_value = 1920
    mock_toplevel.return_value.winfo_screenheight.return_value = 1080
    monkeypatch.setattr("tkinter.Toplevel", mock_toplevel)
    
    monkeypatch.setattr("tkinter.Canvas", MockWidget)
    monkeypatch.setattr("tkinter.Frame", MockWidget)
    monkeypatch.setattr("tkinter.Label", MockWidget)
    monkeypatch.setattr("tkinter.Entry", MockWidget)
    monkeypatch.setattr("tkinter.Button", MockWidget)
    monkeypatch.setattr("tkinter.Checkbutton", MockWidget)  
    monkeypatch.setattr("tkinter.OptionMenu", MockWidget)    

@pytest.fixture
def mock_app():
    """
    Create a mock SoulSenseApp controller for UI tests.
    """
    from unittest.mock import MagicMock, Mock
    
    # Create the mock object
    mock_app = MagicMock()
    
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
    mock_app.root = Mock()
    # Ensure geometry methods return ints to verify math in logic
    mock_app.root.winfo_x.return_value = 0
    mock_app.root.winfo_y.return_value = 0
    mock_app.root.winfo_width.return_value = 800
    mock_app.root.winfo_height.return_value = 600
    mock_app.root.winfo_screenwidth.return_value = 1920
    mock_app.root.winfo_screenheight.return_value = 1080
    mock_app.root.winfo_reqwidth.return_value = 800
    mock_app.root.winfo_reqheight.return_value = 600
    
    return mock_app
