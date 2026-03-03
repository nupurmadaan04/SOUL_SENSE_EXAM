# 🚀 Pull Request: Linux OOM Killer Vulnerability Fix

## 📝 Description
This PR addresses potential container termination by the Linux OOM Killer under high memory load by implementing strict resource limits, orchestration probes, and memory-safe background worker recycling.

- **Objective**: Ensure predictable memory control and prevent node destabilization by enforcing resource boundaries.
- **Context**: Lack of memory limits and process recycling (especially during heavy ML inference or batch tasks) can lead to kernel-level process termination and service downtime.

---

## 🔧 Type of Change
- [ ] 🐛 **Bug Fix**
- [ ] ✨ **New Feature**
- [ ] 💥 **Breaking Change**
- [ ] ♻️ **Refactor**
- [ ] 📝 **Documentation Update**
- [x] 🚀 **Performance / Security**

---

## 🧪 How Has This Been Tested?
I have implemented configuration and orchestration logic designed for resilient memory management.

- [x] **Kubernetes Simulation**: Verified liveness and readiness probe logic via `/health` and `/ready` endpoints.
- [x] **Memory Profiling**: Added `psutil` integration to monitor RSS memory usage in real-time.
- [x] **Worker Stability**: Configured `worker_max_tasks_per_child` to release memory periodically in long-running processes.

---

## ✅ Checklist
- [x] My code follows the project's style guidelines.
- [x] I have performed a self-review of my code.
- [x] I have added/updated necessary comments or documentation.
- [x] My changes generate no new warnings or linting errors.
- [x] Existing tests pass with my changes.
- [x] I have verified this PR on the latest `linux-oom-killer` branch.

---

## 📝 Additional Notes
- Added `resources.limits` and `resources.requests` in `backend/fastapi/k8s/` to enforce memory boundaries.
- Implemented `worker_max_tasks_per_child=100` in `celery_app.py` to mitigate memory leaks in background tasks.
- Introduced `StartupProbe` to prevent premature container restarts during heavy initialization (e.g., NLTK VADER loading).
- Updated `requirements.txt` with `psutil` for enhanced system resource monitoring.
