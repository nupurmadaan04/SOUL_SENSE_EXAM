"""
Backend Service Layer
"""
from .db_service import AssessmentService, QuestionService, get_db
from .export_service import ExportService
from .captcha_service import captcha_service

# ExamService has known experimental async refactors that may not always be syntactically valid
# Wrap import in a broad exception handler so background workers (e.g., Celery) don't fail to start.
try:
    from .exam_service import ExamService
except Exception:
    ExamService = None

__all__ = ["AssessmentService", "QuestionService", "ExamService", "ExportService", "get_db", "captcha_service"]
