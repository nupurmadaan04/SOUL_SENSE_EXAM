import pytest
from unittest.mock import MagicMock
from app.ui.auth import AuthManager

def test_auth_manager_initialization(mock_app):
    """Verify AuthManager can be initialized with a mock app"""
    auth = AuthManager(mock_app)
    assert auth.app == mock_app

def test_submit_user_info_valid(mock_app, mocker):
    """Verify submit_user_info proceeds with valid input"""
    auth = AuthManager(mock_app)
    
    # Mock UI widgets (Entry widgets) using MagicMock
    auth.username_entry = MagicMock()
    auth.username_entry.get.return_value = "TestUser"
    
    auth.age_entry = MagicMock()
    auth.age_entry.get.return_value = "25"
    
    auth.profession_entry = MagicMock()
    auth.profession_entry.get.return_value = "Engineer"
    
    # Mock questions list (needed for logging)
    mock_app.questions = []
    
    # Mock helper used inside the method
    # It imports 'from app.utils import compute_age_group' locally
    mocker.patch("app.utils.compute_age_group", return_value="25-34")
    
    # Call the method
    auth.submit_user_info()
    
    # Verify app data was updated
    assert mock_app.username == "TestUser"
    assert mock_app.age == 25
    assert mock_app.age_group == "25-34"
    assert mock_app.profession == "Engineer"
    
    # Verify it called start_test (not start_exam_flow)
    assert mock_app.start_test.called

def test_submit_user_info_invalid_age(mock_app, mocker):
    """Verify error handling for invalid age"""
    auth = AuthManager(mock_app)
    
    # Mock inputs
    auth.username_entry = MagicMock()
    auth.username_entry.get.return_value = "TestUser"
    
    auth.age_entry = MagicMock()
    auth.age_entry.get.return_value = "not_a_number" 
    
    auth.profession_entry = MagicMock()
    auth.profession_entry.get.return_value = "Engineer"

    # Mock message box module to intercept all calls
    from unittest.mock import patch
    with patch("tkinter.messagebox") as mock_mb:
        # Call method
        auth.submit_user_info()
        
        # Verify error was shown
        assert mock_mb.showwarning.called
        args, _ = mock_mb.showwarning.call_args
        assert args[0] == "Invalid Age" or "invalid number" in args[1]
    
    # Verify flow did NOT proceed
    assert not mock_app.start_test.called
