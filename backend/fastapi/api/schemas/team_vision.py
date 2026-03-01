"""
Pydantic schemas for Team Vision collaborative document management.
Isolated in team_vision.py to match PR references and router imports.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TeamVisionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., description="The team vision document content")


class TeamVisionCreate(TeamVisionBase):
    team_id: str


class TeamVisionUpdate(TeamVisionBase):
    version: int = Field(
        ...,
        description="Fencing token (current version) to prevent stale/lost updates"
    )
    lock_value: str = Field(
        ...,
        description=(
            "The exact lock token returned by /lock endpoint. "
            "Must match the active lease value in Redis for the write to proceed."
        )
    )


class TeamVisionResponse(TeamVisionBase):
    id: int
    team_id: str
    version: int
    updated_at: str
    last_modified_by_id: Optional[int] = None
    lock_status: Optional[dict] = None  # Populated at read-time with current lock holder info


class LockAcquireResponse(BaseModel):
    success: bool
    lock_value: Optional[str] = None  # Token the client must store and re-send on update
    message: str
    expires_in: int = 30  # Seconds until lock TTL expires


class LockReleaseRequest(BaseModel):
    lock_value: str = Field(..., description="The exact lock token to verify ownership before releasing")


class LockRenewRequest(BaseModel):
    lock_value: str = Field(..., description="The exact lock token to verify ownership before renewing")
    extend_by_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Number of seconds to extend the lock TTL (watchdog/heartbeat)"
    )


class LockRenewResponse(BaseModel):
    success: bool
    message: str
    new_expires_in: int = 0
