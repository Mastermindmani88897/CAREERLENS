"""
Candidate profile and related sub-entities ORM models.
Matches approved v1.1 ER design Entities 2 through 8.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    EducationLevel,
    EmploymentType,
    SkillCategory,
    SkillProficiency,
    SkillSource,
    WorkMode,
)

if TYPE_CHECKING:
    from app.models.user import User


def _enum_values(enum_cls: Any) -> list[str]:
    """Extract lowercase enum values for PostgreSQL native enum types."""
    return [e.value for e in enum_cls]


class CandidateProfile(Base):
    """Central candidate profile entity (one per user)."""

    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    headline: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
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
    preferred_work_mode: Mapped[WorkMode] = mapped_column(
        Enum(WorkMode, name="work_mode_enum", values_callable=_enum_values, create_type=True),
        nullable=False,
        default=WorkMode.ANY,
    )
    preferred_employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(
            EmploymentType,
            name="employment_type_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=False,
        default=EmploymentType.ANY,
    )
    preferred_salary_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    preferred_salary_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    preferred_salary_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default="INR",
    )
    open_to_relocation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    linkedin_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    github_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    portfolio_url: Mapped[str | None] = mapped_column(
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="candidate_profile",
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    educations: Mapped[list["Education"]] = relationship(
        "Education",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    experiences: Mapped[list["Experience"]] = relationship(
        "Experience",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile id={self.id} full_name={self.full_name}>"


class Resume(Base):
    """Uploaded resumes and parsed extraction data."""

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    raw_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="resumes",
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} filename={self.filename}>"


class Skill(Base):
    """Individual skills for candidate profiles."""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id",
            "skill_name",
            name="uq_skills_profile_skill",
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
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    category: Mapped[SkillCategory | None] = mapped_column(
        Enum(
            SkillCategory,
            name="skill_category_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=True,
    )
    proficiency_level: Mapped[SkillProficiency | None] = mapped_column(
        Enum(
            SkillProficiency,
            name="skill_proficiency_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=True,
    )
    years_of_experience: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, name="skill_source_enum", values_callable=_enum_values, create_type=True),
        nullable=False,
        default=SkillSource.MANUAL,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="skills",
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id} skill_name={self.skill_name}>"


class Education(Base):
    """Education history per candidate profile."""

    __tablename__ = "educations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    degree: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    field_of_study: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    education_level: Mapped[EducationLevel] = mapped_column(
        Enum(
            EducationLevel,
            name="education_level_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    grade: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="educations",
    )

    def __repr__(self) -> str:
        return f"<Education id={self.id} institution={self.institution} degree={self.degree}>"


class Experience(Base):
    """Work experience records per candidate profile."""

    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        Enum(
            EmploymentType,
            name="employment_type_enum",
            values_callable=_enum_values,
            create_type=True,
        ),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    work_mode: Mapped[WorkMode | None] = mapped_column(
        Enum(WorkMode, name="work_mode_enum", values_callable=_enum_values, create_type=True),
        nullable=True,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    skills_used: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(255)),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="experiences",
    )

    def __repr__(self) -> str:
        return f"<Experience id={self.id} company={self.company} title={self.title}>"


class Project(Base):
    """Personal and academic projects per candidate profile."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    technologies: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(255)),
        nullable=True,
    )
    project_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    repo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="projects",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} title={self.title}>"


class Certification(Base):
    """Professional certifications per candidate profile."""

    __tablename__ = "certifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    issuing_organization: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    issue_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    credential_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    credential_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="certifications",
    )

    def __repr__(self) -> str:
        return f"<Certification id={self.id} name={self.name}>"
