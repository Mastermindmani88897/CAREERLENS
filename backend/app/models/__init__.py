"""
CareerLens ORM models package.
Exports all approved Phase 4 core entities and enums.
"""

from app.models.candidate import (
    CandidateProfile,
    Certification,
    Education,
    Experience,
    Project,
    Resume,
    Skill,
)
from app.models.enums import (
    EducationLevel,
    EmploymentType,
    SkillCategory,
    SkillProficiency,
    SkillSource,
    WorkMode,
)
from app.models.user import User

__all__ = [
    # Entities
    "User",
    "CandidateProfile",
    "Resume",
    "Skill",
    "Education",
    "Experience",
    "Project",
    "Certification",
    # Enums
    "WorkMode",
    "EmploymentType",
    "SkillCategory",
    "SkillProficiency",
    "SkillSource",
    "EducationLevel",
]
