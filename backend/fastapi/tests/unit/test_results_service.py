import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from api.services.results_service import AssessmentResultsService
from api.schemas import DetailedExamResult, CategoryScore, Recommendation
from api.models import Score, Response, Question, QuestionCategory


@pytest.mark.asyncio
class TestAssessmentResultsService:
    """Unit tests for AssessmentResultsService."""

    async def test_get_detailed_results_not_found(self):
        """Test when assessment is not found."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is None

    async def test_get_detailed_results_no_responses(self):
        """Test when assessment exists but no detailed responses."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock score
        mock_score = MagicMock(spec=Score)
        mock_score.id = 1
        mock_score.user_id = 1
        mock_score.total_score = 75
        mock_score.timestamp = "2024-01-01T12:00:00"
        mock_score.session_id = "session123"

        mock_score_result = MagicMock()
        mock_score_result.scalar_one_or_none.return_value = mock_score

        mock_resp_result = MagicMock()
        mock_resp_result.all.return_value = []

        mock_db.execute.side_effect = [mock_score_result, mock_resp_result]

        result = await AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is not None
        assert isinstance(result, DetailedExamResult)
        assert result.assessment_id == 1
        assert result.total_score == 75.0
        assert result.category_breakdown == []

    async def test_get_detailed_results_with_responses(self):
        """Test detailed results with response data."""
        mock_db = AsyncMock(spec=AsyncSession)

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
        mock_question1.category = "Mental Health"

        mock_category1 = MagicMock(spec=QuestionCategory)
        mock_category1.name = "Mental Health"
        mock_category1.max_score = 5

        mock_response2 = MagicMock(spec=Response)
        mock_response2.response_value = 3

        mock_question2 = MagicMock(spec=Question)
        mock_question2.id = 2
        mock_question2.weight = 1.0
        mock_question2.category = "Stress"

        mock_category2 = MagicMock(spec=QuestionCategory)
        mock_category2.name = "Stress"
        mock_category2.max_score = 5

        responses_data = [
            (mock_response1, mock_question1, mock_category1),
            (mock_response2, mock_question2, mock_category2)
        ]

        mock_score_result = MagicMock()
        mock_score_result.scalar_one_or_none.return_value = mock_score

        mock_resp_result = MagicMock()
        mock_resp_result.all.return_value = responses_data

        mock_db.execute.side_effect = [mock_score_result, mock_resp_result]

        result = await AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is not None
        assert isinstance(result, DetailedExamResult)
        assert result.assessment_id == 1
        assert result.total_score == 75.0
        assert result.max_possible_score == 10.0  # 2 questions * 5 max each
        assert len(result.category_breakdown) == 2

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

    async def test_get_detailed_results_wrong_user(self):
        """Test that results are filtered by user_id."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_score = MagicMock(spec=Score)
        mock_score.id = 1
        mock_score.user_id = 1  # Owned by user 1

        mock_score_result = MagicMock()
        mock_score_result.scalar_one_or_none.return_value = mock_score
        mock_db.execute.return_value = mock_score_result

        # User 2 tries to access score 1
        result = await AssessmentResultsService.get_detailed_results(mock_db, 1, 2)

        assert result is None

    async def test_overall_percentage_calculation(self):
        """Test overall percentage calculation matches EQ score requirements."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock score for 45/50 = 90% (High EQ)
        mock_score = MagicMock(spec=Score)
        mock_score.id = 1
        mock_score.user_id = 1
        mock_score.total_score = 45
        mock_score.timestamp = "2024-01-01T12:00:00"
        mock_score.session_id = "session123"

        # Mock 10 responses
        responses_data = []
        for i in range(10):
            mock_response = MagicMock(spec=Response)
            mock_response.response_value = 4.5

            mock_question = MagicMock(spec=Question)
            mock_question.id = i + 1
            mock_question.weight = 1.0
            mock_question.category = f"Category {i % 3}"

            mock_category = MagicMock(spec=QuestionCategory)
            mock_category.name = f"Category {i % 3}"

            responses_data.append((mock_response, mock_question, mock_category))

        mock_score_result = MagicMock()
        mock_score_result.scalar_one_or_none.return_value = mock_score

        mock_resp_result = MagicMock()
        mock_resp_result.all.return_value = responses_data

        mock_db.execute.side_effect = [mock_score_result, mock_resp_result]

        result = await AssessmentResultsService.get_detailed_results(mock_db, 1, 1)

        assert result is not None
        assert result.total_score == 45.0
        assert result.max_possible_score == 50.0  # 10 questions * 5 max each
        assert result.overall_percentage == 90.00  # (45/50)*100 rounded to 2 decimals