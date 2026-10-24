"""
Pydantic schemas for Phase 21 Application Tracking and Status Transitions.

Defines strongly typed request/response models for:
  - Application creation and saving
  - Status updates and transition validation
  - Audit history log representation
  - Paginated application listings with embedded opportunity metadata
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus

# ---------------------------------------------------------------------------
# Embedded opportunity summary for application views
# ---------------------------------------------------------------------------


class ApplicationOpportunitySummary(BaseModel):
    """Essential opportunity metadata embedded in application responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: str
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    work_mode: str
    employment_type: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    job_url: str | None = None


# ---------------------------------------------------------------------------
# Status transition audit log schema
# ---------------------------------------------------------------------------


class ApplicationStatusHistoryResponse(BaseModel):
    """Immutable status audit trail entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    status: ApplicationStatus
    changed_at: datetime
    notes: str | None = None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ApplicationCreate(BaseModel):
    """Payload to create or save a new application record."""

    opportunity_id: uuid.UUID = Field(..., description="Opportunity UUID to apply to or save")
    status: ApplicationStatus = Field(
        default=ApplicationStatus.SAVED,
        description="Initial application status (defaults to saved)",
    )
    applied_date: date | None = Field(
        default=None,
        description="Date applied (automatically populated if status is applied and date omitted)",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional candidate personal notes or application remarks",
    )


class ApplicationStatusUpdate(BaseModel):
    """Payload to transition an application to a new status."""

    status: ApplicationStatus = Field(..., description="New target status")
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional notes documenting the status change",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ApplicationResponse(BaseModel):
    """Standard application response with embedded opportunity metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    opportunity_id: uuid.UUID
    status: ApplicationStatus
    applied_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    opportunity: ApplicationOpportunitySummary | None = None


class ApplicationDetailResponse(ApplicationResponse):
    """Full application detail including complete status transition audit history."""

    status_history: list[ApplicationStatusHistoryResponse] = Field(default_factory=list)


class ApplicationListResponse(BaseModel):
    """Paginated collection of application records."""

    items: list[ApplicationResponse] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
