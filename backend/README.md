# FastAPI Backend - Soul Sense EQ Test

A comprehensive REST API for the Soul Sense Emotional Intelligence Assessment Platform.

## 🚀 Quick Start

```bash
# 1. Install dependencies
cd backend/fastapi
pip install -r requirements.txt
pip install python-multipart pydantic[email]

# 2. Ensure main app database is set up
cd ../..
python -m scripts.setup_dev

# 3. Start the backend server
cd backend/fastapi
python start_server.py
```

The API will be available at:

- **API**: http://127.0.0.1:8000
- **Docs**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 📋 Available Routers

| Router          | Prefix              | Description                                                       |
| --------------- | ------------------- | ----------------------------------------------------------------- |
| **health**      | `/`                 | Health checks and API status                                      |
| **auth**        | `/auth`             | User registration and JWT authentication                          |
| **users**       | `/api/users`        | User management (CRUD)                                            |
| **profiles**    | `/api/profiles`     | User profiles (settings, medical, personal, strengths, emotional) |
| **assessments** | `/api/assessments`  | Assessment management and statistics                              |
| **questions**   | `/api/questions`    | Question bank and categories                                      |
| **analytics**   | `/api/v1/analytics` | Analytics, trends, and benchmarks                                 |
| **journal**     | `/api/v1/journal`   | Journal entries, analytics, and prompts                           |

## 🔧 Configuration

### Environment Variables

Create a `.env` file in `backend/fastapi/`:

```env
# App Settings
APP_ENV=development
HOST=127.0.0.1
PORT=8000
DEBUG=true

# JWT Settings (auto-generated if not provided)
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Database (shares with main app)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///../../data/soulsense.db
```

## 📦 Dependencies

### Required

- `fastapi>=0.95.0` - Web framework
- `uvicorn[standard]>=0.22.0` - ASGI server
- `sqlalchemy>=2.0.0` - Database ORM
- `pydantic>=2.0.0` - Data validation
- `pydantic-settings>=2.0.0` - Settings management
- `python-dotenv>=1.0.0` - Environment variables
- `python-multipart` - Form data parsing
- `pydantic[email]` - Email validation
- `bcrypt` - Password hashing
- `python-jose[cryptography]` - JWT tokens

### Shared with Main App

The backend uses the main app's database models from `app/models.py`.

## 🏗️ Architecture

```
backend/fastapi/
├── app/                     # Application Source Code
│   ├── main.py              # FastAPI app initialization
│   ├── routers/             # API endpoints
│   └── services/            # Business logic
├── docs/                    # Documentation Center
│   ├── api/                 # API Specs, Versioning, Postman
│   ├── guides/              # Quickstart, Troubleshooting
│   ├── reports/             # Test Results, Implementation Summaries
│   └── architecture/        # Deployment, Design Docs
├── tests/                   # Test Suite
│   ├── integration/         # full_api_test.py
│   ├── unit/                # test_api.py, test_crud_api.py
│   └── postman/             # Postman Collection & Environment
├── scripts/                 # Developer & OPS Scripts
│   ├── deployment/          # deploy-*.sh
│   └── tools/               # patch_db.py, debug_auth.py
├── start_server.py          # Server startup script
└── requirements.txt         # Dependencies
```

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Register a New User

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

### Login

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

Response:

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Use Token in Requests

```bash
curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer eyJhbGc..."
```

## 📊 Database

The backend shares the SQLite database with the main desktop application:

- **Location**: `SOUL_SENSE_EXAM/data/soulsense.db`
- **Models**: Imported from `app/models.py`
- **Migrations**: Managed by Alembic in the main app

### Database Models Used

- `User` - User accounts
- `UserSettings` - User preferences
- `MedicalProfile` - Medical information
- `PersonalProfile` - Personal information
- `UserStrengths` - User strengths and goals
- `UserEmotionalPatterns` - Emotional patterns
- `Score` - Assessment scores
- `Response` - Assessment responses
- `Question` - Question bank
- `QuestionCategory` - Question categories
- `JournalEntry` - Journal entries with sentiment analysis

## 🧪 Testing

### Manual Testing

Use the interactive API documentation at http://127.0.0.1:8000/docs

### Automated Tests

```bash
# Run API tests
python tests/unit/test_api.py

# Run CRUD tests
python tests/unit/test_crud_api.py

# Run Full API Verification (Health, Auth, Questions, Journal)
python tests/integration/full_api_test.py
```

### 🔄 Database Patching

If you are updating to incorporate the new Journaling and Questions improvements, you must patch the existing database to include the new columns and schema adjustments:

```bash
cd backend/fastapi
python scripts/tools/patch_db.py
```

## 🚨 Troubleshooting

If you encounter any issues, **please read [TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)** first!

Common issues:

- Missing dependencies (`python-multipart`, `pydantic[email]`)
- Import errors (use backend's `db_service.get_db()`)
- Configuration errors (JWT settings, database URL)
- Python version compatibility (tested on 3.10+, 3.14)

## 🤝 Contributing

When adding new routers or modifying existing ones:

1. **Import from backend modules**, not main app:

   ```python
   # ✅ Correct
   from ..services.db_service import get_db
   from ..models.schemas import YourSchema

   # ❌ Wrong
   from app.db import get_session
   from app.auth import AuthManager
   ```

2. **Define all required schemas** in `app/models/schemas.py`

3. **Add router to `main.py`**:

   ```python
   from .routers import your_router
   app.include_router(your_router.router, prefix="/api/your-route", tags=["your-tag"])
   ```

4. **Update this README** with new endpoints

5. **Test thoroughly** using the `/docs` interface

## 📝 API Examples

### Get All Questions

```bash
curl http://127.0.0.1:8000/api/questions/?limit=10
```

### Get Assessment Statistics

```bash
curl http://127.0.0.1:8000/api/assessments/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create User Settings

```bash
curl -X POST http://127.0.0.1:8000/api/profiles/settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"theme": "dark", "question_count": 15}'
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [JWT.io](https://jwt.io/) - JWT debugger

## 📄 License

Same as the main Soul Sense EQ Test project.
