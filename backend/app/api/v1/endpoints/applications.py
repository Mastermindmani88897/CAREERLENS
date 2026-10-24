"""
Application Tracking API endpoints for Phase 21.

Provides authenticated endpoints for:
  - POST   /applications/            Create or save a new application
  - GET    /applications/            List candidate's applications (with status/search filter)
  - GET    /applications/transitions Get permitted status transition matrix
  - GET    /applications/{id}        Get full application detail with status history
  - PATCH  /applications/{id}/status Transition application status with validation
  - DELETE /applications/{id}        Delete or remove tracked application

Authentication: Bearer JWT required.
Ownership: Candidates can only access and modify their own applications.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.enums import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationListResponse,
    ApplicationStatusUpdate,
)
from app.services.application_service import (
    PERMITTED_TRANSITIONS,
    create_application,
    delete_application,
    get_application_by_id,
    list_applications,
    update_application_status,
)
from app.services.profile_service import get_profile_by_user_id

router = APIRouter()


async def _resolve_profile(db: AsyncSession, user: User):
    """Resolve candidate profile for authenticated user; raises 404 if not found."""
    profile = await get_profile_by_user_id(db, user.id, eager_load=False)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Candidate profile not found. "
                "Please create a candidate profile before tracking job applications."
            ),
        )
    return profile


@router.post(
    "/",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or save a job application",
    description=(
        "Track an application for an active opportunity. "
        "Rejects duplicate submissions for the same opportunity with 409 Conflict."
    ),
)
async def create_app_endpoint(
    payload: ApplicationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationDetailResponse:
    profile = await _resolve_profile(db, current_user)
    app_entity = await create_application(db, profile, payload)
    return ApplicationDetailResponse.model_validate(app_entity)


@router.get(
    "/",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tracked applications for authenticated candidate",
)
async def list_apps_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: ApplicationStatus | None = Query(
        None,
        description="Filter by status (saved, applied, oa, interview, offer, rejected, withdrawn)",
    ),
    search: str | None = Query(None, description="Search by opportunity title, company, or city"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ApplicationListResponse:
    profile = await _resolve_profile(db, current_user)
    return await list_applications(
        db=db,
        profile_id=profile.id,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/transitions",
    summary="Get permitted status transition matrix",
    description="Returns allowed transitions for each status in the lifecycle model.",
)
async def get_transitions_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, list[str]]:
    return {
        src.value: [target.value for target in targets]
        for src, targets in PERMITTED_TRANSITIONS.items()
    }


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single application detail with status history",
)
async def get_app_endpoint(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationDetailResponse:
    profile = await _resolve_profile(db, current_user)
    app_entity = await get_application_by_id(db, application_id, profile.id)
    return ApplicationDetailResponse.model_validate(app_entity)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application status and log audit history",
    description=(
        "Transitions application to a new status. "
        "Rejects invalid transitions with 422 Unprocessable Entity."
    ),
)
async def update_status_endpoint(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationDetailResponse:
    profile = await _resolve_profile(db, current_user)
    app_entity = await update_application_status(
        db=db,
        application_id=application_id,
        profile_id=profile.id,
        payload=payload,
    )
    return ApplicationDetailResponse.model_validate(app_entity)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tracked application",
)
async def delete_app_endpoint(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await _resolve_profile(db, current_user)
    await delete_application(db, application_id, profile.id)
