"""
Pydantic schemas for Phase 14 Opportunity Ingestion and Normalization.
Covers raw rows, normalized DTOs, responses, pagination, and ingestion metrics.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    EducationLevel,
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    WorkMode,
)


class RawOpportunityRow(BaseModel):
    """Raw record structure before normalization (supports CSV and raw JSON)."""

    title: str | None = None
    company: str | None = None
    organization: str | None = None
    description: str | None = None
    opportunity_type: str | None = "job"
    employment_type: str | None = "fulltime"
    work_mode: str | None = "any"
    required_education_level: str | None = "any"
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    salary_min: int | float | str | None = None
    salary_max: int | float | str | None = None
    salary_currency: str | None = None
    min_experience_years: int | float | str | None = None
    max_experience_years: int | float | str | None = None
    application_deadline: str | date | None = None
    job_url: str | None = None
    application_url: str | None = None
    source: str | None = "manual"
    source_id: str | None = None
    posted_date: str | date | None = None
    required_skills: list[str] | str | None = None
    preferred_skills: list[str] | str | None = None
    is_active: bool | str | None = True

    model_config = ConfigDict(extra="ignore")


class OpportunityBase(BaseModel):
    """Base opportunity attributes shared across create/update/response."""

    title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    opportunity_type: OpportunityType = OpportunityType.JOB
    employment_type: EmploymentType = EmploymentType.FULLTIME
    work_mode: WorkMode = WorkMode.ANY
    required_education_level: EducationLevel = EducationLevel.ANY
    location_city: str | None = Field(None, max_length=100)
    location_state: str | None = Field(None, max_length=100)
    location_country: str | None = Field(None, max_length=100)
    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)
    salary_currency: str | None = Field(None, max_length=10)
    min_experience_years: int | None = Field(None, ge=0)
    max_experience_years: int | None = Field(None, ge=0)
    application_deadline: date | None = None
    job_url: str | None = None
    source: OpportunitySource = OpportunitySource.MANUAL
    source_id: str | None = Field(None, max_length=512)
    posted_date: date | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    is_active: bool = True

    @field_validator("job_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if not (stripped.startswith("http://") or stripped.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return stripped


class OpportunityCreate(OpportunityBase):
    """Payload for creating a new Opportunity."""

    pass


class OpportunityUpdate(BaseModel):
    """Payload for updating an existing Opportunity."""

    title: str | None = Field(None, min_length=1, max_length=255)
    company: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    opportunity_type: OpportunityType | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    required_education_level: EducationLevel | None = None
    location_city: str | None = Field(None, max_length=100)
    location_state: str | None = Field(None, max_length=100)
    location_country: str | None = Field(None, max_length=100)
    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)
    salary_currency: str | None = Field(None, max_length=10)
    min_experience_years: int | None = Field(None, ge=0)
    max_experience_years: int | None = Field(None, ge=0)
    application_deadline: date | None = None
    job_url: str | None = None
    source: OpportunitySource | None = None
    source_id: str | None = Field(None, max_length=512)
    posted_date: date | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    is_active: bool | None = None

    @field_validator("job_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if not (stripped.startswith("http://") or stripped.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return stripped


class OpportunitySkillResponse(BaseModel):
    """Skill mapping representation associated with an opportunity."""

    id: uuid.UUID
    opportunity_id: uuid.UUID
    skill_name: str
    is_required: bool

    model_config = ConfigDict(from_attributes=True)


class OpportunityResponse(OpportunityBase):
    """Standard opportunity view representation."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityDetailResponse(OpportunityResponse):
    """Detailed opportunity view representation including relational skills."""

    skills: list[OpportunitySkillResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OpportunityListResponse(BaseModel):
    """Paginated collection of opportunities."""

    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OpportunityIngestResult(BaseModel):
    """Result summary of a batch ingestion operation."""

    total: int
    created: int
    skipped_duplicates: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
