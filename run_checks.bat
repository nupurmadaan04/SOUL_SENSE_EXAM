@echo off
setlocal

echo ========================================================
echo running SOUL SENSE LOCAL QUALITY CHECKS
echo ========================================================

REM Set python path to include repo root
set PYTHONPATH=%CD%
echo [INFO] PYTHONPATH set to %PYTHONPATH%

echo.
echo [1/3] Running Type Checks (MyPy)...
python -m mypy -p backend.fastapi.api
IF %ERRORLEVEL% NEQ 0 (
    echo [FAIL] MyPy checks failed.
    exit /b %ERRORLEVEL%
)
echo [PASS] MyPy checks passed.

echo.
echo [2/3] Running Linter (Flake8)...
python -m flake8 backend/fastapi/api --count --select=E9,F63,F7,F82 --show-source --statistics
IF %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Linting failed.
    exit /b %ERRORLEVEL%
)
echo [PASS] Linter checks passed.

echo.
echo [3/3] Running Tests (Pytest)...
cd backend/fastapi
python -m pytest tests/unit/
IF %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Tests failed.
    exit /b %ERRORLEVEL%
)
echo [PASS] All tests passed.

echo.
echo ========================================================
echo [SUCCESS] ALL CHECKS PASSED! READY TO PUSH.
echo ========================================================
