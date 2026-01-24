# Assessment and Question APIs

RESTful API endpoints for Soul Sense EQ Test assessments and questions.

## Features

✅ **Read-only endpoints** - Safe for client applications  
✅ **Versioned question sets** - API version tracking  
✅ **No client-side logic dependency** - Server-side processing  
✅ **Comprehensive filtering** - By age, category, username, etc.  
✅ **Pagination support** - Efficient data retrieval  
✅ **Statistical endpoints** - Aggregate data analysis  

## Installation

1. Install dependencies:
```bash
cd backend/fastapi
pip install -r requirements.txt
```

2. Configure environment (optional):
```bash
# Create .env file in project root
SOULSENSE_DATABASE_TYPE=sqlite
SOULSENSE_JWT_SECRET_KEY=your-secret-key
```

3. Run the API server:
```bash
# From backend/fastapi directory
uvicorn app.main:app --reload --port 8000

# Or from project root
cd backend/fastapi
python -m uvicorn app.main:app --reload
```

## API Endpoints

### Health Check
- `GET /health` - Check API health status

### Assessments (Scores)

#### List Assessments
```http
GET /api/v1/assessments?username=john&page=1&page_size=10
```

**Query Parameters:**
- `username` (optional): Filter by username
- `age_group` (optional): Filter by age group (e.g., "18-25")
- `page` (default: 1): Page number
- `page_size` (default: 10, max: 100): Items per page

**Response:**
```json
{
  "total": 45,
  "assessments": [
    {
      "id": 1,
      "username": "john",
      "total_score": 35,
      "sentiment_score": 0.75,
      "is_rushed": false,
      "is_inconsistent": false,
      "age": 25,
      "detailed_age_group": "18-25",
      "timestamp": "2026-01-22T10:30:00"
    }
  ],
  "page": 1,
  "page_size": 10
}
```

#### Get Assessment Details
```http
GET /api/v1/assessments/{assessment_id}
```

**Response:**
```json
{
  "id": 1,
  "username": "john",
  "total_score": 35,
  "sentiment_score": 0.75,
  "reflection_text": "I felt calm and focused...",
  "is_rushed": false,
  "is_inconsistent": false,
  "age": 25,
  "detailed_age_group": "18-25",
  "timestamp": "2026-01-22T10:30:00",
  "responses_count": 10
}
```

#### Get Assessment Statistics
```http
GET /api/v1/assessments/stats?username=john
```

**Response:**
```json
{
  "total_assessments": 45,
  "average_score": 34.5,
  "highest_score": 40,
  "lowest_score": 28,
  "average_sentiment": 0.68,
  "age_group_distribution": {
    "18-25": 20,
    "26-35": 15,
    "36-50": 10
  }
}
```

### Questions

#### Get Question Set
```http
GET /api/v1/questions?age=25&limit=20
```

**Query Parameters:**
- `age` (optional): Filter questions appropriate for this age
- `category_id` (optional): Filter by category
- `limit` (default: 100, max: 200): Maximum questions
- `skip` (default: 0): Number to skip (pagination)
- `active_only` (default: true): Only active questions

**Response:**
```json
{
  "version": "1.0.0",
  "total_questions": 45,
  "questions": [
    {
      "id": 1,
      "question_text": "How well do you handle stress?",
      "category_id": 1,
      "difficulty": 2,
      "min_age": 18,
      "max_age": 120,
      "weight": 1.0,
      "tooltip": "Think about recent stressful situations",
      "is_active": true
    }
  ],
  "age_range": {
    "min": 18,
    "max": 65
  }
}
```

#### Get Questions by Age
```http
GET /api/v1/questions/by-age/25?limit=10
```

**Response:** Array of `QuestionResponse` objects

#### Get Specific Question
```http
GET /api/v1/questions/{question_id}
```

#### List Question Categories
```http
GET /api/v1/questions/categories
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Self-Awareness"
  },
  {
    "id": 2,
    "name": "Emotional Regulation"
  }
]
```

### Settings Synchronization

#### Get All Settings
```http
GET /api/sync/settings
```

