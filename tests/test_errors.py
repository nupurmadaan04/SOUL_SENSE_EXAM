import pytest
import os
import logging
import json
import tkinter as tk
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.exceptions import (
    SoulSenseError, DatabaseError, ConfigurationError,
    MLModelError, UIError, ExportError, ErrorCodes
)
from app.db import safe_db_context
from app.config import load_config, CONFIG_PATH
from app.logger import setup_logging, get_logger, log_exception
# NOTE: app.main imports are done inside specific tests to avoid loading heavy UI modules
from app.error_handler import (
    ErrorHandler, get_error_handler, safe_operation, 
    safe_execute, ErrorSeverity, log_error
)

# Test Exceptions
def test_exception_hierarchy():
    exc = DatabaseError("DB Error")
    assert isinstance(exc, SoulSenseError)
    assert isinstance(exc, Exception)

# Test Logger
def test_logger_setup(tmp_path):
    with patch("app.logger.LOG_DIR", str(tmp_path)), \
         patch("app.logger._logging_initialized", False):
        setup_logging()
        assert os.path.exists(tmp_path)
        logger = logging.getLogger()
        assert len(logger.handlers) > 0

# Test DB Handling
def test_safe_db_context_error():
    with patch("app.db.SessionLocal") as MockSession:
        mock_session = MockSession.return_value
        mock_session.commit.side_effect = SQLAlchemyError("Mock DB Error")
        
        with pytest.raises(DatabaseError) as excinfo:
            with safe_db_context() as session:
                pass
        
        assert "A database error occurred" in str(excinfo.value)
        mock_session.rollback.assert_called_once()

# Test Config Error
def test_load_config_missing_is_warning(caplog):
    # Missing config should warn and return defaults
    with patch("os.path.exists", return_value=False):
        cfg = load_config()
        assert "database" in cfg
        assert "Using defaults" in caplog.text or "not found" in caplog.text

def test_load_config_corrupt_raises():
    # Corrupt config should raise ConfigurationError
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=json.JSONDecodeError("Corrupt", "doc", 0)):
        
        with pytest.raises(ConfigurationError):
            load_config()

# Test UI Error Handler
@pytest.mark.skipif(
    not os.environ.get('TEST_FULL_IMPORTS'),
    reason="Skipped to avoid heavy UI imports. Set TEST_FULL_IMPORTS=1 to run."
)
def test_global_exception_handler():
    from app.main import show_error, global_exception_handler
    with patch("app.main.show_error") as mock_show:
        # Args: self, exc_type, exc_value, traceback
        global_exception_handler(None, ValueError, ValueError("Test Error"), None)
        mock_show.assert_called_once()
        args = mock_show.call_args[0]
        assert args[0] == "Unexpected Error"

@pytest.mark.skipif(
    not os.environ.get('TEST_FULL_IMPORTS'),
    reason="Skipped to avoid heavy UI imports. Set TEST_FULL_IMPORTS=1 to run."
)
def test_show_error_logging():
    from app.main import show_error
    with patch("tkinter.messagebox.showerror") as mock_box, \
         patch("logging.error") as mock_log:
        
        err = RuntimeError("Test")
        show_error("Title", "Msg", err)
        
        mock_log.assert_called()
        mock_box.assert_called()


# ============================================================
# NEW TESTS: Centralized Error Handling (Issue #325)
# ============================================================

