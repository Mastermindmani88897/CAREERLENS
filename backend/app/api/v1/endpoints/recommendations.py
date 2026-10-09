"""
Recommendation API endpoints for Phase 17 Semantic Retrieval.
Provides authenticated, personalized opportunity retrieval ranked by
raw vector cosine similarity to the candidate's professional profile.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.enums import EmploymentType, OpportunityType, WorkMode
from app.models.user import User
from app.schemas.recommendation import RecommendationListResponse
from app.services.recommendation_service import get_semantic_recommendations

router = APIRouter()


@router.get(
    "/",
    response_model=RecommendationListResponse,
    summary="Retrieve semantically ranked opportunity recommendations for current user",
)
async def list_recommendations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (1 to 100)"),
    opportunity_type: OpportunityType | None = Query(
        None, description="Filter by opportunity type (job, internship, hackathon)"
    ),
    work_mode: WorkMode | None = Query(
        None, description="Filter by work mode (remote, hybrid, onsite, any)"
    ),
    employment_type: EmploymentType | None = Query(None, description="Filter by employment type"),
    location: str | None = Query(
        None, max_length=100, description="Filter by city, state, or country substring"
    ),
) -> RecommendationListResponse:
    """
    Authenticated semantic retrieval endpoint.

    Compares the authenticated candidate's dense vector embedding against
    active opportunity embeddings in PostgreSQL using pgvector cosine distance.
    Returns results ordered by raw cosine similarity in [-1.0, 1.0].
    """
    return await get_semantic_recommendations(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        opportunity_type=opportunity_type,
        work_mode=work_mode,
        employment_type=employment_type,
        location=location,
    )
