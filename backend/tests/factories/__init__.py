"""
CareerLens Test Factories.
Exports all entity factories for concise imports in test suites.
"""

from tests.factories.base import BaseFactory
from tests.factories.candidate_factory import (
    CandidateProfileFactory,
    CertificationFactory,
    EducationFactory,
    ExperienceFactory,
    ProjectFactory,
    ResumeFactory,
    SkillFactory,
)
from tests.factories.opportunity_factory import (
    OpportunityFactory,
    OpportunitySkillFactory,
)
from tests.factories.tracking_factory import (
    ApplicationFactory,
    ApplicationStatusHistoryFactory,
    InterviewPrepFactory,
    MatchFactory,
)
from tests.factories.user_factory import UserFactory

__all__ = [
    "BaseFactory",
    "UserFactory",
    "CandidateProfileFactory",
    "ResumeFactory",
    "SkillFactory",
    "EducationFactory",
    "ExperienceFactory",
    "ProjectFactory",
    "CertificationFactory",
    "OpportunityFactory",
    "OpportunitySkillFactory",
    "MatchFactory",
    "ApplicationFactory",
    "ApplicationStatusHistoryFactory",
    "InterviewPrepFactory",
]
