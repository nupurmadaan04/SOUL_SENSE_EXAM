import pytest
import sys
from unittest.mock import MagicMock, patch, call

# --- ISOLATION SETUP ---
# See test_cli_refactored.py for detailed explanation.
_patch_targets = ['app.db', 'app.questions', 'app.services.exam_service', 'app.utils']
_orig_modules = {k: sys.modules.get(k) for k in _patch_targets}

for k in _patch_targets:
    sys.modules[k] = MagicMock()

from app.cli import SoulSenseCLI

for k, v in _orig_modules.items():
    if v is not None:
        sys.modules[k] = v
    else:
        sys.modules.pop(k, None)
# -----------------------

@pytest.fixture(autouse=True)
def runtime_isolation():
    """Ensure runtime lazy imports also get mocks"""
    mocks = {
        'app.db': MagicMock(), 
        'app.questions': MagicMock(), 
        'app.services.exam_service': MagicMock(), 
        'app.utils': MagicMock(),
        'app.models': MagicMock(),
    }
    with patch.dict(sys.modules, mocks):
        yield

@pytest.fixture
def cli_instance():
    # Setup mocks
    mock_auth = MagicMock()
    mock_session = MagicMock()
    
    app_utils_mock = sys.modules['app.utils']
    app_utils_mock.load_settings.return_value = {'question_count': 5}
    
    with patch('app.cli.SENTIMENT_AVAILABLE', False):
        cli = SoulSenseCLI(mock_auth, mock_session)
    return cli

def test_authenticate_new_user(cli_instance):
    """Verify flow for creating a new user"""
    inputs = ["start_user", "30"]
    
    with patch.object(cli_instance, 'get_input', side_effect=inputs), \
         patch.object(cli_instance, 'print_header'), \
         patch.object(cli_instance, 'clear_screen'):
         
        # Mock DB
        mock_db = sys.modules['app.db']
        mock_session = MagicMock()
        mock_db.safe_db_context.return_value.__enter__.return_value = mock_session
        
        # Query returns None (User not found)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        cli_instance.authenticate()
        
        assert cli_instance.username == "start_user"
        assert cli_instance.age == 30
        assert mock_session.add.called # Should add new user

def test_authenticate_existing_user(cli_instance):
    """Verify flow for existing user"""
    inputs = ["exist_user", "30"]
    
    with patch.object(cli_instance, 'get_input', side_effect=inputs), \
         patch.object(cli_instance, 'print_header'), \
         patch.object(cli_instance, 'clear_screen'):
         
        mock_db = sys.modules['app.db']
        mock_session = MagicMock()
        mock_db.safe_db_context.return_value.__enter__.return_value = mock_session
        
        # User found
        mock_user = MagicMock()
        mock_user.id = 99
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        cli_instance.authenticate()
        
        # Should NOT add new user
        mock_session.add.assert_not_called()
        # Should load settings for user 99
        mock_db.get_user_settings.assert_called_with(99)

def test_show_results(cli_instance):
    """Verify output of results"""
    # Setup session
    mock_session = MagicMock()
    mock_session.score = 30
    mock_session.sentiment_score = 0.8
    mock_session.responses = [1, 2, 3] # 3 questions
    mock_session.finish_exam.return_value = True
    mock_session.is_rushed = False
    mock_session.is_inconsistent = False
    
    cli_instance.session = mock_session
    cli_instance.username = "test"
    
    # Mock DB for history
    mock_db = sys.modules['app.db']
    mock_conn = MagicMock()
    mock_db.get_connection.return_value = mock_conn
    mock_cursor = mock_conn.cursor.return_value
    # 1. History query
    mock_cursor.fetchall.return_value = [] 
    # 2. Avg query
    mock_cursor.fetchone.return_value = [20.0]
    
    with patch.object(cli_instance, 'get_input', return_value=""), \
         patch.object(cli_instance, 'clear_screen'), \
         patch('builtins.print') as mock_print:
         
        cli_instance.show_results()
        
        mock_session.finish_exam.assert_called()
        # Verify score printed
        # args[0] of print calls
        printed_text = "".join([str(call.args[0]) for call in mock_print.call_args_list])
        assert "30/" in printed_text
        assert "Sentiment:" in printed_text

def test_invalid_age_input(cli_instance):
    """Verify age validation loop"""
    # Inputs: "invalid", "1000", "5" (too young), "20" (valid)
    inputs = ["test", "invalid", "1000", "5", "20"]
    
    with patch.object(cli_instance, 'get_input', side_effect=inputs), \
         patch.object(cli_instance, 'print_header'), \
         patch.object(cli_instance, 'clear_screen'), \
         patch('app.db.safe_db_context'): # Mock DB to pass auth
         
        cli_instance.authenticate()
        
        assert cli_instance.age == 20
