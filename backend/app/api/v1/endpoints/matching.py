"""
Matching API endpoints for Phase 19 Hybrid Matching Engine.

Provides authenticated endpoints for:
  - POST /matches/evaluate      Evaluate hybrid matches (batch or discovery, limit <= 100)
  - POST /matches/              Trigger hybrid match evaluation for one opportunity
  - GET  /matches/              List all persisted matches for candidate (paginated)
  - GET  /matches/{identifier}  Retrieve match by opportunity_id or match_id (ownership)

Authentication: Bearer JWT required for all endpoints.
Ownership: Candidates may only access their own match records.
"""

from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.enums import EligibilityStatus
from app.models.opportunity import Opportunity
from app.models.tracking import Match
from app.models.user import User
from app.schemas.matching import (
    MatchEvaluateRequest,
    MatchListResponse,
    MatchResponse,
    MatchSummaryResponse,
    MatchTriggerRequest,
)
from app.services.matching_service import compute_and_persist_match
from app.services.profile_service import get_profile_by_user_id

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_profile(db: AsyncSession, user: User):
    """Resolve the CandidateProfile for an authenticated user (eager-loads sub-entities)."""
    profile = await get_profile_by_user_id(db, user.id, eager_load=True)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Candidate profile not found. "
                "Please create a profile before requesting match evaluations."
            ),
        )
    return profile


async def _resolve_opportunity(db: AsyncSession, opportunity_id: uuid.UUID) -> Opportunity:
    """Fetch an active Opportunity by id, including its OpportunitySkill rows."""
    stmt = (
        select(Opportunity)
        .options(selectinload(Opportunity.skills))
        .where(Opportunity.id == opportunity_id)
    )
    result = await db.execute(stmt)
    opp: Opportunity | None = result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found.",
        )
    if not opp.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Opportunity {opportunity_id} is inactive and cannot be evaluated.",
        )
    return opp


async def _resolve_match_owned(
    db: AsyncSession,
    identifier: uuid.UUID,
    profile_id: uuid.UUID,
) -> Match:
    """
    Fetch a Match by opportunity_id or match_id; enforce candidate ownership.
    Returns 404 with helpful detail if no match has been computed.
    """
    # 1. First check if identifier matches an opportunity_id for this profile
    stmt = select(Match).where(
        Match.opportunity_id == identifier,
        Match.candidate_profile_id == profile_id,
    )
    result = await db.execute(stmt)
    match: Match | None = result.scalar_one_or_none()

    # 2. Fall back to match_id
    if match is None:
        stmt = select(Match).where(
            Match.id == identifier,
            Match.candidate_profile_id == profile_id,
        )
        result = await db.execute(stmt)
        match = result.scalar_one_or_none()

    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No match evaluation found for opportunity or match {identifier}. "
                "Trigger evaluation via POST /api/v1/matches/evaluate or POST /api/v1/matches/."
            ),
        )
    return match


# ---------------------------------------------------------------------------
# POST /matches/evaluate — batch or discovery match evaluation
# ---------------------------------------------------------------------------


@router.post(
    "/evaluate",
    response_model=MatchListResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate hybrid matches across opportunities (batch or active discovery)",
    description=(
        "Evaluates hybrid match scores across a specified list of opportunity_ids "
        "or up to `limit` active opportunities (capped at 100). Persists each result idempotently."
    ),
)
async def evaluate_matches(
    payload: MatchEvaluateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchListResponse:
    """Evaluate and persist hybrid matches across opportunities."""
    profile = await _resolve_profile(db, current_user)
    limit = min(payload.limit, 100)
    sem_sim = payload.semantic_similarity or 0.0

    if payload.opportunity_ids:
        opp_ids = payload.opportunity_ids[:limit]
        stmt = (
            select(Opportunity)
            .options(selectinload(Opportunity.skills))
            .where(Opportunity.id.in_(opp_ids), Opportunity.is_active.is_(True))
        )
    else:
        stmt = (
            select(Opportunity)
            .options(selectinload(Opportunity.skills))
            .where(Opportunity.is_active.is_(True))
            .order_by(Opportunity.created_at.desc())
            .limit(limit)
        )

    result = await db.execute(stmt)
    opps = result.scalars().all()

    eval_matches: list[Match] = []
    for opp in opps:
        m = await compute_and_persist_match(
            db=db,
            profile=profile,
            opportunity=opp,
            semantic_similarity=sem_sim,
            commit=False,
        )
        eval_matches.append(m)

    await db.commit()
    for m in eval_matches:
        await db.refresh(m)

    eval_matches.sort(key=lambda x: (x.final_score, x.computed_at), reverse=True)

    return MatchListResponse(
        items=[MatchSummaryResponse.model_validate(m) for m in eval_matches],
        total=len(eval_matches),
        page=1,
        page_size=limit,
        total_pages=1 if eval_matches else 0,
    )


# ---------------------------------------------------------------------------
# POST /matches/ — trigger single hybrid match evaluation
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger hybrid match evaluation for one opportunity",
    description=(
        "Compute and persist a hybrid match score between the authenticated "
        "candidate's profile and the specified opportunity. Idempotent: re-triggering "
        "the same pair overwrites the previous result with refreshed scores."
    ),
)
async def trigger_match(
    payload: MatchTriggerRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchResponse:
    """Evaluate and persist a hybrid match for the authenticated candidate."""
    profile = await _resolve_profile(db, current_user)
    opportunity = await _resolve_opportunity(db, payload.opportunity_id)

    match_record = await compute_and_persist_match(
        db=db,
        profile=profile,
        opportunity=opportunity,
        semantic_similarity=payload.semantic_similarity,
        commit=True,
    )
    return MatchResponse.model_validate(match_record)


# ---------------------------------------------------------------------------
# GET /matches/ — list all matches for authenticated candidate
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=MatchListResponse,
    summary="List persisted match evaluations for the authenticated candidate",
)
async def list_matches(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (1 to 100)"),
    eligibility_status: EligibilityStatus | None = Query(
        None,
        description="Filter by eligibility status (eligible, partial, review_required)",
    ),
    min_score: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum final_score threshold (inclusive)",
    ),
) -> MatchListResponse:
    """Retrieve paginated match records for the authenticated candidate, ordered by score."""
    profile = await _resolve_profile(db, current_user)

    filters = [Match.candidate_profile_id == profile.id]
    if eligibility_status is not None:
        filters.append(Match.eligibility_status == eligibility_status)
    if min_score is not None:
        filters.append(Match.final_score >= min_score)

    count_stmt = select(func.count(Match.id)).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    if total == 0:
        return MatchListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
        )

    offset = (page - 1) * page_size
    stmt = (
        select(Match)
        .where(*filters)
        .order_by(Match.final_score.desc(), Match.computed_at.desc(), Match.id.asc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    matches = result.scalars().all()

    return MatchListResponse(
        items=[MatchSummaryResponse.model_validate(m) for m in matches],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# GET /matches/{identifier} — retrieve by opportunity_id or match_id
# ---------------------------------------------------------------------------


@router.get(
    "/{identifier}",
    response_model=MatchResponse,
    summary="Retrieve an existing match evaluation by opportunity_id or match_id",
)
async def get_match(
    identifier: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchResponse:
    """Return full match details for the given opportunity_id or match_id if owned by candidate."""
    profile = await _resolve_profile(db, current_user)
    match_record = await _resolve_match_owned(db, identifier, profile.id)
    return MatchResponse.model_validate(match_record)
