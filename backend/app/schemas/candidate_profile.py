"""
Pydantic schemas for Phase 12 Candidate Profile API and Resume Synchronization.
Defines strongly typed models for candidate profile attributes, sub-resources,
and synchronization responses.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    EducationLevel,
    EmploymentType,
    SkillCategory,
    SkillProficiency,
    SkillSource,
    WorkMode,
)

# -----------------------------------------------------------------------------
# SUB-RESOURCE SCHEMAS
# -----------------------------------------------------------------------------


class SkillBase(BaseModel):
    """Base attributes for candidate skills."""

    skill_name: str = Field(..., min_length=1, max_length=255, description="Name of the skill")
    category: SkillCategory | None = None
    proficiency_level: SkillProficiency | None = None
    years_of_experience: int | None = Field(None, ge=0, le=70)
    source: SkillSource = SkillSource.MANUAL


class SkillCreate(SkillBase):
    """Payload to add a skill to candidate profile."""

    pass


class SkillResponse(SkillBase):
    """API response model for candidate skill."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    created_at: datetime


class EducationBase(BaseModel):
    """Base attributes for education records."""

    institution: str = Field(..., min_length=1, max_length=255)
    degree: str = Field(..., min_length=1, max_length=255)
    field_of_study: str = Field(..., min_length=1, max_length=255)
    education_level: EducationLevel = EducationLevel.BACHELOR
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    grade: str | None = Field(None, max_length=50)
    description: str | None = None

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: date | None, info: Any) -> date | None:
        if v and "start_date" in info.data and info.data["start_date"]:
            start = info.data["start_date"]
            if start and v < start:
                raise ValueError("end_date cannot be earlier than start_date")
        return v


class EducationCreate(EducationBase):
    """Payload to add an education record."""

    pass


class EducationUpdate(BaseModel):
    """Payload to update an existing education record."""

    institution: str | None = Field(None, min_length=1, max_length=255)
    degree: str | None = Field(None, min_length=1, max_length=255)
    field_of_study: str | None = Field(None, min_length=1, max_length=255)
    education_level: EducationLevel | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    grade: str | None = Field(None, max_length=50)
    description: str | None = None


class EducationResponse(EducationBase):
    """API response model for education record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID


class ExperienceBase(BaseModel):
    """Base attributes for work experience records."""

    company: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    employment_type: EmploymentType | None = None
    location: str | None = Field(None, max_length=255)
    work_mode: WorkMode | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    skills_used: list[str] = Field(default_factory=list)

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: date | None, info: Any) -> date | None:
        if v and "start_date" in info.data and info.data["start_date"]:
            start = info.data["start_date"]
            if start and v < start:
                raise ValueError("end_date cannot be earlier than start_date")
        return v


class ExperienceCreate(ExperienceBase):
    """Payload to add a work experience record."""

    pass


class ExperienceUpdate(BaseModel):
    """Payload to update an existing work experience record."""

    company: str | None = Field(None, min_length=1, max_length=255)
    title: str | None = Field(None, min_length=1, max_length=255)
    employment_type: EmploymentType | None = None
    location: str | None = Field(None, max_length=255)
    work_mode: WorkMode | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    description: str | None = None
    skills_used: list[str] | None = None


class ExperienceResponse(ExperienceBase):
    """API response model for work experience record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    created_at: datetime


class ProjectBase(BaseModel):
    """Base attributes for candidate project records."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    project_url: str | None = None
    repo_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectCreate(ProjectBase):
    """Payload to add a project record."""

    pass


class ProjectUpdate(BaseModel):
    """Payload to update an existing project record."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    technologies: list[str] | None = None
    project_url: str | None = None
    repo_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectResponse(ProjectBase):
    """API response model for project record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    created_at: datetime


class CertificationBase(BaseModel):
    """Base attributes for professional certifications."""

    name: str = Field(..., min_length=1, max_length=255)
    issuing_organization: str = Field(..., min_length=1, max_length=255)
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_id: str | None = Field(None, max_length=255)
    credential_url: str | None = None


class CertificationCreate(CertificationBase):
    """Payload to add a certification record."""

    pass


class CertificationUpdate(BaseModel):
    """Payload to update an existing certification record."""

    name: str | None = Field(None, min_length=1, max_length=255)
    issuing_organization: str | None = Field(None, min_length=1, max_length=255)
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_id: str | None = Field(None, max_length=255)
    credential_url: str | None = None


class CertificationResponse(CertificationBase):
    """API response model for certification record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    created_at: datetime


# -----------------------------------------------------------------------------
# CANDIDATE PROFILE SCHEMAS
# -----------------------------------------------------------------------------


class ProfileBase(BaseModel):
    """Core attributes for a candidate profile."""

    full_name: str = Field(..., min_length=1, max_length=255)
    headline: str | None = Field(None, max_length=500)
    summary: str | None = None
    phone: str | None = Field(None, max_length=50)
    location_city: str | None = Field(None, max_length=100)
    location_state: str | None = Field(None, max_length=100)
    location_country: str | None = Field(None, max_length=100)
    preferred_work_mode: WorkMode = WorkMode.ANY
    preferred_employment_type: EmploymentType = EmploymentType.ANY
    preferred_salary_min: int | None = Field(None, ge=0)
    preferred_salary_max: int | None = Field(None, ge=0)
    preferred_salary_currency: str | None = Field("INR", max_length=10)
    open_to_relocation: bool = False
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ProfileCreate(ProfileBase):
    """Payload to explicitly create or initialize a candidate profile."""

    pass


class ProfileUpdate(BaseModel):
    """Payload to update editable candidate profile fields."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    headline: str | None = Field(None, max_length=500)
    summary: str | None = None
    phone: str | None = Field(None, max_length=50)
    location_city: str | None = Field(None, max_length=100)
    location_state: str | None = Field(None, max_length=100)
    location_country: str | None = Field(None, max_length=100)
    preferred_work_mode: WorkMode | None = None
    preferred_employment_type: EmploymentType | None = None
    preferred_salary_min: int | None = Field(None, ge=0)
    preferred_salary_max: int | None = Field(None, ge=0)
    preferred_salary_currency: str | None = Field(None, max_length=10)
    open_to_relocation: bool | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ProfileResponse(ProfileBase):
    """Standard candidate profile API response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProfileDetailResponse(ProfileResponse):
    """Comprehensive candidate profile response with all nested sub-resources."""

    skills: list[SkillResponse] = Field(default_factory=list)
    educations: list[EducationResponse] = Field(default_factory=list)
    experiences: list[ExperienceResponse] = Field(default_factory=list)
    projects: list[ProjectResponse] = Field(default_factory=list)
    certifications: list[CertificationResponse] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# SYNCHRONIZATION SCHEMAS
# -----------------------------------------------------------------------------


class ProfileSyncResult(BaseModel):
    """Structured audit summary returned following a resume-to-profile sync."""

    profile_id: uuid.UUID
    resume_id: uuid.UUID
    fields_updated: list[str] = Field(default_factory=list)
    skills_added: int = 0
    educations_added: int = 0
    experiences_added: int = 0
    projects_added: int = 0
    certifications_added: int = 0
    preserved_fields: list[str] = Field(default_factory=list)
    message: str = "Profile synchronized successfully from resume."
