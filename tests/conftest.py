import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.db import engine

import tkinter as tk

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
    
    return mock_app
