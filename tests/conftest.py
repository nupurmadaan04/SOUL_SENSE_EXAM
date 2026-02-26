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
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from backend.fastapi.api.root_models import Base
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
async def temp_db(monkeypatch):
    """
    Creates a temporary in-memory database for each test.
    Patches backend.fastapi.api.services.db_service.AsyncSessionLocal to use this isolate DB.
    """
    # Create valid in-memory DB URL for SQLite (async version)
    test_url = "sqlite+aiosqlite:///:memory:"
    
    # Create engine with StaticPool for in-memory DB in multi-threaded tests
    test_engine = create_async_engine(
        test_url, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if hasattr(backend_models, "Base") and backend_models.Base is not Base:
            await conn.run_sync(backend_models.Base.metadata.create_all)
    
    # Create async session factory
    TestSessionLocal = async_sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create the shared session for this test
    shared_session = TestSessionLocal()
    
    class AsyncSessionProxy:
        """A proxy that prevents closing the shared session in 'async with' blocks."""
        def __init__(self, session):
            self._session = session
        async def __aenter__(self):
            return self._session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Do nothing to keep the shared session open
            pass
        def __getattr__(self, name):
            return getattr(self._session, name)
        def __aiter__(self):
             return self._session.__aiter__()

    # Patch app.db (Main application)
    try:
        import app.db as app_db
        monkeypatch.setattr(app_db, "async_engine", test_engine)
        monkeypatch.setattr(app_db, "AsyncSessionLocal", TestSessionLocal)
        
        # Override get_async_session to return the proxy
        async def override_get_async_session():
            return AsyncSessionProxy(shared_session)
        
        monkeypatch.setattr(app_db, "get_async_session", override_get_async_session)
    except ImportError:
        pass

    # Patch app.auth.auth
    try:
        import app.auth.auth as app_auth
        monkeypatch.setattr(app_auth, "get_async_session", override_get_async_session)
    except ImportError:
        pass

    # Patch backend db_service (FastAPI)
    try:
        import backend.fastapi.api.services.db_service as backend_db
        monkeypatch.setattr(backend_db, "engine", test_engine)
        monkeypatch.setattr(backend_db, "AsyncSessionLocal", TestSessionLocal)
        
        # Also patch get_db dependency
        async def override_get_db():
            # For FastAPI dependency, we might want a nested session or just the shared one
            # Given these are integration tests, using the shared one is usually safer for state checks
            yield shared_session
        
        monkeypatch.setattr(backend_db, "get_db", override_get_db)
    except ImportError:
        pass
    
    # Clear application caches (memory + disk)
    try:
        from app.questions import clear_all_caches
        clear_all_caches()
    except ImportError:
        pass

    # Provide shared session to test
    try:
        yield shared_session
    finally:
        await shared_session.close()
    
    await test_engine.dispose()


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
