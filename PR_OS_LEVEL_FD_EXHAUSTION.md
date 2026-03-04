# 🚀 Pull Request: OS-Level File Descriptor Exhaustion Fix

## 📝 Description
This PR addresses potential `EMFILE` errors and service crashes under load caused by OS-level file descriptor exhaustion. It converts synchronous database operations to asynchronous flows to ensure deterministic cleanup of database connections, even during exception scenarios or high concurrency bursts.

- **Objective**: Ensure deterministic cleanup of all file descriptors (DB connections) to prevent FastAPI and Celery process crashes under load.
- **Context**: Synchronous SQLAlchemy operations within asynchronous contexts can cause thread starvation and fail to release database connections properly during mid-request crashes or background task failures, leading to file descriptor leaks.

---

## 🔧 Type of Change
- [x] 🐛 **Bug Fix**
- [ ] ✨ **New Feature**
- [ ] 💥 **Breaking Change**
- [x] ♻️ **Refactor**
- [ ] 📝 **Documentation Update**
- [x] 🚀 **Performance / Security**

---

## 🧪 How Has This Been Tested?
I have refactored the core services and API routers to fully leverage Python's asynchronous I/O and `AsyncSession` for predictable connection handling.

- [x] **Concurrency & I/O Flow**: Validated via code inspection that all I/O-bound database calls use `await db.execute()` instead of blocking synchronous `.query()` operations.
- [x] **Deterministic Resource Cleanup**: Ensured `AsyncSession` depends on the application's connection lifecycle appropriately, eliminating manually unmanaged `with SessionLocal():` blocks within async endpoints.
- [x] **End-to-End Async Conversion**: Re-wired FastAPI routers to correctly `await` deeply nested service calls (`ExportService`, `AnalyticsService`, `GamificationService`, etc.).

---

## ✅ Checklist
- [x] My code follows the project's style guidelines.
- [x] I have performed a self-review of my code.
- [x] I have added/updated necessary comments or documentation.
- [x] My changes generate no new warnings or linting errors.
- [x] I have verified this PR on the latest `os-level-file` branch.

---

## 📝 Additional Notes
- **Core Services Refactored**: Fully converted `ExportServiceV2`, `ExportService`, `GamificationService`, `DeepDiveService`, `SettingsSyncService`, and `JournalService` to use async architectures (`select`, `execute`, `scalar_one_or_none`).
- **Routers Overhauled**: Updated dependency injection across `/gamification`, `/export`, `/analytics`, `/deep-dive`, and `/health` to require `AsyncSession` exclusively.
- **Prevented Deadlocks**: Eradicated remaining synchronous SQLAlchemy access in FastApi's event loops, preventing thread pool exhaustion during export/analytics heavy lifting.
