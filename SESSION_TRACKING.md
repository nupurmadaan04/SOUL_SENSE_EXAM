# Session Tracking Documentation

## Overview

The SoulSense EQ Assessment now includes a comprehensive session tracking system that generates unique session IDs for every user login. This feature improves security, enables better session management, and provides detailed tracking of user activities.

## Features

### ✓ Unique Session ID Generation

- Every successful login generates a cryptographically secure session ID (256-bit)
- Uses Python's `secrets` module for secure random token generation
- Each session ID is guaranteed to be unique (format: URL-safe base64 encoded string)

### ✓ Session Persistence

- All session data is stored in the database with comprehensive tracking
- Stores: session ID, user ID, username, timestamps, IP address (optional), user agent (optional)
- Maintains relationship with user records through foreign keys

### ✓ Session Validation

- Sessions can be validated at any time using the session ID
- Automatic expiration after 24 hours of inactivity
- Last accessed timestamp updated on each validation

### ✓ Session Invalidation

- Sessions are properly invalidated on user logout
- Logout timestamp recorded for audit purposes
- Session marked as inactive but retained for historical tracking

### ✓ Multi-Session Support

- Users can have multiple concurrent active sessions (different devices/browsers)
- Each session maintains independent state
- Ability to view all active sessions for a user

### ✓ Session Management

- Bulk invalidation of all sessions for a specific user
- Automatic cleanup of old/expired sessions
- Query active sessions with filtering options

## Architecture

### Database Schema

The `Session` model includes the following fields:

```python
class Session(Base):
    id = Integer (Primary Key)
    session_id = String (Unique, Indexed) - The unique session identifier
    user_id = Integer (Foreign Key to users.id, Indexed)
    username = String (Indexed) - Denormalized for quick lookups
    created_at = String (ISO 8601 timestamp, Indexed)
    last_accessed = String (ISO 8601 timestamp)
    ip_address = String (Optional)
    user_agent = String (Optional)
    is_active = Boolean (Indexed)
    logged_out_at = String (Optional)
```

### Indexes

To optimize query performance, the following indexes are created:

- `idx_session_user_active`: (user_id, is_active)
- `idx_session_username_active`: (username, is_active)
- `idx_session_created`: (created_at)
- Unique index on `session_id`

### Relationships

- `Session.user` → `User.sessions`: Many-to-One relationship
- Cascade delete: When a user is deleted, all their sessions are automatically removed

## Usage

### Basic Authentication Flow

```python
from app.auth import AuthManager

# Create auth manager
auth = AuthManager()

# Register a user
success, message = auth.register_user("john_doe", "secure_password")

# Login (creates a session)
success, message = auth.login_user("john_doe", "secure_password")
if success:
    print(f"Session ID: {auth.current_session_id}")
    print(f"Current User: {auth.current_user}")

# Logout (invalidates the session)
success, message = auth.logout_user()
```

### Session Validation

```python
# Validate a session
is_valid, username = auth.validate_session(session_id)

if is_valid:
    print(f"Valid session for user: {username}")
else:
    print("Invalid or expired session")
```

### Managing Multiple Sessions

```python
# Get all active sessions for a user
active_sessions = auth.get_active_sessions("john_doe")

for session in active_sessions:
    print(f"Session: {session['session_id']}")
    print(f"Created: {session['created_at']}")
    print(f"Last Accessed: {session['last_accessed']}")

# Invalidate all sessions for a user
count = auth.invalidate_user_sessions("john_doe")
print(f"Invalidated {count} sessions")
```

### Session Cleanup

```python
# Clean up sessions older than 24 hours (default)
count = auth.cleanup_old_sessions()

# Clean up sessions older than 48 hours
count = auth.cleanup_old_sessions(hours=48)

print(f"Cleaned up {count} old sessions")
```

## Migration

### For Existing Databases

If you have an existing database without the sessions table:

```bash
# Add the sessions table to your database
python migrations/add_sessions_table.py

# To rollback (remove the sessions table)
python migrations/add_sessions_table.py --rollback
```

### For New Installations

The sessions table will be created automatically when initializing a new database.

## API Reference

### AuthManager Methods

#### `login_user(username, password)`

- **Description**: Authenticates user and creates a new session
- **Parameters**:
  - `username` (str): The username
  - `password` (str): The password
- **Returns**: `(success: bool, message: str)`
- **Side Effects**: Sets `self.current_user` and `self.current_session_id` on success

#### `logout_user()`

- **Description**: Invalidates the current session and clears user data
- **Returns**: `(success: bool, message: str)`
- **Side Effects**: Clears `self.current_user` and `self.current_session_id`

#### `validate_session(session_id)`

- **Description**: Validates if a session is active and not expired
- **Parameters**:
  - `session_id` (str): The session ID to validate
- **Returns**: `(is_valid: bool, username: str or None)`
- **Side Effects**: Updates `last_accessed` timestamp for valid sessions

#### `cleanup_old_sessions(hours=24)`

- **Description**: Invalidates sessions older than specified hours
- **Parameters**:
  - `hours` (int): Age threshold in hours (default: 24)
- **Returns**: `count: int` - Number of sessions cleaned up

#### `get_active_sessions(username=None)`

- **Description**: Retrieves all active sessions, optionally filtered by username
- **Parameters**:
  - `username` (str, optional): Filter by username
