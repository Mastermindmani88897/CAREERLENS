"""
Resume ingestion and extraction API endpoints for Phase 11.
Provides authenticated endpoints to upload, parse, and retrieve resumes.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.resume import (
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeResponse,
)
from app.services.resume_service import (
    get_resume_by_id_for_user,
    ingest_and_parse_resume,
    list_resumes_for_user,
    serialize_resume_model,
)

router = APIRouter()


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse resume document",
    description=(
        "Accepts a PDF, DOCX, or TXT resume, validates it defensively, "
        "extracts text deterministically, and stores structured metadata."
    ),
)
async def upload_resume(
    file: Annotated[UploadFile, File(description="Resume file (.pdf, .docx, .txt)")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeResponse:
    """
    Handle resume upload and deterministic parsing.

    Validates:
    - File extension and MIME type
    - File signature / magic bytes
    - Size limits (MAX_RESUME_SIZE_MB)
    - Rejection of executable code and scripts
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file stream.",
        ) from exc

    resume = await ingest_and_parse_resume(
        db=db,
        user=current_user,
        filename=file.filename,
        content=content,
        content_type=file.content_type,
    )

    return serialize_resume_model(resume)


@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve parsed resume details",
    description=(
        "Fetches structured parsed resume data for the specified ID. "
        "Restricted strictly to the resume owner."
    ),
)
async def get_resume_detail(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeDetailResponse:
    """
    Retrieve resume details and extraction payload.
    Guarantees that a user cannot access another user's resume.
    """
    resume = await get_resume_by_id_for_user(db=db, resume_id=resume_id, user=current_user)
    base_response = serialize_resume_model(resume)

    return ResumeDetailResponse(
        **base_response.model_dump(),
        raw_text=resume.raw_text,
        parsed_json=resume.parsed_json,
    )


@router.get(
    "",
    response_model=ResumeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List uploaded resumes",
    description="Returns all resumes uploaded by the current authenticated user.",
)
async def list_resumes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeListResponse:
    """List resumes for authenticated user."""
    resumes = await list_resumes_for_user(db=db, user=current_user)
    items = [serialize_resume_model(r) for r in resumes]
    return ResumeListResponse(items=items, total=len(items))
