# Quick Start Guide - User and Profile CRUD APIs

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- FastAPI server dependencies installed
- SoulSense database configured

### Installation

```bash
cd backend/fastapi
pip install -r requirements.txt
```

### Start the Server

```bash
uvicorn app.main:app --reload
```

Server will start at: **http://localhost:8000**

---

## 📚 Documentation

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Written Documentation

- **Complete API Reference**: [CRUD_API.md](CRUD_API.md)
- **Implementation Details**: [CRUD_IMPLEMENTATION_SUMMARY.md](CRUD_IMPLEMENTATION_SUMMARY.md)

---

## 🧪 Testing

### Option 1: Automated Test Script

```bash
python test_crud_api.py
```

This will automatically test all CRUD operations.

### Option 2: Interactive Swagger UI

1. Go to http://localhost:8000/docs
2. Click **"Authorize"** button
3. Register/login to get token
4. Try out endpoints interactively

### Option 3: Manual cURL Testing

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "mypass123"}'

# 2. Login and save token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=myuser&password=mypass123" | jq -r '.access_token')

# 3. Get user info
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer $TOKEN"

# 4. Create settings
curl -X POST http://localhost:8000/profiles/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"theme": "dark", "question_count": 15}'

# 5. Get complete profile
curl -X GET http://localhost:8000/users/me/complete \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📋 Available Endpoints

### Authentication (3 endpoints)
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current authenticated user

### Users (9 endpoints)
- `GET /users/me` - Get current user
- `GET /users/me/detail` - Get detailed user info
- `GET /users/me/complete` - Get complete profile
- `PUT /users/me` - Update current user
- `DELETE /users/me` - Delete current user
- `GET /users/` - List all users (paginated)
- `GET /users/{id}` - Get user by ID
- `GET /users/{id}/detail` - Get user details by ID

### Profiles (20 endpoints - 4 per profile type)

Each profile type has: GET, POST, PUT, DELETE

1. **User Settings** (`/profiles/settings`)
2. **Medical Profile** (`/profiles/medical`)
3. **Personal Profile** (`/profiles/personal`)
4. **User Strengths** (`/profiles/strengths`)
5. **Emotional Patterns** (`/profiles/emotional-patterns`)

---

## 🔑 Authentication

All endpoints (except register/login) require JWT authentication:

```
Authorization: Bearer <your-token-here>
```

Get token by calling `POST /auth/login`

---

## 📊 Profile Types

### 1. User Settings
App preferences: theme, notifications, language, question count

### 2. Medical Profile
Health info: blood type, allergies, medications, emergency contacts

### 3. Personal Profile
Biographical data: occupation, education, contact info, bio

### 4. User Strengths
Personal development: top strengths, areas for improvement, goals

### 5. Emotional Patterns
Emotional data: common emotions, triggers, coping strategies

---

## ✅ Example Workflow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Register
response = requests.post(f"{BASE_URL}/auth/register",
    json={"username": "john", "password": "pass123"})

# 2. Login
response = requests.post(f"{BASE_URL}/auth/login",
    data={"username": "john", "password": "pass123"})
token = response.json()["access_token"]

# 3. Create headers with token
headers = {"Authorization": f"Bearer {token}"}

# 4. Get user info
response = requests.get(f"{BASE_URL}/users/me", headers=headers)
print(response.json())

# 5. Create settings
settings = {"theme": "dark", "question_count": 20}
response = requests.post(f"{BASE_URL}/profiles/settings",
    headers=headers, json=settings)

# 6. Create personal profile
profile = {
    "occupation": "Developer",
    "bio": "Tech enthusiast",
    "email": "john@example.com"
}
response = requests.post(f"{BASE_URL}/profiles/personal",
    headers=headers, json=profile)

# 7. Get complete profile
response = requests.get(f"{BASE_URL}/users/me/complete",
    headers=headers)
print(response.json())
```

---

## 🛠️ Common Operations

### Create a Profile
```bash
POST /profiles/{profile-type}
Content-Type: application/json
Authorization: Bearer <token>

{
  "field1": "value1",
  "field2": "value2"
}
```

### Update a Profile (Partial Update)
```bash
PUT /profiles/{profile-type}
Content-Type: application/json
Authorization: Bearer <token>

{
  "field_to_update": "new_value"
}
```

### Get a Profile
```bash
GET /profiles/{profile-type}
Authorization: Bearer <token>
```

### Delete a Profile
```bash
DELETE /profiles/{profile-type}
Authorization: Bearer <token>
```

---

## ⚠️ Important Notes

1. **Password Security**: Passwords are hashed with bcrypt
2. **Token Expiration**: Tokens expire based on config (default: hours)
3. **User Deletion**: Deleting a user cascades to all profiles
4. **Profile Creation**: Create profiles only once, then use update
5. **Partial Updates**: PUT endpoints only update provided fields

---

## 🔍 Troubleshooting

### Server won't start
- Check if port 8000 is available
- Verify dependencies installed: `pip install -r requirements.txt`
- Check database connection in config

### Authentication errors
- Ensure token is valid and not expired
- Use correct header format: `Bearer <token>`
- Register/login to get a fresh token

### Profile already exists error
- Use PUT to update instead of POST to create
- Or delete the profile first, then create new

### Validation errors
- Check field requirements in documentation
- Email must be valid format
- Username must be 3-50 characters
- Password must be 8+ characters

---

## 📦 Files Created

### Services
- `app/services/user_service.py` - User CRUD operations
- `app/services/profile_service.py` - Profile CRUD operations

### Routers
- `app/routers/users.py` - User endpoints
- `app/routers/profiles.py` - Profile endpoints

### Schemas
- `app/models/schemas.py` - Pydantic validation models (40+ schemas)

### Documentation
- `CRUD_API.md` - Complete API reference
- `CRUD_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `QUICKSTART.md` - This file

### Testing
- `test_crud_api.py` - Automated test script

---

## 📞 Support

For detailed information:
- Read [CRUD_API.md](CRUD_API.md) for complete API documentation
- Check [CRUD_IMPLEMENTATION_SUMMARY.md](CRUD_IMPLEMENTATION_SUMMARY.md) for technical details
- Use interactive docs at http://localhost:8000/docs

---

## 🎉 You're Ready!

Start the server and begin creating user profiles!

```bash
uvicorn app.main:app --reload
```

Then visit http://localhost:8000/docs to explore the API.
