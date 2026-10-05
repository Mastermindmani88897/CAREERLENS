"""
Opportunity and opportunity skill factories for deterministic test data generation.
Covers Opportunity and OpportunitySkill entities.
"""

import uuid
from typing import Any

from app.models.enums import (
    EducationLevel,
    EmploymentType,
    OpportunitySource,
    WorkMode,
)
from app.models.opportunity import Opportunity, OpportunitySkill
from tests.factories.base import BaseFactory


class OpportunityFactory(BaseFactory[Opportunity]):
    """Factory for Opportunity entity."""

    model_class = Opportunity

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "title": f"Senior Software Engineer {unique_suffix}",
            "company": "Acme Technology Corp",
            "location_city": "San Francisco",
            "location_state": "CA",
            "location_country": "USA",
            "work_mode": WorkMode.HYBRID,
            "employment_type": EmploymentType.FULLTIME,
            "min_experience_years": 4,
            "required_education_level": EducationLevel.BACHELOR,
            "description": (
                "Seeking an experienced software engineer to build scalable "
                "distributed architectures."
            ),
            "source": OpportunitySource.SYNTHETIC,
            "source_id": f"synthetic_{unique_suffix}",
            "job_url": "https://careers.example.com/jobs/senior-swe",
            "salary_min": 130000,
            "salary_max": 170000,
            "salary_currency": "USD",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["Docker", "Kubernetes"],
            "job_embedding": [0.0] * 384,
            "is_active": True,
        }


class OpportunitySkillFactory(BaseFactory[OpportunitySkill]):
    """Factory for OpportunitySkill entity."""

    model_class = OpportunitySkill

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "opportunity_id": uuid.uuid4(),
            "skill_name": f"Skill_{unique_suffix}",
            "is_required": True,
        }
