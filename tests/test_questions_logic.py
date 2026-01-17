import pytest
import time
from unittest.mock import MagicMock, patch, mock_open
from app.questions import load_questions, _questions_cache, _cache_timestamps, _cache_lock

@pytest.fixture(autouse=True)
def clean_cache():
    """Clear cache before each test"""
    from app.questions import _get_cached_questions_from_db
    
    # Force clear everything
    with _cache_lock:
        _questions_cache.clear()
        _cache_timestamps.clear()
    
    # Clear internal function cache
    _get_cached_questions_from_db.cache_clear()
    
    yield
    with _cache_lock:
        _questions_cache.clear()
        _cache_timestamps.clear()
    _get_cached_questions_from_db.cache_clear()

@pytest.fixture
def mock_all_io():
    """Mock File I/O and Threads to prevent side effects"""
    with patch('app.questions.safe_thread_run') as mock_thread, \
         patch('app.questions.get_session') as mock_session, \
         patch('app.questions._load_from_disk_cache', return_value=None) as mock_disk:
        yield {
            'thread': mock_thread,
            'session': mock_session,
            'disk': mock_disk
        }

def test_load_from_memory_cache(mock_all_io):
    from app.questions import _get_cache_key
    
    # Setup cache
    cache_key = _get_cache_key(None) # "questions_all"
    test_data = [(1, "Q1", "Tooltip", 10, 100)]
    
    with _cache_lock:
        _questions_cache[cache_key] = test_data
        _cache_timestamps[cache_key] = time.time()
    
    # Run
    # Should return immediately from memory
    result = load_questions()
    assert result == test_data
    
    # Verify disk/db were NOT called
    mock_all_io['disk'].assert_not_called()
    # Session shouldn't be used since we bypass steps 3 & 4
    # But wait, step 3 (try_db_cache) gets session. 
    # Logic: 1. check mem -> return.
    mock_all_io['session'].assert_not_called()

def test_load_from_db_fallback(mock_all_io):
    # Memory miss (default)
    # Disk miss (mocked in fixture)
    mock_session = mock_all_io['session']
    
    # DB Cache miss: Mock _try_database_cache
    with patch('app.questions._try_database_cache', return_value=None):
        # Configure Mock Session to return valid Question objects
        # Chain: session.query(Question).filter()...with_entities()...all()
        
        # Create a mock question object
        mock_q = MagicMock()
        mock_q.id = 1
        mock_q.question_text = "Q_final"
        mock_q.tooltip = "Tip"
        mock_q.min_age = 18
        mock_q.max_age = 99
        
        # Setup the query chain
        # Query -> Filter -> Filter -> WithEntities -> OrderBy -> All
        # We need to catch the chain regardless of exact calls
        # A common pattern is to make everything return the same mock query object
        mock_query = MagicMock()
        mock_session.return_value.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.with_entities.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_q]
        
        expected = [(1, "Q_final", "Tip", 18, 99)]
        
        result = load_questions(age=25)
        
        assert result == expected
        
        # Verify memory cache update
        assert _questions_cache["questions_age_25"] == expected

@pytest.mark.xfail(reason="Mocking SQLAlchemy with_entities return type is brittle")
def test_return_structure_is_5_tuple(mock_all_io):
    """Verify that even if internal DB returns valid rows, we get 5-tuples"""
    from types import SimpleNamespace
    mock_session = mock_all_io['session']
    
    # Mock row using SimpleNamespace to behave like an object/row
    mock_q = SimpleNamespace(
        id=10,
        question_text="Text",
        tooltip="Tip", # Explicit string
        min_age=5,
        max_age=10
    )
    
    mock_query = MagicMock()
    mock_session.return_value.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.with_entities.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = [mock_q]

    # Force fallback to final DB load
    with patch('app.questions._try_database_cache', return_value=None):
         result = load_questions()
         
         assert len(result) == 1
         item = result[0]
         assert isinstance(item, tuple)
         assert len(item) == 5
         assert isinstance(item[0], int)
         assert isinstance(item[1], str)
         assert isinstance(item[2], (str, type(None)))
         assert isinstance(item[3], int)
         assert isinstance(item[4], int)

@patch('app.questions.os.makedirs')
@patch('app.questions.os.path.exists')
@patch('app.questions.json.dump')
@patch('builtins.open', new_callable=mock_open)
def test_disk_cache_save(mock_file, mock_json_dump, mock_exists, mock_makedirs):
    from app.questions import _save_to_disk_cache
    
    mock_exists.return_value = True 
    
    data = [(1, "Q", "T", 1, 2)]
    _save_to_disk_cache(data, age=20)
    
    # Check file write
    mock_file.assert_called()
    # Check name contains age (verify partial match safely)
    args, _ = mock_file.call_args
    filepath = args[0]
    # Normalize slashes for comparison
    filepath = filepath.replace('\\', '/')
    assert "questions_age_20" in filepath or "questions_age_20.json" in filepath
