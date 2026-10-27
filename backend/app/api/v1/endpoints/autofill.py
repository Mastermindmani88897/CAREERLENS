"""
External Application Autofill API Endpoints for Phase 27.
Provides authenticated endpoints to prepare, inspect, and cancel autofill sessions.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.autofill import AutofillPrepareRequest, AutofillSessionResponse
from app.services.autofill import (
    AutofillDisabledError,
    AutofillSessionNotFoundError,
    CandidateProfileNotFoundError,
    InvalidURLError,
    OpportunityUnavailableError,
    ProhibitedDestinationError,
    ResumeNotFoundError,
    UnsupportedProviderError,
    cancel_autofill_session,
    get_autofill_session_by_id,
    prepare_autofill_session,
)

router = APIRouter()


@router.post(
    "/prepare",
    response_model=AutofillSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an external application autofill session",
    description=(
        "Validates external opportunity application URL, detects supported ATS provider, "
        "maps verified candidate profile/resume data, and creates or refreshes an active "
        "autofill session."
    ),
)
async def prepare_session(
    payload: AutofillPrepareRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutofillSessionResponse:
    try:
        session = await prepare_autofill_session(db, current_user, payload)
        return AutofillSessionResponse.model_validate(session)
    except AutofillDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    except (CandidateProfileNotFoundError, ResumeNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except OpportunityUnavailableError as exc:
        # Check if opportunity itself is missing vs inactive/invalid
        if "not found" in exc.message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        ) from exc
    except (InvalidURLError, ProhibitedDestinationError, UnsupportedProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.get(
    "/{session_id}",
    response_model=AutofillSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an autofill preparation session",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutofillSessionResponse:
    try:
        session = await get_autofill_session_by_id(db, session_id, current_user)
        return AutofillSessionResponse.model_validate(session)
    except AutofillSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/{session_id}/cancel",
    response_model=AutofillSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an active autofill session",
)
async def cancel_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutofillSessionResponse:
    try:
        session = await cancel_autofill_session(db, session_id, current_user)
        return AutofillSessionResponse.model_validate(session)
    except AutofillSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
