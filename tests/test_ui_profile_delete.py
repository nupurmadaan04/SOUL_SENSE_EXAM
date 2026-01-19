import pytest
from unittest.mock import MagicMock, patch
from app.ui.profile import UserProfileView
from app.models import User

def test_delete_user_data_ui_success(mock_app, temp_db, mocker):
    """Test successful user data deletion through UI."""
    # Create test user
    session = temp_db
    user = User(username="testuser", password_hash="hashedpass")
    session.add(user)
    session.commit()
    user_id = user.id

    # Mock app attributes
    mock_app.username = "testuser"
    mock_app.ui_styles = MagicMock()
    mock_app.ui_styles.get_font.return_value = ("Segoe UI", 10)
    mock_app.current_user_id = user_id
    mock_app.switch_view = MagicMock()
    mock_app.ui_styles = MagicMock()
    mock_app.ui_styles.get_font.return_value = ("Segoe UI", 10)

    # Create profile view
    parent = MagicMock()
    profile_view = UserProfileView(parent, mock_app)

    # Mock messagebox dialogs - patch at the module where it's used
    mock_msgbox = mocker.patch("app.ui.profile.messagebox")
    mock_msgbox.askyesno.side_effect = [True, True]  # User confirms both dialogs

    # Mock delete_user_data to return success
    with patch("app.db.delete_user_data", return_value=True):
        profile_view._delete_user_data()

    # Verify dialogs were shown
    assert mock_msgbox.askyesno.call_count == 2
    assert mock_msgbox.showinfo.called
    mock_app.switch_view.assert_called_with("login")

def test_delete_user_data_ui_cancel_first(mock_app, temp_db, mocker):
    """Test cancellation at first confirmation dialog."""
    # Mock app attributes
    mock_app.username = "testuser"
    mock_app.ui_styles = MagicMock()
    mock_app.ui_styles.get_font.return_value = ("Segoe UI", 10)

    # Create profile view
    parent = MagicMock()
    profile_view = UserProfileView(parent, mock_app)

    # Mock messagebox dialogs - patch at the module where it's used
    mock_msgbox = mocker.patch("app.ui.profile.messagebox")
    mock_msgbox.askyesno.return_value = False  # User cancels first dialog

    profile_view._delete_user_data()

    # Verify only first dialog was shown
    assert mock_msgbox.askyesno.call_count == 1
    assert not mock_msgbox.showinfo.called
    assert not mock_app.switch_view.called

def test_delete_user_data_ui_cancel_second(mock_app, temp_db, mocker):
    """Test cancellation at second confirmation dialog."""
    # Mock app attributes
    mock_app.username = "testuser"
    mock_app.ui_styles = MagicMock()
    mock_app.ui_styles.get_font.return_value = ("Segoe UI", 10)

    # Create profile view
    parent = MagicMock()
    profile_view = UserProfileView(parent, mock_app)

    # Mock messagebox dialogs - patch at the module where it's used
    mock_msgbox = mocker.patch("app.ui.profile.messagebox")
    mock_msgbox.askyesno.side_effect = [True, False]  # Cancel at second dialog

    profile_view._delete_user_data()

    # Verify both dialogs were shown but deletion didn't proceed
    assert mock_msgbox.askyesno.call_count == 2
    assert not mock_msgbox.showinfo.called
    assert not mock_app.switch_view.called

def test_delete_user_data_ui_deletion_failure(mock_app, temp_db, mocker):
    """Test handling of deletion failure."""
    # Create test user
    session = temp_db
    user = User(username="testuser", password_hash="hashedpass")
    session.add(user)
    session.commit()
    user_id = user.id

    # Mock app attributes
    mock_app.username = "testuser"
    mock_app.ui_styles = MagicMock()
    mock_app.ui_styles.get_font.return_value = ("Segoe UI", 10)
    mock_app.current_user_id = user_id

    # Create profile view
    parent = MagicMock()
    profile_view = UserProfileView(parent, mock_app)

    # Mock messagebox dialogs - patch at the module where it's used
    mock_msgbox = mocker.patch("app.ui.profile.messagebox")
    mock_msgbox.askyesno.side_effect = [True, True]  # User confirms both dialogs

    # Mock delete_user_data to return failure
    with patch("app.db.delete_user_data", return_value=False):
        profile_view._delete_user_data()

    # Verify error message was shown
    assert mock_msgbox.askyesno.call_count == 2
    assert mock_msgbox.showerror.called
    assert not mock_app.switch_view.called

def test_delete_user_data_ui_user_not_found(mock_app, mocker):
    """Test handling when user is not found."""
    # Mock app attributes
    mock_app.username = "nonexistent"
    mock_app.ui_styles = MagicMock()
    mock_app.ui_styles.get_font.return_value = ("Segoe UI", 10)

    # Create profile view
    parent = MagicMock()
    profile_view = UserProfileView(parent, mock_app)

    # Mock messagebox dialogs - patch at the module where it's used
    mock_msgbox = mocker.patch("app.ui.profile.messagebox")
    mock_msgbox.askyesno.side_effect = [True, True]  # User confirms both dialogs

    profile_view._delete_user_data()

    # Verify error message was shown
    assert mock_msgbox.askyesno.call_count == 2
    assert mock_msgbox.showerror.called
    assert not mock_app.switch_view.called
