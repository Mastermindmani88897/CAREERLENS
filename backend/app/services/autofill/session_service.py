"""
Autofill Session Orchestration Service for Phase 27.

Coordinates opportunity URL validation, ATS provider detection, candidate profile mapping,
and idempotent session persistence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.autofill import AutofillSession
from app.models.candidate import CandidateProfile, Resume
from app.models.enums import ATSProvider, AutofillSessionStatus
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.autofill import AutofillPrepareRequest
from app.services.autofill.exceptions import (
    AutofillDisabledError,
    AutofillSessionNotFoundError,
    CandidateProfileNotFoundError,
    OpportunityUnavailableError,
    ResumeNotFoundError,
    UnsupportedProviderError,
)
from app.services.autofill.payload_builder import build_normalized_autofill_payload
from app.services.autofill.provider_detector import detect_ats_provider
from app.services.autofill.url_validator import validate_external_application_url


async def prepare_autofill_session(
    db: AsyncSession,
    user: User,
    request: AutofillPrepareRequest,
) -> AutofillSession:
    """
    Validate and prepare an application autofill session for the authenticated candidate.

    Steps:
    1. Verify feature enablement flag (AUTOFILL_ENABLED).
    2. Eagerly load CandidateProfile with skills, educations, experiences.
    3. Verify Opportunity existence, active status, and presence of external job_url.
    4. Defensively validate job_url with strict HTTPS, domain allowlist, and SSRF/DNS inspection.
    5. Detect ATS provider (Greenhouse or Lever).
    6. Authorize and resolve active candidate Resume document.
    7. Build normalized field mapping and missing fields payload.
    8. Check for active unexpired session for same candidate+opportunity (idempotency policy).
    9. Persist session with safe diagnostic telemetry and expiration timestamp.
    """
    if not settings.AUTOFILL_ENABLED:
        raise AutofillDisabledError(
            "External application autofill preparation is currently disabled in system settings."
        )

    # 1. Load CandidateProfile with relations
    profile_stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.user_id == user.id)
        .options(
            selectinload(CandidateProfile.user),
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.educations),
            selectinload(CandidateProfile.experiences),
        )
    )
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise CandidateProfileNotFoundError(
            "Candidate profile not found. Please initialize your candidate profile "
            "before preparing an application."
        )

    # 2. Load Opportunity
    opp_stmt = select(Opportunity).where(Opportunity.id == request.opportunity_id)
    opp_result = await db.execute(opp_stmt)
    opp = opp_result.scalar_one_or_none()
    if opp is None:
        raise OpportunityUnavailableError(f"Opportunity '{request.opportunity_id}' not found.")
    if not opp.is_active:
        raise OpportunityUnavailableError(
            f"Opportunity '{opp.title}' is inactive and cannot be applied to."
        )
    if not opp.job_url:
        raise OpportunityUnavailableError(
            f"Opportunity '{opp.title}' does not have a registered external application URL."
        )

    # 3. Validate URL defensively
    canonical_url, verified_ips = validate_external_application_url(opp.job_url)

    # 4. Detect ATS provider
    detection = detect_ats_provider(canonical_url)
    if not detection.is_supported or detection.provider == ATSProvider.UNSUPPORTED:
        raise UnsupportedProviderError(
            f"The application URL '{canonical_url}' does not belong to a supported "
            "ATS provider (Greenhouse or Lever)."
        )

    # 5. Resolve Resume with ownership verification
    resume: Resume | None = None
    if request.resume_id is not None:
        resume_stmt = select(Resume).where(
            Resume.id == request.resume_id,
            Resume.candidate_profile_id == profile.id,
        )
        resume_result = await db.execute(resume_stmt)
        resume = resume_result.scalar_one_or_none()
        if resume is None:
            raise ResumeNotFoundError(
                f"Resume '{request.resume_id}' not found or does not belong to your "
                "candidate profile."
            )
    else:
        # Select latest active resume
        default_resume_stmt = (
            select(Resume)
            .where(
                Resume.candidate_profile_id == profile.id,
                Resume.is_active.is_(True),
            )
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        default_resume_res = await db.execute(default_resume_stmt)
        resume = default_resume_res.scalar_one_or_none()

    # 6. Build normalized payload
    norm_payload, missing_fields = build_normalized_autofill_payload(profile, resume)

    now = datetime.now(UTC)
    timeout_minutes = max(5, settings.AUTOFILL_SESSION_TIMEOUT_MINUTES)
    expires_at = now + timedelta(minutes=timeout_minutes)

    # 7. Check for compatible existing active session (Idempotency policy)
    existing_stmt = (
        select(AutofillSession)
        .where(
            AutofillSession.candidate_profile_id == profile.id,
            AutofillSession.opportunity_id == opp.id,
            AutofillSession.status.in_(
                [
                    AutofillSessionStatus.PREPARATION_PENDING.value,
                    AutofillSessionStatus.DATA_MAPPED.value,
                    AutofillSessionStatus.CANDIDATE_REVIEW.value,
                ]
            ),
            AutofillSession.expires_at > now,
        )
        .order_by(AutofillSession.created_at.desc())
    )
    existing_result = await db.execute(existing_stmt)
    existing_session = existing_result.scalars().first()

    if existing_session is not None and existing_session.target_url == canonical_url:
        # Reuse existing active session and refresh payload with latest profile data
        existing_session.normalized_payload = norm_payload
        existing_session.missing_fields = missing_fields
        existing_session.resume_id = resume.id if resume else None
        existing_session.expires_at = expires_at
        existing_session.updated_at = now
        await db.commit()
        await db.refresh(existing_session)
        return existing_session

    # 8. Create fresh session
    diag_meta = {
        "verified_ips": verified_ips,
        "board_slug": detection.board_slug,
        "external_job_id": detection.external_job_id,
        "is_direct_apply_page": detection.is_direct_apply_page,
    }

    session = AutofillSession(
        candidate_profile_id=profile.id,
        opportunity_id=opp.id,
        resume_id=resume.id if resume else None,
        ats_provider=detection.provider.value,
        target_url=canonical_url,
        status=AutofillSessionStatus.DATA_MAPPED.value,
        normalized_payload=norm_payload,
        missing_fields=missing_fields,
        diagnostic_metadata=diag_meta,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_autofill_session_by_id(
    db: AsyncSession,
    session_id: uuid.UUID,
    user: User,
) -> AutofillSession:
    """Retrieve an autofill session ensuring candidate ownership."""
    stmt = (
        select(AutofillSession)
        .join(CandidateProfile, AutofillSession.candidate_profile_id == CandidateProfile.id)
        .where(
            AutofillSession.id == session_id,
            CandidateProfile.user_id == user.id,
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise AutofillSessionNotFoundError(f"Autofill session '{session_id}' not found.")
    return session


async def cancel_autofill_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user: User,
) -> AutofillSession:
    """Cancel an active autofill session."""
    session = await get_autofill_session_by_id(db, session_id, user)
    session.status = AutofillSessionStatus.CANCELLED.value
    session.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(session)
    return session
