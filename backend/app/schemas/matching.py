"""
Pydantic schemas for Phase 19 Hybrid Matching Engine.

Defines strongly typed request/response models for:
  - Single-match trigger payloads
  - Six-factor score breakdowns
  - Eligibility status and warnings
  - Match response (single and paginated list)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EligibilityStatus

# ---------------------------------------------------------------------------
# Score breakdown sub-schemas
# ---------------------------------------------------------------------------


class SkillOverlapBreakdown(BaseModel):
    """Skill overlap factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    required_count: int = Field(..., ge=0)
    preferred_count: int = Field(..., ge=0)
    matched_required: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    matched_preferred: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)


class ExperienceBreakdown(BaseModel):
    """Experience factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    candidate_total_years: float = Field(..., ge=0.0)
    required_min_years: int | None = None
    required_max_years: int | None = None
    is_overqualified: bool = False
    experience_gap_years: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class EducationBreakdown(BaseModel):
    """Education factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    required_level: str
    candidate_highest_level: str
    meets_requirement: bool
    warnings: list[str] = Field(default_factory=list)


class LocationWorkModeBreakdown(BaseModel):
    """Location and work-mode factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    opportunity_work_mode: str
    candidate_preferred_work_mode: str
    open_to_relocation: bool
    warnings: list[str] = Field(default_factory=list)


class EmploymentTypeBreakdown(BaseModel):
    """Employment type factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    opportunity_employment_type: str
    candidate_preferred_employment_type: str
    is_match: bool
    warnings: list[str] = Field(default_factory=list)


class ScoringWeights(BaseModel):
    """Factor weights used in the final hybrid score calculation."""

    skill_overlap: float
    experience: float
    education: float
    location_work_mode: float
    employment_type: float
    semantic_similarity: float


class ScoreBreakdown(BaseModel):
    """Full six-factor score breakdown."""

    weights: ScoringWeights
    skill_overlap: SkillOverlapBreakdown
    experience: ExperienceBreakdown
    education: EducationBreakdown
    location_work_mode: LocationWorkModeBreakdown
    employment_type: EmploymentTypeBreakdown
    semantic_similarity_normalized: float = Field(..., ge=0.0, le=1.0)
    semantic_similarity_raw: float = Field(..., ge=-1.0, le=1.0)


class MatchExplanation(BaseModel):
    """Human-readable strengths and gaps."""

    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    """Skill gap analysis: matched and missing skills."""

    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Match response schemas
# ---------------------------------------------------------------------------


class MatchResponse(BaseModel):
    """Full hybrid match evaluation result for a single candidate-opportunity pair."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    opportunity_id: uuid.UUID

    semantic_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Semantic similarity normalized to [0.0, 1.0] and weighted at 5% of final score"
        ),
    )
    deterministic_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic factor score (excludes semantic component)",
    )
    final_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted composite hybrid score",
    )

    eligibility_status: EligibilityStatus = Field(
        ...,
        description="Eligibility determination: eligible, partial, or review_required",
    )
    eligibility_warnings: list[str] | None = Field(
        None,
        description="Structured warnings explaining eligibility constraints or mismatches",
    )

    score_breakdown: dict[str, Any] = Field(
        ...,
        description="Full six-factor score breakdown with per-factor details",
    )
    explanation: dict[str, Any] = Field(
        ...,
        description="Human-readable strengths and gaps",
    )
    skill_gap: dict[str, Any] = Field(
        ...,
        description="Matched and missing required/preferred skills",
    )
    computed_at: datetime = Field(..., description="Timestamp when match was last computed")


class MatchSummaryResponse(BaseModel):
    """Lightweight match summary for list endpoints (omits raw breakdown details)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    opportunity_id: uuid.UUID
    final_score: float = Field(..., ge=0.0, le=1.0)
    eligibility_status: EligibilityStatus
    eligibility_warnings: list[str] | None = None
    computed_at: datetime


# ---------------------------------------------------------------------------
# Request / trigger schemas
# ---------------------------------------------------------------------------


class MatchTriggerRequest(BaseModel):
    """
    Payload to trigger a hybrid match evaluation.

    The caller provides the opportunity_id.  The candidate profile is resolved
    from the authenticated user's session.  semantic_similarity is optional;
    if omitted it defaults to 0.0 (neutral, no vector bias).
    """

    opportunity_id: uuid.UUID = Field(..., description="Opportunity to evaluate against")
    semantic_similarity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description=(
            "Pre-computed cosine similarity score from the semantic retrieval pipeline. "
            "Pass the value from /api/v1/recommendations if available. "
            "Defaults to 0.0 (neutral) when not provided."
        ),
    )


# ---------------------------------------------------------------------------
# Paginated match list
# ---------------------------------------------------------------------------


class MatchListResponse(BaseModel):
    """Paginated list of match summaries for the authenticated candidate."""

    items: list[MatchSummaryResponse] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
