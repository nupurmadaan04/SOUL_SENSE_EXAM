# --------------------------------------------------------------
# File: c:\Users\ayaan shaikh\Documents\EWOC\SOULSENSE2\backend\fastapi\api\services\db_router.py
# --------------------------------------------------------------
"""
Read/Write‑splitting with primary‑replica support.

- POST / PUT / PATCH / DELETE → primary engine
- GET / HEAD / OPTIONS      → replica engine (if configured)

To avoid “read‑your‑own‑writes” we store a short‑lived Redis key
(`recent_write:{user_id}`) whenever a write succeeds.  Subsequent
GET requests that see this key will be forced onto the primary DB for a
configurable lag window (default 5 seconds).

All routers should depend on `get_db(request: Request)` instead of the
old `api.services.db_service.get_db`.
"""

import logging
from datetime import timedelta
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from jose import jwt, JWTError
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from ..config import get_settings_instance

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 1️⃣ Engine / Session creation
# ------------------------------------------------------------------
settings = get_settings_instance()

# Primary (write) engine – always present
_primary_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    future=True,
    connect_args={"check_same_thread": False} if settings.database_type == "sqlite" else {},
)
PrimarySessionLocal = async_sessionmaker(
    _primary_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Replica (read) engine – optional
_ReplicaSessionLocal: Optional[async_sessionmaker] = None
if settings.async_replica_database_url:
    _replica_engine = create_async_engine(
        settings.async_replica_database_url,
        echo=settings.debug,
        future=True,
        connect_args={"check_same_thread": False} if settings.database_type == "sqlite" else {},
    )
    _ReplicaSessionLocal = async_sessionmaker(
        _replica_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    log.info("Read‑replica engine initialised.")
else:
    log.warning("No replica_database_url configured – all reads will hit primary.")

# ------------------------------------------------------------------
# 2️⃣ Redis helper – recent‑write guard
# ------------------------------------------------------------------
_REDIS_TTL_SECONDS = 5  # how long we consider a write “fresh”

async def _redis_client() -> redis.Redis:
    """Lazy‑init a Redis connection (same URL used by CacheService)."""
    return redis.from_url(settings.redis_url, decode_responses=True)

import time
_RECENT_WRITES = {}

async def mark_write(identifier: str | int) -> None:
    """Called after a successful write (POST/PUT/PATCH/DELETE).
    Stores a short‑lived key so subsequent reads for the same user
    are forced onto the primary DB.
    """
    key = f"recent_write:{str(identifier)}"
    try:
        r = await _redis_client()
        await r.set(key, "1", ex=_REDIS_TTL_SECONDS)
    except Exception as e:
        log.warning(f"Failed to check recent write in Redis: {e}, using memory fallback")
        _RECENT_WRITES[key] = time.time() + _REDIS_TTL_SECONDS

async def _has_recent_write(identifier: str | int) -> bool:
    """Check if the user performed a write within the lag window."""
    key = f"recent_write:{str(identifier)}"
    try:
        r = await _redis_client()
        return bool(await r.get(key))
    except Exception as e:
        log.warning(f"Failed to check recent write in Redis: {e}, using memory fallback")
        return _RECENT_WRITES.get(key, 0) > time.time()

# ------------------------------------------------------------------
# 3️⃣ Dependency – get_db
# ------------------------------------------------------------------
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession bound to the correct
    engine based on the HTTP method and recent‑write guard.

    Usage in routers:
        async def my_endpoint(..., db: AsyncSession = Depends(get_db)):
            ...
    """
    use_primary = request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
    extracted_tenant_id = None
    extracted_username = None

    # Extraction Logic (Shared between primary/replica decision and RLS)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            extracted_username = payload.get("sub")
            extracted_tenant_id = payload.get("tid")
        except (JWTError, Exception):
            pass

    # Forced Primary Guard (Read-your-own-writes)
    if not use_primary and extracted_username:
        if await _has_recent_write(extracted_username):
            use_primary = True
            log.debug(f"Read‑your‑own‑writes guard: routing GET for user {extracted_username} to primary.")

    SessionMaker = PrimarySessionLocal if use_primary else (_ReplicaSessionLocal or PrimarySessionLocal)

    async with SessionMaker() as db:
        if extracted_tenant_id and settings.database_type == "postgresql":
            try:
                await db.execute(text("SET app.tenant_id = :tid"), {"tid": str(extracted_tenant_id)})
            except Exception as e:
                log.warning(f"Failed to set tenant_id handle RLS: {e}")

        try:
            yield db
        finally:
            await db.close()

# ------------------------------------------------------------------
# 4️⃣ Helper – write_guard decorator (optional convenience)
# ------------------------------------------------------------------
def write_guard(func):
    """Decorator for service methods that perform writes.
    It automatically calls `mark_write(user_id)` after a successful commit.
    The wrapped function must accept `request: Request` (or have it in scope)
    and must expose the affected `user_id` as the second positional argument
    after `db`.
    """
    async def wrapper(*args, **kwargs):
        if len(args) < 2:
            raise ValueError("write_guard expects at least (db, user_id, ...) args")
        db = args[0]
        user_id = args[1]
        result = await func(*args, **kwargs)
        await mark_write(user_id)
        return result
    return wrapper

# End of db_router.py
