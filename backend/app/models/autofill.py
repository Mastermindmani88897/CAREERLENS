"""
Autofill session ORM model for Phase 27.
Tracks application preparation state, normalized candidate data payload,
unmapped/missing fields, diagnostic telemetry, and expiration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile, Resume
    from app.models.opportunity import Opportunity


class AutofillSession(Base):
    """Application preparation and autofill session entity."""

    __tablename__ = "autofill_sessions"

    __table_args__ = (
        Index("ix_autofill_sessions_candidate_profile_id", "candidate_profile_id"),
        Index("ix_autofill_sessions_opportunity_id", "opportunity_id"),
        Index("ix_autofill_sessions_status", "status"),
        Index("ix_autofill_sessions_expires_at", "expires_at"),
        Index(
            "ix_autofill_sessions_candidate_opp_status",
            "candidate_profile_id",
            "opportunity_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )
    ats_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="preparation_pending",
        server_default="preparation_pending",
        nullable=False,
    )
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    missing_fields: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    diagnostic_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    candidate_profile: Mapped[CandidateProfile] = relationship(
        "CandidateProfile",
        back_populates="autofill_sessions",
    )
    opportunity: Mapped[Opportunity] = relationship(
        "Opportunity",
        back_populates="autofill_sessions",
    )
    resume: Mapped[Resume | None] = relationship(
        "Resume",
        back_populates="autofill_sessions",
    )

    def __repr__(self) -> str:
        return (
            f"<AutofillSession id={self.id} profile_id={self.candidate_profile_id} "
            f"opp_id={self.opportunity_id} provider={self.ats_provider} status={self.status}>"
        )
