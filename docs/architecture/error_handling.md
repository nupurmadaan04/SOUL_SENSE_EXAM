# Error Handling Strategy Documentation

This document outlines the comprehensive error handling strategy implemented in the SoulSense application, covering both the desktop application and FastAPI backend.

## Overview

The SoulSense application implements a multi-layered error handling strategy that ensures:

- **Consistent Error Logging**: Structured logging with severity levels and context
- **User-Friendly Messages**: Non-technical error messages for end users
- **Graceful Degradation**: Application continues functioning despite errors
- **Developer Debugging**: Detailed error information for troubleshooting
- **Exception Hierarchy**: Categorized exceptions with error codes

## Architecture Components

### 1. Exception Hierarchy (`app/exceptions.py`)

#### Base Exception Class

```python
class SoulSenseError(Exception):
    """Base exception for SoulSense application."""
    default_code: int = 0

    def __init__(self, message: str, original_exception: Optional[Exception] = None, error_code: Optional[int] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.error_code = error_code or self.default_code
```

#### Error Code Categories

| Category | Range | Description |
|----------|-------|-------------|
| Database | 1000-1999 | Database connection, queries, integrity |
| Configuration | 2000-2999 | Config file, environment variables |
| Resources | 3000-3999 | Files, assets, external resources |
| Validation | 4000-4999 | User input, data validation |
| Authentication | 5000-5999 | Login, permissions, sessions |
| API | 6000-6999 | External API connections |
| ML | 7000-7999 | Model loading, predictions, training |
| UI | 8000-8999 | Interface rendering, events |
| Export | 9000-9999 | Report generation, file exports |

#### Custom Exception Classes

```python
class DatabaseError(SoulSenseError):          # DB operations
class ConfigurationError(SoulSenseError):     # Config issues
class ResourceError(SoulSenseError):          # Missing files/assets
class ValidationError(SoulSenseError):        # Invalid input
class AuthenticationError(SoulSenseError):    # Auth failures
class APIConnectionError(SoulSenseError):     # External API issues
class MLModelError(SoulSenseError):           # ML model problems
class UIError(SoulSenseError):                # UI rendering/events
class ExportError(SoulSenseError):            # Export operations
```

### 2. Centralized Error Handler (`app/error_handler.py`)

#### Error Severity Levels

```python
class ErrorSeverity:
    LOW = "LOW"           # Minor issues, operation can continue
    MEDIUM = "MEDIUM"     # Notable issues, degraded functionality
    HIGH = "HIGH"         # Critical issues, feature unavailable
    CRITICAL = "CRITICAL" # Application-breaking issues
```

#### Core Features

- **Singleton Pattern**: Single error handler instance across the application
- **Structured Logging**: JSON-formatted logs with context and metadata
- **Error Statistics**: Tracks error frequency by module and type
- **Recent Error History**: Maintains rolling history of recent errors
- **User Message Mapping**: Translates technical errors to user-friendly messages

#### User-Friendly Message Mapping

```python
USER_MESSAGES: Dict[Type[Exception], str] = {
    DatabaseError: "A database error occurred. Please try again later.",
    ConfigurationError: "There's a configuration issue. Please contact support.",
    ResourceError: "A required resource could not be found.",
    ValidationError: "Please check your input and try again.",
    AuthenticationError: "Authentication failed. Please check your credentials.",
    APIConnectionError: "Unable to connect to the service. Check your internet connection.",
    FileNotFoundError: "The requested file could not be found.",
    PermissionError: "Permission denied. Please check file permissions.",
    ConnectionError: "Network connection error. Please check your internet.",
    TimeoutError: "The operation timed out. Please try again.",
}
```

### 3. Error Handling Decorators and Context Managers

#### `@safe_operation` Decorator

```python
@safe_operation(
    fallback=[],                    # Return value on error
    log=True,                       # Log the exception
    user_message="Custom message",  # User-facing message
    severity=ErrorSeverity.MEDIUM,  # Error severity
    show_ui=False,                  # Show error dialog
    reraise=False                   # Re-raise after handling
)
def risky_operation():
    # Operation that might fail
    pass
```

#### `safe_execute` Context Manager

```python
with safe_execute(
    operation_name="Loading dashboard",
    module="dashboard",
    fallback_action=show_default_dashboard,
    log=True,
    severity=ErrorSeverity.MEDIUM,
    show_ui=True
):
    load_dashboard_data()
```

### 4. Global Exception Handlers

#### Desktop Application Global Handler

```python
def setup_global_exception_handlers():
    """Set up global exception handlers for uncaught exceptions."""
    sys.excepthook = global_excepthook  # Handles uncaught exceptions
    tk.Tk.report_callback_exception = tk_exception_handler  # Handles Tkinter errors
```

#### FastAPI Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions in FastAPI."""
    import traceback
    print(f"❌ GLOBAL EXCEPTION: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)}
    )
```

## Error Handling Patterns

### 1. Database Operations

```python
from app.db import safe_db_context

try:
    with safe_db_context() as session:
        # Database operations
        result = session.query(User).filter(User.id == user_id).first()
        return result
except DatabaseError as e:
    # Handle database-specific errors
    logger.error(f"Database operation failed: {e}")
    return None
```

### 2. File Operations

```python
@safe_operation(fallback=None, user_message="Could not load configuration file")
def load_config_file(file_path: str):
    with open(file_path, 'r') as f:
        return json.load(f)
```

### 3. API Calls

```python
with safe_execute("Fetching user data", module="api_client"):
    response = requests.get(f"{API_BASE}/users/{user_id}")
    response.raise_for_status()
    return response.json()
