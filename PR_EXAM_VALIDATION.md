# PR: Enforce API Answer Validation — Issue 6.5

## Summary

This PR engineers formal Pydantic schema-level validation for the exam submission
pathway. Before this change, nothing at the FastAPI perimeter prevented a malicious
client from sending duplicate `question_id` values or arbitrarily short payloads,
which could corrupt analytical scores or trigger partial ML logic.

---

## Problem Statement

| Attack Vector | Before this PR | After this PR |
|---|---|---|
| POST with `[{q_id:5, val:3}, {q_id:5, val:4}]` | Accepted silently | **422 Unprocessable Entity** |
| POST with 3 answers for a 20-question exam | Accepted silently | **422 EXAM_INCOMPLETE** |
| POST with out-of-range `value` (0 or 6) | Accepted silently | **422 field validation error** |

---

## Files Changed

### `backend/fastapi/api/schemas/__init__.py`

**Added `AnswerSubmit`** — atomic answer unit with Pydantic field constraints:
- `question_id: int` (ge=1) — prevents zero/negative IDs
- `value: int` (ge=1, le=5) — enforces Likert 1-5 range

**Added `ExamSubmit`** — the full batch payload schema with:
- `session_id: str` (min_length=1)
- `answers: List[AnswerSubmit]` (min_length=1) — rejects empty submissions
- `is_draft: bool` (default=False) — draft submissions skip completeness check
- `@model_validator(mode='after') check_question_uniqueness` — detects and reports all duplicate `question_id` values **before any DB write**

### `backend/fastapi/api/routers/exams.py`

**Added `POST /api/v1/exams/submit`** with two-layer validation architecture:

```
Layer 1 — Pydantic model_validator (synchronous, schema-level)
   ↓ duplicate question_ids → HTTP 422 (before function body runs)

Layer 2 — Router completeness check (async-safe DB lookup)
   ↓ is_draft=False AND count(answers) != count(active_questions)
   ↓ → HTTP 422 with EXAM_INCOMPLETE error code
   
   ↓ Both checks pass
   ↓ → Responses persisted via ExamService.save_response()
   ↓ → 201 Accepted
```

The completeness check lives in the router (not inside the Pydantic validator)
to avoid async context issues when making database queries inside model validators.

### `backend/fastapi/tests/unit/test_exam_validation.py`

13 pure-Pydantic unit tests (no live DB required, 0.24s runtime):

| Test Class | # Tests | Coverage |
|---|---|---|
| `TestAnswerSubmit` | 4 | Field range bounds (value, question_id) |
| `TestExamSubmitDuplicateDetection` | 5 | Various duplicate patterns + draft flag |
| `TestExamSubmitStructural` | 4 | Empty answers, missing session_id, defaults |

---

## Acceptance Criteria Verification

- [x] **Duplicate question_ids rejected with 422** — `TestExamSubmitDuplicateDetection::test_single_duplicate_rejected`
- [x] **Saturated duplicate attack rejected** — `TestExamSubmitDuplicateDetection::test_saturated_duplicate_payload_rejected`
- [x] **Incomplete submissions fail with verbose 422** — enforced in router (Layer 2)
- [x] **Draft flag exempts only completeness, not duplicate check** — `TestExamSubmitDuplicateDetection::test_draft_does_not_bypass_duplicate_check`
- [x] **Out-of-range answer values rejected** — `TestAnswerSubmit::test_value_below_range_rejected`, `TestAnswerSubmit::test_value_above_range_rejected`

---

## Edge Cases Handled

| Edge Case | Handling |
|---|---|
| Draft save with partial answers | `is_draft=True` skips Layer 2 completeness check |
| Draft save with duplicate answers | Still rejected by Layer 1 (unconditional) |
| All-duplicate payload (q_id=5 × 20) | All duplicated IDs reported in error message |
| Empty answers list | `min_length=1` on `answers` field → 422 |
| Negative / zero question_id | `ge=1` on `question_id` field → 422 |

---

## Testing

```bash
# Run new unit tests
python -m pytest backend/fastapi/tests/unit/test_exam_validation.py -v

# Result: 13 passed in 0.24s
```

**Manual HTTP test (per acceptance criteria):**
```json
POST /api/v1/exams/submit
{
  "session_id": "test-session",
  "answers": [
    {"question_id": 1, "value": 3},
    {"question_id": 1, "value": 4}
  ]
}

→ HTTP 422 Unprocessable Entity
{
  "detail": [
    {
      "type": "value_error",
      "msg": "Value error, Submitted payload contains duplicate question answers
              for question_id(s): [1].  Each question may only be answered once.",
      "loc": ["body"]
    }
  ]
}
```
