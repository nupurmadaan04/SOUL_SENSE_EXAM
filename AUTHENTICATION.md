# 🔐 Authentication System

The Soul Sense EQ Test now includes user authentication for personalized sessions and data security.

## Features

- **User Registration**: Create new accounts with username/password
- **Secure Login**: SHA-256 password hashing for security
- **Session Management**: Personalized user sessions
- **Data Isolation**: User-specific test results and journal entries
- **Logout Functionality**: Secure session termination

## Usage

### First Time Users
1. Run the application: `python -m app.main`
2. Click "Sign Up" on the login screen
3. Enter a username (minimum 3 characters)
4. Enter a password (minimum 6 characters)
5. Confirm your password
6. Click "Create Account"

### Returning Users
1. Run the application: `python -m app.main`
2. Enter your username and password
3. Click "Login" or press Enter

### Main Menu Options
After login, you can:
- **Take EQ Test**: Complete the emotional intelligence assessment
- **Emotional Journal**: Write and analyze daily reflections
- **Logout**: End your session and return to login

## Security Features

- Passwords are hashed using SHA-256 before storage
- No plain text passwords are stored in the database
- User data is isolated by username
- Session-based access control

## Database Schema

The authentication system adds a `users` table:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

## Testing Authentication

Run the demo script to test authentication:
```bash
python -m scripts.demo_auth
```

Run the test suite:
```bash
python -m pytest tests/test_auth.py -v
```