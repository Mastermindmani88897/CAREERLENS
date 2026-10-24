"""
Hybrid Matching Engine — Phase 19.

Implements a deterministic eligibility and scoring pipeline that evaluates
a CandidateProfile against an Opportunity and persists the result in the
`matches` table (idempotently via upsert semantics).

Scoring factor weights (totals exactly 1.00):
  - semantic_similarity  : 0.35
  - skill_overlap        : 0.25
  - experience           : 0.15
  - education            : 0.10
  - location             : 0.05
  - work_mode            : 0.05
  - employment_type      : 0.05

Composite location_work_mode weight = 0.10 (location 0.05 + work_mode 0.05).

Semantic similarity:
  Raw cosine similarity in [-1.0, 1.0].
  Approved formula: max(0.0, cosine_similarity).
  Negative cosine values become 0.0, and positive values remain unchanged.

Eligibility statuses:
  - ELIGIBLE         : all constraints satisfied, score >= 0.50
  - PARTIAL          : soft mismatches only, score >= 0.30
  - REVIEW_REQUIRED  : hard constraint violations, missing mandatory evidence, or score < 0.30
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
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

WEIGHT_SEMANTIC = 0.35
WEIGHT_SKILL_OVERLAP = 0.25
WEIGHT_EXPERIENCE = 0.15
WEIGHT_EDUCATION = 0.10
WEIGHT_LOCATION = 0.05
WEIGHT_WORK_MODE = 0.05
WEIGHT_EMPLOYMENT_TYPE = 0.05

# Composite weight for combined location_work_mode (0.05 + 0.05)
WEIGHT_LOCATION_WORKMODE = round(WEIGHT_LOCATION + WEIGHT_WORK_MODE, 4)

assert (
    abs(
        WEIGHT_SEMANTIC
        + WEIGHT_SKILL_OVERLAP
        + WEIGHT_EXPERIENCE
        + WEIGHT_EDUCATION
        + WEIGHT_LOCATION
        + WEIGHT_WORK_MODE
        + WEIGHT_EMPLOYMENT_TYPE
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
        # Merge if overlapping (start <= prev_end) or adjacent (start <= prev_end + 1 day)
        if start <= prev_end + timedelta(days=1):
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _total_experience_years(experiences: list[Experience]) -> float:
    """
    Calculate total non-overlapping work experience in fractional years.

    Uses today's date for roles where `is_current=True` or `end_date` is None.
    Handles future-start intervals and invalid start/end ranges safely.
    """
    today = date.today()
    intervals: list[tuple[date, date]] = []
    for exp in experiences:
        start = exp.start_date
        # Ignore missing or future-start dates safely
        if start is None or start > today:
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


def _opportunity_skills(opportunity: Opportunity) -> tuple[set[str], set[str]]:
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
      - If both required and preferred skills are present:
          score = 0.70 * req_ratio + 0.30 * pref_ratio
      - If only required skills are present:
          score = req_ratio
      - If only preferred skills are present:
          score = pref_ratio
      - If neither are specified:
          score = 1.0

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

    if required and preferred:
        raw_score = 0.70 * req_ratio + 0.30 * pref_ratio
    elif required:
        raw_score = req_ratio
    elif preferred:
        raw_score = pref_ratio
    else:
        raw_score = 1.0

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
    - If candidate meets min and <= max (or no max): score = 1.0.
    - Above a specified maximum: soft penalty max(0.60, 1 - 0.05 * (years - maximum_years)).
    - Under a positive minimum: score proportionally: years / minimum_years.
    - Overqualification remains a soft penalty and never independently disqualifies.
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
        experience_gap_years = 0.0
        if max_req is not None and total_years > max_req:
            is_overqualified = True
            # Approved formula: max(0.60, 1.0 - 0.05 * (years - maximum_years))
            score = round(max(0.60, 1.0 - 0.05 * (total_years - max_req)), 4)
            warnings.append(
                f"Candidate has {total_years:.1f} years experience; "
                f"role targets up to {max_req} years (soft overqualification)"
            )
        else:
            is_overqualified = False
            score = 1.0
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

    Hierarchy: NONE < DIPLOMA < BACHELOR < MASTER < PHD.
    - If requirement is ANY or NONE: score = 1.0.
    - If candidate meets or exceeds requirement: score = 1.0.
    - If candidate is one level below: score = 0.50.
    - If candidate is two or more levels below: score = 0.20.
    - If candidate has no education credentials for a degree-required role:
      score = 0.50 with missing_evidence warning (triggers review, not automatic rejection).
    """
    required_level = opportunity.required_education_level

    educations = profile.educations or []
    candidate_levels = [edu.education_level for edu in educations]
    has_credentials = any(
        lvl not in (EducationLevel.NONE, EducationLevel.ANY, None) for lvl in candidate_levels
    )

    candidate_order = (
        max(_EDUCATION_ORDER.get(lvl, 0) for lvl in candidate_levels) if candidate_levels else 0
    )
    required_order = _EDUCATION_ORDER.get(required_level, 0)

    warnings: list[str] = []
    missing_evidence = False

    if required_level in (EducationLevel.ANY, EducationLevel.NONE):
        score = 1.0
        meets_requirement = True
    elif not has_credentials and required_order >= 1:
        score = 0.50
        meets_requirement = False
        missing_evidence = True
        warnings.append(
            f"Missing education evidence for degree-required role ({required_level.value}); "
            f"candidate profile contains no education credentials"
        )
    elif candidate_order >= required_order:
        score = 1.0
        meets_requirement = True
    elif candidate_order == required_order - 1:
        # One level below: 0.50
        score = 0.50
        meets_requirement = False
        warnings.append(
            f"Candidate education ({_level_name(candidate_order)}) is one level below "
            f"requirement ({required_level.value})"
        )
    else:
        # Two or more levels below: 0.20
        score = 0.20
        meets_requirement = False
        warnings.append(
            f"Candidate education ({_level_name(candidate_order)}) is two or more levels below "
            f"requirement ({required_level.value})"
        )

    return {
        "score": score,
        "required_level": required_level.value,
        "candidate_highest_level": _level_name(candidate_order),
        "meets_requirement": meets_requirement,
        "missing_evidence": missing_evidence,
        "warnings": warnings,
    }


