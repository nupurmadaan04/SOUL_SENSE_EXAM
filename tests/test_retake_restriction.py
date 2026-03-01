"""
Test cases for Retake Restriction feature (Issue #993).

This module tests:
- System checks if result exists
- Questionnaire disabled after completion
- Attempt count tracking
- Retake attempt blocking
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch
from sqlalchemy import func

from app.services.exam_service import ExamService, ExamSession
from app.models import Score, User


class TestRetakeRestrictionService:
    """Test cases for ExamService retake restriction methods."""

    def test_has_completed_assessment_false_for_new_user(self, temp_db):
        """Test that a new user without scores returns False."""
        # Create a user
        user = User(username="testuser_no_score", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Check should return False
        result = ExamService.has_completed_assessment(user.id)
        assert result is False

    def test_has_completed_assessment_true_with_completed(self, temp_db):
        """Test that a user with completed assessment returns True."""
        # Create a user
        user = User(username="testuser_completed", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Add a completed score
        score = Score(
            username="testuser_completed",
            user_id=user.id,
            total_score=50,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        # Check should return True
        result = ExamService.has_completed_assessment(user.id)
        assert result is True

    def test_has_completed_assessment_false_with_in_progress(self, temp_db):
        """Test that an in-progress assessment does not count as completed."""
        # Create a user
        user = User(username="testuser_in_progress", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Add an in-progress score
        score = Score(
            username="testuser_in_progress",
            user_id=user.id,
            total_score=25,
            status="in_progress",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        # Check should return False (not completed)
        result = ExamService.has_completed_assessment(user.id)
        assert result is False

    def test_get_completed_assessment_count_zero(self, temp_db):
        """Test that count is 0 for user with no completed assessments."""
        user = User(username="testuser_count_zero", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        count = ExamService.get_completed_assessment_count(user.id)
        assert count == 0

    def test_get_completed_assessment_count_multiple(self, temp_db):
        """Test count with multiple completed assessments."""
        user = User(username="testuser_count_multi", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Add multiple completed scores
        for i in range(3):
            score = Score(
                username="testuser_count_multi",
                user_id=user.id,
                total_score=50 + i,
                status="completed",
                attempt_number=i + 1,
                timestamp=datetime.now(UTC).isoformat()
            )
            temp_db.add(score)
        temp_db.commit()
        
        count = ExamService.get_completed_assessment_count(user.id)
        assert count == 3

    def test_get_next_attempt_number_first_attempt(self, temp_db):
        """Test that first attempt returns 1."""
        user = User(username="testuser_first", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        next_attempt = ExamService.get_next_attempt_number(user.id)
        assert next_attempt == 1

    def test_get_next_attempt_number_subsequent(self, temp_db):
        """Test that next attempt is calculated correctly."""
        user = User(username="testuser_subsequent", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Add existing attempts
        for i in range(1, 4):
            score = Score(
                username="testuser_subsequent",
                user_id=user.id,
                total_score=50,
                status="completed",
                attempt_number=i,
                timestamp=datetime.now(UTC).isoformat()
            )
            temp_db.add(score)
        temp_db.commit()
        
        next_attempt = ExamService.get_next_attempt_number(user.id)
        assert next_attempt == 4

    def test_check_retake_allowed_for_none_user_id(self):
        """Test that anonymous users (None user_id) are allowed."""
        is_allowed, message = ExamService.check_retake_allowed(None)
        assert is_allowed is True
        assert "Anonymous" in message

    def test_check_retake_allowed_for_new_user(self, temp_db):
        """Test that new users are allowed to take assessment."""
        user = User(username="testuser_new", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        is_allowed, message = ExamService.check_retake_allowed(user.id)
        assert is_allowed is True
        assert "allowed" in message.lower()

    def test_check_retake_blocked_after_completion(self, temp_db):
        """Test that retake is blocked after completion."""
        user = User(username="testuser_blocked", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Add completed assessment
        score = Score(
            username="testuser_blocked",
            user_id=user.id,
            total_score=75,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        is_allowed, message = ExamService.check_retake_allowed(user.id)
        assert is_allowed is False
        assert "already completed" in message.lower() or "not allowed" in message.lower()


class TestRetakeRestrictionSession:
    """Test cases for ExamSession retake restriction integration."""

    def test_exam_session_check_retake_eligibility_new_user(self, temp_db):
        """Test ExamSession static method for new user."""
        user = User(username="session_new_user", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        is_allowed, message = ExamSession.check_retake_eligibility(user.id)
        assert is_allowed is True

    def test_exam_session_check_retake_eligibility_completed(self, temp_db):
        """Test ExamSession static method blocks completed user."""
        user = User(username="session_completed", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        score = Score(
            username="session_completed",
            user_id=user.id,
            total_score=80,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        is_allowed, message = ExamSession.check_retake_eligibility(user.id)
        assert is_allowed is False

    def test_exam_session_with_user_id(self):
        """Test that ExamSession stores user_id correctly."""
        questions = [
            (1, "Q1", "Tip1", 10, 100),
            (2, "Q2", "Tip2", 10, 100)
        ]
        session = ExamSession(
            username="testuser",
            age=25,
            age_group="adult",
            questions=questions,
            user_id=123
        )
        assert session.user_id == 123

    def test_exam_session_without_user_id(self):
        """Test that ExamSession works without user_id."""
        questions = [
            (1, "Q1", "Tip1", 10, 100),
            (2, "Q2", "Tip2", 10, 100)
        ]
        session = ExamSession(
            username="anonymous",
            age=25,
            age_group="adult",
            questions=questions,
            user_id=None
        )
        assert session.user_id is None


class TestScoreModelFields:
    """Test cases for Score model attempt tracking fields."""

    def test_score_model_has_attempt_number(self, temp_db):
        """Test that Score model has attempt_number field."""
        user = User(username="score_attempt_test", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        score = Score(
            username="score_attempt_test",
            user_id=user.id,
            total_score=50,
            attempt_number=2,
            status="completed",
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        # Retrieve and verify
        retrieved = temp_db.query(Score).filter_by(user_id=user.id).first()
        assert retrieved.attempt_number == 2
        assert retrieved.status == "completed"

    def test_score_model_default_status(self, temp_db):
        """Test that Score model has default status."""
        user = User(username="score_default_test", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Create score without specifying status
        score = Score(
            username="score_default_test",
            user_id=user.id,
            total_score=50,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        retrieved = temp_db.query(Score).filter_by(user_id=user.id).first()
        assert retrieved.status == "completed"  # Default value
        assert retrieved.attempt_number == 1  # Default value


class TestSaveScoreWithAttemptTracking:
    """Test cases for save_score method with attempt tracking."""

    @patch('app.services.exam_service.safe_db_context')
    def test_save_score_auto_calculates_attempt_number(self, mock_safe_db, temp_db):
        """Test that save_score auto-calculates attempt number."""
        # Setup mock
        mock_session = MagicMock()
        mock_safe_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_safe_db.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock user query
        mock_user = MagicMock()
        mock_user.id = 123
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Mock max attempt query (no existing attempts)
        mock_session.query.return_value.filter.return_value.scalar.return_value = None
        
        result = ExamService.save_score(
            username="testuser",
            age=25,
            age_group="adult",
            score=50,
            sentiment_score=0.5,
            reflection_text="Test",
            is_rushed=False,
            is_inconsistent=False,
            detailed_age_group="adult"
        )
        
        assert result is True

    def test_save_score_with_explicit_attempt_number(self, temp_db):
        """Test saving score with explicit attempt number."""
        user = User(username="explicit_attempt", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        result = ExamService.save_score(
            username="explicit_attempt",
            age=25,
            age_group="adult",
            score=50,
            sentiment_score=0.5,
            reflection_text="Test",
            is_rushed=False,
            is_inconsistent=False,
            detailed_age_group="adult",
            status="completed",
            attempt_number=5
        )
        
        assert result is True
        
        # Verify the score was saved with correct attempt number
        saved_score = temp_db.query(Score).filter_by(user_id=user.id).first()
        assert saved_score is not None
        assert saved_score.attempt_number == 5
        assert saved_score.status == "completed"


class TestIntegrationRetakeFlow:
    """Integration tests for complete retake restriction flow."""

    def test_complete_flow_block_retake(self, temp_db):
        """Test complete flow: user takes assessment, tries to retake, is blocked."""
        # 1. Create user
        user = User(username="integration_user", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # 2. Verify user can start (no completed assessment)
        is_allowed, _ = ExamService.check_retake_allowed(user.id)
        assert is_allowed is True
        
        # 3. Simulate completing an assessment
        score = Score(
            username="integration_user",
            user_id=user.id,
            total_score=85,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        # 4. Verify user is now blocked from retaking
        is_allowed, message = ExamService.check_retake_allowed(user.id)
        assert is_allowed is False
        assert "already completed" in message.lower() or "not allowed" in message.lower()
        
        # 5. Verify has_completed_assessment returns True
        assert ExamService.has_completed_assessment(user.id) is True
        
        # 6. Verify count is 1
        assert ExamService.get_completed_assessment_count(user.id) == 1

    def test_attempt_number_increments(self, temp_db):
        """Test that attempt numbers increment correctly across multiple assessments."""
        user = User(username="increment_user", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # First assessment
        score1 = Score(
            username="increment_user",
            user_id=user.id,
            total_score=60,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score1)
        temp_db.commit()
        
        # Get next attempt number (if allowed, which it isn't, but we test the logic)
        next_attempt = ExamService.get_next_attempt_number(user.id)
        assert next_attempt == 2

    def test_anonymous_user_always_allowed(self):
        """Test that anonymous users (no user_id) are always allowed."""
        # Anonymous user should be allowed even if we can't check
        is_allowed, message = ExamService.check_retake_allowed(None)
        assert is_allowed is True
        assert "anonymous" in message.lower() or "bypassed" in message.lower()


class TestErrorHandling:
    """Test error handling in retake restriction."""

    @patch('app.services.exam_service.safe_db_context')
    def test_has_completed_assessment_error_handling(self, mock_safe_db):
        """Test that has_completed_assessment handles errors gracefully."""
        mock_safe_db.side_effect = Exception("Database error")
        
        # Should return False on error (fail-safe)
        result = ExamService.has_completed_assessment(123)
        assert result is False

    @patch('app.services.exam_service.safe_db_context')
    def test_check_retake_allowed_error_handling(self, mock_safe_db):
        """Test that check_retake_allowed handles errors gracefully."""
        mock_safe_db.side_effect = Exception("Database error")
        
        # Should allow on error (fail-safe)
        is_allowed, message = ExamService.check_retake_allowed(123)
        assert is_allowed is True
        assert "could not verify" in message.lower()

    @patch('app.services.exam_service.safe_db_context')
    def test_get_next_attempt_number_error_handling(self, mock_safe_db):
        """Test that get_next_attempt_number handles errors gracefully."""
        mock_safe_db.side_effect = Exception("Database error")
        
        # Should return 1 on error
        result = ExamService.get_next_attempt_number(123)
        assert result == 1


class TestAcceptanceCriteria:
    """Tests directly addressing the acceptance criteria from Issue #993."""

    def test_ac_system_checks_if_result_exists(self, temp_db):
        """
        Acceptance Criteria: System checks if result exists.
        
        The system should be able to determine if a user has an existing
        completed assessment result.
        """
        user = User(username="ac_exists_check", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Before: No result exists
        assert ExamService.has_completed_assessment(user.id) is False
        
        # After: Result exists
        score = Score(
            username="ac_exists_check",
            user_id=user.id,
            total_score=70,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        assert ExamService.has_completed_assessment(user.id) is True

    def test_ac_questionnaire_disabled_after_completion(self, temp_db):
        """
        Acceptance Criteria: Questionnaire disabled after completion.
        
        After a user completes an assessment, they should not be able
        to start a new one (retake restriction).
        """
        user = User(username="ac_disabled", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # User can start initially
        is_allowed, _ = ExamService.check_retake_allowed(user.id)
        assert is_allowed is True
        
        # Complete assessment
        score = Score(
            username="ac_disabled",
            user_id=user.id,
            total_score=80,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        # Now questionnaire should be "disabled" (retake blocked)
        is_allowed, _ = ExamService.check_retake_allowed(user.id)
        assert is_allowed is False

    def test_ac_attempt_count_tracked(self, temp_db):
        """
        Acceptance Criteria: Attempt count tracked.
        
        The system should track how many attempts a user has made.
        """
        user = User(username="ac_attempt_count", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Initially 0 attempts
        assert ExamService.get_completed_assessment_count(user.id) == 0
        assert ExamService.get_next_attempt_number(user.id) == 1
        
        # Add first attempt
        score1 = Score(
            username="ac_attempt_count",
            user_id=user.id,
            total_score=60,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score1)
        temp_db.commit()
        
        assert ExamService.get_completed_assessment_count(user.id) == 1
        assert ExamService.get_next_attempt_number(user.id) == 2

    def test_ac_retake_attempt_blocked(self, temp_db):
        """
        Acceptance Criteria: Retake attempt → Blocked.
        
        When a user tries to retake an assessment after completion,
        the attempt should be blocked.
        """
        user = User(username="ac_blocked", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Complete first assessment
        score = Score(
            username="ac_blocked",
            user_id=user.id,
            total_score=90,
            status="completed",
            attempt_number=1,
            timestamp=datetime.now(UTC).isoformat()
        )
        temp_db.add(score)
        temp_db.commit()
        
        # Try to retake - should be blocked
        is_allowed, message = ExamService.check_retake_allowed(user.id)
        assert is_allowed is False
        assert "already completed" in message.lower() or "not allowed" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
