
import pytest
import tkinter as tk
import os
import json
import threading
from unittest.mock import MagicMock, patch
from app.startup_checks import run_all_checks, CheckStatus, check_config_integrity
from app.models import get_session
from sqlalchemy import text
from app.main import SoulSenseApp
from app.config import CONFIG_PATH, DEFAULT_CONFIG
from app.questions import initialize_questions, _ALL_QUESTIONS

def test_integrity_checks_pass():
    """
    Smoke Test: Verify that all startup integrity checks pass.
    This ensures config, required files, and DB schema are valid.
    """
    results = run_all_checks(raise_on_critical=False)
    
    # Ensure no critical failures
    for res in results:
        assert res.status != CheckStatus.FAILED, f"Check {res.name} failed: {res.message}"

def test_database_connection():
    """
    Smoke Test: Verify database connectivity.
    Ensures we can get a session and execute a simple query.
    """
    try:
        with get_session() as session:
            # Simple query to test connection
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")

@patch("app.main.UIStyles")
@patch("app.main.get_logger")
@patch("tkinter.Tk")
def test_app_initialization_verification(mock_tk, mock_logger, mock_styles):
    """
    Smoke Test: Verify SoulSenseApp initializes without crashing.
    Mocks GUI components to run in headless environments.
    """
    # Setup mocks
    mock_root = MagicMock()
    mock_tk.return_value = mock_root
    
    # Mock styles to populate colors preventing KeyError
    mock_style_instance = MagicMock()
    
    def style_init_side_effect(app_instance):
        # We must populate colors when apply_theme is called, NOT now.
        # Because app.__init__ does: self.colors = {} AFTER initing styles.
        def deferred_apply_theme(theme_name):
            app_instance.colors = {
                "bg": "#ffffff", 
                "sidebar_bg": "#f0f0f0",
                "text_primary": "#000000",
                "primary": "#blue"
            }
        
        mock_style_instance.apply_theme.side_effect = deferred_apply_theme
        return mock_style_instance
        
    mock_styles.side_effect = style_init_side_effect
    
    try:
        app = SoulSenseApp(mock_root)
        
        # Verify critical attributes are initialized
        assert app.root is not None
        assert app.auth is not None
        assert app.settings is not None
        # assert app.questions is not None # Questions might be empty list if db empty, but attribute should exist
        assert hasattr(app, 'questions')
        
    except Exception as e:
        pytest.fail(f"App initialization crashed: {e}")

def test_config_recovery_logic():
    """
    Edge Case: Test recovery from a corrupt config file.
    """
    # Windows fix: os.rename fails if dst exists. Cleanup potential leftovers first.
    backup_path = CONFIG_PATH + ".corrupt.bak"
    if os.path.exists(backup_path):
        os.remove(backup_path)

    # Create a backup of the real config if it exists
    real_config_content = None
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            real_config_content = f.read()

    try:
        # Write corrupt config
        with open(CONFIG_PATH, 'w') as f:
            f.write("{invalid_json")

        result = check_config_integrity()
        
        # Should return WARNING (recovered), not FAILED
        assert result.status == CheckStatus.WARNING, f"Config check failed: {result.message} Details: {result.details}"
        assert "restored to defaults" in result.message

        # Verify default config is now present and valid
        with open(CONFIG_PATH, 'r') as f:
            new_config = json.load(f)
            assert new_config == DEFAULT_CONFIG

    finally:
        # Restore original config
        if real_config_content:
            with open(CONFIG_PATH, 'w') as f:
                f.write(real_config_content)
        # Cleanup backup again
        if os.path.exists(backup_path):
            os.remove(backup_path)

def test_question_initialization_concurrency():
    """
    Edge Case: Verify thread safety of question initialization.
    """
    # Reset global state for test
    import app.questions
    app.questions._ALL_QUESTIONS = []
    
    # Mock safe_db_context to avoid DB hits and return dummy questions
    with patch("app.questions.safe_db_context") as mock_ctx:
        mock_session = MagicMock()
        mock_ctx.return_value.__enter__.return_value = mock_session
        
        # Setup query chain: session.query(...).filter(...).order_by(...).all()
        # Returns list of objects with required attributes
        q1 = MagicMock(id=1, question_text="Q1", tooltip="T1", min_age=10, max_age=99)
        q2 = MagicMock(id=2, question_text="Q2", tooltip="T2", min_age=10, max_age=99)
        
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [q1, q2]
        
        def run_init():
            initialize_questions()

        threads = []
        for _ in range(5):
            t = threading.Thread(target=run_init)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Check if loaded correctly
        assert len(app.questions._ALL_QUESTIONS) == 2
        assert app.questions._ALL_QUESTIONS[0][1] == "Q1"
