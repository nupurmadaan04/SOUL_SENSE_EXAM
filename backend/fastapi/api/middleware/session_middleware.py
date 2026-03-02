from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import logging

logger = logging.getLogger("api.middleware.session")


class SessionCleanupMiddleware(BaseHTTPMiddleware):
    """Ensure any leaked request `db_session` is closed after the response.

    This is a safety-net around the dependency-managed sessions to ensure
    sessions are not left open by accidental code paths or exceptions.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        finally:
            session = getattr(request.state, "db_session", None)
            if session is not None:
                try:
                    # AsyncSession.close() is awaitable
                    close = getattr(session, "close", None)
                    if close is not None:
                        await close()
                        logger.debug("Closed leaked request db_session")
                except Exception:
                    logger.exception("Failed to close leaked db_session")
                finally:
                    try:
                        delattr(request.state, "db_session")
                    except Exception:
                        pass
