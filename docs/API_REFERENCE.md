# SoulSense API Reference

## Overview

The SoulSense API is a comprehensive REST API for the SoulSense EQ Test Platform, providing endpoints for user management, assessments, journaling, analytics, and more. The API is built with FastAPI and uses JWT (JSON Web Tokens) for authentication.

## Base URL

```
https://api.soulsense.com/api/v1
```

All API endpoints are prefixed with `/api/v1`.

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the `Authorization` header as a Bearer token:

```
Authorization: Bearer <your_jwt_token>
```

### Obtaining a Token

1. Register a new user account
2. Login to receive an access token
3. Use the token in subsequent requests

Tokens expire after a configurable period (default: 24 hours).

## API Endpoints

### Authentication

#### Register User

**Endpoint:** `POST /api/v1/auth/register`

**Description:** Create a new user account.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "string",
  "created_at": "2023-01-01T00:00:00Z"
}
```

**Example (curl):**
```bash
curl -X POST "https://api.soulsense.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe", "password": "securepassword123"}'
```

**Example (Python):**
```python
import requests

url = "https://api.soulsense.com/api/v1/auth/register"
data = {"username": "johndoe", "password": "securepassword123"}
response = requests.post(url, json=data)
print(response.json())
```

#### Login

**Endpoint:** `POST /api/v1/auth/login`

**Description:** Authenticate user and receive access token.

**Request Body (Form Data):**
```
username: string
password: string
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Example (curl):**
```bash
curl -X POST "https://api.soulsense.com/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=securepassword123"
```

**Example (Python):**
```python
import requests

url = "https://api.soulsense.com/api/v1/auth/login"
data = {"username": "johndoe", "password": "securepassword123"}
response = requests.post(url, data=data)
token = response.json()["access_token"]
```

#### Get Current User

**Endpoint:** `GET /api/v1/auth/me`

**Description:** Get information about the currently authenticated user.

**Authentication:** Required (Bearer token)

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "created_at": "2023-01-01T00:00:00Z"
}
```

### User Management

#### Get Current User Info

**Endpoint:** `GET /api/v1/users/me`

**Description:** Get basic information about the current user.

**Authentication:** Required

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "created_at": "2023-01-01T00:00:00Z",
  "last_login": "2023-01-15T10:30:00Z"
}
```

#### Get Current User Details

**Endpoint:** `GET /api/v1/users/me/detail`

**Description:** Get detailed user information including profile completion status.

**Authentication:** Required

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "created_at": "2023-01-01T00:00:00Z",
  "last_login": "2023-01-15T10:30:00Z",
  "profile_complete": true,
  "assessment_count": 5
}
```

#### Update Current User

**Endpoint:** `PUT /api/v1/users/me`

**Description:** Update user information.

**Authentication:** Required

**Request Body:**
```json
{
  "username": "newusername",
  "password": "newpassword123"
}
```

**Response:** Same as GET /me

#### Delete Current User

**Endpoint:** `DELETE /api/v1/users/me`

**Description:** Delete the current user account and all associated data.

**Authentication:** Required

**Response:** 204 No Content

### Assessments

#### List Assessments

**Endpoint:** `GET /api/v1/assessments/`

**Description:** Get available assessments.

**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "EQ Assessment",
    "description": "Emotional Intelligence Test",
    "question_count": 50
  }
]
```

#### Start Assessment

**Endpoint:** `POST /api/v1/assessments/start`

**Description:** Start a new assessment session.

**Authentication:** Required

**Request Body:**
```json
{
  "assessment_id": 1
}
```

**Response:**
```json
{
  "session_id": "abc123",
  "assessment_id": 1,
  "questions": [...]
}
```

#### Submit Assessment

**Endpoint:** `POST /api/v1/assessments/{assessment_id}/submit`

**Description:** Submit completed assessment answers.

**Authentication:** Required

**Request Body:**
```json
{
  "responses": [
    {"question_id": 1, "answer": 4},
    {"question_id": 2, "answer": 3}
  ]
}
```

**Response:**
```json
{
  "assessment_id": 1,
  "score": 75,
  "completed_at": "2023-01-15T11:00:00Z"
}
```

#### Get Assessment Results

**Endpoint:** `GET /api/v1/assessments/{assessment_id}/results`

**Description:** Get detailed results for a completed assessment.

**Authentication:** Required

**Response:**
```json
{
  "assessment_id": 1,
  "score": 75,
  "percentile": 80,
  "categories": {
    "self_awareness": 78,
    "empathy": 72
  },
  "completed_at": "2023-01-15T11:00:00Z"
}
```

### Journal

#### Create Journal Entry

**Endpoint:** `POST /api/v1/journal/`

**Description:** Create a new journal entry with automatic sentiment analysis.

**Authentication:** Required

**Request Body:**
```json
{
  "content": "Today was a good day...",
  "tags": ["gratitude", "work"],
  "privacy_level": "private",
  "sleep_hours": 8,
  "energy_level": 7
}
```

**Response:**
```json
{
  "id": 1,
  "content": "Today was a good day...",
  "sentiment_score": 75,
  "word_count": 150,
  "created_at": "2023-01-15T12:00:00Z"
}
```

#### List Journal Entries