def _level_name(order: int) -> str:
    """Map numeric education order back to a human-readable label."""
    reverse = {v: k.value for k, v in _EDUCATION_ORDER.items() if k != EducationLevel.ANY}
    return reverse.get(order, "unknown")


def score_work_mode(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute work-mode compatibility score [0.0, 1.0] (weight: 0.05).

    - If opportunity is ANY: 1.0
    - If candidate has no preference: 0.50 (neutral with missing evidence warning)
    - If candidate preference is ANY: 1.0
    - If exact match: 1.0
    - If opportunity is REMOTE: soft compatibility (0.80) for onsite/hybrid preference
    - If opportunity is HYBRID and candidate prefers REMOTE: 0.70
    - If opportunity is ONSITE and candidate prefers REMOTE:
        - open_to_relocation: 0.60
        - NOT open_to_relocation: 0.0 with explicit work-mode conflict (triggers REVIEW_REQUIRED)
    """
    opp_mode = opportunity.work_mode or WorkMode.ANY
    cand_mode = profile.preferred_work_mode
    open_to_relocation = profile.open_to_relocation or False

    warnings: list[str] = []
    has_conflict = False

    if opp_mode == WorkMode.ANY:
        score = 1.0
    elif cand_mode is None:
        score = 0.50
        warnings.append("Candidate preferred work mode not specified; neutral score applied")
    elif cand_mode == WorkMode.ANY:
        score = 1.0
    elif opp_mode == cand_mode:
        score = 1.0
    elif opp_mode == WorkMode.REMOTE:
        score = 0.80
    elif opp_mode == WorkMode.HYBRID and cand_mode == WorkMode.REMOTE:
        score = 0.70
        warnings.append("Opportunity is hybrid; candidate prefers remote")
    elif opp_mode == WorkMode.ONSITE and cand_mode == WorkMode.REMOTE:
        if open_to_relocation:
            score = 0.60
            warnings.append("Onsite opportunity; candidate prefers remote but open to relocation")
        else:
            score = 0.0
            has_conflict = True
            warnings.append(
                "Explicit work mode conflict: opportunity is onsite but candidate requires remote"
            )
    else:
        score = 0.70

    return {
        "score": round(score, 4),
        "opportunity_work_mode": opp_mode.value,
        "candidate_preferred_work_mode": cand_mode.value if cand_mode else "unspecified",
        "has_conflict": has_conflict,
        "warnings": warnings,
    }


def score_location(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute geographic location compatibility score [0.0, 1.0] (weight: 0.05).

    - If opportunity is REMOTE or has no location restriction: 1.0
    - If candidate location matches opportunity location/city: 1.0
    - If candidate is open to relocation: 0.85
    - If candidate location is unspecified: 0.50 (neutral with missing evidence warning)
    - If location mismatch without relocation: 0.20
    """
    opp_mode = opportunity.work_mode or WorkMode.ANY
    open_to_relocation = profile.open_to_relocation or False
    warnings: list[str] = []

    opp_has_location = bool(
        opportunity.location_city or opportunity.location_state or opportunity.location_country
    )
    cand_has_location = bool(
        profile.location_city or profile.location_state or profile.location_country
    )

    def _locations_match() -> bool:
        parts = [
            (profile.location_city, opportunity.location_city),
            (profile.location_state, opportunity.location_state),
            (profile.location_country, opportunity.location_country),
        ]
        for c_part, o_part in parts:
            if c_part and o_part and c_part.strip().lower() == o_part.strip().lower():
                return True
        return False

    if opp_mode == WorkMode.REMOTE or not opp_has_location:
        score = 1.0
    elif _locations_match():
        score = 1.0
    elif open_to_relocation:
        score = 0.85
        warnings.append("Candidate open to relocation for location requirements")
    elif not cand_has_location:
        score = 0.50
        warnings.append("Candidate location unspecified; neutral location score applied")
    else:
        score = 0.20
        warnings.append(
            f"Location mismatch: candidate at {profile.location_city or 'unspecified'}, "
            f"opportunity at {opportunity.location_city or 'unspecified'}"
        )

    return {
        "score": round(score, 4),
        "opportunity_location": opportunity.location_city,
        "candidate_location": profile.location_city,
        "open_to_relocation": open_to_relocation,
        "warnings": warnings,
    }


def score_location_work_mode(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Combined location and work-mode score for backward compatibility (weight: 0.10).
    Averages score_location (0.05) and score_work_mode (0.05).
    """
    loc = score_location(profile, opportunity)
    wm = score_work_mode(profile, opportunity)
    combined_score = round(0.50 * loc["score"] + 0.50 * wm["score"], 4)
    all_warnings = loc.get("warnings", []) + wm.get("warnings", [])

    return {
        "score": combined_score,
        "opportunity_work_mode": wm["opportunity_work_mode"],
        "candidate_preferred_work_mode": wm["candidate_preferred_work_mode"],
        "open_to_relocation": loc["open_to_relocation"],
        "warnings": all_warnings,
    }


def score_employment_type(
    profile: CandidateProfile,
    opportunity: Opportunity,
) -> dict[str, Any]:
    """
    Compute employment type compatibility score [0.0, 1.0].

    - Missing candidate preference: neutral 0.50 (with warning)
    - Either side is ANY: 1.0
    - Exact match: 1.0
    - Mismatch: 0.0 with warning (triggers REVIEW_REQUIRED, not hard disqualification)
    """
    opp_type = opportunity.employment_type
    cand_type = profile.preferred_employment_type

    warnings: list[str] = []
    is_missing = False

    if cand_type is None:
        score = 0.50
        is_match = False
        is_missing = True
        warnings.append(
            "Candidate preferred employment type unspecified; neutral score 0.50 applied"
        )
    elif opp_type == EmploymentType.ANY or cand_type == EmploymentType.ANY:
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
        "opportunity_employment_type": opp_type.value if opp_type else "any",
        "candidate_preferred_employment_type": cand_type.value if cand_type else "unspecified",
        "is_match": is_match,
        "is_missing": is_missing,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Eligibility evaluator
# ---------------------------------------------------------------------------


def evaluate_eligibility(
    skill_result: dict[str, Any],
    experience_result: dict[str, Any],
    education_result: dict[str, Any],
    location_result: dict[str, Any],
    work_mode_result: dict[str, Any],
    employment_type_result: dict[str, Any],
    final_score: float,
) -> tuple[EligibilityStatus, list[str]]:
    """
    Determine eligibility status and collect structured warnings.

    Precedence rules for REVIEW_REQUIRED:
    1. Severe experience shortfall: candidate experience < 30% of required minimum.
    2. Zero required skills matched when required skills exist.
    3. Severe education shortfall (2+ levels below) OR missing degree evidence.
    4. Explicit work-mode conflict (e.g. onsite role, remote candidate without relocation).
    5. Employment type explicit mismatch.
    6. Low final score (< 0.30).

    Precedence rules for PARTIAL:
    - Score in [0.30, 0.50) without hard review triggers (e.g. 1 level below in education).

    Precedence rules for ELIGIBLE:
    - No review triggers AND final_score >= 0.50.

    Missing evidence (unspecified location, unspecified work-mode, unspecified employment type)
    generates warnings and neutral scores, but does NOT disqualify candidates.
    """
    all_warnings: list[str] = []
    all_warnings.extend(experience_result.get("warnings", []))
    all_warnings.extend(education_result.get("warnings", []))
    all_warnings.extend(location_result.get("warnings", []))
    all_warnings.extend(work_mode_result.get("warnings", []))
    all_warnings.extend(employment_type_result.get("warnings", []))

    review_triggers: list[str] = []

    # 1. Severe experience shortfall (< 30% of required min)
    min_exp = experience_result.get("required_min_years")
    if min_exp and min_exp > 0:
        cand_exp = experience_result.get("candidate_total_years", 0.0)
        if cand_exp < 0.30 * min_exp:
            review_triggers.append(
                f"Severe experience shortfall: {cand_exp:.1f} years vs {min_exp} years required"
            )

    # 2. Zero required skills matched
    req_count = skill_result.get("required_count", 0)
    matched_req = skill_result.get("matched_required", [])
    if req_count > 0 and len(matched_req) == 0:
        review_triggers.append("No required skills matched")

    # 3. Education: severe shortfall or missing evidence for degree-required role
    if education_result.get("missing_evidence"):
        review_triggers.append("Missing education evidence for degree-required role")
    elif (
        not education_result.get("meets_requirement", True)
        and education_result.get("score", 1.0) <= 0.20
    ):
        review_triggers.append("Education level significantly below requirement")

    # 4. Explicit work-mode conflict
    if work_mode_result.get("has_conflict"):
        review_triggers.append("Explicit work mode conflict")

    # 5. Employment type explicit mismatch (not missing preference)
    if not employment_type_result.get("is_match") and not employment_type_result.get("is_missing"):
        review_triggers.append("Employment type mismatch")

    for trigger in review_triggers:
        if trigger not in all_warnings:
            all_warnings.append(trigger)

    if review_triggers or final_score < 0.30:
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
    semantic_similarity: float = 0.0,
) -> dict[str, Any]:
    """
    Run deterministic and semantic scoring factors and return a structured result dict.

    semantic_similarity: raw cosine similarity in [-1.0, 1.0].
      Approved formula: max(0.0, cosine_similarity).
      Negative cosine values map to 0.0; positive values remain unchanged.
    """
    sem_raw = float(semantic_similarity)
    sem_norm = round(min(1.0, max(0.0, sem_raw)), 4)

    skill_result = score_skill_overlap(profile, opportunity)
    exp_result = score_experience(profile, opportunity)
    edu_result = score_education(profile, opportunity)
    loc_result = score_location(profile, opportunity)
    wm_result = score_work_mode(profile, opportunity)
    loc_wm_result = score_location_work_mode(profile, opportunity)
    emp_result = score_employment_type(profile, opportunity)

    weighted_score = (
        WEIGHT_SKILL_OVERLAP * skill_result["score"]
        + WEIGHT_EXPERIENCE * exp_result["score"]
        + WEIGHT_EDUCATION * edu_result["score"]
        + WEIGHT_LOCATION * loc_result["score"]
        + WEIGHT_WORK_MODE * wm_result["score"]
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
                    + WEIGHT_LOCATION * loc_result["score"]
                    + WEIGHT_WORK_MODE * wm_result["score"]
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
        location_result=loc_result,
        work_mode_result=wm_result,
        employment_type_result=emp_result,
        final_score=final_score,
    )

    score_breakdown = {
        "weights": {
            "skill_overlap": WEIGHT_SKILL_OVERLAP,
            "experience": WEIGHT_EXPERIENCE,
            "education": WEIGHT_EDUCATION,
            "location": WEIGHT_LOCATION,
            "work_mode": WEIGHT_WORK_MODE,
            "location_work_mode": WEIGHT_LOCATION_WORKMODE,
            "employment_type": WEIGHT_EMPLOYMENT_TYPE,
            "semantic_similarity": WEIGHT_SEMANTIC,
        },
        "skill_overlap": skill_result,
        "experience": exp_result,
        "education": edu_result,
        "location": loc_result,
        "work_mode": wm_result,
        "location_work_mode": loc_wm_result,
        "employment_type": emp_result,
        "semantic_similarity_normalized": sem_norm,
        "semantic_similarity_raw": round(sem_raw, 4),
    }

    explanation = {
        "strengths": _build_strengths(
            skill_result, exp_result, edu_result, loc_result, wm_result, emp_result
        ),
        "gaps": _build_gaps(
            skill_result, exp_result, edu_result, loc_result, wm_result, emp_result
        ),
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
    wm: dict[str, Any],
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
    if loc["score"] >= 0.85:
        strengths.append("Location compatibility confirmed")
    if wm["score"] >= 0.80:
        strengths.append(f"Work-mode aligned ({wm['candidate_preferred_work_mode']})")
    if emp["is_match"]:
        strengths.append(f"Employment type match ({emp['candidate_preferred_employment_type']})")
    return strengths


def _build_gaps(
    skill: dict[str, Any],
    exp: dict[str, Any],
    edu: dict[str, Any],
    loc: dict[str, Any],
    wm: dict[str, Any],
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
    if loc["score"] < 0.85:
        gaps.extend(loc.get("warnings", []))
    if wm.get("has_conflict") or wm["score"] < 0.80:
        gaps.extend(wm.get("warnings", []))
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
    INSERT … ON CONFLICT support from the ORM layer directly. Thread-safe
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
