"""
Phase 19 Hybrid Matching Engine — Unit Tests.

Covers:
  - Scoring boundaries (0.0, 1.0 bounds) for all six factors
  - Missing information handling (no skills, no experience, no education)
  - Eligibility status determination across all three states
  - Experience interval merging and overlapping date handling
  - Overqualification soft penalty
  - Skill overlap matched/missing detail structures
  - compute_hybrid_match integration (pure, no DB)
  - evaluate_eligibility hard-constraint detection
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
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
    score_location_work_mode,
    score_skill_overlap,
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
    preferred_work_mode: WorkMode = WorkMode.HYBRID,
    preferred_employment_type: EmploymentType = EmploymentType.FULLTIME,
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
    employment_type: EmploymentType = EmploymentType.FULLTIME,
    location_city: str | None = None,
    location_state: str | None = None,
    location_country: str | None = None,
) -> MagicMock:
    opp = MagicMock()
    opp.required_skills = required_skills or []
    opp.preferred_skills = preferred_skills or []
    opp.min_experience_years = min_experience_years
    opp.max_experience_years = max_experience_years
    opp.required_education_level = required_education_level
    opp.work_mode = work_mode
    opp.employment_type = employment_type
    opp.location_city = location_city
    opp.location_state = location_state
    opp.location_country = location_country

    # Build OpportunitySkill mocks
    skills_list: list[MagicMock] = []
    for skill_name, is_req in opp_skills or []:
        osk = MagicMock()
        osk.skill_name = skill_name
        osk.is_required = is_req
        skills_list.append(osk)
    opp.skills = skills_list

    return opp


# ===========================================================================
# SECTION 1: _merge_intervals
# ===========================================================================


class TestMergeIntervals:
    def test_empty_list(self):
        assert _merge_intervals([]) == []

    def test_single_interval(self):
        d1 = date(2020, 1, 1)
        d2 = date(2021, 1, 1)
        assert _merge_intervals([(d1, d2)]) == [(d1, d2)]

    def test_non_overlapping(self):
        intervals = [
            (date(2018, 1, 1), date(2019, 1, 1)),
            (date(2020, 1, 1), date(2021, 1, 1)),
        ]
        result = _merge_intervals(intervals)
        assert len(result) == 2

    def test_overlapping_intervals_are_merged(self):
        intervals = [
            (date(2018, 1, 1), date(2020, 6, 1)),
            (date(2019, 1, 1), date(2021, 1, 1)),
        ]
        result = _merge_intervals(intervals)
        assert len(result) == 1
        assert result[0] == (date(2018, 1, 1), date(2021, 1, 1))

    def test_three_overlapping_collapses_to_one(self):
        intervals = [
            (date(2018, 1, 1), date(2019, 1, 1)),
            (date(2018, 6, 1), date(2020, 1, 1)),
            (date(2019, 6, 1), date(2021, 1, 1)),
        ]
        result = _merge_intervals(intervals)
        assert len(result) == 1
        assert result[0][0] == date(2018, 1, 1)
        assert result[0][1] == date(2021, 1, 1)

    def test_adjacent_intervals_merged(self):
        # Same end/start date should merge
        intervals = [
            (date(2019, 1, 1), date(2020, 1, 1)),
            (date(2020, 1, 1), date(2021, 1, 1)),
        ]
        result = _merge_intervals(intervals)
        assert len(result) == 1

    def test_unsorted_input_sorted_first(self):
        intervals = [
            (date(2021, 1, 1), date(2022, 1, 1)),
            (date(2018, 1, 1), date(2019, 1, 1)),
        ]
        result = _merge_intervals(intervals)
        assert result[0][0] == date(2018, 1, 1)
        assert result[-1][1] == date(2022, 1, 1)


# ===========================================================================
# SECTION 2: _total_experience_years
# ===========================================================================


class TestTotalExperienceYears:
    def test_no_experiences_returns_zero(self):
        profile = _make_profile(experiences=[])
        assert _total_experience_years(profile.experiences) == 0.0

    def test_single_completed_role(self):
        """Exactly 1 year: Jan 1 2020 to Jan 1 2021."""
        exps = [_make_experience(date(2020, 1, 1), date(2021, 1, 1))]
        years = _total_experience_years(exps)
        assert 0.99 < years < 1.01

    def test_current_role_uses_today(self):
        """A role started 2 years ago with is_current=True should count to today."""
        start = date.today() - timedelta(days=730)
        exps = [_make_experience(start, None, is_current=True)]
        years = _total_experience_years(exps)
        assert years >= 1.9  # at least ~2 years

    def test_overlapping_roles_deduplicated(self):
        """Two roles with same period should not double-count."""
        start = date(2020, 1, 1)
        end = date(2022, 1, 1)
        exps = [
            _make_experience(start, end),
            _make_experience(start, end),
        ]
        years = _total_experience_years(exps)
        # Should be ~2 years, not ~4
        assert 1.9 < years < 2.1

    def test_malformed_end_before_start_skipped(self):
        """end_date before start_date should be silently skipped."""
        exps = [
            _make_experience(date(2022, 6, 1), date(2021, 1, 1)),  # reversed
            _make_experience(date(2020, 1, 1), date(2021, 1, 1)),  # valid
        ]
        years = _total_experience_years(exps)
        assert 0.9 < years < 1.1  # only valid interval counted


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
        """Opportunity with no required/preferred skills → score = 1.0."""
        profile = _make_profile(skills=["Python"])
        opp = _make_opportunity()
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(1.0, abs=0.001)

    def test_partial_required_skill_match(self):
        profile = _make_profile(skills=["Python"])
        opp = _make_opportunity(required_skills=["Python", "FastAPI", "PostgreSQL"])
        result = score_skill_overlap(profile, opp)
        # 1/3 required matched, no preferred (pref_ratio=1.0)
        # score = 0.70*(1/3) + 0.30*1.0 = 0.2333 + 0.30 = 0.5333
        expected = round(0.70 * (1 / 3) + 0.30 * 1.0, 4)
        assert result["score"] == pytest.approx(expected, abs=0.01)
        assert "fastapi" in result["missing_required"]
        assert "postgresql" in result["missing_required"]
        assert "python" in result["matched_required"]

    def test_case_insensitive_matching(self):
        profile = _make_profile(skills=["PYTHON", "FastAPI"])
        opp = _make_opportunity(required_skills=["python", "fastapi"])
        result = score_skill_overlap(profile, opp)
        assert result["score"] == pytest.approx(1.0, abs=0.001)

    def test_opportunity_skill_rows_used(self):
        """Skills from OpportunitySkill rows (not ARRAY columns) are considered."""
        profile = _make_profile(skills=["React"])
        opp = _make_opportunity(
            opp_skills=[("React", True), ("Redux", False)],
        )
        result = score_skill_overlap(profile, opp)
        assert "react" in result["matched_required"]
        assert "redux" in result["missing_preferred"]

    def test_score_bounded_0_to_1(self):
        """Score must always be within [0.0, 1.0]."""
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
        # 1 year of experience, requires 4
        start = date.today() - timedelta(days=365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=4)
        result = score_experience(profile, opp)
        # ~1/4 = 0.25
        assert result["score"] == pytest.approx(0.25, abs=0.05)
        assert result["warnings"]  # should have a warning

    def test_overqualification_penalty_applied(self):
        # 15 years, role requires max 3
        start = date.today() - timedelta(days=15 * 365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=1, max_experience_years=3)
        result = score_experience(profile, opp)
        # Threshold = 3 + 2 = 5, excess = ~10 years, penalty = min(0.30, 10*0.05) = 0.30
        assert result["score"] == pytest.approx(0.70, abs=0.05)
        assert result["is_overqualified"] is True

    def test_overqualification_penalty_capped(self):
        """Penalty is capped at 0.30 regardless of how overqualified."""
        start = date.today() - timedelta(days=40 * 365)
        profile = _make_profile(experiences=[(start, None, True)])
        opp = _make_opportunity(min_experience_years=1, max_experience_years=2)
        result = score_experience(profile, opp)
        # Cap ensures score >= 0.70
        assert result["score"] >= 0.70

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

    def test_one_level_below_returns_0_60(self):
        profile = _make_profile(educations=[EducationLevel.DIPLOMA])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["score"] == pytest.approx(0.60, abs=0.001)
        assert result["meets_requirement"] is False

    def test_two_levels_below_returns_0_20(self):
        profile = _make_profile(educations=[EducationLevel.NONE])
        opp = _make_opportunity(required_education_level=EducationLevel.MASTER)
        result = score_education(profile, opp)
        assert result["score"] == pytest.approx(0.20, abs=0.001)

    def test_no_candidate_education_treated_as_none_level(self):
        profile = _make_profile(educations=[])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        # No education = NONE level (order 0), BACHELOR is order 2 → two levels below
        assert result["score"] == pytest.approx(0.20, abs=0.001)

    def test_phd_exceeds_bachelor_requirement(self):
        profile = _make_profile(educations=[EducationLevel.PHD])
        opp = _make_opportunity(required_education_level=EducationLevel.BACHELOR)
        result = score_education(profile, opp)
        assert result["score"] == 1.0

    def test_score_bounded_zero_one(self):
        profile = _make_profile(educations=[EducationLevel.NONE])
        opp = _make_opportunity(required_education_level=EducationLevel.PHD)
        result = score_education(profile, opp)
        assert 0.0 <= result["score"] <= 1.0


# ===========================================================================
# SECTION 6: score_location_work_mode
# ===========================================================================


class TestScoreLocationWorkMode:
    def test_remote_opportunity_always_scores_full(self):
        profile = _make_profile(preferred_work_mode=WorkMode.ONSITE)
        opp = _make_opportunity(work_mode=WorkMode.REMOTE)
        result = score_location_work_mode(profile, opp)
        assert result["score"] == 1.0

    def test_any_opportunity_always_scores_full(self):
        profile = _make_profile(preferred_work_mode=WorkMode.ONSITE)
        opp = _make_opportunity(work_mode=WorkMode.ANY)
        result = score_location_work_mode(profile, opp)
        assert result["score"] == 1.0

    def test_candidate_any_preference_always_scores_full(self):
        profile = _make_profile(preferred_work_mode=WorkMode.ANY)
        opp = _make_opportunity(work_mode=WorkMode.ONSITE)
        result = score_location_work_mode(profile, opp)
        assert result["score"] == 1.0

    def test_exact_match_scores_full(self):
        profile = _make_profile(preferred_work_mode=WorkMode.HYBRID)
        opp = _make_opportunity(work_mode=WorkMode.HYBRID)
        result = score_location_work_mode(profile, opp)
        assert result["score"] == 1.0

    def test_onsite_with_relocation_scores_0_80(self):
        profile = _make_profile(preferred_work_mode=WorkMode.HYBRID, open_to_relocation=True)
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="New York")
        result = score_location_work_mode(profile, opp)
        assert result["score"] == pytest.approx(0.80, abs=0.001)

    def test_onsite_without_relocation_no_location_match_scores_0_40(self):
        profile = _make_profile(
            preferred_work_mode=WorkMode.HYBRID,
            open_to_relocation=False,
            location_city="San Francisco",
        )
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="New York")
        result = score_location_work_mode(profile, opp)
        assert result["score"] == pytest.approx(0.40, abs=0.001)
        assert result["warnings"]

    def test_onsite_with_matching_city_scores_0_80(self):
        profile = _make_profile(
            preferred_work_mode=WorkMode.HYBRID,
            open_to_relocation=False,
            location_city="San Francisco",
        )
        opp = _make_opportunity(work_mode=WorkMode.ONSITE, location_city="San Francisco")
        result = score_location_work_mode(profile, opp)
        assert result["score"] == pytest.approx(0.80, abs=0.001)

    def test_hybrid_opportunity_remote_candidate_scores_0_70(self):
        profile = _make_profile(preferred_work_mode=WorkMode.REMOTE)
        opp = _make_opportunity(work_mode=WorkMode.HYBRID)
        result = score_location_work_mode(profile, opp)
        assert result["score"] == pytest.approx(0.70, abs=0.001)
        assert result["warnings"]


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
        profile = _make_profile(preferred_employment_type=EmploymentType.PARTTIME)
        opp = _make_opportunity(employment_type=EmploymentType.ANY)
        result = score_employment_type(profile, opp)
        assert result["score"] == 1.0
        assert result["is_match"] is True

    def test_candidate_any_preference_returns_full(self):
        profile = _make_profile(preferred_employment_type=EmploymentType.ANY)
        opp = _make_opportunity(employment_type=EmploymentType.CONTRACT)
        result = score_employment_type(profile, opp)
        assert result["score"] == 1.0
        assert result["is_match"] is True

    def test_mismatch_returns_zero_hard(self):
        profile = _make_profile(preferred_employment_type=EmploymentType.FULLTIME)
        opp = _make_opportunity(employment_type=EmploymentType.PARTTIME)
        result = score_employment_type(profile, opp)
        assert result["score"] == 0.0
        assert result["is_match"] is False
        assert result["warnings"]


# ===========================================================================
# SECTION 8: evaluate_eligibility
# ===========================================================================


class TestEvaluateEligibility:
    def _default_skill_result(self, matched=2, total=2) -> dict[str, Any]:
        return {
            "score": 1.0,
            "required_count": total,
            "preferred_count": 0,
            "matched_required": ["python", "fastapi"][:matched],
            "missing_required": ["python", "fastapi"][matched:],
            "matched_preferred": [],
            "missing_preferred": [],
        }

    def _default_exp_result(self) -> dict[str, Any]:
        return {"score": 1.0, "warnings": [], "is_overqualified": False}

    def _default_edu_result(self, meets=True, score=1.0) -> dict[str, Any]:
        return {
            "score": score,
            "meets_requirement": meets,
            "required_level": "bachelor",
            "candidate_highest_level": "bachelor",
            "warnings": [],
        }

    def _default_emp_result(self, is_match=True) -> dict[str, Any]:
        return {
            "score": 1.0 if is_match else 0.0,
            "is_match": is_match,
            "warnings": [] if is_match else ["Employment type mismatch"],
        }

    def test_eligible_when_high_score_no_hard_blocks(self):
        status, warnings = evaluate_eligibility(
            skill_result=self._default_skill_result(),
            experience_result=self._default_exp_result(),
            education_result=self._default_edu_result(),
            employment_type_result=self._default_emp_result(),
            final_score=0.85,
        )
        assert status == EligibilityStatus.ELIGIBLE
        assert warnings == []

    def test_partial_when_moderate_score(self):
        status, warnings = evaluate_eligibility(
            skill_result=self._default_skill_result(),
            experience_result=self._default_exp_result(),
            education_result=self._default_edu_result(),
            employment_type_result=self._default_emp_result(),
            final_score=0.42,
        )
        assert status == EligibilityStatus.PARTIAL

    def test_review_required_below_0_30(self):
        status, _ = evaluate_eligibility(
            skill_result=self._default_skill_result(),
            experience_result=self._default_exp_result(),
            education_result=self._default_edu_result(),
            employment_type_result=self._default_emp_result(),
            final_score=0.28,
        )
        assert status == EligibilityStatus.REVIEW_REQUIRED

    def test_review_required_on_employment_type_mismatch(self):
        status, warnings = evaluate_eligibility(
            skill_result=self._default_skill_result(),
            experience_result=self._default_exp_result(),
            education_result=self._default_edu_result(),
            employment_type_result=self._default_emp_result(is_match=False),
            final_score=0.75,  # high score but still blocked
        )
        assert status == EligibilityStatus.REVIEW_REQUIRED
        assert any("Employment type" in w for w in warnings)

    def test_review_required_when_no_required_skills_matched(self):
        skill_result = self._default_skill_result(matched=0, total=3)
        skill_result["missing_required"] = ["python", "fastapi", "docker"]
        status, warnings = evaluate_eligibility(
            skill_result=skill_result,
            experience_result=self._default_exp_result(),
            education_result=self._default_edu_result(),
            employment_type_result=self._default_emp_result(),
            final_score=0.60,
        )
        assert status == EligibilityStatus.REVIEW_REQUIRED

    def test_review_required_severe_education_gap(self):
        edu_result = self._default_edu_result(meets=False, score=0.20)
        status, _ = evaluate_eligibility(
            skill_result=self._default_skill_result(),
            experience_result=self._default_exp_result(),
            education_result=edu_result,
            employment_type_result=self._default_emp_result(),
            final_score=0.55,
        )
        assert status == EligibilityStatus.REVIEW_REQUIRED

    def test_warnings_collected_from_all_factors(self):
        exp_result = self._default_exp_result()
        exp_result["warnings"] = ["Experience gap warning"]
        edu_result = self._default_edu_result(meets=False, score=0.60)
        edu_result["warnings"] = ["Education one level below"]
        _, warnings = evaluate_eligibility(
            skill_result=self._default_skill_result(),
            experience_result=exp_result,
            education_result=edu_result,
            employment_type_result=self._default_emp_result(),
            final_score=0.55,
        )
        assert "Experience gap warning" in warnings
        assert "Education one level below" in warnings


# ===========================================================================
# SECTION 9: compute_hybrid_match (integration, pure)
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

    def test_strong_match_scores_eligible(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.8)
        assert result["eligibility_status"] == EligibilityStatus.ELIGIBLE
        assert result["final_score"] >= 0.50

    def test_score_bounds_always_0_to_1(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        for sem in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            result = compute_hybrid_match(profile, opp, semantic_similarity=sem)
            assert 0.0 <= result["final_score"] <= 1.0
            assert 0.0 <= result["semantic_score"] <= 1.0
            assert 0.0 <= result["deterministic_score"] <= 1.0

    def test_semantic_similarity_normalized_correctly(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()

        # -1.0 → normalized to 0.0
        r = compute_hybrid_match(profile, opp, semantic_similarity=-1.0)
        assert r["score_breakdown"]["semantic_similarity_normalized"] == pytest.approx(
            0.0, abs=0.001
        )

        # 0.0 → normalized to 0.5
        r = compute_hybrid_match(profile, opp, semantic_similarity=0.0)
        assert r["score_breakdown"]["semantic_similarity_normalized"] == pytest.approx(
            0.5, abs=0.001
        )

        # 1.0 → normalized to 1.0
        r = compute_hybrid_match(profile, opp, semantic_similarity=1.0)
        assert r["score_breakdown"]["semantic_similarity_normalized"] == pytest.approx(
            1.0, abs=0.001
        )

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
        assert "location_work_mode" in bd
        assert "employment_type" in bd
        assert "semantic_similarity_normalized" in bd
        assert "semantic_similarity_raw" in bd

    def test_weights_sum_to_one(self):
        profile = self._strong_profile()
        opp = self._matching_opportunity()
        result = compute_hybrid_match(profile, opp, semantic_similarity=0.5)
        weights = result["score_breakdown"]["weights"]
        total = sum(weights.values())
        assert total == pytest.approx(1.0, abs=1e-9)

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