**Response:**
```json
[
  {
    "key": "theme",
    "value": "dark",
    "version": 1,
    "updated_at": "2026-01-23T10:30:00"
  }
]
```

#### Upsert Setting (with Conflict Detection)
```http
PUT /api/sync/settings/{key}
```

**Request Body:**
- `value` (any): The value to store
- `expected_version` (optional): Current version for optimistic locking

**Response (Standard):** `200 OK` or `201 Created` with the updated setting.

**Response (Conflict - 409):**
```json
{
  "detail": {
    "message": "Version conflict: expected 1, found 2",
    "key": "theme",
    "current_version": 2,
    "current_value": "light"
  }
}
```

#### Batch Upsert
```http
POST /api/sync/settings/batch
```

**Request Body:**
```json
{
  "settings": [
    {"key": "theme", "value": "dark"},
    {"key": "language", "value": "hi"}
  ]
}
```

---

## Interactive API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Get assessments
curl "http://localhost:8000/api/v1/assessments?page=1&page_size=5"

# Get questions for age 25
curl "http://localhost:8000/api/v1/questions?age=25&limit=10"

# Get assessment stats
curl http://localhost:8000/api/v1/assessments/stats

# Get categories
curl http://localhost:8000/api/v1/questions/categories

# Settings Sync (requires Auth)
curl -X PUT "http://localhost:8000/api/sync/settings/theme" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"value": "dark"}'
```

### Python Testing

```python
import requests

BASE_URL = "http://localhost:8000"

# Get questions for a 25-year-old
response = requests.get(f"{BASE_URL}/api/v1/questions", params={"age": 25, "limit": 10})
questions = response.json()
print(f"Found {questions['total_questions']} questions")

# Get assessment stats
response = requests.get(f"{BASE_URL}/api/v1/assessments/stats")
stats = response.json()
print(f"Average score: {stats['average_score']}")
```

## Architecture

```
backend/fastapi/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Configuration settings
│   ├── models/
│   │   └── schemas.py       # Pydantic schemas (API models)
│   ├── routers/
│   │   ├── assessments.py   # Assessment endpoints
│   │   ├── questions.py     # Question endpoints
│   │   ├── settings_sync.py # Settings Synchronization
│   │   ├── auth.py          # Authentication
│   │   └── health.py        # Health check
│   └── services/
│       ├── db_service.py    # Database operations
│       └── settings_sync_service.py # Sync operations
└── requirements.txt         # Python dependencies
```

## Data Models

### QuestionResponse
- `id`: Question ID
- `question_text`: Question text
- `category_id`: Category identifier
- `difficulty`: Difficulty level (1-5)
- `min_age`: Minimum age
- `max_age`: Maximum age
- `weight`: Scoring weight
- `tooltip`: Helpful hint
- `is_active`: Active status

### AssessmentResponse
- `id`: Assessment ID
- `username`: User identifier
- `total_score`: Total EQ score
- `sentiment_score`: NLTK sentiment score
- `is_rushed`: Rushed completion indicator
- `is_inconsistent`: Inconsistency flag
- `age`: User's age
- `detailed_age_group`: Age group classification
- `timestamp`: Completion timestamp

## Version Control

Questions are versioned using the `VERSION` constant from `app/constants.py`. The current version is included in the question set response:

```json
{
  "version": "1.0.0",
  "total_questions": 45,
  "questions": [...]
}
```

## Error Handling

Standard HTTP status codes:
- `200 OK` - Successful request
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error response format:
```json
{
  "detail": "Assessment not found"
}
```

## Future Enhancements

- [ ] Authentication/Authorization for assessment endpoints
- [ ] Rate limiting
- [ ] Caching layer
- [ ] Question recommendation engine
- [ ] Real-time assessment progress tracking
- [ ] Export endpoints (CSV, JSON)
- [ ] GraphQL support

## Related Issues

- Implements: #393 (Create Assessment and Question APIs)
- Depends on: #391

---

**Built with FastAPI** | **Database: SQLite/PostgreSQL** | **Version: 1.0.0**
