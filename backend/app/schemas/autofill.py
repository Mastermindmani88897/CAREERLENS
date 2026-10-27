"""
Pydantic schemas for Phase 27 External Application Autofill.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AutofillPrepareRequest(BaseModel):
    """Payload to initiate an application preparation session."""

    model_config = ConfigDict(extra="forbid")

    opportunity_id: uuid.UUID = Field(
        ...,
        description="UUID of the opportunity listing to prepare application for.",
    )
    resume_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional UUID of a specific resume document. "
            "If omitted, latest active resume is selected."
        ),
    )


class AutofillSessionResponse(BaseModel):
    """Structured response detailing the prepared autofill session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique autofill session identifier.")
    candidate_profile_id: uuid.UUID = Field(..., description="Owner candidate profile UUID.")
    opportunity_id: uuid.UUID = Field(..., description="Target opportunity UUID.")
    resume_id: uuid.UUID | None = Field(None, description="Selected resume UUID.")
    ats_provider: str = Field(..., description="Detected ATS provider ('greenhouse' or 'lever').")
    target_url: str = Field(..., description="Sanitized external application destination URL.")
    status: str = Field(..., description="Current session lifecycle status.")
    normalized_payload: dict[str, Any] = Field(
        ..., description="Standardized candidate field mappings."
    )
    missing_fields: list[str] = Field(
        ..., description="List of unmapped fields or employer questionnaires."
    )
    diagnostic_metadata: dict[str, Any] = Field(..., description="Safe operational diagnostics.")
    expires_at: datetime = Field(..., description="Session expiration timestamp.")
    created_at: datetime = Field(..., description="Session creation timestamp.")
    updated_at: datetime = Field(..., description="Session last updated timestamp.")
