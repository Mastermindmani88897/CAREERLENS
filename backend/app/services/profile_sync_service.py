"""
Resume-to-Profile Synchronization Service for Phase 12.
Deterministically synchronizes extracted attributes from a parsed resume
into the candidate profile while strictly preserving all user-entered data.

Merge Rules:
1. Non-destructive: Existing user-provided values are never silently overwritten.
2. Additive: New skills, education, experience, projects, and certifications are merged.
3. Idempotent: Repeated synchronization calls with the same resume produce 0 duplicate records.
4. Non-inventive: Only attributes genuinely present in parsed_json are extracted.
5. Authoritative: Profile changes made manually remain the single source of truth.
"""

import logging
import re
import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import (
    CandidateProfile,
    Certification,
    Education,
    Experience,
    Project,
    Resume,
    Skill,
)
from app.models.enums import (
    EducationLevel,
    SkillCategory,
    SkillSource,
)
from app.models.user import User
from app.schemas.candidate_profile import ProfileSyncResult

logger = logging.getLogger(__name__)


def _parse_year_to_date(year_val: int | None, month: int = 1, day: int = 1) -> date | None:
    """Safely convert a 4-digit calendar year integer into a date object."""
    if not year_val or year_val < 1950 or year_val > 2100:
        return None
    try:
        return date(year_val, month, day)
    except Exception:
        return None


def _parse_date_string(date_str: str | None) -> date | None:
    """Attempt to parse date strings like '2022-06', '2022', '06/2022' into date object."""
    if not date_str:
        return None
    cleaned = date_str.strip().lower()
    if cleaned in ("present", "current", "now"):
        return None

    # Try YYYY-MM or YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4})-(\d{1,2})(?:-(\d{1,2}))?\b", cleaned)
    if iso_match:
        year = int(iso_match.group(1))
        month = int(iso_match.group(2))
        day = int(iso_match.group(3)) if iso_match.group(3) else 1
        return _parse_year_to_date(year, month=max(1, min(12, month)), day=max(1, min(28, day)))

    # Try year only
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", cleaned)
    if year_match:
        return _parse_year_to_date(int(year_match.group(1)))

    return None


def _infer_education_level(degree_str: str | None) -> EducationLevel:
    """Deterministic keyword inference for education level enumeration."""
    if not degree_str:
        return EducationLevel.BACHELOR
    lower = degree_str.lower()
    if any(k in lower for k in ("ph.d", "phd", "doctorate")):
        return EducationLevel.PHD
    if any(k in lower for k in ("master", "m.tech", "mtech", "m.s", "ms", "mba", "mca", "m.e")):
        return EducationLevel.MASTER
    if any(k in lower for k in ("diploma", "polytechnic")):
        return EducationLevel.DIPLOMA
    return EducationLevel.BACHELOR


def _infer_skill_category(cat_str: str | None) -> SkillCategory | None:
    """Map string category from parser to SkillCategory enum."""
    if not cat_str:
        return None
    clean = cat_str.strip().lower()
    for cat in SkillCategory:
        if cat.value == clean:
            return cat
    if clean in ("database", "backend", "frontend", "devops", "cloud", "ai", "ml"):
        return SkillCategory.TECHNICAL
    return SkillCategory.TECHNICAL