- **Returns**: `list[dict]` - List of session dictionaries

#### `invalidate_user_sessions(username)`

- **Description**: Invalidates all active sessions for a specific user
- **Parameters**:
  - `username` (str): The username
- **Returns**: `count: int` - Number of sessions invalidated

## Security Considerations

### Session ID Generation

- Uses `secrets.token_urlsafe(32)` which generates 256-bit cryptographically secure tokens
- Resistant to brute force attacks
- URL-safe format for easy transmission

### Session Expiration

- Sessions automatically expire after 24 hours of inactivity
- Expired sessions cannot be validated even if they're marked as active

### Session Storage

- Session IDs are indexed for fast lookups
- Timestamps stored in ISO 8601 format (UTC)
- Optional IP address and user agent tracking for enhanced security

### Best Practices

1. Always validate session IDs before granting access
2. Run regular cleanup to remove old sessions
3. Consider implementing additional security measures:
   - IP address validation
   - User agent validation
   - Concurrent session limits
   - Session refresh tokens

## Testing

Run the comprehensive test suite:

```bash
# Run all session tests
pytest tests/test_sessions.py -v

# Run specific test
pytest tests/test_sessions.py::TestSessionManagement::test_session_id_generation_on_login -v
```

### Test Coverage

The test suite covers:

- ✓ Session ID generation on login
- ✓ Unique session IDs for multiple logins
- ✓ Session data storage correctness
- ✓ Session invalidation on logout
- ✓ Multiple concurrent sessions
- ✓ Session validation
- ✓ Session cleanup
- ✓ Bulk session invalidation
- ✓ Last accessed timestamp updates

## Demonstration

Run the demonstration script to see all features in action:

```bash
python demo_session_tracking.py
```

This will demonstrate:

1. Basic session flow (login → session creation → logout)
2. Multiple concurrent sessions
3. Session validation
4. Session cleanup
5. Bulk session invalidation
6. Detailed session information

## Monitoring and Analytics

### Queries for Session Analytics

```python
from app.db import get_session
from app.models import Session
from sqlalchemy import func

session = get_session()

# Total active sessions
active_count = session.query(func.count(Session.id))\
    .filter(Session.is_active == True).scalar()

# Average session duration
# (This would require end time calculation)

# Sessions created today
from datetime import datetime, timedelta
today = datetime.utcnow().date().isoformat()
today_sessions = session.query(func.count(Session.id))\
    .filter(Session.created_at >= today).scalar()

session.close()
```

## Troubleshooting

### Issue: Sessions not being created

**Solution**: Ensure the sessions table exists in your database. Run the migration:

```bash
python migrations/add_sessions_table.py
```

### Issue: Session validation always fails

**Possible causes**:

1. Session has expired (> 24 hours old)
2. Session was logged out
3. Session ID is incorrect

**Debug**:

```python
from app.db import get_session
from app.models import Session

db_session = get_session()
session_record = db_session.query(Session).filter_by(session_id=your_session_id).first()
if session_record:
    print(f"Active: {session_record.is_active}")
    print(f"Created: {session_record.created_at}")
db_session.close()
```

### Issue: Too many active sessions

**Solution**: Run cleanup regularly:

```python
auth = AuthManager()
auth.cleanup_old_sessions(hours=12)  # More aggressive cleanup
```

## Performance Considerations

### Database Indexes

All critical fields are indexed:

- `session_id`: Unique index for O(1) lookup
- `(user_id, is_active)`: Composite index for user session queries
- `(username, is_active)`: Composite index for username-based queries
- `created_at`: Index for time-based queries and cleanup

### Query Optimization

- Use parameterized queries to prevent SQL injection
- Batch operations where possible
- Regular cleanup to prevent table bloat

### Recommended Maintenance

```python
# Run this periodically (e.g., daily cron job)
def daily_session_maintenance():
    auth = AuthManager()

    # Clean up sessions older than 24 hours
    cleaned = auth.cleanup_old_sessions(hours=24)
    logging.info(f"Cleaned up {cleaned} old sessions")

    # Optional: Delete very old session records to save space
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()

    session = get_session()
    try:
        session.query(Session).filter(
            Session.created_at < cutoff
        ).delete()
        session.commit()
    finally:
        session.close()
```

## Future Enhancements

Potential improvements to consider:

1. **Session Refresh**: Implement token refresh mechanism
2. **Concurrent Session Limits**: Limit number of active sessions per user
3. **Device Management**: Allow users to view and manage their devices
4. **Geographic Tracking**: Store and display login locations
5. **Suspicious Activity Detection**: Alert on unusual session patterns
6. **Remember Me**: Extended session duration option
7. **Session Transfer**: Transfer session between devices

## Acceptance Criteria ✓

All acceptance criteria have been met:

- ✓ Every login generates a unique session ID
- ✓ Session ID is cryptographically secure (256-bit)
- ✓ Session data stored with user ID and timestamp
- ✓ Sessions can be validated using session ID
- ✓ Sessions invalidated on logout (marked inactive with timestamp)
- ✓ No stale sessions remain active (automatic cleanup available)
- ✓ No duplicate session IDs (enforced by unique constraint)

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Run the demonstration script to verify functionality
3. Review test cases for usage examples
4. Check logs for error messages

## License

This feature is part of the SoulSense EQ Assessment system and follows the same license terms.
