# 🚀 Pull Request Template

## 📝 Description

Provide a clear and concise description of what this PR does. Mention any related issues using the `Fixes #` or `Closes #` syntax.

- **Objective**: What is the main goal of these changes?
- **Context**: Why are these changes being made?

---

## 🔧 Type of Change

Mark the relevant options:

- [ ] 🐛 **Bug Fix**: A non-breaking change which fixes an issue.
- [ ] ✨ **New Feature**: A non-breaking change which adds functionality.
- [ ] 💥 **Breaking Change**: A fix or feature that would cause existing functionality to not work as expected.
- [ ] ♻️ **Refactor**: Code improvement (no functional changes).
- [ ] 📝 **Documentation Update**: Changes to README, comments, or external docs.
- [ ] 🚀 **Performance / Security**: Improvements to app speed or security posture.

---

## 🧪 How Has This Been Tested?

Describe the tests you ran to verify your changes. Include steps to reproduce if necessary.

- [ ] **Unit Tests**: Ran `pytest` or `npm test`.
- [ ] **Integration Tests**: Verified API endpoints or end-to-end flows.
- [ ] **Manual Verification**: Briefly describe manual steps taken.

---

## 📸 Screenshots / Recordings (if applicable)

Add any relevant visual evidence (screenshots, GIFs, or videos) to help reviewers understand the change.

---

## ✅ Checklist

Confirm you have completed the following steps:

- [ ] My code follows the project's style guidelines.
- [ ] I have performed a self-review of my code.
- [ ] I have added/updated necessary comments or documentation.
- [ ] My changes generate no new warnings or linting errors.
- [ ] Existing tests pass with my changes.
- [ ] I have verified this PR on the latest `main` branch.

---

## � Security Checklist (required for security-related PRs)

> **Reference:** [docs/SECURITY_HARDENING_CHECKLIST.md](docs/SECURITY_HARDENING_CHECKLIST.md)

- [ ] `python scripts/check_security_hardening.py` passes — all required checks ✅
- [ ] Relevant rows in the [Security Hardening Checklist](docs/SECURITY_HARDENING_CHECKLIST.md) are updated
- [ ] No new secrets committed to the repository
- [ ] New endpoints have rate limiting and input validation
- [ ] Security-focused review requested from at least one maintainer

<details>
<summary>Paste hardening status output here</summary>

```
# Run: python scripts/check_security_hardening.py
```

</details>

---

## �📝 Additional Notes

Add any other context, edge cases, or "gotchas" that reviewers should be aware of.
