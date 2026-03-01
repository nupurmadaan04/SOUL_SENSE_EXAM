import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from api.services.results_service import AssessmentResultsService
from api.schemas import DetailedExamResult, CategoryScore, Recommendation
from api.root_models import Score, Response, Question, QuestionCategory


class TestAssessmentResultsService:
    """Unit tests for AssessmentResultsService."""

    def test_get_detailed_results_not_found(self):
        """Test when assessment is not found."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is None

    def test_get_detailed_results_no_responses(self):
        """Test when assessment exists but no detailed responses."""
        mock_db = MagicMock(spec=Session)

        # Mock score
        mock_score = MagicMock(spec=Score)
        mock_score.id = 1
        mock_score.user_id = 1
        mock_score.total_score = 75
        mock_score.timestamp = "2024-01-01T12:00:00"
        mock_score.session_id = "session123"

        # Mock query chain for score
        mock_score_query = MagicMock()
        mock_score_query.filter.return_value.first.return_value = mock_score
        mock_db.query.return_value = mock_score_query

        # Mock responses query returns empty
        mock_responses_query = MagicMock()
        mock_responses_query.join.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.side_effect = [mock_score_query, mock_responses_query]

        result = AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is not None
        assert isinstance(result, DetailedExamResult)
        assert result.assessment_id == 1
        assert result.total_score == 75.0
        assert result.max_possible_score == 0.0
        assert result.category_breakdown == []
        assert result.recommendations == []

    def test_get_detailed_results_with_responses(self):
        """Test detailed results with response data."""
        mock_db = MagicMock(spec=Session)

        # Mock score
        mock_score = MagicMock(spec=Score)
        mock_score.id = 1
        mock_score.user_id = 1
        mock_score.total_score = 75
        mock_score.timestamp = "2024-01-01T12:00:00"
        mock_score.session_id = "session123"

        # Mock responses
        mock_response1 = MagicMock(spec=Response)
        mock_response1.response_value = 4

        mock_question1 = MagicMock(spec=Question)
        mock_question1.id = 1
        mock_question1.weight = 1.0

        mock_category1 = MagicMock(spec=QuestionCategory)
        mock_category1.name = "Mental Health"
        mock_category1.max_score = 5

        mock_response2 = MagicMock(spec=Response)
        mock_response2.response_value = 3

        mock_question2 = MagicMock(spec=Question)
        mock_question2.id = 2
        mock_question2.weight = 1.0

        mock_category2 = MagicMock(spec=QuestionCategory)
        mock_category2.name = "Stress"
        mock_category2.max_score = 5

        responses_data = [
            (mock_response1, mock_question1, mock_category1),
            (mock_response2, mock_question2, mock_category2)
        ]

        # Mock query chain for score
        mock_score_query = MagicMock()
        mock_score_query.filter.return_value.first.return_value = mock_score

        # Mock query chain for responses
        mock_responses_query = MagicMock()
        mock_responses_query.join.return_value.join.return_value.filter.return_value.all.return_value = responses_data

        mock_db.query.side_effect = [mock_score_query, mock_responses_query]

        result = AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is not None
        assert isinstance(result, DetailedExamResult)
        assert result.assessment_id == 1
        assert result.total_score == 75.0
        assert result.max_possible_score == 10.0  # 2 questions * 5 max each
        assert len(result.category_breakdown) == 2

        # Check category breakdown
        categories = {cat.category_name: cat for cat in result.category_breakdown}
        assert "Mental Health" in categories
        assert "Stress" in categories

        mental_health = categories["Mental Health"]
        assert mental_health.score == 4.0
        assert mental_health.max_score == 5.0
        assert mental_health.percentage == 80.0

        stress = categories["Stress"]
        assert stress.score == 3.0
        assert stress.max_score == 5.0
        assert stress.percentage == 60.0

    def test_get_detailed_results_wrong_user(self):
        """Test that results are filtered by user_id."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Try to access assessment 1 as user 2 (should fail)
        result = AssessmentResultsService.get_detailed_results(mock_db, 1, 2)

        assert result is None

    def test_overall_percentage_calculation(self):
        """Test overall percentage calculation matches EQ score requirements."""
        mock_db = MagicMock(spec=Session)

        # Mock score for 45/50 = 90% (High EQ)
        mock_score = MagicMock(spec=Score)
        mock_score.id = 1
        mock_score.user_id = 1
        mock_score.total_score = 45
        mock_score.timestamp = "2024-01-01T12:00:00"
        mock_score.session_id = "session123"

        # Mock 10 responses (10 questions answered)
        responses_data = []
        for i in range(10):
            mock_response = MagicMock(spec=Response)
            mock_response.response_value = 4  # Average of 4.5

            mock_question = MagicMock(spec=Question)
            mock_question.id = i + 1
            mock_question.weight = 1.0

            mock_category = MagicMock(spec=QuestionCategory)
            mock_category.name = f"Category {i % 3}"

            responses_data.append((mock_response, mock_question, mock_category))

        # Mock query chains
        mock_score_query = MagicMock()
        mock_score_query.filter.return_value.first.return_value = mock_score

        mock_responses_query = MagicMock()
        mock_responses_query.join.return_value.join.return_value.filter.return_value.all.return_value = responses_data

        mock_db.query.side_effect = [mock_score_query, mock_responses_query]

        result = AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is not None
        assert result.total_score == 45.0
        assert result.max_possible_score == 50.0  # 10 questions * 5 max each
        assert result.overall_percentage == 90.00  # (45/50)*100 rounded to 2 decimals