"""
Pydantic schemas for Phase 11 Resume Ingestion and Extraction Pipeline.
Defines strongly typed models for validated resume data and API payloads.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResumeStatus(StrEnum):
    """Resume parsing lifecycle status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"


class ContactInfo(BaseModel):
    """Extracted contact information from resume."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ExtractedSkill(BaseModel):
    """Extracted skill with evidence and source section."""

    skill: str
    category: str | None = None
    source_section: str = "skills"
    evidence: str | None = None


class ExtractedEducation(BaseModel):
    """Extracted educational record."""

    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    grade: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    evidence: str | None = None


class ExtractedExperience(BaseModel):
    """Extracted professional or internship experience record."""

    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    skills_used: list[str] = Field(default_factory=list)
    evidence: str | None = None


class ExtractedProject(BaseModel):
    """Extracted personal or academic project."""

    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None
    evidence: str | None = None


class ExtractedCertification(BaseModel):
    """Extracted certification or credential."""

    name: str
    issuing_organization: str | None = None
    issue_date: str | None = None
    credential_url: str | None = None
    evidence: str | None = None


class DetectedSections(BaseModel):
    """Structured text segments categorized by resume section."""

    contact: str | None = None
    summary: str | None = None
    skills: str | None = None
    education: str | None = None
    experience: str | None = None
    projects: str | None = None
    certifications: str | None = None
    achievements: str | None = None
    publications: str | None = None
    languages: str | None = None
    other: str | None = None


class ParsedResumeData(BaseModel):
    """Structured resume data payload stored in Resume.parsed_json."""

    status: ResumeStatus = ResumeStatus.PARSED
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: list[ExtractedSkill] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    experience: list[ExtractedExperience] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    certifications: list[ExtractedCertification] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    summary: str | None = None
    raw_character_count: int = 0
    normalized_character_count: int = 0
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = None


class ResumeResponse(BaseModel):
    """API response model for an uploaded/processed resume."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int | None = None
    status: ResumeStatus
    error_message: str | None = None
    parsed_data: ParsedResumeData | None = None
    created_at: datetime


class ResumeDetailResponse(ResumeResponse):
    """Detailed API response model including raw text for preview and audit."""

    raw_text: str | None = None
    parsed_json: dict[str, Any] | None = None


class ResumeListResponse(BaseModel):
    """Paginated or listed resumes for current authenticated candidate."""

    items: list[ResumeResponse]
    total: int
