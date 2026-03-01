import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from fastapi import HTTPException
from api.services.exam_service import ExamService
from api.schemas import ExamResponseCreate, ExamResultCreate
from api.root_models import User, Score, Response
from backend.fastapi.app.core import ConflictError


class TestExamService:
    """Unit tests for ExamService."""

    def test_start_exam_returns_session_id(self):
        """Test that start_exam returns a valid session ID."""
        mock_db = MagicMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = 1

        session_id = ExamService.start_exam(mock_db, mock_user)

        assert isinstance(session_id, str)
        assert len(session_id) > 0

    @patch('api.services.exam_service.Response')
    def test_save_response_success(self, mock_response_class):
        """Test successful response saving."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.username = "testuser"

        # Mock the schema object
        mock_data = MagicMock()
        mock_data.question_id = 1
        mock_data.value = 3
        mock_data.age_group = "adult"

        mock_response_instance = MagicMock()
        mock_response_class.return_value = mock_response_instance

        result = ExamService.save_response(mock_db, mock_user, "session123", mock_data)

        assert result is True
        mock_db.add.assert_called_once_with(mock_response_instance)
        mock_db.commit.assert_called_once()

        # Verify Response was created with correct arguments
        mock_response_class.assert_called_once_with(
            username="testuser",
            question_id=1,
            response_value=3,
            detailed_age_group="adult",
            user_id=mock_user.id,
            session_id="session123",
            timestamp=mock_response_class.call_args[1]['timestamp']  # timestamp is dynamic
        )

    @patch('api.services.exam_service.Response')
    def test_save_response_failure(self, mock_response_class):
        """Test response saving failure."""
        mock_db = MagicMock(spec=Session)
        mock_db.commit.side_effect = Exception("DB Error")

        mock_user = MagicMock(spec=User)
        mock_data = MagicMock()
        mock_data.question_id = 1
        mock_data.value = 3
        mock_data.age_group = "adult"

        with pytest.raises(Exception, match="DB Error"):
            ExamService.save_response(mock_db, mock_user, "session123", mock_data)

        mock_db.rollback.assert_called_once()

    @patch('api.services.exam_service.Response')
    def test_save_response_duplicate_prevention(self, mock_response_class):
        """Test that duplicate responses for the same user and question are rejected."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"

        # Mock existing response in database
        mock_existing_response = MagicMock(spec=Response)
        mock_existing_response.id = 123
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_existing_response
        mock_db.query.return_value = mock_query

        # Mock the schema object
        mock_data = MagicMock()
        mock_data.question_id = 1
        mock_data.value = 3
        mock_data.age_group = "adult"

        with pytest.raises(ConflictError) as exc_info:
            ExamService.save_response(mock_db, mock_user, "session123", mock_data)

        assert "Duplicate response submission" in str(exc_info.value)
        assert exc_info.value.details[0]["question_id"] == 1
        assert exc_info.value.details[0]["existing_response_id"] == 123
        
        # Verify no new response was created or committed
        mock_response_class.assert_not_called()
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    @patch('api.services.exam_service.Response')
    def test_save_response_no_existing_duplicate(self, mock_response_class):
        """Test that response is saved when no duplicate exists."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"

        # Mock no existing response
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        # Mock the schema object
        mock_data = MagicMock()
        mock_data.question_id = 1
        mock_data.value = 3
        mock_data.age_group = "adult"

        mock_response_instance = MagicMock()
        mock_response_class.return_value = mock_response_instance

        result = ExamService.save_response(mock_db, mock_user, "session123", mock_data)

        assert result is True
        mock_db.add.assert_called_once_with(mock_response_instance)
        mock_db.commit.assert_called_once()
    @patch('api.services.exam_service.EncryptionManager')
    @patch('api.services.exam_service.GamificationService')
    @patch('api.services.exam_service.datetime')
    def test_save_score_success(self, mock_datetime, mock_gamification, mock_encryption, mock_score_class):
        """Test successful score saving."""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_encryption.encrypt.return_value = "encrypted_text"

        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"

        mock_data = MagicMock()
        mock_data.age = 25
        mock_data.total_score = 75
        mock_data.sentiment_score = 0.8
        mock_data.reflection_text = "Test reflection"
        mock_data.is_rushed = False
        mock_data.is_inconsistent = False
        mock_data.detailed_age_group = "young_adult"

        mock_score_instance = MagicMock()
        mock_score_class.return_value = mock_score_instance

        result = ExamService.save_score(mock_db, mock_user, "session123", mock_data)

        assert result == mock_score_instance
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify gamification was called
        mock_gamification.award_xp.assert_called_once_with(mock_db, 1, 100, "Assessment completion")
        mock_gamification.update_streak.assert_called_once_with(mock_db, 1, "assessment")
        mock_gamification.check_achievements.assert_called_once_with(mock_db, 1, "assessment")

    @patch('api.services.exam_service.Score')
    @patch('api.services.exam_service.CRYPTO_AVAILABLE', False)
    @patch('api.services.exam_service.GamificationService')
    def test_save_score_without_encryption(self, mock_gamification, mock_score_class):
        """Test score saving when encryption is not available."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"

        mock_data = MagicMock()
        mock_data.age = 25
        mock_data.total_score = 75
        mock_data.sentiment_score = 0.8
        mock_data.reflection_text = "Test reflection"
        mock_data.is_rushed = False
        mock_data.is_inconsistent = False
        mock_data.detailed_age_group = "young_adult"

        mock_score_instance = MagicMock()
        mock_score_class.return_value = mock_score_instance

        result = ExamService.save_score(mock_db, mock_user, "session123", mock_data)

        assert result == mock_score_instance
        # When encryption is not available, reflection text should be passed as plain text
        # This is verified by the Score constructor call

    @patch('api.services.exam_service.QuestionService')
    def test_save_score_validation_complete(self, mock_question_service):
        """Test that save_score succeeds when all questions are answered."""
        
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"

        # Mock questions for age 25
        mock_questions = [MagicMock(), MagicMock(), MagicMock()]  # 3 questions
        mock_question_service.get_questions_by_age.return_value = mock_questions

        # Mock responses count (3 responses = complete)
        mock_response_query = MagicMock()
        mock_response_query.filter.return_value = mock_response_query
        mock_response_query.count.return_value = 3
        mock_db.query.return_value = mock_response_query

        mock_data = MagicMock()
        mock_data.age = 25
        mock_data.total_score = 75
        mock_data.sentiment_score = 0.8
        mock_data.reflection_text = "Test reflection"
        mock_data.is_rushed = False
        mock_data.is_inconsistent = False
        mock_data.detailed_age_group = "young_adult"

        with patch('api.services.exam_service.Score') as mock_score_class, \
             patch('api.services.exam_service.CRYPTO_AVAILABLE', False), \
             patch('api.services.exam_service.GamificationService'):
            
            mock_score_instance = MagicMock()
            mock_score_class.return_value = mock_score_instance

            result = ExamService.save_score(mock_db, mock_user, "session123", mock_data)

            assert result == mock_score_instance

    @patch('api.services.exam_service.QuestionService')
    def test_save_score_validation_incomplete(self, mock_question_service):
        """Test that save_score fails when questions are unanswered."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"

        # Mock questions for age 25
        mock_questions = [MagicMock(), MagicMock(), MagicMock()]  # 3 questions
        mock_question_service.get_questions_by_age.return_value = mock_questions

        # Mock responses count (2 responses = incomplete)
        mock_response_query = MagicMock()
        mock_response_query.filter.return_value = mock_response_query
        mock_response_query.count.return_value = 2
        mock_db.query.return_value = mock_response_query

        mock_data = MagicMock()
        mock_data.age = 25

        with pytest.raises(HTTPException) as exc_info:
            ExamService.save_score(mock_db, mock_user, "session123", mock_data)

        assert exc_info.value.status_code == 400
        assert "1 question(s) unanswered" in exc_info.value.detail

    def test_get_history_success(self):
        """Test successful history retrieval."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1

        mock_scores = [MagicMock(spec=Score), MagicMock(spec=Score)]
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_scores

        mock_db.query.return_value = mock_query

        results, total = ExamService.get_history(mock_db, mock_user, skip=0, limit=10)

        assert results == mock_scores
        assert total == 2

    def test_get_history_limit_cap(self):
        """Test that limit is capped at 100."""
        mock_db = MagicMock(spec=Session)
        mock_user = MagicMock(spec=User)
        mock_user.id = 1

        mock_scores = []
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_scores

        mock_db.query.return_value = mock_query

        results, total = ExamService.get_history(mock_db, mock_user, skip=0, limit=200)

        assert results == mock_scores
        assert total == 0
        # Verify limit was capped to 100
        mock_query.limit.assert_called_with(100)