import pytest
import time
from unittest.mock import MagicMock, patch
from app.services.exam_service import ExamSession

@pytest.fixture
def mock_questions():
    # Format: (id, text, tooltip, min_age, max_age)
    return [
        (1, "Question 1", "Tip 1", 10, 100),
        (2, "Question 2", "Tip 2", 10, 100),
        (3, "Question 3", "Tip 3", 10, 100)
    ]

@pytest.fixture
def exam_session(mock_questions):
    return ExamSession("testuser", 25, "adult", mock_questions)

def test_session_initialization(exam_session, mock_questions):
    assert exam_session.username == "testuser"
    assert exam_session.age == 25
    assert len(exam_session.questions) == 3
    assert exam_session.current_question_index == 0
    assert len(exam_session.responses) == 0
    assert not exam_session.is_finished()

def test_start_exam(exam_session):
    exam_session.start_exam()
    assert exam_session.current_question_index == 0
    assert exam_session.score == 0
    # question_start_time should be set
    assert exam_session.question_start_time is not None

def test_get_current_question(exam_session):
    # Should get first question tuple (Text, Tooltip)
    q_text, q_tip = exam_session.get_current_question()
    assert q_text == "Question 1"
    assert q_tip == "Tip 1"

@patch('app.db.get_connection')
def test_submit_answer_valid(mock_conn, exam_session):
    exam_session.start_exam()
    
    # Mock DB cursor for _save_response_to_db
    mock_cursor = MagicMock()
    mock_conn.return_value.cursor.return_value = mock_cursor
    
    # Submit valid answer (1-4)
    exam_session.submit_answer(3) 
    
    assert len(exam_session.responses) == 1
    assert exam_session.responses[0] == 3
    assert exam_session.current_question_index == 1
    
    # Verify progress: (current_q_num, total, pct)
    # After answering 1, we are on index 1 (which is 2nd question)
    prog = exam_session.get_progress()
    # assert prog == (2, 3, 100.0/3) # Floating point risk
    assert prog[0] == 2
    assert prog[1] == 3
    assert prog[2] == pytest.approx(33.33, abs=0.01)

def test_submit_answer_invalid(exam_session):
    exam_session.start_exam()
    # Value must be 1-4
    with pytest.raises(ValueError, match="Answer must be between 1 and 4"):
        exam_session.submit_answer(5)

@patch('app.db.safe_db_context')
def test_exam_completion_flow(mock_safe_db, exam_session, temp_db):  # Add temp_db fixture
    # Mock the database session
    mock_session = MagicMock()
    mock_safe_db.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_safe_db. return_value.__exit__ = MagicMock(return_value=False)  # Fix: remove space
    
    # Mock User query for finish_exam
    mock_user = MagicMock()
    mock_user.id = 123
    mock_session. query.return_value.filter_by.return_value.first. return_value = mock_user
    
    exam_session.start_exam()
    
    # Answer all 3 questions
    exam_session.submit_answer(2)
    exam_session.submit_answer(3)
    exam_session.submit_answer(4)
    
    assert exam_session.is_finished() is True
    assert exam_session. current_question_index == 3
    
    # Calculate metrics is called inside finish_exam usually, but let's check state
    exam_session.calculate_metrics()
    assert exam_session. score == 2 + 3 + 4  # Fix: remove space
    
    # Test finish_exam (DB save) - now properly mocked
    result = exam_session.finish_exam()
    assert result is True
    
    # Verify session operations were called
    assert mock_session.add. called or mock_session.commit. called
    
def test_timing_tracking(exam_session):
    with patch('app.db.get_connection'):
        exam_session.start_exam()
        time.sleep(0.1)
        exam_session.submit_answer(2)
        
        response_time = exam_session.response_times[0]
        assert response_time >= 0.1

def test_go_back_and_overwrite(exam_session):
    with patch('app.db.get_connection'):
        exam_session.start_exam()
        
        # Answer Q1 with 2
        exam_session.submit_answer(2) 
        assert exam_session.current_question_index == 1
        assert exam_session.responses[0] == 2
        
        # Go Back
        success = exam_session.go_back()
        assert success is True
        assert exam_session.current_question_index == 0
        
        # Overwrite Q1 with 4
        exam_session.submit_answer(4)
        assert exam_session.responses[0] == 4
        assert exam_session.current_question_index == 1
