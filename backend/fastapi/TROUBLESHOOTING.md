# Backend Troubleshooting Guide

This guide documents common issues encountered when setting up the FastAPI backend and their solutions.

## Quick Start Checklist

Before running the backend, ensure:

- [ ] Virtual environment is activated
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Additional dependencies: `pip install python-multipart pydantic[email]`
- [ ] Main app database exists at `../../data/soulsense.db`
- [ ] Python version 3.10+ (tested on 3.14)

## Common Issues & Solutions

### 1. ModuleNotFoundError: No module named 'app.db'

**Error:**

```
ModuleNotFoundError: No module named 'app.db'
```

**Cause:** Backend routers were importing from the main app's `app.db` module which doesn't exist in the backend context.

**Solution:** Use backend's `db_service.get_db()` instead:

```python
# ❌ Wrong
from app.db import get_session

# ✅ Correct
from ..services.db_service import get_db
```

**Files affected:**

- `app/routers/users.py`
- `app/routers/profiles.py`
- `app/routers/auth.py`

---

### 2. ModuleNotFoundError: No module named 'app.auth'

**Error:**

```
ModuleNotFoundError: No module named 'app.auth'
```

**Cause:** Backend was trying to import `AuthManager` from main app's `app.auth` module.

**Solution:** Implement password hashing directly using bcrypt:

```python
# ❌ Wrong
from app.auth import AuthManager
auth_manager = AuthManager()
password_hash = auth_manager.hash_password(password)

# ✅ Correct
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
```

**Files affected:**

- `app/routers/auth.py`
- `app/services/user_service.py`

---

### 3. ModuleNotFoundError: No module named 'app.constants'

**Error:**

```
ModuleNotFoundError: No module named 'app.constants'
```

**Cause:** Questions router was importing VERSION from main app's constants.

**Solution:** Define constants locally in the backend:

```python
# ❌ Wrong
from app.constants import VERSION

# ✅ Correct
VERSION = "1.0.0"
```

**Files affected:**

- `app/routers/questions.py`

---

### 4. ImportError: cannot import name 'Base' from 'app.models'

**Error:**

```
ImportError: cannot import name 'Base' from 'app.models' (unknown location)
```

**Cause:** Python couldn't resolve the import path from backend to main app's models.

**Solution:** Use `importlib` for explicit module loading in `db_service.py`:

```python
import os
import importlib.util
import sys

# Get absolute path to SOUL_SENSE_EXAM/app/models.py
current_dir = os.path.dirname(__file__)
models_path = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..', 'app', 'models.py'))

# Load the models module
spec = importlib.util.spec_from_file_location("app.models", models_path)
models_module = importlib.util.module_from_spec(spec)
sys.modules['app.models'] = models_module
spec.loader.exec_module(models_module)

# Import the classes we need
Base = models_module.Base
Score = models_module.Score
# ... etc
```

**Files affected:**

- `app/services/db_service.py`

---

### 5. Missing Schema Classes

**Error:**

```
ImportError: cannot import name 'AssessmentListResponse' from 'app.models.schemas'
```

**Cause:** Schema definitions were incomplete or missing.

**Solution:** Ensure all required schemas are defined in `app/models/schemas.py`:

- `AssessmentListResponse`
- `AssessmentDetailResponse`
- `AssessmentStatsResponse`
- `QuestionListResponse`
- `QuestionResponse`
- `QuestionCategoryResponse`

**Files affected:**

- `app/models/schemas.py`

---

### 6. Missing python-multipart Dependency

**Error:**

```
You can install "python-multipart" to be able to use form data
```

**Cause:** OAuth2 password flow requires form data parsing.

**Solution:**

```bash
pip install python-multipart
```

---

### 7. Missing pydantic[email] Dependency

**Error:**

```
ImportError: email-validator is not installed
```

**Cause:** Email validation in schemas requires email-validator package.

**Solution:**

```bash
pip install pydantic[email]
```

---

### 8. Missing JWT Configuration

**Error:**

```
AttributeError: 'Settings' object has no attribute 'jwt_secret_key'
```

**Cause:** JWT settings were not defined in config.

**Solution:** Add to `app/config.py`:

```python
import secrets

class Settings(BaseSettings):
    # ... existing settings ...

    # JWT configuration
    jwt_secret_key: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
```

**Files affected:**

- `app/config.py`

---

### 9. Missing Database Configuration

**Error:**

```
AttributeError: 'Settings' object has no attribute 'database_url'
```

**Cause:** Database settings were not defined in config.

**Solution:** Add to `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Database configuration
    database_type: str = "sqlite"
    database_url: str = "sqlite:///../../data/soulsense.db"
```

**Files affected:**

- `app/config.py`

---

## Complete Setup Steps

1. **Install all dependencies:**

```bash
cd backend/fastapi
pip install -r requirements.txt
pip install python-multipart pydantic[email]
```

2. **Verify database exists:**

```bash
# From SOUL_SENSE_EXAM directory
python -m scripts.setup_dev
```

3. **Start the backend:**

```bash
cd backend/fastapi
python start_server.py
```

4. **Verify all routers are loaded:**
   Check the startup message for:

```
📋 Registered routers: health, auth, users, profiles, assessments, questions, analytics
```

## Testing the Backend

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{ "status": "ok" }
```

### API Documentation

Visit: http://127.0.0.1:8000/docs

### Register a User

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

## Architecture Notes

### Database Sharing

The backend shares the same SQLite database with the main desktop application:

```
SOUL_SENSE_EXAM/
├── data/
│   └── soulsense.db  ← Shared database
├── app/              ← Main desktop app
│   └── models.py     ← Database models
└── backend/fastapi/  ← API backend
    └── app/
        └── services/
            └── db_service.py  ← Imports from main app
```

### Import Strategy

- Backend imports database models from main app using `importlib`
- Backend implements its own authentication logic (bcrypt)
- Backend defines its own Pydantic schemas
- Backend uses its own dependency injection (`get_db()`)

## Python Version Compatibility

Tested on:

- ✅ Python 3.14
- ✅ Python 3.10+

Known issues:

- Some packages (Pillow, matplotlib) may need version adjustments for Python 3.14
- Use flexible version constraints in requirements.txt

## Getting Help

If you encounter issues not covered here:

1. Check the main walkthrough: `C:\Users\Rohan Rathod\.gemini\antigravity\brain\...\walkthrough.md`
2. Review the implementation plan for architecture details
3. Check FastAPI logs for detailed error messages
4. Verify all import paths are correct for your environment
