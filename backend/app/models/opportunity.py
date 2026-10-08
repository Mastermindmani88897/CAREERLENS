"""
Opportunity and opportunity skills ORM models.
Matches approved v1.1 ER design Entities 9 and 10.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    EducationLevel,
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    WorkMode,
)

if TYPE_CHECKING:
    from app.models.tracking import Application, InterviewPrep, Match


def _enum_values(enum_cls: Any) -> list[str]:
    """Extract lowercase enum values for PostgreSQL native enum types."""
    return [e.value for e in enum_cls]


class Opportunity(Base):
    """Job opportunity listing entity."""

    __tablename__ = "opportunities"

    __table_args__ = (
        Index(
            "opportunities_source_dedup_idx",
            "source",
            "source_id",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
        Index("opportunities_active_idx", "is_active"),
        Index("opportunities_type_idx", "opportunity_type"),
        Index("opportunities_employment_type_idx", "employment_type"),
        Index("opportunities_work_mode_idx", "work_mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    opportunity_type: Mapped[OpportunityType] = mapped_column(
        Enum(
            OpportunityType,
            name="opportunity_type_enum",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
        default=OpportunityType.JOB,
        server_default="job",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    required_skills: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    preferred_skills: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    min_experience_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    max_experience_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    required_education_level: Mapped[EducationLevel] = mapped_column(
        Enum(
            EducationLevel,
            name="education_level_enum",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
        default=EducationLevel.ANY,
    )
    location_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    location_state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    location_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    work_mode: Mapped[WorkMode] = mapped_column(
        Enum(
            WorkMode,
            name="work_mode_enum",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
        default=WorkMode.ANY,
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(
            EmploymentType,
            name="employment_type_enum",
            values_callable=_enum_values,
            create_type=False,
        ),
        nullable=False,
    )
    salary_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    salary_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    salary_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    application_deadline: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    job_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    source: Mapped[OpportunitySource] = mapped_column(
        Enum(
            OpportunitySource,
            name="opportunity_source_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=False,
    )
    source_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    posted_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    job_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )
    embedding_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
    skills: Mapped[list["OpportunitySkill"]] = relationship(
        "OpportunitySkill",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    interview_preps: Mapped[list["InterviewPrep"]] = relationship(
        "InterviewPrep",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Opportunity id={self.id} title={self.title} company={self.company}>"


class OpportunitySkill(Base):
    """Normalized skill mapping for job opportunities."""

    __tablename__ = "opportunity_skills"

    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "skill_name",
            name="uq_opportunity_skills_opp_skill",
        ),
        Index("opp_skills_opp_id_idx", "opportunity_id"),
        Index("opp_skills_name_idx", "skill_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="skills",
    )

    def __repr__(self) -> str:
        return (
            f"<OpportunitySkill id={self.id} "
            f"opportunity_id={self.opportunity_id} skill_name={self.skill_name}>"
        )
