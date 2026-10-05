"""
Candidate profile and sub-entity factories for deterministic test data generation.
Covers CandidateProfile, Resume, Skill, Education, Experience, Project, and Certification.
"""

import uuid
from datetime import date
from typing import Any

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
from tests.factories.base import BaseFactory


class CandidateProfileFactory(BaseFactory[CandidateProfile]):
    """Factory for CandidateProfile entity."""

    model_class = CandidateProfile

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "user_id": uuid.uuid4(),
            "full_name": f"Test Candidate {unique_suffix}",
            "headline": "Full-Stack Software Engineer",
            "summary": "Experienced engineer with a background in distributed systems.",
            "phone": "+1-555-0199",
            "location_city": "San Francisco",
            "location_state": "CA",
            "location_country": "USA",
            "preferred_work_mode": WorkMode.HYBRID,
            "preferred_employment_type": EmploymentType.FULLTIME,
            "preferred_salary_min": 100000,
            "preferred_salary_max": 140000,
            "preferred_salary_currency": "INR",
            "open_to_relocation": True,
        }


class ResumeFactory(BaseFactory[Resume]):
    """Factory for Resume entity."""

    model_class = Resume

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "candidate_profile_id": uuid.uuid4(),
            "filename": f"resume_{unique_suffix}.pdf",
            "file_path": f"/data/uploads/resumes/resume_{unique_suffix}.pdf",
            "file_type": "pdf",
            "file_size_bytes": 1048576,
            "raw_text": "Extracted resume content with software engineering background.",
            "parsed_json": {"summary": "Software engineer with 4 years experience."},
            "is_active": True,
        }


class SkillFactory(BaseFactory[Skill]):
    """Factory for Skill entity."""

    model_class = Skill

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "candidate_profile_id": uuid.uuid4(),
            "skill_name": f"Python_{unique_suffix}",
            "category": SkillCategory.TECHNICAL,
            "proficiency_level": SkillProficiency.ADVANCED,
            "years_of_experience": 4,
            "source": SkillSource.MANUAL,
        }


class EducationFactory(BaseFactory[Education]):
    """Factory for Education entity."""

    model_class = Education

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        return {
            "candidate_profile_id": uuid.uuid4(),
            "institution": "State University of Technology",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science",
            "education_level": EducationLevel.BACHELOR,
            "start_date": date(2018, 9, 1),
            "end_date": date(2022, 5, 20),
            "is_current": False,
            "grade": "3.8/4.0",
        }


class ExperienceFactory(BaseFactory[Experience]):
    """Factory for Experience entity."""

    model_class = Experience

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        return {
            "candidate_profile_id": uuid.uuid4(),
            "company": "Innovative Solutions Corp",
            "title": "Software Engineer",
            "employment_type": EmploymentType.FULLTIME,
            "location": "San Francisco, CA",
            "work_mode": WorkMode.HYBRID,
            "start_date": date(2022, 6, 1),
            "end_date": None,
            "is_current": True,
            "description": "Designed and maintained high-throughput API microservices.",
            "skills_used": ["Python", "FastAPI", "PostgreSQL"],
        }


class ProjectFactory(BaseFactory[Project]):
    """Factory for Project entity."""

    model_class = Project

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "candidate_profile_id": uuid.uuid4(),
            "title": f"Distributed Task Scheduler {unique_suffix}",
            "description": "Fault-tolerant distributed background worker architecture.",
            "project_url": "https://github.com/example/task-scheduler",
            "repo_url": "https://github.com/example/task-scheduler-repo",
            "technologies": ["Python", "AsyncIO", "Redis"],
            "start_date": date(2023, 1, 1),
            "end_date": date(2023, 6, 1),
        }


class CertificationFactory(BaseFactory[Certification]):
    """Factory for Certification entity."""

    model_class = Certification

    @classmethod
    def default_attributes(cls) -> dict[str, Any]:
        unique_suffix = uuid.uuid4().hex[:8]
        return {
            "candidate_profile_id": uuid.uuid4(),
            "name": f"Cloud Practitioner Certificate {unique_suffix}",
            "issuing_organization": "Cloud Computing Institute",
            "issue_date": date(2023, 3, 15),
            "expiry_date": date(2026, 3, 15),
            "credential_id": f"CERT-{unique_suffix.upper()}",
            "credential_url": "https://credentials.example.com/verify",
        }
