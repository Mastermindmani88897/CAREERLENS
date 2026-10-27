"""
Normalized Autofill Payload Builder for Phase 27.

Transforms authenticated CandidateProfile and authorized Resume records into
a typed, standardized application payload suitable for third-party ATS adapters.
Enforces strict zero-inference policy: never invents screening answers, sponsorship needs,
or demographic attributes.
"""

from __future__ import annotations

from typing import Any

from app.models.candidate import CandidateProfile, Resume


def derive_names(full_name: str | None) -> tuple[str, str]:
    """
    Safely split full name into first and last name components.
    Handles single names gracefully without crashing.
    """
    if not full_name:
        return "", ""
    parts = [p.strip() for p in full_name.strip().split() if p.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def build_normalized_autofill_payload(
    profile: CandidateProfile,
    resume: Resume | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """
    Construct standardized autofill payload and list of missing fields.

    Args:
        profile: CandidateProfile entity with eager or lazy loaded relations.
        resume: Optional authorized Resume entity belonging to the candidate.

    Returns:
        tuple of (normalized_payload_dict, missing_fields_list)
    """
    first_name, last_name = derive_names(profile.full_name)

    # 1. Contact information
    email = profile.user.email if (profile.user and profile.user.email) else ""
    phone = profile.phone or ""

    contact = {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": profile.full_name or f"{first_name} {last_name}".strip(),
        "email": email,
        "phone": phone,
        "location_city": profile.location_city or "",
        "location_state": profile.location_state or "",
        "location_country": profile.location_country or "",
        "linkedin_url": profile.linkedin_url or "",
        "github_url": profile.github_url or "",
        "portfolio_url": profile.portfolio_url or "",
    }

    # 2. Education history
    educations = []
    if profile.educations:
        for edu in profile.educations:
            educations.append(
                {
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study,
                    "education_level": (
                        edu.education_level.value
                        if hasattr(edu.education_level, "value")
                        else str(edu.education_level)
                    ),
                    "start_date": edu.start_date.isoformat() if edu.start_date else None,
                    "end_date": edu.end_date.isoformat() if edu.end_date else None,
                    "is_current": edu.is_current,
                    "grade": edu.grade,
                }
            )

    # 3. Experience history
    experiences = []
    if profile.experiences:
        for exp in profile.experiences:
            experiences.append(
                {
                    "company": exp.company,
                    "title": exp.title,
                    "start_date": exp.start_date.isoformat() if exp.start_date else None,
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "is_current": exp.is_current,
                    "description": exp.description,
                    "skills_used": exp.skills_used or [],
                }
            )

    # 4. Verified skills
    skills = [s.skill_name for s in (profile.skills or []) if s.skill_name]

    # 5. Safe resume metadata (NO raw full text)
    resume_meta = None
    if resume is not None:
        resume_meta = {
            "resume_id": str(resume.id),
            "filename": resume.filename,
            "file_type": resume.file_type,
            "file_size_bytes": resume.file_size_bytes,
        }

    # Assemble structured payload
    payload: dict[str, Any] = {
        "contact": contact,
        "educations": educations,
        "experiences": experiences,
        "skills": skills,
        "resume": resume_meta,
    }

    # 6. Evaluate missing fields requiring candidate intervention
    missing_fields: list[str] = []
    if not first_name or not last_name:
        missing_fields.append("contact.legal_name")
    if not phone:
        missing_fields.append("contact.phone")
    if not educations:
        missing_fields.append("education.history")
    if not resume_meta:
        missing_fields.append("resume.attachment")

    # Standard ATS screening disclosures that cannot be inferred automatically
    missing_fields.extend(
        [
            "screening.work_authorization_status",
            "screening.visa_sponsorship_needed",
            "screening.salary_expectations",
            "screening.custom_employer_questions",
        ]
    )

    return payload, missing_fields