```

### 4. UI Operations

```python
def update_ui_safe():
    try:
        # UI update operations
        self.status_label.config(text="Loading...")
        # ... more UI updates
    except Exception as e:
        get_error_handler().handle_exception(
            e, module="ui", operation="update_display",
            show_ui=True, severity=ErrorSeverity.MEDIUM
        )
```

## Logging Strategy

### Log Levels by Severity

- **CRITICAL**: Application-breaking errors, logged with full traceback
- **HIGH**: Feature-breaking errors, logged with traceback
- **MEDIUM**: Notable errors, logged with message only
- **LOW**: Minor issues, logged for monitoring

### Structured Log Format

```json
{
    "timestamp": "2024-01-28T10:30:00.123456",
    "severity": "HIGH",
    "module": "database",
    "operation": "user_query",
    "error_type": "DatabaseError",
    "message": "Connection timeout",
    "user_id": "123",
    "context": {"query": "SELECT * FROM users"},
    "traceback": "...full traceback..."
}
```

### Log Destinations

- **Console**: Immediate feedback during development
- **File**: Persistent logs in `logs/` directory
- **Database**: Error statistics and recent error history
- **UI**: User notifications for actionable errors

## User Feedback Mechanisms

### 1. Error Dialogs

```python
from app.main import show_error

def handle_user_error():
    try:
        perform_operation()
    except ValidationError as e:
        show_error("Invalid Input", str(e), e)
    except Exception as e:
        show_error("Unexpected Error", "An unexpected error occurred.", e)
```

### 2. Status Messages

- **Success**: Green confirmation messages
- **Warning**: Yellow caution messages
- **Error**: Red error messages with actionable guidance

### 3. Graceful Degradation

- **Fallback Values**: Return safe defaults when operations fail
- **Feature Disabling**: Disable problematic features while keeping core functionality
- **Offline Mode**: Continue operation with cached data when services unavailable

## Error Recovery Strategies

### 1. Automatic Retry

```python
def retry_operation(operation, max_attempts=3, delay=1.0):
    for attempt in range(max_attempts):
        try:
            return operation()
        except (ConnectionError, TimeoutError) as e:
            if attempt < max_attempts - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            else:
                raise e
```

### 2. Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerError("Service temporarily unavailable")

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
```

### 3. Fallback Operations

```python
def get_user_data_with_fallback(user_id):
    try:
        # Primary: Database query
        return db.query_user(user_id)
    except DatabaseError:
        try:
            # Secondary: Cache lookup
            return cache.get_user(user_id)
        except CacheError:
            # Tertiary: Default values
            return User.default()
```

## Testing Error Handling

### Unit Tests

```python
def test_database_error_handling():
    with patch('app.db.SessionLocal') as mock_session:
        mock_session.side_effect = SQLAlchemyError("Mock DB error")

        with pytest.raises(DatabaseError) as excinfo:
            with safe_db_context():
                pass

        assert "database error occurred" in str(excinfo.value).lower()
```

### Integration Tests

```python
def test_error_handler_ui_integration():
    handler = get_error_handler()

    with patch('app.main.show_error') as mock_show_error:
        handler.handle_exception(
            ValidationError("Invalid input"),
            show_ui=True
        )

        mock_show_error.assert_called_once()
        args = mock_show_error.call_args[0]
        assert "Invalid input" in args[1]
```

## Monitoring and Alerting

### Error Metrics

- **Error Rate**: Errors per minute/hour by module
- **Error Types**: Most frequent error categories
- **User Impact**: Errors affecting user experience
- **System Health**: Database connectivity, API availability

### Alerting Thresholds

```python
ERROR_THRESHOLDS = {
    'database_connection_failures': {'warning': 5, 'critical': 10},
    'api_timeout_errors': {'warning': 10, 'critical': 25},
    'ui_render_failures': {'warning': 3, 'critical': 8},
}
```

### Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    checks = {
        'database': check_database_health(),
        'external_apis': check_api_health(),
        'file_system': check_filesystem_health(),
        'memory': check_memory_usage(),
    }

    overall_status = 'healthy' if all(checks.values()) else 'unhealthy'

    return {
        'status': overall_status,
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }
```

## Best Practices

### 1. Exception Design

- **Specific Exceptions**: Use specific exception types over generic ones
- **Error Codes**: Include error codes for programmatic handling
- **Context Preservation**: Chain original exceptions when wrapping
- **Immutable Messages**: Don't modify exception messages after creation

### 2. Error Handling

- **Fail Fast**: Validate inputs early and fail immediately
- **Resource Cleanup**: Use context managers for resource management
- **Timeout Handling**: Set reasonable timeouts for all operations
- **Circuit Breakers**: Protect against cascading failures

### 3. Logging

- **Structured Logs**: Use consistent log formats with metadata
- **Appropriate Levels**: Choose log levels based on severity and audience
- **Performance**: Avoid expensive operations in logging code
- **Privacy**: Sanitize sensitive data before logging

### 4. User Experience

- **Clear Messages**: Use simple, actionable error messages
- **Progressive Disclosure**: Show basic info first, details on request
- **Recovery Options**: Provide clear paths to resolve issues
- **Consistency**: Use consistent error presentation across the application

## Migration and Maintenance

### Version Compatibility

- **Backward Compatibility**: Maintain exception interfaces across versions
- **Deprecation Warnings**: Warn before removing error types
- **Migration Guides**: Document error handling changes in releases

### Performance Considerations

- **Memory Usage**: Limit error history size to prevent memory leaks
- **Log Rotation**: Implement log rotation to manage disk usage
- **Async Processing**: Handle errors asynchronously when possible
- **Rate Limiting**: Prevent error logging from overwhelming systems

This comprehensive error handling strategy ensures the SoulSense application remains robust, user-friendly, and maintainable while providing excellent debugging capabilities for developers.