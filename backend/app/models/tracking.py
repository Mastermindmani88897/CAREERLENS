"""
Matches, application tracking, status audit history, and interview prep ORM models.
Matches approved v1.1 ER design Entities 11 through 14.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApplicationStatus, EligibilityStatus

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile
    from app.models.opportunity import Opportunity


def _enum_values(enum_cls: Any) -> list[str]:
    """Extract lowercase enum values for PostgreSQL native enum types."""
    return [e.value for e in enum_cls]


class Match(Base):
    """Match score evaluation between candidate profile and opportunity."""

    __tablename__ = "matches"

    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id",
            "opportunity_id",
            name="uq_matches_candidate_opportunity",
        ),
        Index(
            "matches_profile_score_idx",
            "candidate_profile_id",
            text("final_score DESC"),
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
    semantic_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    deterministic_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    final_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    eligibility_status: Mapped[EligibilityStatus] = mapped_column(
        Enum(
            EligibilityStatus,
            name="eligibility_status_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=False,
    )
    eligibility_warnings: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    explanation: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    explanation_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    skill_gap: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="matches",
    )
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="matches",
    )

    def __repr__(self) -> str:
        return (
            f"<Match id={self.id} profile_id={self.candidate_profile_id} "
            f"opportunity_id={self.opportunity_id} final_score={self.final_score}>"
        )


class Application(Base):
    """Job application tracking record."""

    __tablename__ = "applications"

    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id",
            "opportunity_id",
            name="uq_applications_candidate_opportunity",
        ),
        Index("applications_profile_status_idx", "candidate_profile_id", "status"),
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
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=False,
        default=ApplicationStatus.SAVED,
    )
    applied_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="applications",
    )
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="applications",
    )
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} profile_id={self.candidate_profile_id} "
            f"opportunity_id={self.opportunity_id} status={self.status}>"
        )


class ApplicationStatusHistory(Base):
    """Immutable audit trail log for application status transitions."""

    __tablename__ = "application_status_history"

    __table_args__ = (Index("status_history_app_id_idx", "application_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status_enum",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="status_history",
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationStatusHistory id={self.id} "
            f"application_id={self.application_id} status={self.status}>"
        )


class InterviewPrep(Base):
    """Interview preparation content tailored to candidate profile and opportunity."""

    __tablename__ = "interview_prep"

    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id",
            "opportunity_id",
            name="uq_interview_prep_candidate_opportunity",
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
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    generation_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
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
    candidate_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="interview_preps",
    )
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="interview_preps",
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewPrep id={self.id} profile_id={self.candidate_profile_id} "
            f"opportunity_id={self.opportunity_id}>"
        )