**Endpoint:** `GET /api/v1/journal/`

**Description:** Get paginated list of user's journal entries.

**Authentication:** Required

**Query Parameters:**
- `skip`: Number of entries to skip (default: 0)
- `limit`: Maximum entries to return (default: 20)
- `start_date`: Filter from date (YYYY-MM-DD)
- `end_date`: Filter to date (YYYY-MM-DD)

**Response:**
```json
{
  "total": 25,
  "entries": [...],
  "page": 1,
  "page_size": 20
}
```

#### Get Journal Prompts

**Endpoint:** `GET /api/v1/journal/prompts`

**Description:** Get AI-generated journaling prompts.

**Query Parameters:**
- `category`: Filter by category (gratitude, reflection, goals, emotions, creativity)

**Response:**
```json
{
  "prompts": [
    {
      "id": 1,
      "category": "gratitude",
      "text": "What are three things you're grateful for today?"
    }
  ],
  "category": "gratitude"
}
```

#### Search Journal Entries

**Endpoint:** `GET /api/v1/journal/search`

**Description:** Search journal entries by content, tags, or sentiment.

**Authentication:** Required

**Query Parameters:**
- `query`: Search text
- `tags`: Comma-separated tags
- `min_sentiment`: Minimum sentiment score (0-100)
- `max_sentiment`: Maximum sentiment score (0-100)

**Response:** Same as list endpoint

#### Get Journal Analytics

**Endpoint:** `GET /api/v1/journal/analytics`

**Description:** Get analytics on journaling patterns.

**Authentication:** Required

**Response:**
```json
{
  "total_entries": 25,
  "avg_sentiment": 70,
  "mood_distribution": {
    "positive": 15,
    "neutral": 7,
    "negative": 3
  },
  "writing_frequency": "daily"
}
```

#### Export Journal Entries

**Endpoint:** `GET /api/v1/journal/export`

**Description:** Export journal entries in JSON or TXT format.

**Authentication:** Required

**Query Parameters:**
- `format`: Export format (json or txt)
- `start_date`: Start date filter
- `end_date`: End date filter

**Response:** File download

#### Get Journal Entry

**Endpoint:** `GET /api/v1/journal/{journal_id}`

**Description:** Get a specific journal entry.

**Authentication:** Required

#### Update Journal Entry

**Endpoint:** `PUT /api/v1/journal/{journal_id}`

**Description:** Update a journal entry.

**Authentication:** Required

#### Delete Journal Entry

**Endpoint:** `DELETE /api/v1/journal/{journal_id}`

**Description:** Delete a journal entry.

**Authentication:** Required

### Analytics

#### Get Analytics Summary

**Endpoint:** `GET /api/v1/analytics/summary`

**Description:** Get overall analytics summary (aggregated data only).

**Rate Limited:** 30 requests per minute

**Response:**
```json
{
  "total_assessments": 1000,
  "unique_users": 500,
  "global_avg_score": 72.5,
  "age_group_stats": {...}
}
```

#### Get Trend Analytics

**Endpoint:** `GET /api/v1/analytics/trends`

**Description:** Get trend analytics over time.

**Rate Limited:** 30 requests per minute

**Query Parameters:**
- `period`: Time period (daily, weekly, monthly)
- `limit`: Number of periods (max 24)

**Response:**
```json
{
  "period_type": "monthly",
  "data": [
    {
      "period": "2023-01",
      "avg_score": 70,
      "assessment_count": 50
    }
  ]
}
```

#### Get Benchmark Comparison

**Endpoint:** `GET /api/v1/analytics/benchmarks`

**Description:** Get percentile-based benchmark data.

**Rate Limited:** 30 requests per minute

**Response:**
```json
[
  {
    "metric": "overall_score",
    "global_average": 72.5,
    "percentiles": {
      "25": 65,
      "50": 72,
      "75": 80,
      "90": 85
    }
  }
]
```

#### Get Population Insights

**Endpoint:** `GET /api/v1/analytics/insights`

**Description:** Get population-level insights.

**Rate Limited:** 30 requests per minute

**Response:**
```json
{
  "most_common_age_group": "25-34",
  "highest_performing_age_group": "35-44",
  "total_population": 500,
  "completion_rate": 0.85
}
```

### Health Check

#### Health Status

**Endpoint:** `GET /api/v1/health/`

**Description:** Get API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-01-15T12:00:00Z",
  "version": "1.0.0"
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200`: Success
- `201`: Created
- `204`: No Content
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

Error responses include a JSON object with `detail` field:

```json
{
  "detail": "Error description"
}
```

## Rate Limiting

Some endpoints have rate limits to prevent abuse:

- Analytics endpoints: 30 requests per minute per IP
- General API: No strict limits, but monitored

## Data Privacy

- User data is protected and only accessible to authenticated users
- Analytics endpoints return aggregated data only
- No individual user data is exposed in public endpoints
- All data transmission uses HTTPS

## SDKs and Libraries

Official SDKs are available for:
- Python: `pip install soulsense-api`
- JavaScript/Node.js: `npm install soulsense-api`

## Support

For API support, contact: api-support@soulsense.com

## Changelog

### v1.0.0
- Initial release
- Basic authentication, user management, assessments, journaling, and analytics endpoints
