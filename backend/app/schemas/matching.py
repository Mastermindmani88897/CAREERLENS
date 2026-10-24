"""
Pydantic schemas for Phase 19 Hybrid Matching Engine.

Defines strongly typed request/response models for:
  - Match trigger and evaluation payloads (single and batch)
  - Factor score breakdowns
  - Eligibility status and structured warnings
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
    missing_evidence: bool = False
    warnings: list[str] = Field(default_factory=list)


class LocationBreakdown(BaseModel):
    """Geographic location factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    opportunity_location: str | None = None
    candidate_location: str | None = None
    open_to_relocation: bool = False
    warnings: list[str] = Field(default_factory=list)


class WorkModeBreakdown(BaseModel):
    """Work mode factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    opportunity_work_mode: str
    candidate_preferred_work_mode: str
    has_conflict: bool = False
    warnings: list[str] = Field(default_factory=list)


class LocationWorkModeBreakdown(BaseModel):
    """Combined location and work-mode factor details for backward compatibility."""

    score: float = Field(..., ge=0.0, le=1.0)
    opportunity_work_mode: str
    candidate_preferred_work_mode: str
    open_to_relocation: bool = False
    warnings: list[str] = Field(default_factory=list)


class EmploymentTypeBreakdown(BaseModel):
    """Employment type factor details."""

    score: float = Field(..., ge=0.0, le=1.0)
    opportunity_employment_type: str
    candidate_preferred_employment_type: str
    is_match: bool
    is_missing: bool = False
    warnings: list[str] = Field(default_factory=list)


class ScoringWeights(BaseModel):
    """Factor weights used in the final hybrid score calculation."""

    skill_overlap: float = 0.35
    experience: float = 0.25
    education: float = 0.15
    location: float = 0.05
    work_mode: float = 0.05
    location_work_mode: float = 0.10
    employment_type: float = 0.10
    semantic_similarity: float = 0.05


class ScoreBreakdown(BaseModel):
    """Full score breakdown across all factors."""

    weights: ScoringWeights
    skill_overlap: SkillOverlapBreakdown
    experience: ExperienceBreakdown
    education: EducationBreakdown
    location: LocationBreakdown | None = None
    work_mode: WorkModeBreakdown | None = None
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
        description="Cosine similarity normalized to [0.0, 1.0] via max(0, cosine)",
    )
    deterministic_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic score across non-semantic factors",
    )
    final_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted composite hybrid score",
    )

    eligibility_status: EligibilityStatus
    eligibility_warnings: list[str] | None = None

    score_breakdown: dict[str, Any]
    explanation: dict[str, Any]
    skill_gap: dict[str, Any]

    computed_at: datetime


class MatchSummaryResponse(BaseModel):
    """Lightweight match summary for list endpoints (omits raw breakdown details)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    opportunity_id: uuid.UUID
    semantic_score: float
    deterministic_score: float
    final_score: float
    eligibility_status: EligibilityStatus
    eligibility_warnings: list[str] | None = None
    computed_at: datetime


# ---------------------------------------------------------------------------
# Request / trigger schemas
# ---------------------------------------------------------------------------


class MatchTriggerRequest(BaseModel):
    """Payload to trigger a hybrid match evaluation for a single opportunity."""

    opportunity_id: uuid.UUID = Field(..., description="Opportunity to evaluate against")
    semantic_similarity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description=(
            "Pre-computed cosine similarity score from the semantic retrieval pipeline. "
            "Defaults to 0.0 (neutral) when not provided."
        ),
    )


class MatchEvaluateRequest(BaseModel):
    """
    Payload for POST /api/v1/matches/evaluate.
    Accepts optional list of opportunity_ids and a limit capped at 100.
    """

    opportunity_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional list of specific opportunity IDs to evaluate",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of opportunities to evaluate (capped at 100)",
    )
    semantic_similarity: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Optional pre-computed cosine similarity score (defaults to 0.0)",
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
