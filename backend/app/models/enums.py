"""
Database enumerations for CareerLens data models.
Matches approved v1.1 ER design PostgreSQL native ENUM types.
"""

from enum import Enum


class WorkMode(str, Enum):
    """Work mode preferences and requirements."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY = "any"


class EmploymentType(str, Enum):
    """Employment type preferences and requirements."""

    FULLTIME = "fulltime"
    PARTTIME = "parttime"
    INTERNSHIP = "internship"
    CONTRACT = "contract"
    ANY = "any"


class SkillCategory(str, Enum):
    """Category classification for candidate and opportunity skills."""

    TECHNICAL = "technical"
    SOFT = "soft"
    TOOL = "tool"
    LANGUAGE = "language"
    DOMAIN = "domain"


class SkillProficiency(str, Enum):
    """Proficiency level for candidate skills."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillSource(str, Enum):
    """Source origin of candidate skill."""

    RESUME = "resume"
    MANUAL = "manual"


class EducationLevel(str, Enum):
    """Education attainment level for eligibility evaluation."""

    NONE = "none"
    DIPLOMA = "diploma"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    ANY = "any"
