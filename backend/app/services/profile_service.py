"""
Candidate Profile service module for Phase 12.
Provides business logic for profile retrieval, creation, updates,
and sub-resource management (skills, education, experience, projects, certifications).
Strictly enforces ownership and relational integrity.
"""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import (
    CandidateProfile,
    Certification,
    Education,
    Experience,
    Project,
    Skill,
)
from app.models.user import User
from app.schemas.candidate_profile import (
    CertificationCreate,
    CertificationUpdate,
    EducationCreate,
    EducationUpdate,
    ExperienceCreate,
    ExperienceUpdate,
    ProfileCreate,
    ProfileUpdate,
    ProjectCreate,
    ProjectUpdate,
    SkillCreate,
)

logger = logging.getLogger(__name__)


async def _trigger_profile_embedding(db: AsyncSession, profile_id: uuid.UUID) -> None:
    """Non-fatal candidate profile embedding generation trigger."""
    try:
        from app.services.embeddings import generate_candidate_profile_embedding

        await generate_candidate_profile_embedding(db, profile_id, commit=True)
    except Exception as exc:
        logger.warning(
            "Non-fatal error generating candidate profile embedding for %s: %s",
            profile_id,
            type(exc).__name__,
        )


# -----------------------------------------------------------------------------
# CANDIDATE PROFILE CORE OPERATIONS
# -----------------------------------------------------------------------------


