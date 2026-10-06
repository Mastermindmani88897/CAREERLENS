"""
Candidate Profile and Resume Synchronization API endpoints for Phase 12.
Provides authenticated RESTful endpoints for:
- Candidate Profile CRUD (/api/v1/profiles/me)
- Resume-to-Profile Synchronization (/api/v1/profiles/me/sync-from-resume/{resume_id})
- Skills sub-resource (/api/v1/profiles/me/skills)
- Education sub-resource (/api/v1/profiles/me/education)
- Experience sub-resource (/api/v1/profiles/me/experience)
- Projects sub-resource (/api/v1/profiles/me/projects)
- Certifications sub-resource (/api/v1/profiles/me/certifications)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.candidate_profile import (
    CertificationCreate,
    CertificationResponse,
    CertificationUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    ProfileCreate,
    ProfileDetailResponse,
    ProfileResponse,
    ProfileSyncResult,
    ProfileUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SkillCreate,
    SkillResponse,
)
from app.services.profile_service import (
    add_certification,
    add_education,
    add_experience,
    add_project,
    add_skill,
    create_candidate_profile,
    delete_certification,
    delete_education,
    delete_experience,
    delete_project,
    delete_skill,
    get_or_create_profile_for_user,
    list_certifications,
    list_education,
    list_experience,
    list_projects,
    list_skills,
    update_candidate_profile,
    update_certification,
    update_education,
    update_experience,
    update_project,
)
from app.services.profile_sync_service import sync_profile_from_resume

router = APIRouter()


# -----------------------------------------------------------------------------
# CANDIDATE PROFILE CORE ENDPOINTS
# -----------------------------------------------------------------------------


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create candidate profile",
    description="Explicitly initialize candidate profile for authenticated user.",
)
async def create_profile(
    profile_in: ProfileCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    profile = await create_candidate_profile(db=db, user=current_user, profile_in=profile_in)
    return ProfileResponse.model_validate(profile)


@router.get(
    "/me",
    response_model=ProfileDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user candidate profile",
    description="Returns candidate profile with all sub-resources (skills, education, etc.).",
)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileDetailResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    return ProfileDetailResponse.model_validate(profile)


@router.put(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate profile",
    description="Update candidate profile attributes (preserves non-provided fields).",
)
async def update_my_profile(
    profile_in: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    profile = await update_candidate_profile(db=db, user=current_user, profile_in=profile_in)
    return ProfileResponse.model_validate(profile)


@router.post(
    "/me/sync-from-resume/{resume_id}",
    response_model=ProfileSyncResult,
    status_code=status.HTTP_200_OK,
    summary="Synchronize profile from parsed resume",
    description=(
        "Controlled merge of extracted attributes from a parsed resume into the candidate profile. "
        "Strictly preserves existing user-entered values and prevents duplicates."
    ),
)
async def sync_from_resume(
    resume_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileSyncResult:
    return await sync_profile_from_resume(db=db, user=current_user, resume_id=resume_id)


# -----------------------------------------------------------------------------
# SKILLS SUB-RESOURCE ENDPOINTS
# -----------------------------------------------------------------------------


@router.get(
    "/me/skills",
    response_model=list[SkillResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate skills",
)
async def get_skills(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SkillResponse]:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    skills = await list_skills(db=db, profile_id=profile.id)
    return [SkillResponse.model_validate(s) for s in skills]


@router.post(
    "/me/skills",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add skill to profile",
)
async def create_skill(
    skill_in: SkillCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    skill = await add_skill(db=db, profile_id=profile.id, skill_in=skill_in)
    return SkillResponse.model_validate(skill)


@router.delete(
    "/me/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete skill from profile",
)
async def remove_skill(
    skill_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    await delete_skill(db=db, profile_id=profile.id, skill_id=skill_id)


# -----------------------------------------------------------------------------
# EDUCATION SUB-RESOURCE ENDPOINTS
# -----------------------------------------------------------------------------


@router.get(
    "/me/education",
    response_model=list[EducationResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate education records",
)
async def get_education(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EducationResponse]:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    items = await list_education(db=db, profile_id=profile.id)
    return [EducationResponse.model_validate(e) for e in items]


@router.post(
    "/me/education",
    response_model=EducationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add education record",
)
async def create_education(
    edu_in: EducationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EducationResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await add_education(db=db, profile_id=profile.id, edu_in=edu_in)
    return EducationResponse.model_validate(item)


@router.put(
    "/me/education/{education_id}",
    response_model=EducationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update education record",
)
async def modify_education(
    education_id: uuid.UUID,
    edu_in: EducationUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EducationResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await update_education(
        db=db,
        profile_id=profile.id,
        education_id=education_id,
        edu_in=edu_in,
    )
    return EducationResponse.model_validate(item)


@router.delete(
    "/me/education/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete education record",
)
async def remove_education(
    education_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    await delete_education(db=db, profile_id=profile.id, education_id=education_id)


# -----------------------------------------------------------------------------
# EXPERIENCE SUB-RESOURCE ENDPOINTS
# -----------------------------------------------------------------------------


@router.get(
    "/me/experience",
    response_model=list[ExperienceResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate work experience",
)
async def get_experience(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ExperienceResponse]:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    items = await list_experience(db=db, profile_id=profile.id)
    return [ExperienceResponse.model_validate(e) for e in items]


@router.post(
    "/me/experience",
    response_model=ExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add work experience record",
)
async def create_experience(
    exp_in: ExperienceCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await add_experience(db=db, profile_id=profile.id, exp_in=exp_in)
    return ExperienceResponse.model_validate(item)


@router.put(
    "/me/experience/{experience_id}",
    response_model=ExperienceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update work experience record",
)
async def modify_experience(
    experience_id: uuid.UUID,
    exp_in: ExperienceUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await update_experience(
        db=db,
        profile_id=profile.id,
        experience_id=experience_id,
        exp_in=exp_in,
    )
    return ExperienceResponse.model_validate(item)


@router.delete(
    "/me/experience/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete work experience record",
)
async def remove_experience(
    experience_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    await delete_experience(db=db, profile_id=profile.id, experience_id=experience_id)


# -----------------------------------------------------------------------------
# PROJECTS SUB-RESOURCE ENDPOINTS
# -----------------------------------------------------------------------------


@router.get(
    "/me/projects",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate projects",
)
async def get_projects(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProjectResponse]:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    items = await list_projects(db=db, profile_id=profile.id)
    return [ProjectResponse.model_validate(p) for p in items]


@router.post(
    "/me/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add project record",
)
async def create_project(
    proj_in: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await add_project(db=db, profile_id=profile.id, proj_in=proj_in)
    return ProjectResponse.model_validate(item)


@router.put(
    "/me/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project record",
)
async def modify_project(
    project_id: uuid.UUID,
    proj_in: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await update_project(
        db=db,
        profile_id=profile.id,
        project_id=project_id,
        proj_in=proj_in,
    )
    return ProjectResponse.model_validate(item)


@router.delete(
    "/me/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project record",
)
async def remove_project(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    await delete_project(db=db, profile_id=profile.id, project_id=project_id)


# -----------------------------------------------------------------------------
# CERTIFICATIONS SUB-RESOURCE ENDPOINTS
# -----------------------------------------------------------------------------


@router.get(
    "/me/certifications",
    response_model=list[CertificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate certifications",
)
async def get_certifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CertificationResponse]:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    items = await list_certifications(db=db, profile_id=profile.id)
    return [CertificationResponse.model_validate(c) for c in items]


@router.post(
    "/me/certifications",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add certification record",
)
async def create_certification(
    cert_in: CertificationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificationResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await add_certification(db=db, profile_id=profile.id, cert_in=cert_in)
    return CertificationResponse.model_validate(item)


@router.put(
    "/me/certifications/{certification_id}",
    response_model=CertificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update certification record",
)
async def modify_certification(
    certification_id: uuid.UUID,
    cert_in: CertificationUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificationResponse:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    item = await update_certification(
        db=db,
        profile_id=profile.id,
        certification_id=certification_id,
        cert_in=cert_in,
    )
    return CertificationResponse.model_validate(item)


@router.delete(
    "/me/certifications/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete certification record",
)
async def remove_certification(
    certification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await get_or_create_profile_for_user(db=db, user=current_user)
    await delete_certification(db=db, profile_id=profile.id, certification_id=certification_id)
