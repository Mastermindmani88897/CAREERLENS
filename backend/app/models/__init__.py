"""
CareerLens ORM models package.
Exports all approved Phase 4 and Phase 6 core entities and enums.
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
    ApplicationStatus,
    EducationLevel,
    EligibilityStatus,
    EmploymentType,
    OpportunitySource,
    SkillCategory,
    SkillProficiency,
    SkillSource,
    WorkMode,
)
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.tracking import (
    Application,
    ApplicationStatusHistory,
    InterviewPrep,
    Match,
)
from app.models.user import User

__all__ = [
    # Entities (Phase 4: Candidate & Identity)
    "User",
    "CandidateProfile",
    "Resume",
    "Skill",
    "Education",
    "Experience",
    "Project",
    "Certification",
    # Entities (Phase 6: Opportunity & Tracking)
    "Opportunity",
    "OpportunitySkill",
    "Match",
    "Application",
    "ApplicationStatusHistory",
    "InterviewPrep",
    # Enums
    "WorkMode",
    "EmploymentType",
    "SkillCategory",
    "SkillProficiency",
    "SkillSource",
    "EducationLevel",
    "OpportunitySource",
    "EligibilityStatus",
    "ApplicationStatus",
]
