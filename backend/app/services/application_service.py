"""
Application Tracking Service for Phase 21.

Implements business logic, lifecycle state transitions, duplicate prevention,
and audit trail logging for candidate applications.
"""

from __future__ import annotations

import math
import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import cache, make_applications_list_key
from app.models.candidate import CandidateProfile
from app.models.enums import ApplicationStatus
from app.models.opportunity import Opportunity
from app.models.tracking import Application, ApplicationStatusHistory
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)

# ---------------------------------------------------------------------------
# Permitted Status Transitions State Machine
# ---------------------------------------------------------------------------

PERMITTED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.SAVED: {
        ApplicationStatus.APPLIED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.APPLIED: {
        ApplicationStatus.OA,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OA: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.INTERVIEW,  # Subsequent interview round
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.REJECTED,  # Declined offer
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REJECTED: set(),  # Terminal state
    ApplicationStatus.WITHDRAWN: set(),  # Terminal state
}


def get_permitted_transitions(current_status: ApplicationStatus) -> list[str]:
    """Return permitted target status values for a given application status."""
    return [s.value for s in PERMITTED_TRANSITIONS.get(current_status, set())]


# ---------------------------------------------------------------------------
# Service operations
# ---------------------------------------------------------------------------


async def create_application(
    db: AsyncSession,
    profile: CandidateProfile,
    payload: ApplicationCreate,
) -> Application:
    """
    Create a new application record for the authenticated candidate.
    Enforces uniqueness per candidate-opportunity pair (prevents duplicate submission).
    """
    # 1. Verify opportunity exists and is active
    opp_stmt = select(Opportunity).where(Opportunity.id == payload.opportunity_id)
    opp_result = await db.execute(opp_stmt)
    opp = opp_result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {payload.opportunity_id} not found.",
        )
    if not opp.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Opportunity {payload.opportunity_id} is inactive and cannot be applied to.",
        )

    # 2. Check for duplicate application
    dup_stmt = select(Application).where(
        Application.candidate_profile_id == profile.id,
        Application.opportunity_id == payload.opportunity_id,
    )
    dup_result = await db.execute(dup_stmt)
    existing = dup_result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An application for opportunity '{opp.title}' already exists "
                f"with status '{existing.status.value}'."
            ),
        )

    # 3. Determine applied date
    applied_date = payload.applied_date
    if payload.status == ApplicationStatus.APPLIED and applied_date is None:
        applied_date = date.today()

    # 4. Construct application entity
    application = Application(
        candidate_profile_id=profile.id,
        opportunity_id=payload.opportunity_id,
        status=payload.status,
        applied_date=applied_date,
        notes=payload.notes,
    )
    db.add(application)
    await db.flush()

    # 5. Record initial status history audit entry
    history = ApplicationStatusHistory(
        application_id=application.id,
        status=payload.status,
        notes=payload.notes or "Initial application status record.",
    )
    db.add(history)

    await db.commit()
    await cache.invalidate_prefix(f"apps:list:{profile.id}")

    # Refresh with eager opportunity relation
    return await get_application_by_id(db, application.id, profile.id)


async def update_application_status(
    db: AsyncSession,
    application_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
) -> Application:
    """
    Update application status enforcing permitted lifecycle transitions.
    Appends an immutable entry to ApplicationStatusHistory.
    """
    application = await get_application_by_id(db, application_id, profile_id)

    current_status = application.status
    target_status = payload.status

    # Validate transition
    if target_status != current_status:
        allowed = PERMITTED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid status transition from '{current_status.value}' "
                    f"to '{target_status.value}'. "
                    f"Permitted transitions from '{current_status.value}': "
                    f"{[s.value for s in allowed]}"
                ),
            )

    # Update applied_date if transitioning to applied and not previously set
    if target_status == ApplicationStatus.APPLIED and application.applied_date is None:
        application.applied_date = date.today()

    application.status = target_status
    if payload.notes is not None:
        application.notes = payload.notes

    # Append audit trail
    history = ApplicationStatusHistory(
        application_id=application.id,
        status=target_status,
        notes=payload.notes
        or (f"Transitioned from {current_status.value} to {target_status.value}."),
    )
    db.add(history)

    await db.commit()
    await cache.invalidate_prefix(f"apps:list:{profile_id}")
    return await get_application_by_id(db, application_id, profile_id)


async def get_application_by_id(
    db: AsyncSession,
    application_id: uuid.UUID,
    profile_id: uuid.UUID,
) -> Application:
    """Fetch an application with eager loaded relations; enforces candidate ownership."""
    stmt = (
        select(Application)
        .options(
            selectinload(Application.opportunity),
            selectinload(Application.status_history),
        )
        .where(
            Application.id == application_id,
            Application.candidate_profile_id == profile_id,
        )
    )
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found.",
        )
    return application


async def list_applications(
    db: AsyncSession,
    profile_id: uuid.UUID,
    status_filter: ApplicationStatus | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ApplicationListResponse:
    """Retrieve paginated application records for the candidate with filtering and search."""
    cache_params = {
        "status_filter": status_filter.value if status_filter else None,
        "search": search.strip().lower() if search else None,
        "page": page,
        "page_size": page_size,
    }
    cache_key = make_applications_list_key(profile_id, cache_params)
    cached_list = await cache.get(cache_key)
    if cached_list is not None:
        return cached_list

    filters = [Application.candidate_profile_id == profile_id]

    if status_filter is not None:
        filters.append(Application.status == status_filter)

    query = select(Application).join(Application.opportunity).where(*filters)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Opportunity.title).like(term),
                func.lower(Opportunity.company).like(term),
                func.lower(Opportunity.location_city).like(term),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    if total == 0:
        return ApplicationListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
        )

    offset = (page - 1) * page_size
    items_stmt = (
        query.options(selectinload(Application.opportunity))
        .order_by(Application.updated_at.desc(), Application.id.asc())
        .offset(offset)
        .limit(page_size)
    )
    items_result = await db.execute(items_stmt)
    apps = items_result.scalars().all()

    response = ApplicationListResponse(
        items=[ApplicationResponse.model_validate(a) for a in apps],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    await cache.set(cache_key, response, ttl=60.0)
    return response


async def delete_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    profile_id: uuid.UUID,
) -> None:
    """Delete an application record owned by the candidate."""
    application = await get_application_by_id(db, application_id, profile_id)
    await db.delete(application)
    await db.commit()
    await cache.invalidate_prefix(f"apps:list:{profile_id}")
