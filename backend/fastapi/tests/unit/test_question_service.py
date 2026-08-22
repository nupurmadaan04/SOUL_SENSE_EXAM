import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from api.services.db_service import QuestionService
from api.root_models import Question, QuestionCategory


@pytest.mark.asyncio
class TestQuestionService:
    """Unit tests for QuestionService."""

    async def test_get_questions_no_filters(self):
        """Test getting questions without filters."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_questions = [MagicMock(spec=Question), MagicMock(spec=Question)]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = mock_questions

        mock_db.execute.side_effect = [mock_count_result, mock_items_result]

        questions, total = await QuestionService.get_questions(mock_db)

        assert questions == mock_questions
        assert total == 2

    async def test_get_questions_with_filters(self):
        """Test getting questions with age and category filters."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_questions = [MagicMock(spec=Question)]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = mock_questions

        mock_db.execute.side_effect = [mock_count_result, mock_items_result]

        questions, total = await QuestionService.get_questions(
            mock_db,
            min_age=20,
            max_age=30,
            category_id=1,
            active_only=True
        )

        assert questions == mock_questions
        assert total == 1
        assert mock_db.execute.call_count == 2

    async def test_get_question_by_id_found(self):
        """Test getting a question by ID when found."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_question = MagicMock(spec=Question)
        mock_question.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_question
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_question_by_id(mock_db, 1)

        assert result == mock_question

    async def test_get_question_by_id_not_found(self):
        """Test getting a question by ID when not found."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_question_by_id(mock_db, 999)

        assert result is None

    async def test_get_questions_by_age(self):
        """Test getting questions filtered by age."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_questions = [MagicMock(spec=Question), MagicMock(spec=Question)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_questions
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_questions_by_age(mock_db, 25, limit=10)

        assert result == mock_questions
        assert mock_db.execute.called

    async def test_get_questions_by_age_no_limit(self):
        """Test getting questions by age without limit."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_questions = [MagicMock(spec=Question)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_questions
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_questions_by_age(mock_db, 30)

        assert result == mock_questions

    async def test_get_categories(self):
        """Test getting all categories."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_categories = [MagicMock(spec=QuestionCategory), MagicMock(spec=QuestionCategory)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_categories
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_categories(mock_db)

        assert result == mock_categories

    async def test_get_category_by_id_found(self):
        """Test getting a category by ID when found."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_category = MagicMock(spec=QuestionCategory)
        mock_category.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_category
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_category_by_id(mock_db, 1)

        assert result == mock_category

    async def test_get_category_by_id_not_found(self):
        """Test getting a category by ID when not found."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await QuestionService.get_category_by_id(mock_db, 999)

        assert result is None