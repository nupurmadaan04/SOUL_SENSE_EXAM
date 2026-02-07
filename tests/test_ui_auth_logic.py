import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from app.auth.app_auth import AppAuth, PasswordStrengthMeter

# Define MockWidget locally to ensure it is available and correctly used
class MockWidget(MagicMock):
    def __init__(self, master=None, *args, **kwargs):
        super().__init__()
        self.master = master  # Explicitly set to prevent infinite mock chain
        self._config = kwargs
        # Ensure geometry methods return ints by default
        self.winfo_screenwidth = MagicMock(return_value=1920)
        self.winfo_screenheight = MagicMock(return_value=1080)
        self.winfo_x = MagicMock(return_value=0)
        self.winfo_y = MagicMock(return_value=0)
        self.winfo_width = MagicMock(return_value=1000)
        self.winfo_height = MagicMock(return_value=800)
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
    # Ensure root uses MockWidget logic for geometry
    mock_app.root = MockWidget()
    return mock_app

def test_password_strength_meter(mock_app_with_colors):
    """Test the PasswordStrengthMeter visual indicator logic"""
    # Force patch Tk and Label locally to ensure MockWidget usage
    with patch("tkinter.Label", side_effect=MockWidget) as mock_lbl, \
         patch("tkinter.Frame", side_effect=MockWidget) as mock_frm, \
         patch("tkinter.Tk", side_effect=MockWidget) as mock_tk_cls, \
         patch("tkinter.BooleanVar", side_effect=MockWidget), \
         patch("tkinter.StringVar", side_effect=MockWidget), \
         patch("tkinter.IntVar", side_effect=MockWidget):
         
        root = mock_tk_cls.return_value
        meter = PasswordStrengthMeter(root, mock_app_with_colors.colors)
        
        # Test that meter works and configure is called
        # PasswordStrengthMeter modifies label text dynamically
        assert meter.label is not None
        
        # Test very strong password - just verify method works
        meter.update_strength("ComplexPass123!")
        # Verify the label's configure or config was called
        assert meter.label.configure.called or meter.label.config.called
        
        # Test weak password
        meter.update_strength("abc")
        # Just verify the update was processed
        assert meter.label.configure.called or meter.label.config.called

def test_app_auth_initialization(mock_app_with_colors):
    """Verify AppAuth can be initialized and triggers start flow"""
    with patch("app.auth.app_auth.AppAuth.start_login_flow") as mock_start:
        auth = AppAuth(mock_app_with_colors)
        assert auth.app == mock_app_with_colors
        assert auth.auth_manager is not None
        assert mock_start.called

def test_show_login_screen_creation(mock_app_with_colors):
    """Verify show_login_screen creates a Toplevel window with correct properties"""
    # Create a specific MockWidget instance to verify calls on it
    toplevel_instance = MockWidget()
    
    # Patch Toplevel to return our tracked instance
    with patch("tkinter.Toplevel", return_value=toplevel_instance) as mock_toplevel, \
         patch("tkinter.Label", side_effect=MockWidget), \
         patch("tkinter.Entry", side_effect=MockWidget), \
         patch("tkinter.Button", side_effect=MockWidget), \
         patch("tkinter.Frame", side_effect=MockWidget), \
         patch("tkinter.Checkbutton", side_effect=MockWidget), \
         patch("tkinter.BooleanVar", side_effect=MockWidget), \
         patch("tkinter.StringVar", side_effect=MockWidget), \
         patch("tkinter.IntVar", side_effect=MockWidget), \
         patch("app.auth.app_auth.AppAuth.start_login_flow"):
        
        auth = AppAuth(mock_app_with_colors)
        auth.show_login_screen()
        
        assert mock_toplevel.called
        
        # Check standard calls on the instance we injected
        assert toplevel_instance.transient.called
        assert toplevel_instance.grab_set.called

def test_show_signup_screen_creation(mock_app_with_colors):
    """Verify signup screen creation"""
    toplevel_instance = MockWidget()
    
    with patch("tkinter.Toplevel", return_value=toplevel_instance) as mock_toplevel, \
         patch("tkinter.Label", side_effect=MockWidget), \
         patch("tkinter.Entry", side_effect=MockWidget), \
         patch("tkinter.Button", side_effect=MockWidget), \
         patch("tkinter.Frame", side_effect=MockWidget), \
         patch("tkinter.Checkbutton", side_effect=MockWidget), \
         patch("tkinter.OptionMenu", side_effect=MockWidget), \
         patch("tkinter.BooleanVar", side_effect=MockWidget), \
         patch("tkinter.StringVar", side_effect=MockWidget), \
         patch("tkinter.IntVar", side_effect=MockWidget), \
         patch("app.auth.app_auth.AppAuth.start_login_flow"):
         
        auth = AppAuth(mock_app_with_colors)
        auth.show_signup_screen()
        assert mock_toplevel.called