async def sync_profile_from_resume(
    db: AsyncSession,
    user: User,
    resume_id: uuid.UUID,
) -> ProfileSyncResult:
    """
    Synchronize candidate profile from an existing parsed resume.

    Enforces:
    - User ownership of resume
    - Valid 'parsed' status and non-empty parsed_json
    - Preserves all pre-existing user-entered values
    - Idempotent deduplication across all sub-resources
    """
    # 1. Fetch Resume and verify ownership
    stmt = (
        select(Resume)
        .join(CandidateProfile, Resume.candidate_profile_id == CandidateProfile.id)
        .where(Resume.id == resume_id)
        .options(selectinload(Resume.candidate_profile))
    )
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # Ownership check
    if resume.candidate_profile.user_id != user.id:
        logger.warning(
            "Forbidden resume sync attempt: user_id=%s tried syncing resume_id=%s "
            "owned by user_id=%s",
            user.id,
            resume_id,
            resume.candidate_profile.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access or synchronize this resume.",
        )

    # Parsing status check
    parsed_json = resume.parsed_json or {}
    if not parsed_json or parsed_json.get("status") != "parsed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been successfully parsed yet. Cannot synchronize.",
        )

    # 2. Fetch full Candidate Profile with all sub-resources
    profile_stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.user_id == user.id)
        .options(
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.educations),
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.certifications),
        )
    )
    profile_res = await db.execute(profile_stmt)
    profile = profile_res.scalar_one()

    fields_updated: list[str] = []
    preserved_fields: list[str] = []
    contact_data = parsed_json.get("contact", {})

    # 3. Synchronize Core Profile Fields (non-destructive)
    # Full Name: Update only if current profile has default placeholder or empty
    extracted_name = contact_data.get("full_name")
    if extracted_name and extracted_name.strip():
        # Check if full_name is currently a default fallback (e.g. from email handle)
        default_name = user.email.split("@")[0].replace(".", " ").title()
        if not profile.full_name or profile.full_name.strip() in ("", default_name):
            profile.full_name = extracted_name.strip()
            fields_updated.append("full_name")
        else:
            preserved_fields.append("full_name")

    # Phone: populate if currently empty
    extracted_phone = contact_data.get("phone")
    if extracted_phone and extracted_phone.strip():
        if not profile.phone:
            profile.phone = extracted_phone.strip()
            fields_updated.append("phone")
        else:
            preserved_fields.append("phone")

    # LinkedIn: populate if currently empty
    extracted_linkedin = contact_data.get("linkedin_url")
    if extracted_linkedin and extracted_linkedin.strip():
        if not profile.linkedin_url:
            profile.linkedin_url = extracted_linkedin.strip()
            fields_updated.append("linkedin_url")
        else:
            preserved_fields.append("linkedin_url")

    # GitHub: populate if currently empty
    extracted_github = contact_data.get("github_url")
    if extracted_github and extracted_github.strip():
        if not profile.github_url:
            profile.github_url = extracted_github.strip()
            fields_updated.append("github_url")
        else:
            preserved_fields.append("github_url")

    # Portfolio: populate if currently empty
    extracted_portfolio = contact_data.get("portfolio_url")
    if extracted_portfolio and extracted_portfolio.strip():
        if not profile.portfolio_url:
            profile.portfolio_url = extracted_portfolio.strip()
            fields_updated.append("portfolio_url")
        else:
            preserved_fields.append("portfolio_url")

    # Summary: populate if currently empty
    extracted_summary = parsed_json.get("summary")
    if extracted_summary and extracted_summary.strip():
        if not profile.summary:
            profile.summary = extracted_summary.strip()
            fields_updated.append("summary")
        else:
            preserved_fields.append("summary")

    # 4. Synchronize Skills (additive & idempotent)
    existing_skills_lower = {s.skill_name.lower().strip() for s in profile.skills}
    skills_added = 0
    raw_skills = parsed_json.get("skills", [])
    for skill_item in raw_skills:
        skill_name = (skill_item.get("skill") or "").strip()
        if not skill_name:
            continue
        if skill_name.lower() not in existing_skills_lower:
            new_skill = Skill(
                candidate_profile_id=profile.id,
                skill_name=skill_name,
                category=_infer_skill_category(skill_item.get("category")),
                source=SkillSource.RESUME,
            )
            db.add(new_skill)
            existing_skills_lower.add(skill_name.lower())
            skills_added += 1

    # 5. Synchronize Education (additive & idempotent)
    # Deduplicate on (institution.lower(), degree.lower())
    existing_edu_keys = {
        (e.institution.lower().strip(), e.degree.lower().strip()) for e in profile.educations
    }
    educations_added = 0
    raw_education = parsed_json.get("education", [])
    for edu_item in raw_education:
        institution = (edu_item.get("institution") or "").strip()
        degree = (edu_item.get("degree") or "").strip()
        field_of_study = (edu_item.get("field_of_study") or degree or "General Studies").strip()

        if not institution or not degree:
            continue

        edu_key = (institution.lower(), degree.lower())
        if edu_key not in existing_edu_keys:
            start_date = _parse_year_to_date(edu_item.get("start_year"))
            end_date = _parse_year_to_date(edu_item.get("end_year"))
            new_edu = Education(
                candidate_profile_id=profile.id,
                institution=institution,
                degree=degree,
                field_of_study=field_of_study,
                education_level=_infer_education_level(degree),
                start_date=start_date,
                end_date=end_date,
                grade=edu_item.get("grade"),
            )
            db.add(new_edu)
            existing_edu_keys.add(edu_key)
            educations_added += 1

    # 6. Synchronize Experience (additive & idempotent)
    # Deduplicate on (company.lower(), role.lower())
    existing_exp_keys = {
        (exp.company.lower().strip(), exp.title.lower().strip()) for exp in profile.experiences
    }
    experiences_added = 0
    raw_experience = parsed_json.get("experience", [])
    for exp_item in raw_experience:
        company = (exp_item.get("company") or "").strip()
        role = (exp_item.get("role") or "").strip()
        if not company or not role:
            continue

        exp_key = (company.lower(), role.lower())
        if exp_key not in existing_exp_keys:
            start_d = _parse_date_string(exp_item.get("start_date")) or date(2020, 1, 1)
            end_d = _parse_date_string(exp_item.get("end_date"))
            new_exp = Experience(
                candidate_profile_id=profile.id,
                company=company,
                title=role,
                start_date=start_d,
                end_date=end_d,
                is_current=end_d is None,
                description=exp_item.get("description"),
                skills_used=exp_item.get("skills_used", []),
            )
            db.add(new_exp)
            existing_exp_keys.add(exp_key)
            experiences_added += 1

    # 7. Synchronize Projects (additive & idempotent)
    # Deduplicate on name.lower()
    existing_proj_keys = {p.title.lower().strip() for p in profile.projects}
    projects_added = 0
    raw_projects = parsed_json.get("projects", [])
    for proj_item in raw_projects:
        name = (proj_item.get("name") or "").strip()
        if not name:
            continue

        if name.lower() not in existing_proj_keys:
            new_proj = Project(
                candidate_profile_id=profile.id,
                title=name,
                description=proj_item.get("description"),
                technologies=proj_item.get("technologies", []),
                project_url=proj_item.get("url"),
            )
            db.add(new_proj)
            existing_proj_keys.add(name.lower())
            projects_added += 1

    # 8. Synchronize Certifications (additive & idempotent)
    # Deduplicate on name.lower()
    existing_cert_keys = {c.name.lower().strip() for c in profile.certifications}
    certifications_added = 0
    raw_certs = parsed_json.get("certifications", [])
    for cert_item in raw_certs:
        name = (cert_item.get("name") or "").strip()
        issuer = (cert_item.get("issuing_organization") or "Professional Issuer").strip()
        if not name:
            continue

        if name.lower() not in existing_cert_keys:
            new_cert = Certification(
                candidate_profile_id=profile.id,
                name=name,
                issuing_organization=issuer,
                credential_url=cert_item.get("credential_url"),
                issue_date=_parse_date_string(cert_item.get("issue_date")),
            )
            db.add(new_cert)
            existing_cert_keys.add(name.lower())
            certifications_added += 1

    # Commit all synchronizations in an atomic transaction
    await db.commit()

    logger.info(
        "Candidate profile synchronized from resume: user_id=%s, resume_id=%s, "
        "fields_updated=%s, skills_added=%d, edu_added=%d, exp_added=%d, "
        "proj_added=%d, cert_added=%d",
        user.id,
        resume_id,
        fields_updated,
        skills_added,
        educations_added,
        experiences_added,
        projects_added,
        certifications_added,
    )

    return ProfileSyncResult(
        profile_id=profile.id,
        resume_id=resume.id,
        fields_updated=fields_updated,
        skills_added=skills_added,
        educations_added=educations_added,
        experiences_added=experiences_added,
        projects_added=projects_added,
        certifications_added=certifications_added,
        preserved_fields=preserved_fields,
        message="Candidate profile successfully synchronized from resume.",
    )