class TestErrorHandler:
    """Test cases for the ErrorHandler class."""
    
    def test_error_handler_singleton(self):
        """ErrorHandler should be a singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2
    
    def test_log_error_records_to_history(self):
        """log_error should record errors in history."""
        handler = get_error_handler()
        initial_count = len(handler._last_errors)
        
        test_exc = ValueError("Test error for history")
        handler.log_error(test_exc, module="test", operation="test_op")
        
        assert len(handler._last_errors) > initial_count
        last_entry = handler._last_errors[-1]
        assert last_entry["error_type"] == "ValueError"
        assert last_entry["module"] == "test"
        assert last_entry["operation"] == "test_op"
    
    def test_log_error_tracks_stats(self):
        """log_error should track error statistics by type."""
        handler = get_error_handler()
        
        test_exc = KeyError("Stats test key")
        handler.log_error(test_exc, module="stats_test", operation="op")
        
        stats = handler.get_error_stats()
        assert "stats_test.KeyError" in stats
        assert stats["stats_test.KeyError"] >= 1
    
    def test_get_user_message_for_database_error(self):
        """Should return user-friendly message for DatabaseError."""
        handler = get_error_handler()
        exc = DatabaseError("Internal DB failure")
        msg = handler.get_user_message(exc)
        # DatabaseError message should be the exception message itself
        assert "Internal DB failure" in msg or "database" in msg.lower()
    
    def test_get_user_message_fallback(self):
        """Should return default message for unknown exceptions."""
        handler = get_error_handler()
        exc = Exception("Custom unknown error")
        msg = handler.get_user_message(exc, default_message="Fallback")
        assert msg == "Fallback"
    
    def test_get_recent_errors(self):
        """Should return recent error entries."""
        handler = get_error_handler()
        handler.log_error(RuntimeError("Recent test"), module="recent")
        
        recent = handler.get_recent_errors(5)
        assert len(recent) <= 5
        assert all("timestamp" in entry for entry in recent)


class TestSafeOperationDecorator:
    """Test cases for the @safe_operation decorator."""
    
    def test_decorator_returns_fallback_on_error(self):
        """Decorator should return fallback value on exception."""
        @safe_operation(fallback="fallback_value", log=False)
        def failing_func():
            raise ValueError("Intentional failure")
        
        result = failing_func()
        assert result == "fallback_value"
    
    def test_decorator_returns_normal_value_on_success(self):
        """Decorator should return normal value when no exception."""
        @safe_operation(fallback="fallback")
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_decorator_logs_error(self):
        """Decorator should log errors when log=True."""
        handler = get_error_handler()
        initial_count = len(handler._last_errors)
        
        @safe_operation(fallback=None, log=True)
        def logging_func():
            raise TypeError("Logged error")
        
        logging_func()
        assert len(handler._last_errors) > initial_count
    
    def test_decorator_reraises_when_requested(self):
        """Decorator should re-raise when reraise=True."""
        @safe_operation(reraise=True)
        def reraising_func():
            raise RuntimeError("Should be re-raised")
        
        with pytest.raises(RuntimeError):
            reraising_func()


class TestSafeExecuteContextManager:
    """Test cases for the safe_execute context manager."""
    
    def test_context_manager_catches_exception(self):
        """Context manager should catch and handle exceptions."""
        handler = get_error_handler()
        initial_count = len(handler._last_errors)
        
        with safe_execute("test operation", module="test_cm"):
            raise ValueError("Context manager test")
        
        # Should not raise, and should log
        assert len(handler._last_errors) > initial_count
    
    def test_context_manager_calls_fallback(self):
        """Context manager should call fallback action on error."""
        fallback_called = {"value": False}
        
        def fallback_action():
            fallback_called["value"] = True
        
        with safe_execute("fallback test", fallback_action=fallback_action):
            raise KeyError("Trigger fallback")
        
        assert fallback_called["value"] is True
    
    def test_context_manager_reraises_when_requested(self):
        """Context manager should re-raise when reraise=True."""
        with pytest.raises(IndexError):
            with safe_execute("reraise test", reraise=True):
                raise IndexError("Should propagate")


class TestNewExceptionTypes:
    """Test cases for new exception types."""
    
    def test_ml_model_error(self):
        """MLModelError should have correct default code."""
        exc = MLModelError("Model load failed")
        assert isinstance(exc, SoulSenseError)
        assert exc.error_code == ErrorCodes.ML_MODEL_LOAD_FAILED
    
    def test_ui_error(self):
        """UIError should have correct default code."""
        exc = UIError("Render failed")
        assert isinstance(exc, SoulSenseError)
        assert exc.error_code == ErrorCodes.UI_RENDER_FAILED
    
    def test_export_error(self):
        """ExportError should have correct default code."""
        exc = ExportError("PDF generation failed")
        assert isinstance(exc, SoulSenseError)
        assert exc.error_code == ErrorCodes.EXPORT_FAILED
    
    def test_error_code_in_string(self):
        """Error code should appear in exception string."""
        exc = DatabaseError("Connection lost")
        exc_str = str(exc)
        assert f"E{ErrorCodes.DB_QUERY_FAILED}" in exc_str


class TestLoggerEnhancements:
    """Test cases for enhanced logger functionality."""
    
    def test_get_logger_returns_logger(self):
        """get_logger should return a Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_get_logger_caches_loggers(self):
        """get_logger should return same instance for same name."""
        logger1 = get_logger("cached_module")
        logger2 = get_logger("cached_module")
        assert logger1 is logger2
    
    def test_log_exception_helper(self):
        """log_exception should log with correct format."""
        with patch("logging.Logger.log") as mock_log:
            exc = RuntimeError("Helper test")
            log_exception(exc, message="Test context", module="test_helper")
            mock_log.assert_called()


class TestLogError:
    """Test cases for quick log_error helper."""
    
    def test_log_error_function(self):
        """log_error helper should record to handler."""
        handler = get_error_handler()
        initial_count = len(handler._last_errors)
        
        log_error(AttributeError("Quick log test"), module="quick", operation="test")
        
        assert len(handler._last_errors) > initial_count

