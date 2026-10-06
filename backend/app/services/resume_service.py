"""
Resume service orchestrating ingestion, validation, extraction, and persistence.
Adheres to Phase 11 boundaries:
- Secure untrusted file upload handling
- Isolated storage within RESUME_UPLOAD_DIR
- Deterministic extraction pipeline execution
- Reuses existing CandidateProfile and Resume ORM models
- Enforces strict user-level authorization
- Operational-only metadata logging
"""

import logging
import time
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile, Resume
from app.models.user import User
from app.schemas.resume import (
    ParsedResumeData,
    ResumeResponse,
    ResumeStatus,
)
from app.services.resume_parser import (
    MalformedFileError,
    NoExtractableTextError,
    PasswordProtectedFileError,
    ResumeParser,
    ResumeValidationError,
    generate_secure_storage_path,
    get_extractor,
    validate_resume_file,
)

logger = logging.getLogger(__name__)


async def get_or_create_candidate_profile(
    db: AsyncSession,
    user: User,
    full_name: str | None = None,
) -> CandidateProfile:
    """
    Retrieve existing CandidateProfile for user or initialize a minimal profile record.
    Preserves architectural boundary: does not collect unnecessary sensitive profile data.
    """
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile is None:
        default_name = full_name or user.email.split("@")[0].replace(".", " ").title()
        profile = CandidateProfile(
            user_id=user.id,
            full_name=default_name,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


def serialize_resume_model(resume: Resume) -> ResumeResponse:
    """Transform Resume ORM model to API response schema."""
    parsed_json = resume.parsed_json or {}
    status_str = parsed_json.get("status", ResumeStatus.PARSED.value)
    try:
        resume_status = ResumeStatus(status_str)
    except ValueError:
        resume_status = ResumeStatus.PARSED

    error_message = parsed_json.get("error_message")

    # If parsed successfully, reconstruct ParsedResumeData
    parsed_data = None
    if resume_status == ResumeStatus.PARSED and "contact" in parsed_json:
        try:
            parsed_data = ParsedResumeData.model_validate(parsed_json)
        except Exception:
            parsed_data = None

    return ResumeResponse(
        id=resume.id,
        candidate_profile_id=resume.candidate_profile_id,
        filename=resume.filename,
        file_type=resume.file_type,
        file_size_bytes=resume.file_size_bytes,
        status=resume_status,
        error_message=error_message,
        parsed_data=parsed_data,
        created_at=resume.created_at,
    )


async def ingest_and_parse_resume(
    db: AsyncSession,
    user: User,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> Resume:
    """
    Ingest, validate, extract, and persist an uploaded resume document.

    Raises:
        HTTPException 400: Validation failure (extension, size, magic bytes).
        HTTPException 422: No extractable text found (e.g. scanned PDF without OCR).
        HTTPException 400: Password-protected or corrupted file.
    """
    start_time = time.monotonic()

    # 1. Defensive validation
    try:
        file_type, sanitized_name = validate_resume_file(
            filename=filename,
            content=content,
            content_type=content_type,
        )
    except ResumeValidationError as exc:
        logger.warning(
            "Resume validation rejected: user_id=%s, reason=%s",
            user.id,
            exc.safe_message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.safe_message,
        ) from exc

    # 2. Secure file persistence
    secure_filename, storage_path = generate_secure_storage_path(sanitized_name)
    try:
        Path(storage_path).write_bytes(content)
    except Exception as exc:
        logger.error(
            "Failed to write resume file: user_id=%s, error_type=%s",
            user.id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded document.",
        ) from exc

    # 3. Ensure candidate profile
    profile = await get_or_create_candidate_profile(db, user)

    # 4. Text extraction with format-specific extractor
    raw_text: str | None = None
    extraction_error: str | None = None
    extractor = get_extractor(file_type)

    try:
        raw_text = extractor.extract_text(content)
    except NoExtractableTextError as exc:
        extraction_error = exc.safe_message
        # Create failed resume record to preserve upload audit trail
        resume = Resume(
            candidate_profile_id=profile.id,
            filename=sanitized_name,
            file_path=storage_path,
            file_type=file_type,
            file_size_bytes=len(content),
            raw_text="",
            parsed_json={
                "status": ResumeStatus.FAILED.value,
                "error_message": extraction_error,
            },
            is_active=False,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        logger.info(
            "Resume extraction yielded no text: resume_id=%s, file_type=%s, duration=%.3fs",
            resume.id,
            file_type,
            time.monotonic() - start_time,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=extraction_error,
        ) from exc

    except (PasswordProtectedFileError, MalformedFileError) as exc:
        extraction_error = exc.safe_message
        resume = Resume(
            candidate_profile_id=profile.id,
            filename=sanitized_name,
            file_path=storage_path,
            file_type=file_type,
            file_size_bytes=len(content),
            raw_text="",
            parsed_json={
                "status": ResumeStatus.FAILED.value,
                "error_message": extraction_error,
            },
            is_active=False,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        logger.info(
            "Resume extraction failed: resume_id=%s, error_category=%s",
            resume.id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=extraction_error,
        ) from exc

    # 5. Execute deterministic parsing pipeline
    normalized_text, parsed_data = ResumeParser.parse(raw_text)

    # 6. Persist successful resume record
    resume = Resume(
        candidate_profile_id=profile.id,
        filename=sanitized_name,
        file_path=storage_path,
        file_type=file_type,
        file_size_bytes=len(content),
        raw_text=raw_text,
        parsed_json=parsed_data.model_dump(mode="json"),
        is_active=True,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    duration = time.monotonic() - start_time
    logger.info(
        "Resume successfully parsed: resume_id=%s, file_type=%s, skills_found=%d, duration=%.3fs",
        resume.id,
        file_type,
        len(parsed_data.skills),
        duration,
    )

    return resume


async def get_resume_by_id_for_user(
    db: AsyncSession,
    resume_id: uuid.UUID,
    user: User,
) -> Resume:
    """
    Retrieve resume ensuring strict candidate ownership authorization.
    Rejects requests attempting to access another user's resume.
    """
    stmt = (
        select(Resume)
        .join(CandidateProfile, Resume.candidate_profile_id == CandidateProfile.id)
        .where(
            Resume.id == resume_id,
            CandidateProfile.user_id == user.id,
        )
    )
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if resume is None:
        # Check if resume exists for any user to log unauthorized access attempt
        check_stmt = select(Resume.id).where(Resume.id == resume_id)
        check_res = await db.execute(check_stmt)
        if check_res.scalar_one_or_none() is not None:
            logger.warning(
                "Unauthorized resume access attempt: user_id=%s, resume_id=%s",
                user.id,
                resume_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resume.",
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    return resume


async def list_resumes_for_user(
    db: AsyncSession,
    user: User,
) -> list[Resume]:
    """Retrieve all resumes uploaded by the authenticated user, ordered by creation date."""
    stmt = (
        select(Resume)
        .join(CandidateProfile, Resume.candidate_profile_id == CandidateProfile.id)
        .where(CandidateProfile.user_id == user.id)
        .order_by(Resume.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
