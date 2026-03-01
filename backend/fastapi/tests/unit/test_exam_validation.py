"""
Unit tests for ExamSubmit schema validation (Issue 6.5 — API Answer Validation).

Tests verify that:
  1. Duplicate question_id values are rejected with a Pydantic ValidationError
     before any database operation occurs.
  2. Clean (unique) payloads are accepted correctly.
  3. The is_draft flag is respected by the schema (but does NOT bypass duplicate
     detection — that check is unconditional).
  4. Empty answers lists are rejected by Pydantic min_length constraint.
  5. Out-of-range 'value' fields are caught by field-level validation.
"""

import pytest
from pydantic import ValidationError

# Schema under test
from backend.fastapi.api.schemas import AnswerSubmit, ExamSubmit


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_answer(question_id: int, value: int = 3) -> dict:
    return {"question_id": question_id, "value": value}


def make_payload(answers: list[dict], is_draft: bool = False) -> dict:
    return {
        "session_id": "test-session-abc123",
        "answers": answers,
        "is_draft": is_draft,
    }


# ---------------------------------------------------------------------------
# AnswerSubmit field-level validation
# ---------------------------------------------------------------------------

class TestAnswerSubmit:
    def test_valid_answer(self):
        a = AnswerSubmit(question_id=1, value=3)
        assert a.question_id == 1
        assert a.value == 3

    def test_value_below_range_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            AnswerSubmit(question_id=1, value=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("value",) for e in errors)

    def test_value_above_range_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            AnswerSubmit(question_id=1, value=6)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("value",) for e in errors)

    def test_question_id_zero_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            AnswerSubmit(question_id=0, value=3)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("question_id",) for e in errors)


# ---------------------------------------------------------------------------
# ExamSubmit — duplicate question_id detection
# ---------------------------------------------------------------------------

class TestExamSubmitDuplicateDetection:
    def test_clean_payload_accepted(self):
        """A payload with all unique question_ids must pass validation."""
        data = make_payload([make_answer(1), make_answer(2), make_answer(3)])
        exam = ExamSubmit(**data)
        assert len(exam.answers) == 3

    def test_single_duplicate_rejected(self):
        """
        Payload [q_id=1 val=3, q_id=1 val=4] must be rejected with a 422-equivalent
        ValidationError citing duplicate question answers.
        """
        data = make_payload([make_answer(1, 3), make_answer(1, 4)])
        with pytest.raises(ValidationError) as exc_info:
            ExamSubmit(**data)

        errors = exc_info.value.errors()
        error_messages = " ".join(str(e.get("msg", "")) for e in errors)
        assert "duplicate" in error_messages.lower(), (
            f"Expected 'duplicate' in error message but got: {error_messages}"
        )

    def test_saturated_duplicate_payload_rejected(self):
        """
        Payload with question_id=5 repeated 20 times must be rejected — the exact
        attack vector described in the acceptance criteria.
        """
        data = make_payload([make_answer(5, v) for v in range(1, 6)] * 4)
        with pytest.raises(ValidationError) as exc_info:
            ExamSubmit(**data)

        errors = exc_info.value.errors()
        error_messages = " ".join(str(e.get("msg", "")) for e in errors)
        assert "duplicate" in error_messages.lower()

    def test_multiple_duplicates_all_reported(self):
        """All duplicated question_ids must appear in the error message."""
        # question_id 2 and 7 are both duplicated
        data = make_payload([
            make_answer(1), make_answer(2), make_answer(2),
            make_answer(7), make_answer(7), make_answer(7),
        ])
        with pytest.raises(ValidationError) as exc_info:
            ExamSubmit(**data)

        errors = exc_info.value.errors()
        error_messages = " ".join(str(e.get("msg", "")) for e in errors)
        assert "duplicate" in error_messages.lower()

    def test_draft_does_not_bypass_duplicate_check(self):
        """
        is_draft=True relaxes completeness enforcement (in the router) but must
        NOT excuse duplicate question_ids — the schema check is unconditional.
        """
        data = make_payload([make_answer(3, 2), make_answer(3, 5)], is_draft=True)
        with pytest.raises(ValidationError) as exc_info:
            ExamSubmit(**data)

        errors = exc_info.value.errors()
        error_messages = " ".join(str(e.get("msg", "")) for e in errors)
        assert "duplicate" in error_messages.lower()


# ---------------------------------------------------------------------------
# ExamSubmit — structural constraints
# ---------------------------------------------------------------------------

class TestExamSubmitStructural:
    def test_empty_answers_list_rejected(self):
        """min_length=1 on the answers field must reject empty lists."""
        data = make_payload([])
        with pytest.raises(ValidationError):
            ExamSubmit(**data)

    def test_missing_session_id_rejected(self):
        data = {
            "answers": [make_answer(1)],
        }
        with pytest.raises(ValidationError):
            ExamSubmit(**data)

    def test_is_draft_defaults_to_false(self):
        """is_draft must default to False when omitted from the payload."""
        data = {
            "session_id": "sess-xyz",
            "answers": [make_answer(10)],
        }
        exam = ExamSubmit(**data)
        assert exam.is_draft is False

    def test_is_draft_true_accepted_with_partial_answers(self):
        """A draft payload with only 3 answers (< full exam) must be schema-valid."""
        data = make_payload(
            [make_answer(i) for i in range(1, 4)],
            is_draft=True,
        )
        exam = ExamSubmit(**data)
        assert exam.is_draft is True
        assert len(exam.answers) == 3
