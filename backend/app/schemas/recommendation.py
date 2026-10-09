"""
Pydantic schemas for Phase 17 Semantic Retrieval.
Defines strongly-typed models for candidate recommendation responses
and raw cosine semantic similarity scores.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.opportunity import OpportunityResponse


class SemanticOpportunityItem(OpportunityResponse):
    """
    Opportunity listing augmented with a raw cosine semantic similarity score.
    The semantic_similarity score reflects vector alignment in [-1.0, 1.0].
    It is not a probability, hiring percentage, or eligibility evaluation.
    """

    semantic_similarity: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description=(
            "Raw cosine similarity between candidate profile and opportunity vector (-1.0 to 1.0)"
        ),
    )

    model_config = ConfigDict(from_attributes=True)


class RecommendationListResponse(BaseModel):
    """Paginated collection of semantically retrieved opportunities."""

    items: list[SemanticOpportunityItem] = Field(
        default_factory=list,
        description="Ranked list of semantically similar opportunities",
    )
    total: int = Field(..., ge=0, description="Total count of eligible matching opportunities")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
