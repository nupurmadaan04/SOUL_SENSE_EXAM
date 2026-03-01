# Database Error Handling

This document describes the database connection failure handling implementation for the Soul Sense application.

## Overview

The application now includes comprehensive error handling for database connection failures to ensure graceful degradation when the database is unavailable, preventing application crashes and providing user-friendly error messages.

## Implementation

### Core Components

#### 1. Database Error Handler (`db_error_handler.py`)

A utility module that provides consistent database error handling across all services:

- **`DatabaseConnectionError`**: Custom exception for database connection issues
- **`safe_db_query()`**: Function to safely execute database queries with error handling
- **`handle_db_operation()`**: Decorator for wrapping service methods
- **`db_error_handler()`**: Context manager for complex database operations

#### 2. Service-Level Protection

All database operations in services are now protected with try-catch blocks that:

- Catch SQLAlchemy exceptions (`OperationalError`, `DatabaseError`, `DisconnectionError`)
- Log detailed error information for debugging
- Return user-friendly error messages
- Prevent application crashes

### Error Handling Flow

```
Database Operation → SQLAlchemy Exception → Custom Handler → User-Friendly Response
     ↓                    ↓                        ↓                    ↓
  Query/Commit      Connection Failed        Log Error         HTTP 503 Response
```

## Services Updated

### AuthService (`auth_service.py`)
- `register_user()`: Protected user registration with database error handling
- Handles both initial user checks and final commit operations

### UserService (`user_service.py`)
- `get_user_by_id()`: Safe user retrieval by ID
- `get_user_by_username()`: Safe user retrieval by username
- `get_all_users()`: Safe user listing with pagination
- `create_user()`: Protected user creation

### ProfileService (`profile_service.py`)
- `_verify_user_exists()`: Safe user verification for profile operations

## Error Responses

### Database Connection Errors
- **HTTP Status**: 503 Service Unavailable
- **Message**: "Service temporarily unavailable. Please try again later."
- **Logging**: Detailed error information written to application logs

### Global Fallback
- **Global Exception Handler**: Catches any unhandled exceptions
- **HTTP Status**: 500 Internal Server Error
- **Message**: "An internal error occurred. Please try again later."

## Testing

The implementation includes comprehensive testing:

```bash
# Run database error handling tests
python test_db_error_handling.py
```

Test coverage includes:
- Exception handling correctness
- SQLAlchemy error conversion
- Service-level error handling
- User-friendly message generation

## Benefits

1. **Application Stability**: No crashes during database outages
2. **User Experience**: Clear, non-technical error messages
3. **Monitoring**: Detailed logging for debugging and alerting
4. **Graceful Degradation**: Application continues running during DB issues
5. **Consistent Handling**: Uniform error handling across all services

## Usage Examples

### Using safe_db_query

```python
from .db_error_handler import safe_db_query, DatabaseConnectionError

def get_user(self, user_id: int):
    try:
        return safe_db_query(
            self.db,
            lambda: self.db.query(User).filter(User.id == user_id).first(),
            "get user by ID"
        )
    except DatabaseConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later."
        )
```

### Using the decorator

```python
from .db_error_handler import handle_db_operation

@handle_db_operation("user registration")
def register_user(self, user_data):
    # Database operations here
    pass
```

## Future Enhancements

- Database connection retry logic
- Circuit breaker pattern for repeated failures
- Database health check endpoints
- Metrics and monitoring integration