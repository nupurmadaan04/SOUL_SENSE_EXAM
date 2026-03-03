import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend", "fastapi"))

try:
    from api.models import User, Score, Response, ExamSession, Question, UserSession
    print("Models imported successfully")
except Exception as e:
    print(f"Error importing models: {e}")
    import traceback
    traceback.print_exc()

try:
    from api.services.exam_service import ExamService
    print("ExamService imported successfully")
except Exception as e:
    print(f"Error importing ExamService: {e}")
    import traceback
    traceback.print_exc()
