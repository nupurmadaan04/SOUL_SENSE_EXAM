import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, UTC
from app.auth.idle_watcher import IdleWatcher
from app.services.lifecycle import deactivate_dormant_accounts
from app.models import User
from app.auth.auth import AuthManager

# --- IDLE WATCHER TESTS ---

def test_idle_watcher_timeout():
    """Verify IdleWatcher triggers callback on timeout"""
    root = MagicMock()
    callback = MagicMock()
    
    # Create watcher with 10s timeout
    watcher = IdleWatcher(root, callback, timeout_seconds=10)
    
    # Patch time module where it is used
    with patch("app.auth.idle_watcher.time.time") as mock_time:
        start_time = 1000.0
        mock_time.return_value = start_time
        
        watcher.start() # capture start time as 1000
        
        # Advance time past timeout (1000 + 11 = 1011)
        mock_time.return_value = start_time + 11
        
        # Trigger check
        watcher._check_idle()
        
        # Verify callback called
        assert callback.called
        assert not watcher.is_running

def test_idle_watcher_warning():
    """Verify warning shows 30s before timeout"""
    root = MagicMock()
    root.winfo_x.return_value = 0
    root.winfo_y.return_value = 0
    root.winfo_width.return_value = 100
    root.winfo_height.return_value = 100
    
    callback = MagicMock()
    
    watcher = IdleWatcher(root, callback, timeout_seconds=60)
    
    with patch("app.auth.idle_watcher.time.time") as mock_time, \
         patch("app.auth.idle_watcher.tk.Toplevel") as mock_toplevel, \
         patch("app.auth.idle_watcher.tk.Label") as mock_label, \
         patch("app.auth.idle_watcher.tk.Button") as mock_button:
        
        # Setup mock toplevel to prevent GUI issues
        mock_warning = MagicMock()
        mock_toplevel.return_value = mock_warning
        
        start_time = 1000.0
        mock_time.return_value = start_time
        watcher.start()
        
        # Advance to 35s elapsed (25s remaining < 30s threshold)
        mock_time.return_value = start_time + 35
        
        watcher._check_idle()
        
        # Verify warning dialog created
        assert mock_toplevel.called
        assert watcher.warning_shown
        assert not callback.called

# --- LIFECYCLE TESTS ---

def test_deactivate_dormant_accounts(temp_db):
    """Verify dormant accounts are deactivated (except admin)"""
# --- LIFECYCLE TESTS ---

def test_deactivate_dormant_accounts(temp_db):
    """Verify dormant accounts are deactivated (except admin)"""
    session = temp_db # temp_db is the session
    session.close = MagicMock() # Prevent function from closing session
    
    # Create users with explicit IDs to avoid constraint issues during manual reassignment
    # Use timezone-aware datetimes to match lifecycle.py
    old_date = (datetime.now(UTC) - timedelta(days=100)).isoformat()
    
    # ID 1 = Admin (exempt)
    admin_user = User(id=1, username="admin", password_hash="hash", 
                      is_active=True, last_activity=old_date)
    
    # ID 2 = Dormant (should deactivate)
    dormant_user = User(id=2, username="dormant", password_hash="hash", 
                        is_active=True, last_activity=old_date)
                        
    # ID 3 = Active (should stay active)
    active_user = User(id=3, username="active", password_hash="hash", 
                       is_active=True, last_activity=datetime.now(UTC).isoformat())
                       
    session.add_all([admin_user, dormant_user, active_user])
    session.commit()

    with patch("app.services.lifecycle.get_session", return_value=session):
        count = deactivate_dormant_accounts(days=90)
        
        session.refresh(dormant_user)
        session.refresh(active_user)
        session.refresh(admin_user)
        
        assert not dormant_user.is_active
        assert active_user.is_active
        assert admin_user.is_active # Exempt
        assert count == 1

# --- AUTH MANAGER UPDATE TESTS ---

def test_login_updates_last_activity(mocker):
    """Verify login updates last_activity"""
    mock_session = MagicMock()
    mocker.patch("app.auth.auth.get_session", return_value=mock_session)
    
    mock_user = MagicMock()
    mock_user.password_hash = "hash"
    mock_user.username = "testuser"
    mock_user.id = 1
    mock_user.is_2fa_enabled = False  # Disable 2FA
    mock_user.is_active = True  # Ensure account is active
    mock_user.last_activity = None  # Initialize attribute
    mock_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    auth = AuthManager()
    
    # Mock verify
    mocker.patch.object(auth, "verify_password", return_value=True)
    mocker.patch.object(auth, "_is_locked_out", return_value=False)
    mocker.patch.object(auth, "_generate_session_id", return_value="fake-session-id")
    mocker.patch.object(auth, "_generate_session_token")
    mocker.patch("app.auth.auth.AuditService.log_event")  # Mock audit logging
    
    auth.login_user("testuser", "pass")
    
    # Verify last_activity was updated (not just that attribute exists)
    assert mock_user.last_activity is not None
    # And session committed
    assert mock_session.commit.called

