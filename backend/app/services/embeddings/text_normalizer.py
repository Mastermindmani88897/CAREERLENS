"""
Deterministic text normalization and builders for Phase 16 Local Embedding Foundation.
Constructs compact, standardized semantic representations of opportunities and candidates.
Excludes all personal identifying information (PII), credentials, IDs, and compensation data.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.candidate import (
        CandidateProfile,
        Certification,
        Education,
        Experience,
        Project,
        Skill,
    )
    from app.models.opportunity import Opportunity, OpportunitySkill


def normalize_whitespace(text: str | None) -> str:
    """
    Normalize whitespace by trimming and collapsing multiple spaces/newlines
    into a single space.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def build_opportunity_embedding_text(
    opportunity: Opportunity,
    skills: list[OpportunitySkill] | None = None,
) -> str:
    """
    Construct deterministic text for Opportunity embeddings.

    Included fields:
    - Title
    - Company
    - Opportunity Type
    - Employment Type
    - Work Mode
    - Location
    - Experience Requirements
    - Education Requirements
    - Required Skills (sorted deterministically)
    - Preferred Skills (sorted deterministically)
    - Description (compacted)

    Excluded fields:
    - Primary key IDs, foreign keys, source URL, raw JSON payloads, created/updated timestamps.
    """
    parts: list[str] = []

    # 1. Core identifiers
    if opportunity.title:
        parts.append(f"Role: {normalize_whitespace(opportunity.title)}")

    if opportunity.company:
        parts.append(f"Company: {normalize_whitespace(opportunity.company)}")

    # 2. Opportunity types & modes
    opp_type = getattr(opportunity, "opportunity_type", None)
    if opp_type:
        val = opp_type.value if hasattr(opp_type, "value") else str(opp_type)
        parts.append(f"Type: {normalize_whitespace(val)}")

    emp_type = getattr(opportunity, "employment_type", None)
    if emp_type:
        val = emp_type.value if hasattr(emp_type, "value") else str(emp_type)
        parts.append(f"Employment: {normalize_whitespace(val)}")

    work_mode = getattr(opportunity, "work_mode", None)
    if work_mode:
        val = work_mode.value if hasattr(work_mode, "value") else str(work_mode)
        parts.append(f"Work Mode: {normalize_whitespace(val)}")

    loc_val = getattr(opportunity, "location", None)
    if not loc_val:
        city = getattr(opportunity, "location_city", None)
        country = getattr(opportunity, "location_country", None)
        if city and country:
            loc_val = f"{city}, {country}"
        elif city:
            loc_val = city
        elif country:
            loc_val = country
    if loc_val:
        parts.append(f"Location: {normalize_whitespace(loc_val)}")

    # 3. Experience & education requirements
    min_exp = getattr(opportunity, "min_experience_years", None)
    max_exp = getattr(opportunity, "max_experience_years", None)
    if min_exp is not None or max_exp is not None:
        if min_exp is not None and max_exp is not None:
            parts.append(f"Experience: {min_exp}-{max_exp} years")
        elif min_exp is not None:
            parts.append(f"Experience: {min_exp}+ years")
        elif max_exp is not None:
            parts.append(f"Experience: up to {max_exp} years")

    edu_req = getattr(opportunity, "required_education_level", None) or getattr(
        opportunity, "education_requirement", None
    )
    if edu_req:
        val = edu_req.value if hasattr(edu_req, "value") else str(edu_req)
        parts.append(f"Education: {normalize_whitespace(val)}")

    # 4. Skills (sorted deterministically)
    active_skills = skills if skills is not None else getattr(opportunity, "skills", [])
    if active_skills:
        req_skills: list[str] = []
        pref_skills: list[str] = []
        for s in active_skills:
            s_name = getattr(s, "skill_name", "")
            if not s_name:
                continue
            is_req = getattr(s, "is_required", True)
            if is_req:
                req_skills.append(normalize_whitespace(s_name))
            else:
                pref_skills.append(normalize_whitespace(s_name))

        if req_skills:
            sorted_req = sorted(set(req_skills), key=lambda x: x.lower())
            parts.append(f"Required Skills: {', '.join(sorted_req)}")
        if pref_skills:
            sorted_pref = sorted(set(pref_skills), key=lambda x: x.lower())
            parts.append(f"Preferred Skills: {', '.join(sorted_pref)}")

    # 5. Opportunity Description (truncated to 2000 chars to fit sequence capacity)
    if opportunity.description:
        cleaned_desc = normalize_whitespace(opportunity.description)
        if len(cleaned_desc) > 2000:
            cleaned_desc = cleaned_desc[:2000]
        parts.append(f"Description: {cleaned_desc}")

    return " | ".join(parts)


