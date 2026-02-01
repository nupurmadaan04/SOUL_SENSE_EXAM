import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from app.auth.app_auth import AppAuth, PasswordStrengthMeter

@pytest.fixture
def mock_app_with_colors(mock_app):
    """Enhanced mock app with required UI colors"""
    mock_app.colors = {
        "bg": "#ffffff",
        "primary": "#3B82F6",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "surface": "#FFFFFF",
        "border": "#E2E8F0"
    }
    return mock_app

def test_password_strength_meter(mock_app_with_colors):
    """Test the PasswordStrengthMeter visual indicator logic"""
    # Create a real root for widget testing (headless safe via conftest mocks)
    root = tk.Tk()
    meter = PasswordStrengthMeter(root, mock_app_with_colors.colors)
    
    # Test default
    assert "Password Strength" in meter.label.cget("text")
    
    # Test very strong password
    meter.update_strength("ComplexPass123!")
    # Score should be high (>=8 chars, upper, lower, digit, special)
    assert "Strong" in meter.label.cget("text")
    
    # Test weak password
    meter.update_strength("abc")
    assert "Weak" in meter.label.cget("text") or "Too Weak" in meter.label.cget("text")
    
    root.destroy()

def test_app_auth_initialization(mock_app_with_colors):
    """Verify AppAuth can be initialized and triggers start flow"""
    # Prevent the delayed Tcl call from firing during test
    with patch("app.auth.app_auth.AppAuth.start_login_flow") as mock_start:
        auth = AppAuth(mock_app_with_colors)
        assert auth.app == mock_app_with_colors
        assert auth.auth_manager is not None
        assert mock_start.called

@patch("tkinter.Toplevel")
def test_show_login_screen_creation(mock_toplevel, mock_app_with_colors):
    """Verify show_login_screen creates a Toplevel window with correct properties"""
    # Mock root methods used during window creation
    mock_app_with_colors.root.winfo_x.return_value = 0
    mock_app_with_colors.root.winfo_y.return_value = 0
    mock_app_with_colors.root.winfo_width.return_value = 1000
    mock_app_with_colors.root.winfo_height.return_value = 800
    
    with patch("app.auth.app_auth.AppAuth.start_login_flow"):
        auth = AppAuth(mock_app_with_colors)
        auth.show_login_screen()
        
        assert mock_toplevel.called
        # Verify the window was made transient and modal
        window_mock = mock_toplevel.return_value
        assert window_mock.transient.called
        assert window_mock.grab_set.called

@patch("tkinter.Toplevel")
def test_show_signup_screen_creation(mock_toplevel, mock_app_with_colors):
    """Verify signup screen creation"""
    mock_app_with_colors.root.winfo_x.return_value = 0
    mock_app_with_colors.root.winfo_y.return_value = 0
    mock_app_with_colors.root.winfo_width.return_value = 1000
    mock_app_with_colors.root.winfo_height.return_value = 800
    
    with patch("app.auth.app_auth.AppAuth.start_login_flow"):
        auth = AppAuth(mock_app_with_colors)
        auth.show_signup_screen()
        assert mock_toplevel.called
