"""
Contact Us router for handling contact form submissions.
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
try:
    from app.core import NotFoundError, InternalServerError
except ImportError:
    from app.core import NotFoundError, InternalServerError

router = APIRouter(tags=["Contact"])


class ContactSubmissionRequest(BaseModel):
    """Request model for contact form submission."""
    name: str = Field(..., min_length=2, max_length=100, description="Sender's full name")
    email: EmailStr = Field(..., description="Sender's email address")
    subject: str = Field(..., min_length=5, max_length=200, description="Message subject")
    message: str = Field(..., min_length=10, max_length=2000, description="Message content")


class ContactSubmissionResponse(BaseModel):
    """Response model for a contact submission."""
    id: str
    name: str
    email: str
    subject: str
    message: str
    timestamp: str
    read: bool


class SubmitSuccessResponse(BaseModel):
    """Response model for successful submission."""
    success: bool = True
    message: str = "Your message has been received. We'll get back to you soon!"
    submission_id: str


@router.post("/submit", response_model=SubmitSuccessResponse)
async def submit_contact_form(data: ContactSubmissionRequest):
    """
    Submit a contact form message.
    
    The submission is stored in a JSON file for later review.
    """
    try:
        submission = await contact_service.create(
            name=data.name,
            email=data.email,
            subject=data.subject,
            message=data.message
        )
        
        return SubmitSuccessResponse(
            submission_id=submission["id"]
        )
    except Exception as e:
        raise InternalServerError(
            message="Failed to submit contact form",
            details=[{"code": "CONTACT_ERROR", "error": str(e)}]
        )


@router.get("/submissions")
async def get_contact_submissions(
    limit: int = Query(default=100, ge=1, le=500, description="Maximum submissions to return"),
    offset: int = Query(default=0, ge=0, description="Number of submissions to skip"),
    unread_only: bool = Query(default=False, description="Filter to only unread submissions")
):
    """
    Get all contact form submissions (admin endpoint).
    
    Returns paginated list of submissions sorted by timestamp (newest first).
    """
    try:
        result = await contact_service.get_all(
            limit=limit,
            offset=offset,
            unread_only=unread_only
        )
        return result
    except Exception as e:
        raise InternalServerError(
            message="Failed to fetch submissions",
            details=[{"code": "FETCH_ERROR", "error": str(e)}]
        )


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str):
    """Get a specific submission by ID."""
    submission = await contact_service.get_by_id(submission_id)
    
    if not submission:
        raise NotFoundError(resource="Submission", resource_id=submission_id)
    
    return submission


@router.patch("/submissions/{submission_id}/read")
async def mark_submission_read(submission_id: str):
    """Mark a submission as read."""
    submission = await contact_service.mark_read(submission_id)
    
    if not submission:
        raise NotFoundError(resource="Submission", resource_id=submission_id)
    
    return {"success": True, "submission": submission}


@router.delete("/submissions/{submission_id}")
async def delete_submission(submission_id: str):
    """Delete a submission by ID."""
    deleted = await contact_service.delete(submission_id)
    
    if not deleted:
        raise NotFoundError(resource="Submission", resource_id=submission_id)
    
    return {"success": True, "message": "Submission deleted"}
