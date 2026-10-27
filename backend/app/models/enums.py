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


class OpportunityType(StrEnum):
    """Opportunity classification type (Phase 14 & 26)."""

    JOB = "job"
    INTERNSHIP = "internship"
    HACKATHON = "hackathon"
    CODING_CONTEST = "coding_contest"


class OpportunitySource(StrEnum):
    """Source origin of opportunity/job listing (Phase 6 & 26)."""

    SYNTHETIC = "synthetic"
    MANUAL = "manual"
    API = "api"
    REMOTIVE = "remotive"
    ARBEITNOW = "arbeitnow"
    CODEFORCES = "codeforces"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ADZUNA = "adzuna"
    USAJOBS = "usajobs"
    REMOTEOK = "remoteok"
    DEVPOST = "devpost"


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


class ATSProvider(StrEnum):
    """Supported Applicant Tracking System (ATS) providers for autofill (Phase 27)."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    UNSUPPORTED = "unsupported"


class AutofillSessionStatus(StrEnum):
    """Lifecycle status for an application autofill session (Phase 27)."""

    PREPARATION_PENDING = "preparation_pending"
    DATA_MAPPED = "data_mapped"
    CANDIDATE_REVIEW = "candidate_review"
    ASSISTANT_LAUNCHED = "assistant_launched"
    FIELDS_POPULATED = "fields_populated"
    AWAITING_CANDIDATE_ACTION = "awaiting_candidate_action"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUBMITTED_VERIFIED = "submitted_verified"
    SUBMISSION_UNCERTAIN = "submission_uncertain"
    FAILED = "failed"
    CANCELLED = "cancelled"
