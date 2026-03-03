# 🚀 Pull Request: Mitigate Business Logic Abuse in Exam Flow

## 📝 Description
This PR implements a robust server-side state machine and session validation layer for the Soul Sense exam workflow. It addresses critical business logic vulnerabilities where users could bypass the intended sequence of steps, skip questions, or manipulate timers to gain unfair advantages.

- **Objective**: Ensure that all exam submissions follow a valid, time-limited, and sequence-verified workflow.
- **Context**: Previously, the system lacked a server-side state tracker for exam sessions. Attackers could theoretically submit a final score directly without answering questions or circumvent the 60-minute time limit.

---

## 🔧 Type of Change
Mark the relevant options:
- [x] 🐛 **Bug Fix**: A non-breaking change which fixes an issue.
- [x] ✨ **New Feature**: A non-breaking change which adds functionality.
- [ ] 💥 **Breaking Change**: A fix or feature that would cause existing functionality to not work as expected.
- [ ] ♻️ **Refactor**: Code improvement (no functional changes).
- [x] 📝 **Documentation Update**: Changes to README, comments, or external docs.
- [x] 🚀 **Performance / Security**: Improvements to app speed or security posture.

---

## 🧪 How Has This Been Tested?
I verified the changes using manual API interaction and simulated exploit attempts:

- [x] **Unit Tests**: Verified state transition logic in `ExamService`.
- [x] **Integration Tests**: Tested `/api/v1/exams/start`, `/api/v1/exams/submit`, and `/api/v1/exams/{session_id}/complete` in sequence.
- [x] **Manual Verification**: 
    - Attempted to call `/complete` without a session (Rejected with `404`).
    - Attempted to call `/complete` immediately after `/start` (Rejected with `WFK001` - Invalid State).
    - Verified session expiry logic rejects interactions after 60 minutes.

---

## 📸 Screenshots / Recordings (if applicable)
N/A (Backend Security Implementation)

---

## ✅ Checklist
Confirm you have completed the following steps:
- [x] My code follows the project's style guidelines.
- [x] I have performed a self-review of my code.
- [x] I have added/updated necessary comments or documentation.
- [x] My changes generate no new warnings or linting errors.
- [x] Existing tests pass with my changes.
- [x] I have verified this PR on the latest `main` branch.

---

## 📝 Additional Notes
- The new `ExamSession` table is required. Run migrations before testing.
- The `WFK_*` error codes provide detailed feedback to the frontend for handling expired or invalid sessions gracefully.
