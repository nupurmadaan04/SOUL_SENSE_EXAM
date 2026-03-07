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
import asyncio
from datetime import timedelta
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from jose import jwt, JWTError
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from ..config import get_settings_instance
from .replica_lag_monitor import init_lag_monitor, get_lag_monitor

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 1️⃣ Engine / Session creation
# ------------------------------------------------------------------
settings = get_settings_instance()

# Engine kwargs helper: SQLite does not accept queue pool arguments
def _build_engine_kwargs() -> dict:
    kwargs = {
        "echo": settings.debug,
        "future": True,
    }
    if settings.database_type == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(
            {
                "pool_size": 20,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
        )
    return kwargs

# Primary (write) engine – always present with optimized connection pooling
_primary_engine = create_async_engine(
    settings.async_database_url,
    **_build_engine_kwargs(),
)
PrimarySessionLocal = async_sessionmaker(
    _primary_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Replica (read) engine – optional with optimized connection pooling
_ReplicaSessionLocal: Optional[async_sessionmaker] = None
if settings.async_replica_database_url:
    replica_kwargs = _build_engine_kwargs()
    if settings.database_type != "sqlite":
        replica_kwargs.update(
            {
                "pool_size": 30,
                "max_overflow": 15,
            }
        )
    _replica_engine = create_async_engine(
        settings.async_replica_database_url,
        **replica_kwargs,
    )
    _ReplicaSessionLocal = async_sessionmaker(
        _replica_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    log.info("Read‑replica engine initialised with optimized connection pooling.")
    
    # Initialize replica lag monitor if lag detection is enabled
    if settings.enable_replica_lag_detection:
        _replica_lag_monitor = init_lag_monitor(
            replica_engine=_replica_engine,
            primary_engine=_primary_engine
        )
        log.info(
            f"Replica lag monitoring enabled: "
            f"threshold={settings.replica_lag_threshold_ms}ms, "
            f"interval={settings.replica_lag_check_interval_seconds}s"
        )
    else:
        log.info("Replica lag monitoring disabled by configuration")
else:
    log.warning("No replica_database_url configured – all reads will hit primary.")

try:
    from sqlalchemy import event

    def _pool_connect(dbapi_con, con_record):
        log.debug("Pool connect: %s", con_record)

    def _pool_checkout(dbapi_con, con_record, con_proxy):
        log.debug("Pool checkout: %s", con_record)

    def _pool_checkin(dbapi_con, con_record):
        log.debug("Pool checkin: %s", con_record)

    if hasattr(_primary_engine, "sync_engine") and getattr(_primary_engine.sync_engine, "pool", None) is not None:
        event.listen(_primary_engine.sync_engine.pool, "connect", _pool_connect)
        event.listen(_primary_engine.sync_engine.pool, "checkout", _pool_checkout)
        event.listen(_primary_engine.sync_engine.pool, "checkin", _pool_checkin)

    if _ReplicaSessionLocal and hasattr(_replica_engine, "sync_engine") and getattr(_replica_engine.sync_engine, "pool", None) is not None:
        event.listen(_replica_engine.sync_engine.pool, "connect", _pool_connect)
        event.listen(_replica_engine.sync_engine.pool, "checkout", _pool_checkout)
        event.listen(_replica_engine.sync_engine.pool, "checkin", _pool_checkin)
except Exception:
    log.debug("Replica/Primary pool event logging not enabled")

# ------------------------------------------------------------------
# 2️⃣ Redis helper – recent‑write guard
# ------------------------------------------------------------------
_REDIS_TTL_SECONDS = 5  # how long we consider a write “fresh”

async def _redis_client() -> redis.Redis:
    """Lazy‑init a Redis connection (same URL used by CacheService)."""
    return redis.from_url(
        settings.redis_url, 
        decode_responses=True,
        socket_timeout=1.0,
        socket_connect_timeout=1.0,
        retry_on_timeout=False
    )

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
    existing_session = getattr(request.state, "db_session", None)
    if existing_session is not None:
        yield existing_session
        return

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
    
    # Replica Lag Check - fallback to primary if unhealthy
    if not use_primary and _ReplicaSessionLocal:
        lag_monitor = get_lag_monitor()
        if lag_monitor:
            # Periodically check lag (async background check)
            if not lag_monitor.is_replica_healthy():
                use_primary = True
                log.warning(
                    "Replica lag exceeds threshold or replica unhealthy - "
                    f"routing read to primary (lag: {lag_monitor._last_lag_ms}ms)"
                )
        elif settings.enable_replica_lag_detection:
            # Lag detection enabled but monitor not initialized - fail safe to primary
            use_primary = True
            log.warning("Replica lag detection enabled but monitor not initialized - routing to primary")

    SessionMaker = PrimarySessionLocal if use_primary else (_ReplicaSessionLocal or PrimarySessionLocal)

    timeout_seconds = int(getattr(settings, "db_request_timeout_seconds", 30))

    async with SessionMaker() as db:
        request.state.db_session = db
        if extracted_tenant_id and settings.database_type == "postgresql":
            try:
                await db.execute(text("SET app.tenant_id = :tid"), {"tid": str(extracted_tenant_id)})
            except Exception as e:
                log.warning(f"Failed to set tenant_id handle RLS: {e}")

        try:
            async with asyncio.timeout(timeout_seconds):
                yield db
        except TimeoutError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database operation timed out",
            ) from exc
        except Exception:
            await db.rollback()
            raise
        finally:
            if getattr(request.state, "db_session", None) is db:
                delattr(request.state, "db_session")
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