def build_candidate_embedding_text(
    profile: CandidateProfile,
    skills: list[Skill] | None = None,
    experiences: list[Experience] | None = None,
    educations: list[Education] | None = None,
    projects: list[Project] | None = None,
    certifications: list[Certification] | None = None,
) -> str:
    """
    Construct deterministic text for CandidateProfile embeddings.

    Included fields:
    - Professional headline
    - Professional summary
    - Technical and domain skills (sorted deterministically)
    - Work experiences (sorted deterministically by start_date / company)
    - Education history (sorted deterministically)
    - Projects & technologies (sorted deterministically)
    - Certifications (sorted deterministically)

    EXCLUDED (Privacy & Security):
    - Full name / personal identity
    - Passwords / hashes
    - Email, phone, street addresses
    - User IDs, profile IDs
    - Authentication tokens / API keys
    - Compensation / salary information
    - External social profile URLs
    """
    parts: list[str] = []

    # 1. Professional headline & summary
    headline = getattr(profile, "headline", None)
    if headline:
        parts.append(f"Title: {normalize_whitespace(headline)}")

    summary = getattr(profile, "summary", None)
    if summary:
        cleaned_summary = normalize_whitespace(summary)
        if len(cleaned_summary) > 1000:
            cleaned_summary = cleaned_summary[:1000]
        parts.append(f"Summary: {cleaned_summary}")

    # 2. Skills (sorted deterministically by name)
    active_skills = skills if skills is not None else getattr(profile, "skills", [])
    if active_skills:
        skill_entries: list[str] = []
        for s in active_skills:
            s_name = getattr(s, "skill_name", "")
            if not s_name:
                continue
            clean_name = normalize_whitespace(s_name)
            prof = getattr(s, "proficiency_level", None)
            prof_val = prof.value if hasattr(prof, "value") else (str(prof) if prof else "")
            if prof_val:
                skill_entries.append(f"{clean_name} ({prof_val})")
            else:
                skill_entries.append(clean_name)
        if skill_entries:
            sorted_skills = sorted(set(skill_entries), key=lambda x: x.lower())
            parts.append(f"Skills: {', '.join(sorted_skills)}")

    # 3. Work experiences (sorted deterministically)
    active_exp = experiences if experiences is not None else getattr(profile, "experiences", [])
    if active_exp:
        exp_entries: list[str] = []
        # Sort by title, company
        sorted_exp_objs = sorted(
            active_exp,
            key=lambda e: (
                str(getattr(e, "start_date", "") or ""),
                str(getattr(e, "title", "") or "").lower(),
                str(getattr(e, "company", "") or "").lower(),
            ),
            reverse=True,
        )
        for e in sorted_exp_objs:
            title = normalize_whitespace(getattr(e, "title", ""))
            company = normalize_whitespace(getattr(e, "company", ""))
            desc = normalize_whitespace(getattr(e, "description", "") or "")
            if len(desc) > 300:
                desc = desc[:300]
            skills_used = getattr(e, "skills_used", None) or []
            exp_text = f"{title} at {company}"
            if skills_used:
                sorted_used = sorted(skills_used, key=lambda x: x.lower())
                exp_text += f" (Skills: {', '.join(sorted_used)})"
            if desc:
                exp_text += f": {desc}"
            exp_entries.append(exp_text)
        if exp_entries:
            parts.append(f"Experience: {' | '.join(exp_entries)}")

    # 4. Education (sorted deterministically)
    active_edu = educations if educations is not None else getattr(profile, "educations", [])
    if active_edu:
        edu_entries: list[str] = []
        sorted_edu_objs = sorted(
            active_edu,
            key=lambda d: (
                str(getattr(d, "degree", "") or "").lower(),
                str(getattr(d, "institution", "") or "").lower(),
            ),
        )
        for d in sorted_edu_objs:
            degree = normalize_whitespace(getattr(d, "degree", ""))
            field = normalize_whitespace(getattr(d, "field_of_study", ""))
            inst = normalize_whitespace(getattr(d, "institution", ""))
            edu_text = f"{degree} in {field} from {inst}" if field else f"{degree} from {inst}"
            edu_entries.append(edu_text)
        if edu_entries:
            parts.append(f"Education: {' | '.join(edu_entries)}")

    # 5. Projects (sorted deterministically)
    active_proj = projects if projects is not None else getattr(profile, "projects", [])
    if active_proj:
        proj_entries: list[str] = []
        sorted_proj_objs = sorted(
            active_proj,
            key=lambda p: str(getattr(p, "title", "") or "").lower(),
        )
        for p in sorted_proj_objs:
            title = normalize_whitespace(getattr(p, "title", ""))
            techs = getattr(p, "technologies", None) or []
            desc = normalize_whitespace(getattr(p, "description", "") or "")
            if len(desc) > 200:
                desc = desc[:200]
            proj_text = title
            if techs:
                sorted_techs = sorted(techs, key=lambda x: x.lower())
                proj_text += f" ({', '.join(sorted_techs)})"
            if desc:
                proj_text += f": {desc}"
            proj_entries.append(proj_text)
        if proj_entries:
            parts.append(f"Projects: {' | '.join(proj_entries)}")

    # 6. Certifications (sorted deterministically)
    active_certs = (
        certifications if certifications is not None else getattr(profile, "certifications", [])
    )
    if active_certs:
        cert_entries: list[str] = []
        sorted_cert_objs = sorted(
            active_certs,
            key=lambda c: str(getattr(c, "name", "") or "").lower(),
        )
        for c in sorted_cert_objs:
            name = normalize_whitespace(getattr(c, "name", ""))
            org = normalize_whitespace(getattr(c, "issuing_organization", ""))
            cert_entries.append(f"{name} ({org})" if org else name)
        if cert_entries:
            parts.append(f"Certifications: {', '.join(cert_entries)}")

    return " | ".join(parts)
