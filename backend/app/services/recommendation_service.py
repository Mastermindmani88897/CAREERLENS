"""
Recommendation service module for Phase 17 Semantic Retrieval.
Orchestrates authenticated candidate profile resolution, embedding freshness verification,
and pgvector cosine distance retrieval across active opportunities.
"""

import logging
import math
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EmploymentType, OpportunityType, WorkMode
from app.models.opportunity import Opportunity
from app.schemas.opportunity import OpportunityResponse
from app.schemas.recommendation import (
    RecommendationListResponse,
    SemanticOpportunityItem,
)
from app.services.embeddings import (
    generate_candidate_profile_embedding,
    is_candidate_embedding_stale,
)
from app.services.embeddings.text_normalizer import build_candidate_embedding_text
from app.services.profile_service import get_profile_by_user_id

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


async def get_semantic_recommendations(
    db: AsyncSession,
    user: "User",
    page: int = 1,
    page_size: int = 20,
    opportunity_type: OpportunityType | None = None,
    work_mode: WorkMode | None = None,
    employment_type: EmploymentType | None = None,
    location: str | None = None,
) -> RecommendationListResponse:
    """
    Retrieve active opportunities ordered by raw cosine similarity to the candidate's profile.

    Enforces:
    - User ownership and mandatory profile existence.
    - Content sufficiency verification before embedding calculation.
    - On-demand embedding generation for missing or stale profiles.
    - Preservation of previous valid vectors if on-demand regeneration fails.
    - Exclusion of inactive opportunities and opportunities with NULL vectors.
    - Deterministic tie-breaking on identical similarity scores.
    """
    # 1. Resolve candidate profile for authenticated user
    profile = await get_profile_by_user_id(db, user.id, eager_load=True)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Candidate profile not found. Please create a profile before "
                "requesting recommendations."
            ),
        )

    # 2. Check profile text sufficiency
    profile_text = build_candidate_embedding_text(
        profile,
        skills=profile.skills,
        experiences=profile.experiences,
        educations=profile.educations,
        projects=profile.projects,
        certifications=profile.certifications,
    )
    has_content = bool(profile_text.strip())

    # 3. Check embedding existence and freshness
    candidate_vector = profile.profile_embedding
    is_stale = is_candidate_embedding_stale(
        profile,
        skills=profile.skills,
        educations=profile.educations,
        experiences=profile.experiences,
        projects=profile.projects,
        certifications=profile.certifications,
    )

    if candidate_vector is None or is_stale:
        if has_content:
            new_vector = await generate_candidate_profile_embedding(db, profile.id, commit=True)
            if new_vector is not None:
                candidate_vector = new_vector
            elif candidate_vector is not None and any(x != 0.0 for x in candidate_vector):
                # Preservation semantics: fall back to previous valid vector if regeneration fails
                logger.warning(
                    "Embedding regeneration failed for candidate %s; using existing vector",
                    profile.id,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Candidate profile embedding could not be generated. "
                        "Please verify your profile details."
                    ),
                )
        else:
            # Profile has no content
            if candidate_vector is not None and any(x != 0.0 for x in candidate_vector):
                # Use existing vector if available
                pass
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Candidate profile has insufficient content for recommendations. "
                        "Please add skills, experience, or headline to your profile."
                    ),
                )

    if not candidate_vector or all(x == 0.0 for x in candidate_vector):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Candidate profile has insufficient content for recommendations. "
                "Please add skills, experience, or headline to your profile."
            ),
        )

    # 4. Construct SQL filters
    filters = [
        Opportunity.is_active.is_(True),
        Opportunity.job_embedding.is_not(None),
    ]

    if opportunity_type is not None:
        filters.append(Opportunity.opportunity_type == opportunity_type)

    if work_mode is not None:
        filters.append(Opportunity.work_mode == work_mode)

    if employment_type is not None:
        filters.append(Opportunity.employment_type == employment_type)

    if location and location.strip():
        loc_term = f"%{location.strip()}%"
        filters.append(
            or_(
                Opportunity.location_city.ilike(loc_term),
                Opportunity.location_state.ilike(loc_term),
                Opportunity.location_country.ilike(loc_term),
            )
        )

    # 5. Count eligible opportunities
    count_stmt = select(func.count(Opportunity.id)).where(*filters)
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    if total == 0:
        return RecommendationListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
        )

    # 6. Query opportunities ordered by cosine distance with deterministic tie-breaking
    distance_expr = Opportunity.job_embedding.cosine_distance(candidate_vector)
    offset = (page - 1) * page_size

    stmt = (
        select(Opportunity, distance_expr.label("distance"))
        .where(*filters)
        .order_by(
            distance_expr.asc(),
            Opportunity.posted_date.desc().nulls_last(),
            Opportunity.created_at.desc(),
            Opportunity.id.asc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # 7. Build response items with raw cosine similarity
    items: list[SemanticOpportunityItem] = []
    for opp, dist in rows:
        # Raw cosine similarity = 1.0 - cosine_distance, bounded strictly within [-1.0, 1.0]
        raw_similarity = round(max(-1.0, min(1.0, 1.0 - float(dist))), 4)
        opp_data = OpportunityResponse.model_validate(opp).model_dump()
        items.append(
            SemanticOpportunityItem(
                **opp_data,
                semantic_similarity=raw_similarity,
            )
        )

    return RecommendationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
