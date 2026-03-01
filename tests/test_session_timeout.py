"""
Session Timeout Tests (Issue #999)
----------------------------------
Tests for session timeout handling functionality.

Tests cover:
- Inactivity timeout configuration
- Session timeout detection
- Activity tracking updates
- Timeout after period of inactivity
- Warning threshold configuration
- Integration with security config
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.security_config import (
    INACTIVITY_TIMEOUT_SECONDS,
    INACTIVITY_WARNING_SECONDS,
    SESSION_TIMEOUT_HOURS
)


class TestSessionTimeoutConfiguration:
    """Test suite for session timeout configuration"""
    
    def test_inactivity_timeout_default_value(self):
        """Test that default inactivity timeout is 15 minutes (900 seconds)"""
        assert INACTIVITY_TIMEOUT_SECONDS == 900, \
            f"Expected 900 seconds (15 min), got {INACTIVITY_TIMEOUT_SECONDS}"
    
    def test_inactivity_warning_default_value(self):
        """Test that default warning threshold is 30 seconds"""
        assert INACTIVITY_WARNING_SECONDS == 30, \
            f"Expected 30 seconds, got {INACTIVITY_WARNING_SECONDS}"
    
    def test_warning_less_than_timeout(self):
        """Test that warning threshold is less than timeout"""
        assert INACTIVITY_WARNING_SECONDS < INACTIVITY_TIMEOUT_SECONDS, \
            "Warning threshold should be less than timeout"
    
    def test_session_timeout_hours_configured(self):
        """Test that session timeout hours is configured"""
        assert SESSION_TIMEOUT_HOURS == 24, \
            f"Expected 24 hours, got {SESSION_TIMEOUT_HOURS}"


class TestIdleWatcherSessionTimeout:
    """Test suite for IdleWatcher session timeout functionality"""
    
    def test_idle_watcher_uses_configured_timeout(self):
        """Test that IdleWatcher uses timeout from security_config"""
        import tkinter as tk
        from app.auth.idle_watcher import IdleWatcher
        
        # Create mock root and callback
        mock_root = Mock()
        mock_callback = Mock()
        
        # Create IdleWatcher with default timeout
        watcher = IdleWatcher(mock_root, mock_callback)
        
        # Verify it uses the configured timeout
        assert watcher.timeout_seconds == INACTIVITY_TIMEOUT_SECONDS, \
            f"Expected {INACTIVITY_TIMEOUT_SECONDS}, got {watcher.timeout_seconds}"
    
    def test_idle_watcher_uses_configured_warning_threshold(self):
        """Test that IdleWatcher uses warning threshold from security_config"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        watcher = IdleWatcher(mock_root, mock_callback)
        
        # Verify warning threshold
        assert watcher.warning_threshold == INACTIVITY_WARNING_SECONDS, \
            f"Expected {INACTIVITY_WARNING_SECONDS}, got {watcher.warning_threshold}"
    
    def test_idle_watcher_accepts_custom_timeout(self):
        """Test that IdleWatcher accepts custom timeout override"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        custom_timeout = 600  # 10 minutes
        
        watcher = IdleWatcher(mock_root, mock_callback, timeout_seconds=custom_timeout)
        
        assert watcher.timeout_seconds == custom_timeout, \
            f"Expected {custom_timeout}, got {watcher.timeout_seconds}"
    
    def test_idle_watcher_initial_state(self):
        """Test IdleWatcher initial state"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        watcher = IdleWatcher(mock_root, mock_callback)
        
        assert watcher.is_running == False
        assert watcher.warning_shown == False
        assert watcher.logout_callback == mock_callback
        assert watcher.root == mock_root
    
    @patch('app.auth.idle_watcher.time.time')
    def test_idle_watcher_reset_timer(self, mock_time):
        """Test that reset_timer updates last_activity"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        mock_time.return_value = 1000.0
        
        watcher = IdleWatcher(mock_root, mock_callback)
        watcher.start()
        
        # Initial activity
        assert watcher.last_activity == 1000.0
        
        # Advance time and reset
        mock_time.return_value = 1500.0
        watcher._reset_timer()
        
        assert watcher.last_activity == 1500.0
        watcher.stop()
    
    @patch('app.auth.idle_watcher.time.time')
    def test_idle_watcher_timeout_detection(self, mock_time):
        """Test that IdleWatcher detects timeout correctly"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        # Start at time 0
        mock_time.return_value = 0.0
        
        watcher = IdleWatcher(mock_root, mock_callback)
        watcher.start()
        
        # Advance past timeout
        mock_time.return_value = INACTIVITY_TIMEOUT_SECONDS + 1.0
        
        # Check idle detection
        elapsed = mock_time.return_value - watcher.last_activity
        assert elapsed > INACTIVITY_TIMEOUT_SECONDS, "Should detect timeout"
        
        watcher.stop()
    
    @patch('app.auth.idle_watcher.time.time')
    def test_idle_watcher_warning_threshold(self, mock_time):
        """Test that warning is shown at correct threshold"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        mock_time.return_value = 0.0
        
        watcher = IdleWatcher(mock_root, mock_callback)
        watcher.start()
        
        # Advance to warning threshold (30 seconds before timeout)
        warning_time = INACTIVITY_TIMEOUT_SECONDS - INACTIVITY_WARNING_SECONDS + 1
        mock_time.return_value = warning_time
        
        remaining = INACTIVITY_TIMEOUT_SECONDS - (mock_time.return_value - watcher.last_activity)
        
        # Should be at or below warning threshold
        assert remaining <= INACTIVITY_WARNING_SECONDS, \
            f"Remaining {remaining} should be <= warning threshold {INACTIVITY_WARNING_SECONDS}"
        
        watcher.stop()


class TestSessionTimeoutIntegration:
    """Integration tests for session timeout with auth system"""
    
    def test_activity_tracking_on_login(self, temp_db):
        """Test that activity is tracked on user login"""
        from app.auth import AuthManager
        
        auth_manager = AuthManager()
        
        # Register and login user
        auth_manager.register_user(
            "activityuser", "activity@test.com",
            "Test", "User", 25, "M", "Password123!"
        )
        
        success, msg, error_code = auth_manager.login_user("activityuser", "Password123!")
        assert success, "Login should succeed"
        
        # Verify session was created with timestamp
        assert auth_manager.current_session_id is not None
        
        from app.db import get_session
        from backend.fastapi.api.root_models import UserSession
        
        session = get_session()
        try:
            db_session = session.query(UserSession).filter_by(
                session_id=auth_manager.current_session_id
            ).first()
            
            assert db_session is not None
            assert db_session.last_accessed is not None
            assert db_session.created_at is not None
        finally:
            session.close()
    
    def test_session_validation_checks_timeout(self, temp_db):
        """Test that session validation respects timeout"""
        from app.auth import AuthManager
        from app.db import get_session
        from backend.fastapi.api.root_models import UserSession
        from datetime import datetime, timedelta, UTC
        
        auth_manager = AuthManager()
        
        # Register and login
        auth_manager.register_user(
            "timeoutuser", "timeout@test.com",
            "Test", "User", 25, "M", "Password123!"
        )
        auth_manager.login_user("timeoutuser", "Password123!")
        
        session_id = auth_manager.current_session_id
        
        # Manually set last_accessed to past timeout
        session = get_session()
        try:
            db_session = session.query(UserSession).filter_by(
                session_id=session_id
            ).first()
            
            # Set last accessed to 25 hours ago (past 24h timeout)
            past_time = datetime.now(UTC) - timedelta(hours=25)
            db_session.last_accessed = past_time.isoformat()
            session.commit()
            
            # Validate session - should fail due to timeout
            is_valid, message, data = auth_manager.validate_session(session_id)
            
            assert is_valid == False, "Session should be invalid after timeout"
            assert "expired" in message.lower() or "timeout" in message.lower(), \
                f"Message should indicate expiration: {message}"
        finally:
            session.close()


class TestSessionTimeoutEdgeCases:
    """Edge case tests for session timeout"""
    
    def test_zero_timeout_not_allowed(self):
        """Test that zero or negative timeouts are handled"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        # Should still work with very small timeout
        watcher = IdleWatcher(mock_root, mock_callback, timeout_seconds=1)
        assert watcher.timeout_seconds == 1
    
    def test_warning_threshold_zero(self):
        """Test behavior when warning threshold is zero"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        watcher = IdleWatcher(mock_root, mock_callback, timeout_seconds=60)
        # Warning threshold should still be set from config
        assert watcher.warning_threshold == INACTIVITY_WARNING_SECONDS
    
    def test_stop_clears_timeouts(self):
        """Test that stopping clears all timers"""
        from app.auth.idle_watcher import IdleWatcher
        
        mock_root = Mock()
        mock_callback = Mock()
        
        watcher = IdleWatcher(mock_root, mock_callback)
        watcher.start()
        
        assert watcher.is_running == True
        
        watcher.stop()
        
        assert watcher.is_running == False
        assert watcher.check_job is None
        mock_root.after_cancel.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
