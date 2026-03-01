"""API router for Team Vision collaborative document management."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from ..services.db_service import get_db
from ..models import TeamVisionDocument, User
from .auth import get_current_user
from ..utils.redlock import redlock_service
from ..schemas.team_vision import (
    TeamVisionResponse, TeamVisionCreate, TeamVisionUpdate,
    LockAcquireResponse, LockReleaseRequest,
    LockRenewRequest, LockRenewResponse
)

logger = logging.getLogger("api.routers.team_vision")

router = APIRouter(tags=["Team EI - Vision Documents"])


@router.get("/{document_id}", response_model=TeamVisionResponse)
async def get_team_vision(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Fetches a document and its current lock status.
    The UI uses lock_status to switch between Edit and Read-Only modes.
    """
    stmt = select(TeamVisionDocument).filter(TeamVisionDocument.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Team Vision Document not found")

    lock_info = await redlock_service.get_lock_info(str(document_id))

    response_dict = doc.to_dict()
    # Strip the internal lock_value from public response (only expose user_id + expires_in)
    if lock_info:
        response_dict["lock_status"] = {
            "user_id": lock_info["user_id"],
            "expires_in": lock_info["expires_in"]
        }
    else:
        response_dict["lock_status"] = None

    return TeamVisionResponse(**response_dict)


@router.post("/{document_id}/lock", response_model=LockAcquireResponse)
async def acquire_vision_lock(
    document_id: int,
    ttl_seconds: int = 30,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Acquires an exclusive edit lock for the document using single-instance
    Redis locking (SET NX EX). Returns a `lock_value` token the client MUST
    store and present on every subsequent PUT or /renew call.

    Returns 200 with success=False if another user currently holds the lock.
    """
    success, lock_val = await redlock_service.acquire_lock(
        str(document_id), current_user.id, ttl_seconds
    )

    if not success:
        return LockAcquireResponse(
            success=False,
            message="Document is currently being edited by another user.",
            expires_in=0
        )

    return LockAcquireResponse(
        success=True,
        lock_value=lock_val,
        message="Lock acquired. Store the lock_value — you must send it with every update and /renew call.",
        expires_in=ttl_seconds
    )


@router.post("/{document_id}/renew", response_model=LockRenewResponse)
async def renew_vision_lock(
    document_id: int,
    req: LockRenewRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Watchdog / Heartbeat endpoint.
    Extends the TTL of an active lock so long editing sessions do not
    silently lose their lock mid-edit. The client should call this every
    ~20 seconds (when the default TTL is 30 seconds).

    The lock_value token is validated atomically via a Lua script before
    the TTL is extended, preventing any other user from hijacking the lease.
    Returns 403 if the token is invalid or the lock already expired.
    """
    success = await redlock_service.renew_lock(
        str(document_id), req.lock_value, req.extend_by_seconds
    )

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Lock renewal failed: invalid token or lock has already expired."
        )

    return LockRenewResponse(
        success=True,
        message=f"Lock extended by {req.extend_by_seconds}s.",
        new_expires_in=req.extend_by_seconds
    )


@router.post("/{document_id}/unlock")
async def release_vision_lock(
    document_id: int,
    req: LockReleaseRequest,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Releases the lock using the exact lock_value token (Lua-script-atomic,
    TOCTOU-safe). Returns 403 if the token is invalid or the lock expired.
    """
    success = await redlock_service.release_lock(str(document_id), req.lock_value)
    if not success:
        raise HTTPException(
            status_code=403,
            detail="Failed to release lock: invalid token or lock already expired."
        )
    return {"message": "Lock released successfully."}


@router.put("/{document_id}", response_model=TeamVisionResponse)
async def update_team_vision(
    document_id: int,
    update_data: TeamVisionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Saves changes to a Team Vision document.
    Enforces TWO independent safety layers:

    Layer 1 — Lock Token Check (Exact lease-value equality):
        The `lock_value` in the request must match the active Redis lease value
        exactly. This is stricter than user-id-only checks and proves the caller
        still holds the specific lease they acquired.

    Layer 2 — Fencing Token (Monotonic version check):
        The `version` in the request must match the current DB version.
        Even if a lock expires and is acquired by someone else, the version
        mismatch catches any stale write attempt (final safety net).
    """
    # --- LAYER 1: Exact lock_value equality (not just user_id) ---
    lock_info = await redlock_service.get_lock_info(str(document_id))

    if not lock_info:
        raise HTTPException(
            status_code=423,  # Locked
            detail="No active lock found. Acquire the lock before editing."
        )

    # Validate exact token match (reviewer gap #2 fix)
    if lock_info["lock_value"] != update_data.lock_value:
        raise HTTPException(
            status_code=403,
            detail="Lock token mismatch. Your lease may have expired or been acquired by another session."
        )

    # Sanity-check: the token's embedded user_id must also match (defence-in-depth)
    if lock_info["user_id"] != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not own the current lock on this document."
        )

    # --- Fetch current record ---
    stmt = select(TeamVisionDocument).filter(TeamVisionDocument.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # --- LAYER 2: Fencing Token (version must match exactly) ---
    if doc.version != update_data.version:
        raise HTTPException(
            status_code=409,  # Conflict
            detail=(
                f"Stale update rejected. Server version is {doc.version}, "
                f"you sent {update_data.version}. Refresh the document and retry."
            )
        )

    # --- Perform update and increment fencing token ---
    doc.title = update_data.title
    doc.content = update_data.content
    doc.version += 1  # Monotonic increment — next writer must present this new value
    doc.last_modified_by_id = current_user.id

    await db.commit()
    await db.refresh(doc)

    return TeamVisionResponse(**doc.to_dict())


@router.post("/", response_model=TeamVisionResponse)
async def create_team_vision(
    data: TeamVisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """Creates a new Team Vision document."""
    doc = TeamVisionDocument(
        team_id=data.team_id,
        title=data.title,
        content=data.content,
        version=1,
        last_modified_by_id=current_user.id
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return TeamVisionResponse(**doc.to_dict())
