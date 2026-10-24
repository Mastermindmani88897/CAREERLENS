"""
Phase 19 Hybrid Matching Engine — Unit Tests (Audited & Verified).

Covers:
  - Approved weights: semantic 0.35, skills 0.25, experience 0.15, education 0.10,
    location 0.05, work_mode 0.05, employment_type 0.05 (sum = 1.00)
  - Asserting every single weight and weighted calculation against a known example
  - Scoring boundaries (0.0, 1.0 bounds) for all factors
  - Missing information handling (no skills, no experience, no education, missing preferences)
  - Eligibility status determination across all three states (ELIGIBLE, PARTIAL, REVIEW_REQUIRED)
  - Experience interval merging (overlapping and adjacent dates)
  - Overqualification soft penalty: max(0.60, 1.0 - 0.05 * (years - max_req))
  - Education hierarchy and one-level-below (0.50) / two-level-below (0.20) rules
  - Missing education evidence handling for degree-required roles
  - Semantic score max(0, cosine) normalization (negative -> 0.0, positive -> unchanged)
  - Separate location (0.05) and work-mode (0.05) scoring
  - Explicit work-mode conflict and severe experience shortfall triggers
  - Skill overlap matched/missing detail structures
  - compute_hybrid_match integration (pure, no DB)
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.models.enums import (
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    WorkMode,
)
from app.services.matching_service import (
    _merge_intervals,
    _total_experience_years,
    compute_hybrid_match,
    evaluate_eligibility,
    score_education,
    score_employment_type,
    score_experience,
    score_location,
    score_location_work_mode,
    score_skill_overlap,
    score_work_mode,
)

# ---------------------------------------------------------------------------
# Helper builders for mock objects
# ---------------------------------------------------------------------------


def _make_skill(name: str) -> MagicMock:
    sk = MagicMock()
    sk.skill_name = name
    return sk


def _make_education(level: EducationLevel) -> MagicMock:
    edu = MagicMock()
    edu.education_level = level
    return edu


def _make_experience(
    start: date,
    end: date | None = None,
    is_current: bool = False,
) -> MagicMock:
    exp = MagicMock()
    exp.start_date = start
    exp.end_date = end
    exp.is_current = is_current
    return exp


def _make_profile(
    skills: list[str] | None = None,
    educations: list[EducationLevel] | None = None,
    experiences: list[tuple[date, date | None, bool]] | None = None,
    preferred_work_mode: WorkMode | None = WorkMode.HYBRID,
    preferred_employment_type: EmploymentType | None = EmploymentType.FULLTIME,
    location_city: str | None = "San Francisco",
    location_state: str | None = "CA",
    location_country: str | None = "USA",
    open_to_relocation: bool = False,
) -> MagicMock:
    profile = MagicMock()
    profile.skills = [_make_skill(s) for s in (skills or [])]
    profile.educations = (
        [_make_education(lvl) for lvl in educations] if educations is not None else []
    )
    profile.experiences = (
        [_make_experience(s, e, curr) for (s, e, curr) in experiences]
        if experiences is not None
        else []
    )
    profile.preferred_work_mode = preferred_work_mode
    profile.preferred_employment_type = preferred_employment_type
    profile.location_city = location_city
    profile.location_state = location_state
    profile.location_country = location_country
    profile.open_to_relocation = open_to_relocation
    return profile


def _make_opportunity(
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
    opp_skills: list[tuple[str, bool]] | None = None,
    min_experience_years: int | None = None,
    max_experience_years: int | None = None,
    required_education_level: EducationLevel = EducationLevel.ANY,
    work_mode: WorkMode = WorkMode.ANY,
    employment_type: EmploymentType = EmploymentType.ANY,
    location_city: str | None = None,
    location_state: str | None = None,
    location_country: str | None = None,
) -> MagicMock:
    opp = MagicMock()
    opp.required_skills = required_skills or []
    opp.preferred_skills = preferred_skills or []

    skills_list = []
    for s_name, is_req in opp_skills or []:
        sk = MagicMock()
        sk.skill_name = s_name
        sk.is_required = is_req
        skills_list.append(sk)
    opp.skills = skills_list

    opp.min_experience_years = min_experience_years
    opp.max_experience_years = max_experience_years
    opp.required_education_level = required_education_level
    opp.work_mode = work_mode
    opp.employment_type = employment_type
    opp.location_city = location_city
    opp.location_state = location_state
    opp.location_country = location_country
    return opp


# ===========================================================================
# SECTION 1: Interval Merging
# ===========================================================================


class TestMergeIntervals:
    def test_empty_list(self):
        assert _merge_intervals([]) == []

    def test_single_interval(self):
        d1 = date(2020, 1, 1)
        d2 = date(2021, 1, 1)
        assert _merge_intervals([(d1, d2)]) == [(d1, d2)]

    def test_non_overlapping(self):
        iv1 = (date(2018, 1, 1), date(2019, 1, 1))
        iv2 = (date(2020, 1, 1), date(2021, 1, 1))
        result = _merge_intervals([iv1, iv2])
        assert result == [iv1, iv2]

    def test_overlapping_intervals_are_merged(self):
        iv1 = (date(2018, 1, 1), date(2020, 6, 1))
        iv2 = (date(2019, 1, 1), date(2021, 1, 1))
        result = _merge_intervals([iv1, iv2])
        assert result == [(date(2018, 1, 1), date(2021, 1, 1))]

    def test_three_overlapping_collapses_to_one(self):
        iv1 = (date(2018, 1, 1), date(2019, 6, 1))
        iv2 = (date(2019, 1, 1), date(2020, 1, 1))
        iv3 = (date(2019, 9, 1), date(2021, 1, 1))
        result = _merge_intervals([iv1, iv2, iv3])
        assert result == [(date(2018, 1, 1), date(2021, 1, 1))]

    def test_adjacent_intervals_merged(self):
        iv1 = (date(2020, 1, 1), date(2020, 1, 31))
        iv2 = (date(2020, 2, 1), date(2020, 2, 28))
        result = _merge_intervals([iv1, iv2])
        assert result == [(date(2020, 1, 1), date(2020, 2, 28))]

    def test_unsorted_input_sorted_first(self):
        iv1 = (date(2020, 1, 1), date(2021, 1, 1))
        iv2 = (date(2018, 1, 1), date(2019, 1, 1))
        result = _merge_intervals([iv1, iv2])
        assert result[0] == iv2
        assert result[1] == iv1


# ===========================================================================
# SECTION 2: _total_experience_years
# ===========================================================================


class TestTotalExperienceYears:
    def test_no_experiences_returns_zero(self):
        assert _total_experience_years([]) == 0.0

    def test_single_completed_role(self):
        start = date(2020, 1, 1)
        end = date(2022, 1, 1)
        exp = _make_experience(start, end, is_current=False)
        years = _total_experience_years([exp])
        assert pytest.approx(2.0, abs=0.05) == years

    def test_current_role_uses_today(self):
        start = date.today() - timedelta(days=365)
        exp = _make_experience(start, None, is_current=True)
        years = _total_experience_years([exp])
        assert pytest.approx(1.0, abs=0.05) == years

    def test_overlapping_roles_deduplicated(self):
        exp1 = _make_experience(date(2020, 1, 1), date(2022, 1, 1))
        exp2 = _make_experience(date(2021, 1, 1), date(2023, 1, 1))
        years = _total_experience_years([exp1, exp2])
        assert pytest.approx(3.0, abs=0.05) == years

    def test_malformed_end_before_start_skipped(self):
        exp = _make_experience(date(2022, 1, 1), date(2020, 1, 1))
        assert _total_experience_years([exp]) == 0.0

    def test_future_start_skipped(self):
        future_start = date.today() + timedelta(days=365)
        exp = _make_experience(future_start, None, is_current=True)
        assert _total_experience_years([exp]) == 0.0


# ===========================================================================
# SECTION 3: score_skill_overlap
# ===========================================================================


class TestScoreSkillOverlap:
    def test_perfect_match_required_and_preferred(self):
        profile = _make_profile(skills=["Python", "FastAPI", "Docker", "Kubernetes"])
        opp = _make_opportunity(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker", "Kubernetes"],
        )
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(1.0, abs=0.001)
        assert result["missing_required"] == []
        assert result["missing_preferred"] == []

    def test_no_candidate_skills(self):
        profile = _make_profile(skills=[])
        opp = _make_opportunity(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
        )
        result = score_skill_overlap(profile, opp)
        assert result["score"] == 0.0
        assert "python" in result["missing_required"]

    def test_no_opportunity_skills(self):
        profile = _make_profile(skills=["Python"])
        opp = _make_opportunity()
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(1.0, abs=0.001)

    def test_partial_required_match_no_preferred(self):
        profile = _make_profile(skills=["Python"])
        opp = _make_opportunity(required_skills=["Python", "FastAPI", "PostgreSQL"])
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(1 / 3, abs=0.01)
        assert "fastapi" in result["missing_required"]
        assert "postgresql" in result["missing_required"]
        assert "python" in result["matched_required"]

    def test_partial_required_with_preferred(self):
        profile = _make_profile(skills=["Python", "Docker"])
        opp = _make_opportunity(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
        )
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(0.65, abs=0.01)

    def test_case_insensitive_matching(self):
        profile = _make_profile(skills=["PYTHON", "FastAPI"])
        opp = _make_opportunity(required_skills=["python", "fastapi"])
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(1.0, abs=0.001)

    def test_opportunity_skill_rows_used(self):
        profile = _make_profile(skills=["React"])
        opp = _make_opportunity(
            opp_skills=[("React", True), ("Redux", False)],
        )
        result = score_skill_overlap(profile, opp)
        assert "react" in result["matched_required"]
        assert "redux" in result["missing_preferred"]

    def test_score_bounded_0_to_1(self):
        profile = _make_profile(skills=["Python"] * 50)
        opp = _make_opportunity(required_skills=["Python"])
        result = score_skill_overlap(profile, opp)
        assert 0.0 <= result["score"] <= 1.0


# ===========================================================================
# SECTION 4: score_experience
# ===========================================================================


class TestScoreExperience:
    def test_no_min_requirement_returns_full(self):
        profile = _make_profile(experiences=[])
        opp = _make_opportunity(min_experience_years=None)
        result = score_experience(profile, opp)
        assert result["score"] == 1.0

    def test_meets_minimum_returns_full(self):
        start = date.today() - timedelta(days=5 * 365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=3)
        result = score_experience(profile, opp)
        assert result["score"] == pytest.approx(1.0, abs=0.05)

    def test_underqualified_proportional_penalty(self):
        start = date.today() - timedelta(days=365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=4)
        result = score_experience(profile, opp)
        assert result["score"] == pytest.approx(0.25, abs=0.05)
        assert result["warnings"]

    def test_overqualification_formula_applied(self):
        start = date.today() - timedelta(days=5 * 365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=1, max_experience_years=3)
        result = score_experience(profile, opp)
        assert result["score"] == pytest.approx(0.90, abs=0.05)
        assert result["is_overqualified"] is True

    def test_overqualification_penalty_capped_at_0_60(self):
        start = date.today() - timedelta(days=25 * 365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=1, max_experience_years=3)
        result = score_experience(profile, opp)
        assert result["score"] == pytest.approx(0.60, abs=0.01)

    def test_score_bounded_zero_one(self):
        profile = _make_profile(experiences=[])
        opp = _make_opportunity(min_experience_years=10)
        result = score_experience(profile, opp)
        assert 0.0 <= result["score"] <= 1.0


# ===========================================================================
# SECTION 5: score_education
# ===========================================================================


class TestScoreEducation:
    def test_any_requirement_always_passes(self):
        profile = _make_profile(educations=[EducationLevel.NONE])
        opp = _make_opportunity(required_education_level=EducationLevel.ANY)
        result = score_education(profile, opp)
        assert result["score"] == 1.0
        assert result["meets_requirement"] is True

    def test_exact_match_returns_full(self):
        profile = _make_profile(educations=[EducationLevel.BACHELOR])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["score"] == 1.0
        assert result["meets_requirement"] is True

    def test_exceeds_requirement_returns_full(self):
        profile = _make_profile(educations=[EducationLevel.MASTER])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["score"] == 1.0

    def test_one_level_below_returns_0_50(self):
        profile = _make_profile(educations=[EducationLevel.DIPLOMA])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["score"] == pytest.approx(0.50, abs=0.001)
        assert result["meets_requirement"] is False

    def test_two_levels_below_returns_0_20(self):
        profile = _make_profile(educations=[EducationLevel.DIPLOMA])
        opp = _make_opportunity(required_education_level=EducationLevel.MASTER)
        result = score_education(profile, opp)
        assert result["score"] == pytest.approx(0.20, abs=0.001)

    def test_missing_education_evidence_triggers_review(self):
        profile = _make_profile(educations=[])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["missing_evidence"] is True
        assert result["score"] == 0.50
        assert len(result["warnings"]) > 0

    def test_phd_exceeds_bachelor_requirement(self):
        profile = _make_profile(educations=[EducationLevel.PHD])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["score"] == 1.0


# ===========================================================================
# SECTION 6: score_location and score_work_mode
# ===========================================================================


class TestScoreLocationAndWorkMode:
    def test_remote_opportunity_always_scores_full(self):
        profile = _make_profile(preferred_work_mode=WorkMode.ONSITE)
        opp = _make_opportunity(work_mode=WorkMode.REMOTE)
        assert score_location(profile, opp)["score"] == 1.0

    def test_location_match_returns_full(self):
        profile = _make_profile(location_city="Seattle")
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="Seattle")
        assert score_location(profile, opp)["score"] == 1.0

    def test_open_to_relocation_scores_0_85(self):
        profile = _make_profile(location_city="Miami", open_to_relocation=True)
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="Seattle")
        assert score_location(profile, opp)["score"] == 0.85

    def test_missing_location_scores_neutral_0_50(self):
        profile = _make_profile(location_city=None, location_state=None, location_country=None)
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="Seattle")
        res = score_location(profile, opp)
        assert res["score"] == 0.50
        assert any("unspecified" in w for w in res["warnings"])

    def test_onsite_without_relocation_no_location_match_scores_0_20(self):
        profile = _make_profile(location_city="Chicago", open_to_relocation=False)
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="New York")
        res = score_location(profile, opp)
        assert res["score"] == 0.20
        assert any("mismatch" in w.lower() for w in res["warnings"])

    def test_work_mode_exact_match(self):
        profile = _make_profile(preferred_work_mode=WorkMode.HYBRID)
        opp = _make_opportunity(work_mode=WorkMode.HYBRID)
        assert score_work_mode(profile, opp)["score"] == 1.0

    def test_work_mode_missing_preference_neutral(self):
        profile = _make_profile(preferred_work_mode=None)
        opp = _make_opportunity(work_mode=WorkMode.HYBRID)
        res = score_work_mode(profile, opp)
        assert res["score"] == 0.50
        assert any("not specified" in w for w in res["warnings"])

    def test_explicit_work_mode_conflict_onsite_vs_remote(self):
        profile = _make_profile(preferred_work_mode=WorkMode.REMOTE, open_to_relocation=False)
        opp = _make_opportunity(work_mode=WorkMode.ONSITE)
        res = score_work_mode(profile, opp)
        assert res["score"] == 0.0
        assert res["has_conflict"] is True

    def test_hybrid_opportunity_remote_candidate_scores_0_70(self):
        profile = _make_profile(preferred_work_mode=WorkMode.REMOTE)
        opp = _make_opportunity(work_mode=WorkMode.HYBRID)
        res = score_work_mode(profile, opp)
        assert res["score"] == 0.70

    def test_location_work_mode_composite(self):
        profile = _make_profile(location_city="Seattle", preferred_work_mode=WorkMode.HYBRID)
        opp = _make_opportunity(location_city="Seattle", work_mode=WorkMode.HYBRID)
        res = score_location_work_mode(profile, opp)
        assert res["score"] == 1.0


# ===========================================================================
# SECTION 7: score_employment_type
# ===========================================================================


class TestScoreEmploymentType:
    def test_exact_match_returns_full(self):
        profile = _make_profile(preferred_employment_type=EmploymentType.FULLTIME)
        opp = _make_opportunity(employment_type=EmploymentType.FULLTIME)
        result = score_employment_type(profile, opp)
        assert result["score"] == 1.0
        assert result["is_match"] is True

    def test_opportunity_any_returns_full(self):
        profile = _make_profile(preferred_employment_type=EmploymentType.FULLTIME)
        opp = _make_opportunity(employment_type=EmploymentType.ANY)
        result = score_employment_type(profile, opp)
        assert result["score"] == 1.0

    def test_candidate_any_preference_returns_full(self):
        profile = _make_profile(preferred_employment_type=EmploymentType.ANY)
        opp = _make_opportunity(employment_type=EmploymentType.CONTRACT)
        result = score_employment_type(profile, opp)
        assert result["score"] == 1.0

    def test_missing_preference_returns_neutral_0_50(self):
        profile = _make_profile(preferred_employment_type=None)
        opp = _make_opportunity(employment_type=EmploymentType.FULLTIME)
        result = score_employment_type(profile, opp)
        assert result["score"] == 0.50
        assert result["is_missing"] is True

    def test_mismatch_returns_zero(self):
        profile = _make_profile(preferred_employment_type=EmploymentType.INTERNSHIP)
        opp = _make_opportunity(employment_type=EmploymentType.FULLTIME)
        result = score_employment_type(profile, opp)
        assert result["score"] == 0.0
        assert result["is_match"] is False


# ===========================================================================
# SECTION 8: evaluate_eligibility
# ===========================================================================


class TestEvaluateEligibility:
    def test_eligible_when_high_score_no_blocks(self):
        skill = {"required_count": 2, "matched_required": ["python", "sql"], "score": 1.0}
        exp = {"required_min_years": 3, "candidate_total_years": 4.0, "warnings": []}
        edu = {"meets_requirement": True, "score": 1.0, "warnings": []}
        loc = {"score": 1.0, "warnings": []}
        wm = {"score": 1.0, "has_conflict": False, "warnings": []}
        emp = {"is_match": True, "is_missing": False, "warnings": []}

        status, _ = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.85)
        assert status == EligibilityStatus.ELIGIBLE

    def test_partial_when_moderate_score(self):
        skill = {"required_count": 2, "matched_required": ["python"], "score": 0.50}
        exp = {"required_min_years": 3, "candidate_total_years": 2.5, "warnings": []}
        edu = {"meets_requirement": False, "score": 0.50, "warnings": ["1 level below"]}
        loc = {"score": 1.0, "warnings": []}
        wm = {"score": 1.0, "has_conflict": False, "warnings": []}
        emp = {"is_match": True, "is_missing": False, "warnings": []}

        status, _ = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.45)
        assert status == EligibilityStatus.PARTIAL

    def test_review_required_below_0_30(self):
        skill = {"required_count": 2, "matched_required": ["python"], "score": 0.20}
        exp = {"required_min_years": 3, "candidate_total_years": 2.0, "warnings": []}
        edu = {"meets_requirement": True, "score": 1.0, "warnings": []}
        loc = {"score": 1.0, "warnings": []}
        wm = {"score": 1.0, "has_conflict": False, "warnings": []}
        emp = {"is_match": True, "is_missing": False, "warnings": []}

        status, _ = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.25)
        assert status == EligibilityStatus.REVIEW_REQUIRED

    def test_severe_experience_shortfall_review_required(self):
        skill = {"required_count": 2, "matched_required": ["python", "sql"], "score": 1.0}
        exp = {"required_min_years": 5, "candidate_total_years": 0.5, "warnings": []}
        edu = {"meets_requirement": True, "score": 1.0, "warnings": []}
        loc = {"score": 1.0, "warnings": []}
        wm = {"score": 1.0, "has_conflict": False, "warnings": []}
        emp = {"is_match": True, "is_missing": False, "warnings": []}

        status, warnings = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.60)
        assert status == EligibilityStatus.REVIEW_REQUIRED
        assert any("Severe experience shortfall" in w for w in warnings)

    def test_missing_education_evidence_triggers_review(self):
        skill = {"required_count": 2, "matched_required": ["python", "sql"], "score": 1.0}
        exp = {"required_min_years": 2, "candidate_total_years": 3.0, "warnings": []}
        edu = {"meets_requirement": False, "missing_evidence": True, "score": 0.50, "warnings": []}
        loc = {"score": 1.0, "warnings": []}
        wm = {"score": 1.0, "has_conflict": False, "warnings": []}
        emp = {"is_match": True, "is_missing": False, "warnings": []}

        status, warnings = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.70)
        assert status == EligibilityStatus.REVIEW_REQUIRED
        assert any("Missing education evidence" in w for w in warnings)

    def test_explicit_work_mode_conflict_triggers_review(self):
        skill = {"required_count": 2, "matched_required": ["python", "sql"], "score": 1.0}
        exp = {"required_min_years": 2, "candidate_total_years": 3.0, "warnings": []}
        edu = {"meets_requirement": True, "score": 1.0, "warnings": []}
        loc = {"score": 1.0, "warnings": []}
        wm = {"score": 0.0, "has_conflict": True, "warnings": ["Explicit work mode conflict"]}
        emp = {"is_match": True, "is_missing": False, "warnings": []}

        status, warnings = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.75)
        assert status == EligibilityStatus.REVIEW_REQUIRED

    def test_warnings_collected_from_all_factors(self):
        skill = {"required_count": 1, "matched_required": ["python"], "warnings": []}
        exp = {"warnings": ["Exp warning"]}
        edu = {"meets_requirement": False, "score": 0.50, "warnings": ["Edu warning"]}
        loc = {"warnings": ["Loc warning"]}
        wm = {"has_conflict": False, "warnings": ["WM warning"]}
        emp = {"is_match": True, "is_missing": False, "warnings": ["Emp warning"]}

        _, warnings = evaluate_eligibility(skill, exp, edu, loc, wm, emp, final_score=0.60)
        assert "Exp warning" in warnings
        assert "Edu warning" in warnings
        assert "Loc warning" in warnings
        assert "WM warning" in warnings
        assert "Emp warning" in warnings


# ===========================================================================
# SECTION 9: compute_hybrid_match
# ===========================================================================


class TestComputeHybridMatch:
    def _strong_profile(self) -> MagicMock:
        start = date.today() - timedelta(days=5 * 365)
        return _make_profile(
            skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            educations=[EducationLevel.BACHELOR],
            experiences=[(start, None, True)],
            preferred_work_mode=WorkMode.HYBRID,
            preferred_employment_type=EmploymentType.FULLTIME,
        )

    def _matching_opportunity(self) -> MagicMock:
        return _make_opportunity(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            min_experience_years=3,
            max_experience_years=7,
            required_education_level=EducationLevel.BACHELOR,
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.FULLTIME,
        )

    def test_returns_required_keys(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.8)
        required_keys = [
            "semantic_score",
            "deterministic_score",
            "final_score",
            "eligibility_status",
            "eligibility_warnings",
            "score_breakdown",
            "explanation",
            "skill_gap",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_score_bounds_always_0_to_1(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        for sem in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            result = compute_hybrid_match(profile, opp, semantic_similarity=sem)
            assert 0.0 <= result["final_score"] <= 1.0
            assert 0.0 <= result["semantic_score"] <= 1.0
            assert 0.0 <= result["deterministic_score"] <= 1.0

    def test_semantic_similarity_max_0_rule(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()

        # Negative cosine -> 0.0
        r_neg = compute_hybrid_match(profile, opp, semantic_similarity=-0.6)
        assert r_neg["semantic_score"] == 0.0
        assert r_neg["score_breakdown"]["semantic_similarity_normalized"] == 0.0

        # Zero cosine -> 0.0
        r_zero = compute_hybrid_match(profile, opp, semantic_similarity=0.0)
        assert r_zero["semantic_score"] == 0.0

        # Positive cosine -> unchanged
        r_pos = compute_hybrid_match(profile, opp, semantic_similarity=0.85)
        assert r_pos["semantic_score"] == pytest.approx(0.85, abs=0.001)

    def test_weights_exact_values_and_sum(self):
        """Verify every single weight matches the approved Phase 19 specification."""
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.5)
        weights = result["score_breakdown"]["weights"]

        # Exact individual factor weights
        assert weights["semantic_similarity"] == 0.35
        assert weights["skill_overlap"] == 0.25
        assert weights["experience"] == 0.15
        assert weights["education"] == 0.10
        assert weights["location"] == 0.05
        assert weights["work_mode"] == 0.05
        assert weights["employment_type"] == 0.05
        assert weights["location_work_mode"] == 0.10

        # Distinct 7-factor sum must equal exactly 1.00
        distinct_sum = (
            weights["semantic_similarity"]
            + weights["skill_overlap"]
            + weights["experience"]
            + weights["education"]
            + weights["location"]
            + weights["work_mode"]
            + weights["employment_type"]
        )
        assert distinct_sum == pytest.approx(1.0, abs=1e-9)

    def test_weighted_calculation_against_known_example(self):
        """
        Verify weighted score calculation against a hand-computed known example:
          - semantic: 0.80 -> norm 0.80 -> 0.35 * 0.80 = 0.2800
          - skills: 1 of 2 req, 1 of 1 pref -> 0.65 -> 0.25 * 0.65 = 0.1625
          - experience: 3 yrs vs min 3 -> 1.00 -> 0.15 * 1.00 = 0.1500
          - education: Diploma vs Bachelor -> 0.50 -> 0.10 * 0.50 = 0.0500
          - location: Austin vs Austin -> 1.00 -> 0.05 * 1.00 = 0.0500
          - work_mode: Hybrid vs Hybrid -> 1.00 -> 0.05 * 1.00 = 0.0500
          - employment_type: Fulltime vs Fulltime -> 1.00 -> 0.05 * 1.00 = 0.0500
          Total = 0.2800 + 0.1625 + 0.1500 + 0.0500 + 0.0500 + 0.0500 + 0.0500 = 0.7925
          Deterministic = 0.5125 / 0.65 = 0.7885
        """
        start = date.today() - timedelta(days=3 * 365)
        profile = _make_profile(
            skills=["Python", "Docker"],
            educations=[EducationLevel.DIPLOMA],
            experiences=[(start, None, True)],
            preferred_work_mode=WorkMode.HYBRID,
            preferred_employment_type=EmploymentType.FULLTIME,
            location_city="Austin",
        )
        opp = _make_opportunity(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            min_experience_years=3,
            required_education_level=EducationLevel.BACHELOR,
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.FULLTIME,
            location_city="Austin",
        )
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.80)

        assert result["score_breakdown"]["semantic_similarity_normalized"] == 0.80
        assert result["score_breakdown"]["skill_overlap"]["score"] == 0.65
        assert result["score_breakdown"]["experience"]["score"] == pytest.approx(1.0, abs=0.01)
        assert result["score_breakdown"]["education"]["score"] == 0.50
        assert result["score_breakdown"]["location"]["score"] == 1.00
        assert result["score_breakdown"]["work_mode"]["score"] == 1.00
        assert result["score_breakdown"]["employment_type"]["score"] == 1.00

        expected_final = 0.7925
        assert result["final_score"] == pytest.approx(expected_final, abs=0.005)

        expected_det = round((0.1625 + 0.1500 + 0.0500 + 0.0500 + 0.0500 + 0.0500) / 0.65, 4)
        assert result["deterministic_score"] == pytest.approx(expected_det, abs=0.005)

    def test_strong_match_scores_eligible(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.8)
        assert result["eligibility_status"] == EligibilityStatus.ELIGIBLE
        assert result["final_score"] >= 0.50

    def test_poor_profile_review_required(self):
        profile = _make_profile(
            skills=[],
            educations=[EducationLevel.NONE],
            experiences=[],
            preferred_employment_type=EmploymentType.PARTTIME,
        )
        opp = _make_opportunity(
            required_skills=["Python", "FastAPI", "AWS"],
            min_experience_years=5,
            required_education_level=EducationLevel.MASTER,
            employment_type=EmploymentType.FULLTIME,
        )
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.0)
        assert result["eligibility_status"] == EligibilityStatus.REVIEW_REQUIRED

    def test_score_breakdown_contains_all_factors(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.5)
        bd = result["score_breakdown"]
        assert "weights" in bd
        assert "skill_overlap" in bd
        assert "experience" in bd
        assert "education" in bd
        assert "location" in bd
        assert "work_mode" in bd
        assert "location_work_mode" in bd
        assert "employment_type" in bd
        assert "semantic_similarity_normalized" in bd
        assert "semantic_similarity_raw" in bd

    def test_skill_gap_structure_correct(self):
        profile = _make_profile(skills=["Python"])
        opp = _make_opportunity(required_skills=["Python", "Docker"])
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.0)
        sg = result["skill_gap"]
        assert "python" in sg["matched_required_skills"]
        assert "docker" in sg["missing_required_skills"]

    def test_explanation_has_strengths_and_gaps(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.8)
        assert "strengths" in result["explanation"]
        assert "gaps" in result["explanation"]
