"""
Match, application tracking, status history, and interview prep factories.
Covers Match, Application, ApplicationStatusHistory, and InterviewPrep entities.
"""

import uuid
from datetime import date
from typing import Any

from app.models.enums import ApplicationStatus, EligibilityStatus
from app.models.tracking import (
    Application,
    ApplicationStatusHistory,
    InterviewPrep,
    Match,
)
from tests.factories.base import BaseFactory


class MatchFactory(BaseFactory[Match]):
    """Factory for Match entity."""

    model_class = Match

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        return {
            "candidate_profile_id": uuid.uuid4(),
            "opportunity_id": uuid.uuid4(),
            "semantic_score": 0.88,
            "deterministic_score": 0.84,
            "final_score": 0.86,
            "score_breakdown": {
                "semantic_score": 0.88,
                "skill_overlap_score": 0.90,
                "experience_score": 0.80,
                "education_score": 0.85,
                "location_workmode_score": 0.90,
                "employment_type_score": 1.0,
            },
            "explanation": {
                "strengths": ["Strong Python experience", "FastAPI proficiency"],
                "gaps": [],
            },
            "skill_gap": {
                "matched_skills": ["Python", "FastAPI"],
                "missing_skills": [],
            },
            "explanation_text": "Candidate demonstrates high competency in backend requirements.",
            "eligibility_status": EligibilityStatus.ELIGIBLE,
        }


class ApplicationFactory(BaseFactory[Application]):
    """Factory for Application entity."""

    model_class = Application

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        return {
            "candidate_profile_id": uuid.uuid4(),
            "opportunity_id": uuid.uuid4(),
            "status": ApplicationStatus.APPLIED,
            "applied_date": date.today(),
            "notes": "Application submitted via primary job board portal.",
        }


class ApplicationStatusHistoryFactory(BaseFactory[ApplicationStatusHistory]):
    """Factory for ApplicationStatusHistory entity."""

    model_class = ApplicationStatusHistory

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        return {
            "application_id": uuid.uuid4(),
            "status": ApplicationStatus.APPLIED,
            "notes": "Moved candidate from saved wishlist to applied pipeline.",
        }


class InterviewPrepFactory(BaseFactory[InterviewPrep]):
    """Factory for InterviewPrep entity."""

    model_class = InterviewPrep

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        return {
            "candidate_profile_id": uuid.uuid4(),
            "opportunity_id": uuid.uuid4(),
            "generation_method": "template",
            "content": {
                "company_brief": "Innovative high-scale technology enterprise.",
                "technical_questions": [
                    {
                        "question": (
                            "Explain async database connection lifecycle and transaction safety."
                        ),
                        "focus": "SQLAlchemy + asyncpg",
                    }
                ],
                "behavioral_questions": [
                    {
                        "question": (
                            "Describe an engineering trade-off you navigated under tight deadlines."
                        ),
                        "focus": "Collaboration & Pragmatism",
                    }
                ],
                "role_alignment_analysis": {
                    "core_matches": ["FastAPI", "PostgreSQL"],
                    "potential_gaps": ["Kubernetes"],
                },
            },
        }
