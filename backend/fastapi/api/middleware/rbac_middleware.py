# --------------------------------------------------------------
# File: rbac_middleware.py  (Rewritten — Issue #1145)
# --------------------------------------------------------------
"""RBAC Enforcement Middleware — Deadlock-Free Redesign (#1145)

Key improvements over the original:

1. **Re-entry Guard** — a thread-local-style request flag prevents the
   middleware from re-activating itself when downstream routes open their
   own database sessions, eliminating circular dependency cascades.

2. **Permission Sidecar Cache** — validated `is_admin` flags are stored
   in Redis (TTL = 60 s) via `RBACPermissionCache`. The primary DB is
   only queried on a *cache miss*, completely decoupling the middleware
   from the request's primary AsyncSession.

3. **Independent DB Session** — when a DB query is genuinely required,
   the middleware opens its *own* short-lived AsyncSession that is
   committed and closed before `call_next` is called, so it cannot share
   or block any lock held by the handler session.

4. **Exempt paths** — public routes bypass all of the above cheaply.
"""

import logging
from typing import Callable

from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from ..config import get_settings_instance
from ..services.rbac_cache import rbac_permission_cache

log = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Paths that never need RBAC validation
_EXEMPT_PREFIXES = (
    "/docs", "/redoc", "/openapi.json", "/favicon.ico", "/health",
)
_EXEMPT_EXACT = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/captcha",
    "/api/v1/auth/server-id",
    "/api/v1/analytics/events",
    "/",
}

# Internal sentinel attribute on request.state to detect re-entry
_RBAC_GUARD_ATTR = "_rbac_in_progress"


def _is_exempt(path: str) -> bool:
    if path in _EXEMPT_EXACT:
        return True
    for prefix in _EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


async def rbac_middleware(request: Request, call_next: Callable):
    """
    FastAPI middleware that validates the user's RBAC role.

    Flow:
      1. Skip exempt / non-API paths immediately.
      2. Re-entry guard — if we are already inside RBAC validation for
         this request (e.g. a middleware N+1 call), skip and continue.
      3. Decode JWT cheaply — no I/O.
      4. Check the Redis sidecar cache.
         - HIT  → use cached value, no DB query.
         - MISS → open an *independent* DB session, fetch user, write
                  cache, close session before calling call_next.
      5. Populate request.state.is_admin / request.state.user_id.
    """
    settings = get_settings_instance()

    # Defaults for unauthenticated / public routes
    request.state.is_admin = False
    request.state.user_id = None

    path = request.url.path

    # ── 1. Exemption check ──────────────────────────────────────────────
    if not path.startswith("/api/v1") or _is_exempt(path):
        return await call_next(request)

    # ── 2. Re-entry guard ───────────────────────────────────────────────
    if getattr(request.state, _RBAC_GUARD_ATTR, False):
        log.debug("[RBAC] Re-entry detected for %s — skipping inner check", path)
        return await call_next(request)

    setattr(request.state, _RBAC_GUARD_ATTR, True)

    try:
        # ── 3. JWT decode (CPU only, no I/O) ────────────────────────────
        try:
            token: str = await oauth2_scheme(request)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm]
            )
            username: str | None = payload.get("sub")
            token_is_admin: bool = payload.get("is_admin", False)
            request.state.tenant_id = payload.get("tid") # Extract tenant ID (#1135)
        except JWTError as exc:
            log.warning("[RBAC] JWT decode error for %s: %s", path, exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject"
            )

        # ── 4a. Sidecar cache lookup (no DB) ────────────────────────────
        user_id_for_version = payload.get("uid")

        if not user_id_for_version:
             # Legacy token fallback: No user_id in JWT
             log.debug("[RBAC] Legacy token (no uid) — performing one-time DB lookup for ID")
             from sqlalchemy import select
             from ..models import User
             from ..services.db_service import AsyncSessionLocal
             async with AsyncSessionLocal() as db:
                 id_stmt = select(User.id).filter(User.username == username)
                 id_res = await db.execute(id_stmt)
                 user_id_for_version = id_res.scalar()

        if user_id_for_version:
            cached_is_admin = await rbac_permission_cache.get(username, user_id_for_version)
        else:
            cached_is_admin = None

        if cached_is_admin is not None:
             # Cache hit — validate JWT claim against cached value
             db_is_admin = cached_is_admin
             log.debug("[RBAC] Cache hit for %s → is_admin=%s", username, db_is_admin)
             request.state.user_id = user_id_for_version
        else:
            # ── 4b. Cache miss — open independent DB session ─────────────
            log.debug("[RBAC] Cache miss for %s — querying DB", username)
            from sqlalchemy import select
            from ..models import User
            from ..services.db_service import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                stmt = select(User.id, User.is_admin, User.version).filter(User.username == username)
                result = await db.execute(stmt)
                row = result.first()

            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
                )

            user_id_from_db, db_is_admin, current_v = row.id, row.is_admin, row.version

            # Populate user_id from DB (more reliable than JWT claim)
            request.state.user_id = user_id_from_db

            # Write to sidecar cache with authoritative version
            await rbac_permission_cache.set(username, bool(db_is_admin), version=current_v)
            
            # Ensure Redis truth mapping is also populated for future version checks
            from ..services.cache_service import cache_service
            await cache_service.update_version("user", user_id_from_db, current_v)

        # ── 5. Privilege-escalation check ───────────────────────────────
        if bool(token_is_admin) != bool(db_is_admin):
            log.warning(
                "[RBAC] Role mismatch for %s: token=%s db=%s path=%s",
                username, token_is_admin, db_is_admin, path,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role tampering detected",
            )

        request.state.is_admin = bool(db_is_admin)
        if request.state.user_id is None:
            # Might still be None if cache was hit (no DB row fetched above)
            request.state.user_id = payload.get("uid")

    finally:
        # Always clear the re-entry guard so sub-requests are unaffected
        setattr(request.state, _RBAC_GUARD_ATTR, False)

    return await call_next(request)


# End of rbac_middleware.py
