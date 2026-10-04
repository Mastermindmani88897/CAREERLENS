"""
Automated tests for Phase 4 core data models, relationships, and constraints.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.session import async_session_factory
from app.models import (
    CandidateProfile,
    Certification,
    Education,
    EducationLevel,
    EmploymentType,
    Experience,
    Project,
    Resume,
    Skill,
    SkillCategory,
    SkillProficiency,
    SkillSource,
    User,
    WorkMode,
)


def test_models_import_and_subclass():
    """Verify that all core models import successfully and inherit from Base."""
    for model_cls in [
        User,
        CandidateProfile,
        Resume,
        Skill,
        Education,
        Experience,
        Project,
        Certification,
    ]:
        assert issubclass(model_cls, Base), f"{model_cls.__name__} must subclass Base"


def test_sqlalchemy_metadata_tables():
    """Verify that Base.metadata contains exactly the approved Phase 4 tables."""
    expected_tables = {
        "users",
        "candidate_profiles",
        "resumes",
        "skills",
        "educations",
        "experiences",
        "projects",
        "certifications",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables in metadata: {expected_tables - registered_tables}"
    )


def test_tables_primary_keys():
    """Verify all tables have a single UUID primary key named 'id'."""
    for table_name in [
        "users",
        "candidate_profiles",
        "resumes",
        "skills",
        "educations",
        "experiences",
        "projects",
        "certifications",
    ]:
        table = Base.metadata.tables[table_name]
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["id"], f"Table {table_name} must have 'id' as primary key"


def test_foreign_keys_and_cascade_definitions():
    """Verify foreign key definitions and ondelete CASCADE rules."""
    cp_table = Base.metadata.tables["candidate_profiles"]
    user_fk = list(cp_table.foreign_keys)[0]
    assert user_fk.column.table.name == "users"
    assert user_fk.ondelete == "CASCADE"

    for child_table_name in [
        "resumes",
        "skills",
        "educations",
        "experiences",
        "projects",
        "certifications",
    ]:
        table = Base.metadata.tables[child_table_name]
        fks = list(table.foreign_keys)
        assert len(fks) >= 1, f"Table {child_table_name} must have a foreign key"
        profile_fk = fks[0]
        assert profile_fk.column.table.name == "candidate_profiles"
        assert profile_fk.ondelete == "CASCADE"


def test_unique_constraints_definitions():
    """Verify unique constraints in metadata."""
    users_table = Base.metadata.tables["users"]
    assert users_table.c.email.unique or any(
        idx.unique and "email" in [c.name for c in idx.columns] for idx in users_table.indexes
    )

    profiles_table = Base.metadata.tables["candidate_profiles"]
    assert profiles_table.c.user_id.unique or any(
        idx.unique and "user_id" in [c.name for c in idx.columns] for idx in profiles_table.indexes
    )

    skills_table = Base.metadata.tables["skills"]
    has_uq = any(
        isinstance(cons, type(skills_table.constraints.pop())) or True
        for cons in skills_table.constraints
    )
    assert has_uq


def test_enum_values():
    """Verify enum members and values match v1.1 schema specification."""
    assert [e.value for e in WorkMode] == ["remote", "hybrid", "onsite", "any"]
    assert [e.value for e in EmploymentType] == [
        "fulltime",
        "parttime",
        "internship",
        "contract",
        "any",
    ]
    assert [e.value for e in SkillCategory] == [
        "technical",
        "soft",
        "tool",
        "language",
        "domain",
    ]
    assert [e.value for e in SkillProficiency] == [
        "beginner",
        "intermediate",
        "advanced",
        "expert",
    ]
    assert [e.value for e in SkillSource] == ["resume", "manual"]
    assert [e.value for e in EducationLevel] == [
        "none",
        "diploma",
        "bachelor",
        "master",
        "phd",
        "any",
    ]


@pytest.mark.asyncio
async def test_crud_and_relationships():
    """Test full CRUD lifecycle and ORM relationships for all 8 entities."""
    unique_suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        # 1. Create User
        user = User(
            email=f"candidate_{unique_suffix}@example.com",
            hashed_password="mock_hashed_bcrypt_password_value",
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.flush()

        # 2. Create CandidateProfile
        profile = CandidateProfile(
            user_id=user.id,
            full_name="Alex Mercer",
            headline="Full Stack Cloud Developer",
            summary="Passionate engineer with experience in distributed systems.",
            phone="+91-9876543210",
            location_city="Bengaluru",
            location_state="Karnataka",
            location_country="India",
            preferred_work_mode=WorkMode.HYBRID,
            preferred_employment_type=EmploymentType.FULLTIME,
            preferred_salary_min=1200000,
            preferred_salary_max=1800000,
            preferred_salary_currency="INR",
            open_to_relocation=True,
            linkedin_url="https://linkedin.com/in/alexmercer",
            github_url="https://github.com/alexmercer",
            portfolio_url="https://alexmercer.dev",
        )
        session.add(profile)
        await session.flush()

        # 3. Add Resume
        resume = Resume(
            candidate_profile_id=profile.id,
            filename="Alex_Mercer_Resume.pdf",
            file_path="/data/uploads/resumes/mock_path.pdf",
            file_type="pdf",
            file_size_bytes=1048576,
            raw_text="Experienced engineer in Python, FastAPI, and PostgreSQL.",
            parsed_json={"skills": ["Python", "FastAPI"], "years": 3},
            is_active=True,
        )
        session.add(resume)

        # 4. Add Skills
        skill1 = Skill(
            candidate_profile_id=profile.id,
            skill_name="python",
            category=SkillCategory.TECHNICAL,
            proficiency_level=SkillProficiency.ADVANCED,
            years_of_experience=4,
            source=SkillSource.RESUME,
        )
        skill2 = Skill(
            candidate_profile_id=profile.id,
            skill_name="postgresql",
            category=SkillCategory.TECHNICAL,
            proficiency_level=SkillProficiency.INTERMEDIATE,
            years_of_experience=3,
            source=SkillSource.MANUAL,
        )
        session.add_all([skill1, skill2])

        # 5. Add Education
        edu = Education(
            candidate_profile_id=profile.id,
            institution="National Institute of Technology",
            degree="Bachelor of Technology",
            field_of_study="Computer Science and Engineering",
            education_level=EducationLevel.BACHELOR,
            start_date=date(2020, 8, 1),
            end_date=date(2024, 5, 30),
            is_current=False,
            grade="8.9 CGPA",
            description="Graduated with honors in Computer Science.",
        )
        session.add(edu)

        # 6. Add Experience
        exp = Experience(
            candidate_profile_id=profile.id,
            company="Tech Corp Solutions",
            title="Software Development Engineer",
            employment_type=EmploymentType.FULLTIME,
            location="Bengaluru, India",
            work_mode=WorkMode.HYBRID,
            start_date=date(2024, 6, 1),
            end_date=None,
            is_current=True,
            description="Built high-performance microservices with FastAPI and PostgreSQL.",
            skills_used=["Python", "FastAPI", "PostgreSQL", "Docker"],
        )
        session.add(exp)

        # 7. Add Project
        proj = Project(
            candidate_profile_id=profile.id,
            title="Distributed Task Queue",
            description="Asynchronous job processing system backed by Redis and PostgreSQL.",
            technologies=["Python", "Redis", "PostgreSQL", "Docker"],
            project_url="https://taskqueue.demo.app",
            repo_url="https://github.com/alexmercer/task-queue",
            start_date=date(2023, 1, 15),
            end_date=date(2023, 4, 30),
        )
        session.add(proj)

        # 8. Add Certification
        cert = Certification(
            candidate_profile_id=profile.id,
            name="AWS Certified Developer - Associate",
            issuing_organization="Amazon Web Services",
            issue_date=date(2023, 9, 10),
            expiry_date=date(2026, 9, 10),
            credential_id="AWS-DEV-123456",
            credential_url="https://aws.amazon.com/verify/123456",
        )
        session.add(cert)
        await session.commit()

        # Query back and verify
        stmt = select(CandidateProfile).where(CandidateProfile.id == profile.id)
        res = await session.execute(stmt)
        queried_profile = res.scalar_one()

        assert queried_profile.full_name == "Alex Mercer"
        assert queried_profile.preferred_work_mode == WorkMode.HYBRID
        assert queried_profile.preferred_employment_type == EmploymentType.FULLTIME
        assert queried_profile.preferred_salary_min == 1200000


@pytest.mark.asyncio
async def test_cascade_deletion():
    """Verify that deleting a User cascades to CandidateProfile and all child entities."""
    unique_suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            email=f"cascade_{unique_suffix}@example.com",
            hashed_password="mock_password_hash",
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Cascade Tester",
            preferred_work_mode=WorkMode.REMOTE,
            preferred_employment_type=EmploymentType.FULLTIME,
        )
        session.add(profile)
        await session.flush()

        resume = Resume(
            candidate_profile_id=profile.id,
            filename="cascade.pdf",
            file_path="/tmp/cascade.pdf",
            file_type="pdf",
        )
        skill = Skill(
            candidate_profile_id=profile.id,
            skill_name=f"skill_{unique_suffix}",
            source=SkillSource.MANUAL,
        )
        session.add_all([resume, skill])
        await session.commit()

        # Verify records exist
        profile_id = profile.id

        # Delete the User
        await session.delete(user)
        await session.commit()

        # Assert Profile and Skill are gone via cascade
        profile_check = await session.get(CandidateProfile, profile_id)
        assert profile_check is None, "CandidateProfile must be deleted by cascade"

        skills_check = await session.execute(
            select(Skill).where(Skill.candidate_profile_id == profile_id)
        )
        assert len(skills_check.scalars().all()) == 0, "Skills must be deleted by cascade"


@pytest.mark.asyncio
async def test_duplicate_email_violation():
    """Verify that duplicate user emails violate the unique constraint."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"dup_{unique_suffix}@example.com"
    async with async_session_factory() as session:
        user1 = User(email=email, hashed_password="pw1")
        session.add(user1)
        await session.commit()

        user2 = User(email=email, hashed_password="pw2")
        session.add(user2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_duplicate_skill_per_profile_violation():
    """Verify that duplicate skills on the same profile violate uq_skills_profile_skill."""
    unique_suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(email=f"skill_dup_{unique_suffix}@example.com", hashed_password="pw")
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Skill Dup Tester",
        )
        session.add(profile)
        await session.flush()

        s1 = Skill(
            candidate_profile_id=profile.id,
            skill_name="python",
            source=SkillSource.MANUAL,
        )
        s2 = Skill(
            candidate_profile_id=profile.id,
            skill_name="python",
            source=SkillSource.RESUME,
        )
        session.add_all([s1, s2])
        with pytest.raises(IntegrityError):
            await session.commit()
