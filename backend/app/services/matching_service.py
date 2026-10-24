"""
Hybrid Matching Engine — Phase 19.

Implements a six-factor deterministic eligibility and scoring pipeline that
evaluates a CandidateProfile against a single Opportunity and persists the
result in the `matches` table (idempotently via upsert semantics).

Factor weights (must sum to 1.00):
  - skill_overlap        : 0.35
  - experience           : 0.25
  - education            : 0.15
  - location_work_mode   : 0.10
  - employment_type      : 0.10
  - semantic_similarity  : 0.05

The semantic_similarity input is the raw cosine similarity score [-1.0, 1.0]
already stored or freshly computed by the embedding pipeline.  This module
does NOT generate embeddings; it only consumes the pre-computed value.

Eligibility statuses:
  - ELIGIBLE         : all hard constraints satisfied, score >= 0.50
  - PARTIAL          : soft mismatches only, score >= 0.30
  - REVIEW_REQUIRED  : hard constraint violations OR score < 0.30
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    WorkMode,
)
from app.models.opportunity import Opportunity
from app.models.tracking import Match

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile, Experience

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.00)
# ---------------------------------------------------------------------------

WEIGHT_SKILL_OVERLAP = 0.35
WEIGHT_EXPERIENCE = 0.25
WEIGHT_EDUCATION = 0.15
WEIGHT_LOCATION_WORKMODE = 0.10
WEIGHT_EMPLOYMENT_TYPE = 0.10
WEIGHT_SEMANTIC = 0.05

assert (
    abs(
        WEIGHT_SKILL_OVERLAP
        + WEIGHT_EXPERIENCE
        + WEIGHT_EDUCATION
        + WEIGHT_LOCATION_WORKMODE
        + WEIGHT_EMPLOYMENT_TYPE
        + WEIGHT_SEMANTIC
        - 1.00
    )
    < 1e-9
), "Scoring weights must sum to exactly 1.00"

# Education level ordering (higher index = higher attainment)
_EDUCATION_ORDER: dict[EducationLevel, int] = {
    EducationLevel.NONE: 0,
    EducationLevel.DIPLOMA: 1,
    EducationLevel.BACHELOR: 2,
    EducationLevel.MASTER: 3,
    EducationLevel.PHD: 4,
    EducationLevel.ANY: 0,  # "any" requirement = no constraint
}

# Soft overqualification: penalise if candidate vastly exceeds max_experience_years
_OVERQUALIFICATION_PENALTY_PER_YEAR = 0.05  # 5% per extra year beyond (max + 2)
_OVERQUALIFICATION_PENALTY_CAP = 0.30  # maximum 30% deduction


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _merge_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """
    Merge overlapping or adjacent employment date intervals.

    Returns a sorted list of non-overlapping (start, end) pairs.
    """
    if not intervals:
        return []
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[date, date]] = [sorted_ivs[0]]
    for start, end in sorted_ivs[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _total_experience_years(experiences: list[Experience]) -> float:
    """
    Calculate total non-overlapping work experience in fractional years.

    Uses today's date for roles where `is_current=True` or `end_date` is None.
    """
    today = date.today()
    intervals: list[tuple[date, date]] = []
    for exp in experiences:
        start = exp.start_date
        if start is None:
            continue
        end = exp.end_date if (exp.end_date and not exp.is_current) else today
        if end < start:
            # Guard against malformed dates
            continue
        intervals.append((start, end))

    merged = _merge_intervals(intervals)
    total_days = sum((e - s).days for s, e in merged)
    return total_days / 365.25


def _normalize_skill(name: str) -> str:
    """Lowercase, strip, collapse internal whitespace for skill matching."""
    return " ".join(name.lower().split())


def _candidate_skill_names(profile: CandidateProfile) -> set[str]:
    """Return normalized set of all candidate skill names."""
    return {_normalize_skill(s.skill_name) for s in profile.skills}


def _opportunity_skills(
    opportunity: Opportunity,
) -> tuple[set[str], set[str]]:
    """
    Return (required_skills, preferred_skills) from an opportunity.

    Pulls from both OpportunitySkill rows and the denormalised ARRAY columns,
    deduplicating so neither source is double-counted.
    """
    required: set[str] = set()
    preferred: set[str] = set()

    # From structured OpportunitySkill rows
    for osk in opportunity.skills:
        name = _normalize_skill(osk.skill_name)
        if osk.is_required:
            required.add(name)
        else:
            preferred.add(name)

    # From denormalised ARRAY columns (fallback / supplementary)
    for name in opportunity.required_skills or []:
        required.add(_normalize_skill(name))
    for name in opportunity.preferred_skills or []:
        preferred.add(_normalize_skill(name))

    return required, preferred


# ---------------------------------------------------------------------------
# Individual factor scorers
# ---------------------------------------------------------------------------


def score_skill_overlap(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute skill overlap score [0.0, 1.0].

    Formula:
      - required_ratio  = len(matched_required) / max(len(required), 1)
      - preferred_ratio = len(matched_preferred) / max(len(preferred), 1)
      - score = 0.70 * required_ratio + 0.30 * preferred_ratio

    Returns a breakdown dict with matched/missing skill details.
    """
    candidate_skills = _candidate_skill_names(profile)
    required, preferred = _opportunity_skills(opportunity)

    matched_required = required & candidate_skills
    missing_required = required - candidate_skills
    matched_preferred = preferred & candidate_skills
    missing_preferred = preferred - candidate_skills

    req_ratio = len(matched_required) / len(required) if required else 1.0
    pref_ratio = len(matched_preferred) / len(preferred) if preferred else 1.0

    raw_score = 0.70 * req_ratio + 0.30 * pref_ratio
    score = round(min(1.0, max(0.0, raw_score)), 4)

    return {
        "score": score,
        "required_count": len(required),
        "preferred_count": len(preferred),
        "matched_required": sorted(matched_required),
        "missing_required": sorted(missing_required),
        "matched_preferred": sorted(matched_preferred),
        "missing_preferred": sorted(missing_preferred),
    }


