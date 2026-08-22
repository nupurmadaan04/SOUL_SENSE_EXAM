"""Core exceptions module."""

class DomainError(Exception):
    """Base exception for application domain errors."""
    def __init__(self, message: str = "A domain error occurred"):
        self.message = message
        super().__init__(self.message)

class NotFoundError(DomainError):
    """Resource not found error."""
    pass

class ConflictError(DomainError):
    """Conflict error."""
    pass

class AuthorizationError(DomainError):
    """Authorization failed."""
    pass

class AuthenticationError(DomainError):
    """Authentication failed."""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided."""
    pass

class TokenExpiredError(AuthenticationError):
    """Token has expired."""
    pass

class BusinessLogicError(DomainError):
    """Business logic violation."""
    pass

class ValidationError(DomainError):
    """Validation error."""
    pass

class InternalServerError(DomainError):
    """Internal server error."""
    pass

class RateLimitError(DomainError):
    """Rate limit exceeded."""
    pass

class BadRequestError(DomainError):
    """Bad request error."""
    pass
