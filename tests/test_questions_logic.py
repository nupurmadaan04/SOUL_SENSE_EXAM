import pytest
from unittest.mock import MagicMock, patch
from app.questions import load_questions, initialize_questions

@pytest.fixture(autouse=True)
def reset_questions_state():
    """Reset global question list before and after each test"""
    import app.questions
    # Save original state
    original_list = app.questions._ALL_QUESTIONS
    # Clear it
    app.questions._ALL_QUESTIONS = []
    
    yield
    
    # Restore or clear (clearing is safer for independence)
    app.questions._ALL_QUESTIONS = []

@patch('app.questions.safe_db_context')
def test_initialize_questions(mock_ctx):
    """Test that initialize_questions loads data from DB into global list"""
    # Setup mock session
    mock_session = MagicMock()
    mock_ctx.return_value.__enter__.return_value = mock_session
    
    # Configure mock query result
    # We simulate the return of 5 columns as defined in the query
    # Using namedtuple to simulate SQLAlchemy Row (attribute + index access)
    from collections import namedtuple
    Row = namedtuple('Row', ['id', 'question_text', 'tooltip', 'min_age', 'max_age'])
    
    mock_data = [
        Row(1, "Question 1", "Tooltip 1", 18, 100),
        Row(2, "Question 2", None, 25, 60)
    ]
    
    # Mock the query chain
    mock_query = mock_session.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = mock_data
    
    # Execute
    success = initialize_questions()
    
    assert success is True
    
    # Verify global list is populated
    from app.questions import _ALL_QUESTIONS
    assert len(_ALL_QUESTIONS) == 2
    assert _ALL_QUESTIONS[0] == mock_data[0]
    assert _ALL_QUESTIONS[1] == mock_data[1]

def test_load_questions_lazy_loading():
    """Test that load_questions triggers initialization if list is empty"""
    import app.questions
    
    # Verify pre-condition
    assert app.questions._ALL_QUESTIONS == []
    
    with patch('app.questions.initialize_questions') as mock_init:
        # Mock init to succeed and populate list (simulate side effect)
        def side_effect():
             app.questions._ALL_QUESTIONS = [(1, "Q1", "T1", 18, 99)]
             return True
        mock_init.side_effect = side_effect
        
        # Call load_questions
        result = load_questions()
        
        # Verify init was called
        mock_init.assert_called_once()
        assert len(result) == 1
        assert result[0][1] == "Q1"

def test_load_questions_filtering():
    """Test age filtering logic on in-memory list"""
    import app.questions
    
    # Manually populate the global list
    app.questions._ALL_QUESTIONS = [
        (1, "General Q", "All ages", 18, 100),
        (2, "Young Q", "Young only", 18, 25),
        (3, "Mid Q", "Mid only", 30, 50),
        (4, "Old Q", "Old only", 60, 100),
    ]
    
    # Test 1: Age 20 (Should get 1 and 2)
    res_20 = load_questions(age=20)
    ids_20 = sorted([q[0] for q in res_20])
    assert ids_20 == [1, 2]
    
    # Test 2: Age 40 (Should get 1 and 3)
    res_40 = load_questions(age=40)
    ids_40 = sorted([q[0] for q in res_40])
    assert ids_40 == [1, 3]
    
    # Test 3: Age 70 (Should get 1 and 4)
    res_70 = load_questions(age=70)
    ids_70 = sorted([q[0] for q in res_70])
    assert ids_70 == [1, 4]
    
    # Test 4: No Age (Should get all)
    res_all = load_questions(age=None)
    assert len(res_all) == 4

def test_get_question_count_optimized():
    """Test the optimized get_question_count using in-memory list"""
    from app.questions import get_question_count
    import app.questions
    
    app.questions._ALL_QUESTIONS = [
        (1, "Q1", "", 10, 20),
        (2, "Q2", "", 10, 20),
        (3, "Q3", "", 30, 40)
    ]
    
    assert get_question_count() == 3
    assert get_question_count(age=15) == 2
    assert get_question_count(age=35) == 1
    assert get_question_count(age=99) == 0
