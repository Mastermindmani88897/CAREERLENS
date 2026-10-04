"""
Database enumerations for CareerLens data models.
Matches approved v1.1 ER design PostgreSQL native ENUM types.
"""

from enum import StrEnum


class WorkMode(StrEnum):
    """Work mode preferences and requirements."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


class EmploymentType(StrEnum):
    """Employment type preferences and requirements."""

    FULLTIME = "fulltime"
    PARTTIME = "parttime"
    INTERNSHIP = "internship"
    CONTRACT = "contract"
    ANY = "any"


class SkillCategory(StrEnum):
    """Category classification for candidate and opportunity skills."""

    TECHNICAL = "technical"
    SOFT = "soft"
    TOOL = "tool"
    LANGUAGE = "language"
    DOMAIN = "domain"


class SkillProficiency(StrEnum):
    """Proficiency level for candidate skills."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillSource(StrEnum):
    """Source origin of candidate skill."""

    RESUME = "resume"
    MANUAL = "manual"


class EducationLevel(StrEnum):
    """Education attainment level for eligibility evaluation."""

    NONE = "none"
    DIPLOMA = "diploma"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    ANY = "any"


class OpportunitySource(StrEnum):
    """Source origin of opportunity/job listing."""

    SYNTHETIC = "synthetic"
    MANUAL = "manual"
    API = "api"


class EligibilityStatus(StrEnum):
    """Eligibility status resulting from candidate evaluation."""

    ELIGIBLE = "eligible"
    PARTIAL = "partial"
    REVIEW_REQUIRED = "review_required"


class ApplicationStatus(StrEnum):
    """Application tracking lifecycle status."""

    SAVED = "saved"
    APPLIED = "applied"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