async def get_profile_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    eager_load: bool = False,
) -> CandidateProfile | None:
    """
    Retrieve candidate profile associated with a user ID.
    If eager_load is True, loads all sub-resources for full profile payload.
    """
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    if eager_load:
        stmt = stmt.options(
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.educations),
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.certifications),
        )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_profile_for_user(
    db: AsyncSession,
    user: User,
) -> CandidateProfile:
    """Retrieve existing profile or create a default initialized one."""
    profile = await get_profile_by_user_id(db, user.id, eager_load=True)
    if profile is None:
        default_name = user.email.split("@")[0].replace(".", " ").title()
        profile = CandidateProfile(
            user_id=user.id,
            full_name=default_name,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        # Re-query with eager loading to initialize relationships cleanly
        profile = await get_profile_by_user_id(db, user.id, eager_load=True)
        assert profile is not None
    return profile


async def create_candidate_profile(
    db: AsyncSession,
    user: User,
    profile_in: ProfileCreate,
) -> CandidateProfile:
    """
    Explicitly create a new candidate profile.
    Raises HTTP 409 Conflict if a profile already exists for this user.
    """
    existing = await get_profile_by_user_id(db, user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate profile already exists for this user.",
        )

    profile_data = profile_in.model_dump()
    profile = CandidateProfile(
        user_id=user.id,
        **profile_data,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    await _trigger_profile_embedding(db, profile.id)
    return profile


async def update_candidate_profile(
    db: AsyncSession,
    user: User,
    profile_in: ProfileUpdate,
) -> CandidateProfile:
    """
    Update editable candidate profile fields.
    Initializes profile if none exists yet, then applies updates.
    """
    profile = await get_or_create_profile_for_user(db, user)

    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    await _trigger_profile_embedding(db, profile.id)
    return profile


# -----------------------------------------------------------------------------
# SKILLS SUB-RESOURCE OPERATIONS
# -----------------------------------------------------------------------------


async def list_skills(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> list[Skill]:
    """List all skills associated with candidate profile."""
    stmt = (
        select(Skill)
        .where(Skill.candidate_profile_id == profile_id)
        .order_by(Skill.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_skill(
    db: AsyncSession,
    profile_id: uuid.UUID,
    skill_in: SkillCreate,
) -> Skill:
    """
    Add a skill to candidate profile.
    Enforces uniqueness of skill name within the candidate profile.
    """
    # Check for duplicate skill name (case-insensitive)
    existing_stmt = select(Skill).where(
        Skill.candidate_profile_id == profile_id,
        func.lower(Skill.skill_name) == skill_in.skill_name.lower().strip(),
    )
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{skill_in.skill_name}' already exists in profile.",
        )

    skill = Skill(
        candidate_profile_id=profile_id,
        skill_name=skill_in.skill_name.strip(),
        category=skill_in.category,
        proficiency_level=skill_in.proficiency_level,
        years_of_experience=skill_in.years_of_experience,
        source=skill_in.source,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    await _trigger_profile_embedding(db, profile_id)
    return skill


async def delete_skill(
    db: AsyncSession,
    profile_id: uuid.UUID,
    skill_id: uuid.UUID,
) -> None:
    """Delete a skill from candidate profile by skill ID."""
    stmt = select(Skill).where(
        Skill.id == skill_id,
        Skill.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    skill = res.scalar_one_or_none()
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    await db.delete(skill)
    await db.commit()
    await _trigger_profile_embedding(db, profile_id)


# -----------------------------------------------------------------------------
# EDUCATION SUB-RESOURCE OPERATIONS
# -----------------------------------------------------------------------------


async def list_education(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> list[Education]:
    """List all education records for candidate profile."""
    stmt = (
        select(Education)
        .where(Education.candidate_profile_id == profile_id)
        .order_by(Education.start_date.desc().nullslast())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def add_education(
    db: AsyncSession,
    profile_id: uuid.UUID,
    edu_in: EducationCreate,
) -> Education:
    """Add an education record to candidate profile."""
    edu = Education(
        candidate_profile_id=profile_id,
        **edu_in.model_dump(),
    )
    db.add(edu)
    await db.commit()
    await db.refresh(edu)
    await _trigger_profile_embedding(db, profile_id)
    return edu


async def update_education(
    db: AsyncSession,
    profile_id: uuid.UUID,
    education_id: uuid.UUID,
    edu_in: EducationUpdate,
) -> Education:
    """Update an existing education record."""
    stmt = select(Education).where(
        Education.id == education_id,
        Education.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    edu = res.scalar_one_or_none()
    if edu is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found.",
        )

    update_data = edu_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(edu, field, value)

    # Validate end_date >= start_date if both set
    if edu.start_date and edu.end_date and edu.end_date < edu.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date cannot be earlier than start_date.",
        )

    await db.commit()
    await db.refresh(edu)
    await _trigger_profile_embedding(db, profile_id)
    return edu


async def delete_education(
    db: AsyncSession,
    profile_id: uuid.UUID,
    education_id: uuid.UUID,
) -> None:
    """Delete an education record."""
    stmt = select(Education).where(
        Education.id == education_id,
        Education.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    edu = res.scalar_one_or_none()
    if edu is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found.",
        )

    await db.delete(edu)
    await db.commit()
    await _trigger_profile_embedding(db, profile_id)


# -----------------------------------------------------------------------------
# EXPERIENCE SUB-RESOURCE OPERATIONS
# -----------------------------------------------------------------------------


async def list_experience(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> list[Experience]:
    """List all work experience records for candidate profile."""
    stmt = (
        select(Experience)
        .where(Experience.candidate_profile_id == profile_id)
        .order_by(Experience.start_date.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def add_experience(
    db: AsyncSession,
    profile_id: uuid.UUID,
    exp_in: ExperienceCreate,
) -> Experience:
    """Add a work experience record to candidate profile."""
    exp = Experience(
        candidate_profile_id=profile_id,
        **exp_in.model_dump(),
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    await _trigger_profile_embedding(db, profile_id)
    return exp


async def update_experience(
    db: AsyncSession,
    profile_id: uuid.UUID,
    experience_id: uuid.UUID,
    exp_in: ExperienceUpdate,
) -> Experience:
    """Update an existing work experience record."""
    stmt = select(Experience).where(
        Experience.id == experience_id,
        Experience.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    exp = res.scalar_one_or_none()
    if exp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found.",
        )

    update_data = exp_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(exp, field, value)

    # Validate end_date >= start_date if both set
    if exp.start_date and exp.end_date and exp.end_date < exp.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date cannot be earlier than start_date.",
        )

    await db.commit()
    await db.refresh(exp)
    await _trigger_profile_embedding(db, profile_id)
    return exp


async def delete_experience(
    db: AsyncSession,
    profile_id: uuid.UUID,
    experience_id: uuid.UUID,
) -> None:
    """Delete a work experience record."""
    stmt = select(Experience).where(
        Experience.id == experience_id,
        Experience.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    exp = res.scalar_one_or_none()
    if exp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience record not found.",
        )

    await db.delete(exp)
    await db.commit()
    await _trigger_profile_embedding(db, profile_id)


# -----------------------------------------------------------------------------
# PROJECTS SUB-RESOURCE OPERATIONS
# -----------------------------------------------------------------------------


async def list_projects(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> list[Project]:
    """List all projects for candidate profile."""
    stmt = (
        select(Project)
        .where(Project.candidate_profile_id == profile_id)
        .order_by(Project.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def add_project(
    db: AsyncSession,
    profile_id: uuid.UUID,
    proj_in: ProjectCreate,
) -> Project:
    """Add a project to candidate profile."""
    proj = Project(
        candidate_profile_id=profile_id,
        **proj_in.model_dump(),
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    await _trigger_profile_embedding(db, profile_id)
    return proj


async def update_project(
    db: AsyncSession,
    profile_id: uuid.UUID,
    project_id: uuid.UUID,
    proj_in: ProjectUpdate,
) -> Project:
    """Update an existing project record."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    proj = res.scalar_one_or_none()
    if proj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    update_data = proj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(proj, field, value)

    await db.commit()
    await db.refresh(proj)
    await _trigger_profile_embedding(db, profile_id)
    return proj


async def delete_project(
    db: AsyncSession,
    profile_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    """Delete a project."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    proj = res.scalar_one_or_none()
    if proj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    await db.delete(proj)
    await db.commit()
    await _trigger_profile_embedding(db, profile_id)


# -----------------------------------------------------------------------------
# CERTIFICATIONS SUB-RESOURCE OPERATIONS
# -----------------------------------------------------------------------------


async def list_certifications(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> list[Certification]:
    """List all certifications for candidate profile."""
    stmt = (
        select(Certification)
        .where(Certification.candidate_profile_id == profile_id)
        .order_by(Certification.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def add_certification(
    db: AsyncSession,
    profile_id: uuid.UUID,
    cert_in: CertificationCreate,
) -> Certification:
    """Add a certification to candidate profile."""
    cert = Certification(
        candidate_profile_id=profile_id,
        **cert_in.model_dump(),
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    await _trigger_profile_embedding(db, profile_id)
    return cert


async def update_certification(
    db: AsyncSession,
    profile_id: uuid.UUID,
    certification_id: uuid.UUID,
    cert_in: CertificationUpdate,
) -> Certification:
    """Update an existing certification record."""
    stmt = select(Certification).where(
        Certification.id == certification_id,
        Certification.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    cert = res.scalar_one_or_none()
    if cert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found.",
        )

    update_data = cert_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(cert, field, value)

    await db.commit()
    await db.refresh(cert)
    await _trigger_profile_embedding(db, profile_id)
    return cert


async def delete_certification(
    db: AsyncSession,
    profile_id: uuid.UUID,
    certification_id: uuid.UUID,
) -> None:
    """Delete a certification."""
    stmt = select(Certification).where(
        Certification.id == certification_id,
        Certification.candidate_profile_id == profile_id,
    )
    res = await db.execute(stmt)
    cert = res.scalar_one_or_none()
    if cert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certification not found.",
        )

    await db.delete(cert)
    await db.commit()
    await _trigger_profile_embedding(db, profile_id)