def score_experience(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute experience score [0.0, 1.0].

    Rules:
    - If opportunity has no min_experience_years: score = 1.0.
    - If candidate meets min: score starts at 1.0.
    - Soft overqualification penalty if candidate > (max_experience_years + 2).
    - If candidate < min: proportional penalty.
    """
    experiences = list(profile.experiences) if profile.experiences else []
    total_years = _total_experience_years(experiences)

    min_req = opportunity.min_experience_years
    max_req = opportunity.max_experience_years

    warnings: list[str] = []

    if min_req is None:
        score = 1.0
        experience_gap_years = 0.0
        is_overqualified = False
    elif total_years >= min_req:
        score = 1.0
        experience_gap_years = 0.0

        # Soft overqualification penalty
        threshold = (max_req if max_req is not None else min_req) + 2
        is_overqualified = total_years > threshold
        if is_overqualified:
            excess = total_years - threshold
            penalty = min(
                _OVERQUALIFICATION_PENALTY_CAP,
                excess * _OVERQUALIFICATION_PENALTY_PER_YEAR,
            )
            score = round(max(0.0, score - penalty), 4)
            warnings.append(
                f"Candidate has {total_years:.1f} years experience; "
                f"role targets up to {max_req or min_req} years (soft overqualification)"
            )
    else:
        # Under-qualified
        experience_gap_years = min_req - total_years
        score = round(max(0.0, total_years / min_req), 4)
        is_overqualified = False
        warnings.append(
            f"Candidate has {total_years:.1f} years; "
            f"role requires {min_req} years (gap: {experience_gap_years:.1f} years)"
        )

    return {
        "score": score,
        "candidate_total_years": round(total_years, 2),
        "required_min_years": min_req,
        "required_max_years": max_req,
        "is_overqualified": is_overqualified,
        "experience_gap_years": round(total_years - (min_req or 0), 2),
        "warnings": warnings,
    }


def score_education(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute education score [0.0, 1.0].

    - If requirement is ANY or NONE: score = 1.0.
    - If candidate meets or exceeds requirement: score = 1.0.
    - If candidate is one level below: score = 0.60.
    - If candidate is two or more levels below: score = 0.20.
    """
    required_level = opportunity.required_education_level

    # Highest candidate education level
    candidate_levels = [edu.education_level for edu in (profile.educations or [])]
    candidate_order = (
        max(_EDUCATION_ORDER.get(lvl, 0) for lvl in candidate_levels) if candidate_levels else 0
    )

    required_order = _EDUCATION_ORDER.get(required_level, 0)

    warnings: list[str] = []
    meets_requirement: bool

    if required_level in (EducationLevel.ANY, EducationLevel.NONE):
        score = 1.0
        meets_requirement = True
    elif candidate_order >= required_order:
        score = 1.0
        meets_requirement = True
    elif candidate_order == required_order - 1:
        score = 0.60
        meets_requirement = False
        warnings.append(
            f"Candidate education ({_level_name(candidate_order)}) is one level below "
            f"requirement ({required_level.value})"
        )
    else:
        score = 0.20
        meets_requirement = False
        warnings.append(
            f"Candidate education ({_level_name(candidate_order)}) is significantly below "
            f"requirement ({required_level.value})"
        )

    return {
        "score": score,
        "required_level": required_level.value,
        "candidate_highest_level": _level_name(candidate_order),
        "meets_requirement": meets_requirement,
        "warnings": warnings,
    }


def _level_name(order: int) -> str:
    """Map numeric education order back to a human-readable label."""
    reverse = {v: k.value for k, v in _EDUCATION_ORDER.items() if k != EducationLevel.ANY}
    return reverse.get(order, "unknown")


def score_location_work_mode(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute location and work-mode compatibility score [0.0, 1.0].

    Scoring rules:
    - REMOTE opportunity + any candidate preference: 1.0
    - Opportunity work_mode == ANY: 1.0
    - Candidate preferred_work_mode == ANY: 1.0
    - Exact match of work modes: 1.0
    - ONSITE and candidate is open_to_relocation or location matches: 0.80
    - ONSITE without relocation and no location match: 0.40
    - HYBRID mismatches (preference is REMOTE only): 0.70
    """
    opp_mode = opportunity.work_mode
    cand_mode = profile.preferred_work_mode
    open_to_relocation = profile.open_to_relocation or False

    warnings: list[str] = []

    def _locations_match() -> bool:
        parts = [
            (profile.location_city, opportunity.location_city),
            (profile.location_state, opportunity.location_state),
            (profile.location_country, opportunity.location_country),
        ]
        for cand_loc, opp_loc in parts:
            if cand_loc and opp_loc:
                if cand_loc.strip().lower() == opp_loc.strip().lower():
                    return True
        return False

    if opp_mode == WorkMode.REMOTE:
        score = 1.0
    elif opp_mode == WorkMode.ANY or cand_mode == WorkMode.ANY:
        score = 1.0
    elif opp_mode == cand_mode:
        score = 1.0
    elif opp_mode == WorkMode.ONSITE:
        if open_to_relocation or _locations_match():
            score = 0.80
        else:
            score = 0.40
            warnings.append(
                "Onsite opportunity but candidate not open to relocation and location mismatch"
            )
    elif opp_mode == WorkMode.HYBRID and cand_mode == WorkMode.REMOTE:
        score = 0.70
        warnings.append("Candidate prefers remote but opportunity is hybrid")
    else:
        score = 0.70

    return {
        "score": round(score, 4),
        "opportunity_work_mode": opp_mode.value,
        "candidate_preferred_work_mode": cand_mode.value,
        "open_to_relocation": open_to_relocation,
        "warnings": warnings,
    }


def score_employment_type(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute employment type compatibility score [0.0, 1.0].

    - Exact match: 1.0
    - Either side is ANY: 1.0
    - Mismatch: 0.0 (hard eligibility constraint)
    """
    opp_type = opportunity.employment_type
    cand_type = profile.preferred_employment_type

    warnings: list[str] = []

    if opp_type == EmploymentType.ANY or cand_type == EmploymentType.ANY:
        score = 1.0
        is_match = True
    elif opp_type == cand_type:
        score = 1.0
        is_match = True
    else:
        score = 0.0
        is_match = False
        warnings.append(
            f"Employment type mismatch: opportunity is {opp_type.value}, "
            f"candidate prefers {cand_type.value}"
        )

    return {
        "score": score,
        "opportunity_employment_type": opp_type.value,
        "candidate_preferred_employment_type": cand_type.value,
        "is_match": is_match,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Eligibility evaluator
# ---------------------------------------------------------------------------


def evaluate_eligibility(
    skill_result: dict[str, Any],
    experience_result: dict[str, Any],
    education_result: dict[str, Any],
    employment_type_result: dict[str, Any],
    final_score: float,
) -> tuple[EligibilityStatus, list[str]]:
    """
    Determine eligibility status and collect all warnings.

    Hard constraints (trigger REVIEW_REQUIRED regardless of score):
    - Employment type mismatch (is_match == False)
    - Education completely unsatisfied (meets_requirement == False AND score < 0.25)
    - Missing ALL required skills (matched_required is empty when required > 0)

    Soft mismatches (trigger PARTIAL if no hard blocks, score in [0.30, 0.50)):
    - Score between 0.30 and 0.50

    ELIGIBLE: no hard blocks AND final_score >= 0.50
    """
    all_warnings: list[str] = []
    all_warnings.extend(experience_result.get("warnings", []))
    all_warnings.extend(education_result.get("warnings", []))
    all_warnings.extend(employment_type_result.get("warnings", []))

    hard_blocks: list[str] = []

    # Hard: employment type hard mismatch
    if not employment_type_result.get("is_match", True):
        hard_blocks.append("Employment type hard mismatch")

    # Hard: education severely fails (order-2+ below AND score < 0.25)
    if (
        not education_result.get("meets_requirement", True)
        and education_result.get("score", 1.0) < 0.25
    ):
        hard_blocks.append("Education level severely below requirement")

    # Hard: zero required skills matched (when required > 0)
    req_count = skill_result.get("required_count", 0)
    matched_req = skill_result.get("matched_required", [])
    if req_count > 0 and len(matched_req) == 0:
        hard_blocks.append("No required skills matched")

    all_warnings.extend(hard_blocks)

    if hard_blocks or final_score < 0.30:
        return EligibilityStatus.REVIEW_REQUIRED, all_warnings
    elif final_score < 0.50:
        return EligibilityStatus.PARTIAL, all_warnings
    else:
        return EligibilityStatus.ELIGIBLE, all_warnings


# ---------------------------------------------------------------------------
# Core compute function (pure, no DB)
# ---------------------------------------------------------------------------


def compute_hybrid_match(
    profile: CandidateProfile,
    opportunity: Opportunity,
    semantic_similarity: float,
) -> dict[str, Any]:
    """
    Run all six scoring factors and return a fully structured result dict.

    semantic_similarity: raw cosine similarity in [-1.0, 1.0].
      Normalized to [0.0, 1.0] via (x + 1) / 2 before applying weight.
    """
    # Normalize semantic similarity from [-1, 1] to [0, 1]
    sem_norm = round((float(semantic_similarity) + 1.0) / 2.0, 4)
    sem_norm = min(1.0, max(0.0, sem_norm))

    skill_result = score_skill_overlap(profile, opportunity)
    exp_result = score_experience(profile, opportunity)
    edu_result = score_education(profile, opportunity)
    loc_result = score_location_work_mode(profile, opportunity)
    emp_result = score_employment_type(profile, opportunity)

    weighted_score = (
        WEIGHT_SKILL_OVERLAP * skill_result["score"]
        + WEIGHT_EXPERIENCE * exp_result["score"]
        + WEIGHT_EDUCATION * edu_result["score"]
        + WEIGHT_LOCATION_WORKMODE * loc_result["score"]
        + WEIGHT_EMPLOYMENT_TYPE * emp_result["score"]
        + WEIGHT_SEMANTIC * sem_norm
    )
    final_score = round(min(1.0, max(0.0, weighted_score)), 4)

    deterministic_score = round(
        min(
            1.0,
            max(
                0.0,
                (
                    WEIGHT_SKILL_OVERLAP * skill_result["score"]
                    + WEIGHT_EXPERIENCE * exp_result["score"]
                    + WEIGHT_EDUCATION * edu_result["score"]
                    + WEIGHT_LOCATION_WORKMODE * loc_result["score"]
                    + WEIGHT_EMPLOYMENT_TYPE * emp_result["score"]
                )
                / (1.0 - WEIGHT_SEMANTIC),
            ),
        ),
        4,
    )

    eligibility_status, all_warnings = evaluate_eligibility(
        skill_result=skill_result,
        experience_result=exp_result,
        education_result=edu_result,
        employment_type_result=emp_result,
        final_score=final_score,
    )

    score_breakdown = {
        "weights": {
            "skill_overlap": WEIGHT_SKILL_OVERLAP,
            "experience": WEIGHT_EXPERIENCE,
            "education": WEIGHT_EDUCATION,
            "location_work_mode": WEIGHT_LOCATION_WORKMODE,
            "employment_type": WEIGHT_EMPLOYMENT_TYPE,
            "semantic_similarity": WEIGHT_SEMANTIC,
        },
        "skill_overlap": skill_result,
        "experience": exp_result,
        "education": edu_result,
        "location_work_mode": loc_result,
        "employment_type": emp_result,
        "semantic_similarity_normalized": sem_norm,
        "semantic_similarity_raw": round(float(semantic_similarity), 4),
    }

    explanation = {
        "strengths": _build_strengths(skill_result, exp_result, edu_result, loc_result, emp_result),
        "gaps": _build_gaps(skill_result, exp_result, edu_result, loc_result, emp_result),
    }

    skill_gap = {
        "matched_required_skills": skill_result["matched_required"],
        "missing_required_skills": skill_result["missing_required"],
        "matched_preferred_skills": skill_result["matched_preferred"],
        "missing_preferred_skills": skill_result["missing_preferred"],
    }

    return {
        "semantic_score": round(sem_norm, 4),
        "deterministic_score": deterministic_score,
        "final_score": final_score,
        "eligibility_status": eligibility_status,
        "eligibility_warnings": all_warnings if all_warnings else None,
        "score_breakdown": score_breakdown,
        "explanation": explanation,
        "skill_gap": skill_gap,
    }


def _build_strengths(
    skill: dict[str, Any],
    exp: dict[str, Any],
    edu: dict[str, Any],
    loc: dict[str, Any],
    emp: dict[str, Any],
) -> list[str]:
    strengths: list[str] = []
    if skill["score"] >= 0.80:
        strengths.append(
            f"Strong skill alignment ({len(skill['matched_required'])} required skills matched)"
        )
    if exp["score"] >= 0.90 and not exp.get("is_overqualified"):
        yrs = exp.get("candidate_total_years", 0)
        strengths.append(f"Experience level well-matched ({yrs:.1f} years)")
    if edu["meets_requirement"]:
        strengths.append(f"Education meets requirement ({edu['required_level']})")
    if loc["score"] >= 0.90:
        strengths.append("Location/work-mode fully compatible")
    if emp["is_match"]:
        strengths.append(f"Employment type match ({emp['candidate_preferred_employment_type']})")
    return strengths


def _build_gaps(
    skill: dict[str, Any],
    exp: dict[str, Any],
    edu: dict[str, Any],
    loc: dict[str, Any],
    emp: dict[str, Any],
) -> list[str]:
    gaps: list[str] = []
    if skill["missing_required"]:
        gaps.append(f"Missing required skills: {', '.join(skill['missing_required'][:5])}")
    if exp.get("warnings"):
        gaps.extend(exp["warnings"])
    if not edu["meets_requirement"]:
        gaps.append(
            f"Education gap: have {edu['candidate_highest_level']}, need {edu['required_level']}"
        )
    if loc["score"] < 0.80:
        gaps.extend(loc.get("warnings", []))
    if not emp["is_match"]:
        gaps.extend(emp.get("warnings", []))
    return gaps


# ---------------------------------------------------------------------------
# Persistence: idempotent upsert
# ---------------------------------------------------------------------------


async def upsert_match(
    db: AsyncSession,
    profile_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    match_data: dict[str, Any],
    commit: bool = True,
) -> Match:
    """
    Insert or update a Match record for (profile_id, opportunity_id).

    Uses SELECT + UPDATE (optimistic upsert) to avoid needing database-level
    INSERT … ON CONFLICT support from the ORM layer directly.  Thread-safe
    within a single async session context.
    """
    stmt = select(Match).where(
        Match.candidate_profile_id == profile_id,
        Match.opportunity_id == opportunity_id,
    )
    result = await db.execute(stmt)
    existing: Match | None = result.scalar_one_or_none()

    if existing is not None:
        existing.semantic_score = match_data["semantic_score"]
        existing.deterministic_score = match_data["deterministic_score"]
        existing.final_score = match_data["final_score"]
        existing.eligibility_status = match_data["eligibility_status"]
        existing.eligibility_warnings = match_data["eligibility_warnings"]
        existing.score_breakdown = match_data["score_breakdown"]
        existing.explanation = match_data["explanation"]
        existing.skill_gap = match_data["skill_gap"]
        existing.computed_at = datetime.now(tz=UTC)
        match_record = existing
    else:
        match_record = Match(
            candidate_profile_id=profile_id,
            opportunity_id=opportunity_id,
            semantic_score=match_data["semantic_score"],
            deterministic_score=match_data["deterministic_score"],
            final_score=match_data["final_score"],
            eligibility_status=match_data["eligibility_status"],
            eligibility_warnings=match_data["eligibility_warnings"],
            score_breakdown=match_data["score_breakdown"],
            explanation=match_data["explanation"],
            skill_gap=match_data["skill_gap"],
        )
        db.add(match_record)

    if commit:
        await db.commit()
        await db.refresh(match_record)

    return match_record


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------


async def compute_and_persist_match(
    db: AsyncSession,
    profile: CandidateProfile,
    opportunity: Opportunity,
    semantic_similarity: float = 0.0,
    commit: bool = True,
) -> Match:
    """
    Compute hybrid match scores for (profile, opportunity) and persist the result.

    This is the primary entry-point called from API endpoints.
    Returns the persisted Match ORM instance.
    """
    logger.info(
        "Computing hybrid match: profile=%s opportunity=%s",
        profile.id,
        opportunity.id,
    )

    match_data = compute_hybrid_match(
        profile=profile,
        opportunity=opportunity,
        semantic_similarity=semantic_similarity,
    )

    match_record = await upsert_match(
        db=db,
        profile_id=profile.id,
        opportunity_id=opportunity.id,
        match_data=match_data,
        commit=commit,
    )

    logger.info(
        "Match persisted: profile=%s opportunity=%s final_score=%.4f eligibility=%s",
        profile.id,
        opportunity.id,
        match_record.final_score,
        match_record.eligibility_status,
    )

    return match_record
