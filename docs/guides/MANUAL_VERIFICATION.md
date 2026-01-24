# Manual Verification Guide

Use this guide to verify that the application and its components are working correctly after the file reorganization.

## 1. Verify Main Desktop App

**Goal**: Ensure the main application launches and connects to the database.

1. Open your terminal in the project root (`SOUL_SENSE_EXAM/`).
2. Run the application:
   ```bash
   python -m app.main
   ```
   _OR if you use the batch file:_
   ```bash
   run.bat
   ```
3. **Check**:
   - Does the menu appear?
   - Can you select "Option 7: Version" (if available) or "Option 1: Start New Exam"?
   - If it works, the **App Core** is healthy.

## 2. Verify Backend API

**Goal**: Ensure the FastAPI server starts and endpoints are accessible.

1. Open a new terminal.
2. Navigate to the backend folder (optional, or run from root):
   ```bash
   # Option A: From Root
   python backend/fastapi/start_server.py
   ```
3. **Check**:
   - Look for `Uvicorn running on http://0.0.0.0:8000`.
   - Open browser to: [http://localhost:8000/docs](http://localhost:8000/docs).
   - If the Swagger UI loads, the **Backend** is healthy.

## 3. Verify Utility Scripts

**Goal**: Ensure moved scripts can still find the `app` module.

1. Run the database seeder (safe, checks for existing users):

   ```bash
   python scripts/setup/seed_db.py
   ```

   - **Success**: Output starts with `Seeding database...` or `Successfully seeded...`.
   - **Failure**: `ModuleNotFoundError: No module named 'app'`.

2. Run the score checker:
   ```bash
   python scripts/verification/check_scores.py
   ```

   - **Success**: Output shows `Total scores in database: ...`.

## 4. Verify Database Path

**Goal**: Ensure the database is found at `data/soulsense.db`.

1. Run the schema migrator:
   ```bash
   python scripts/setup/migrate_schema.py
   ```

   - **Success**: `Migration completed.`
   - **Failure**: `Database ... not found`.

## Trouble?

If you see `ModuleNotFoundError`, make sure you are running commands from the **Project Root** (`SOUL_SENSE_EXAM/`), not inside `scripts/`.
