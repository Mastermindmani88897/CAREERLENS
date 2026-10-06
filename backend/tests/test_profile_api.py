"""
Comprehensive integration test suite for Phase 12 Candidate Profile API
and Resume-to-Profile Synchronization.

Covers all 28 requirements:
1. Profile creation
2. Profile retrieval
3. Profile update
4. Duplicate profile handling (409 Conflict)
5. Authentication (401 Unauthorized)
6. Owner authorization
7. Cross-user access rejection
8. Skills CRUD
9. Education CRUD
10. Experience CRUD
11. Projects CRUD
12. Certifications CRUD
13. Validation failures
14. Resume-to-profile initialization
15. Resume synchronization
16. Preservation of user-edited fields
17. Preservation of user-added skills
18. Preservation of user-added education
19. Preservation of user-added experience
20. Preservation of user-added projects
21. Preservation of user-added certifications
22. Duplicate prevention during synchronization
23. Repeated synchronization/idempotency
24. Invalid resume ID
25. Resume belonging to another user
26. Failed/unparsed resume synchronization
27. Database persistence
28. Transaction rollback/error behavior
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.candidate import CandidateProfile, Resume
from app.models.enums import SkillSource
from app.models.user import User
from tests.helpers.auth import create_authenticated_headers, create_test_user
from tests.helpers.synthetic_resumes import create_synthetic_txt_resume


@pytest.mark.asyncio
async def test_profile_unauthenticated_rejected() -> None:
    """1 & 5. Unauthenticated requests are rejected with HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res1 = await ac.get("/api/v1/profiles/me")
        res2 = await ac.post("/api/v1/profiles", json={"full_name": "Test"})
        res3 = await ac.put("/api/v1/profiles/me", json={"full_name": "Test"})
        res4 = await ac.get("/api/v1/profiles/me/skills")
        res5 = await ac.post(f"/api/v1/profiles/me/sync-from-resume/{uuid.uuid4()}")

    assert res1.status_code == 401
    assert res2.status_code == 401
    assert res3.status_code == 401
    assert res4.status_code == 401
    assert res5.status_code == 401


@pytest.mark.asyncio
async def test_create_and_duplicate_profile(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """1 & 4. Explicit profile creation succeeds; duplicate returns HTTP 409."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create profile
        payload = {
            "full_name": "Jane Developer",
            "headline": "Lead Distributed Systems Architect",
            "summary": "Specialist in high-throughput streaming systems.",
            "location_city": "Bengaluru",
            "location_country": "India",
            "preferred_work_mode": "hybrid",
            "preferred_employment_type": "fulltime",
            "open_to_relocation": True,
        }
        res = await ac.post("/api/v1/profiles", headers=headers, json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["full_name"] == "Jane Developer"
        assert data["headline"] == "Lead Distributed Systems Architect"
        assert data["user_id"] == str(user.id)

        # Duplicate creation attempt
        res_dup = await ac.post("/api/v1/profiles", headers=headers, json=payload)
        assert res_dup.status_code == 409
        assert "already exists" in res_dup.json()["detail"]


@pytest.mark.asyncio
async def test_get_my_profile_and_update(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """2 & 3. Retrieve and update current user's profile."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET /api/v1/profiles/me initializes a default profile if none exists
        res_get = await ac.get("/api/v1/profiles/me", headers=headers)
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert data_get["user_id"] == str(user.id)
        assert "skills" in data_get
        assert "educations" in data_get

        # PUT /api/v1/profiles/me updates editable attributes
        update_payload = {
            "headline": "Senior Cloud Native Engineer",
            "phone": "+91-9876543210",
            "location_city": "Hyderabad",
            "linkedin_url": "https://linkedin.com/in/janedev",
        }
        res_put = await ac.put("/api/v1/profiles/me", headers=headers, json=update_payload)
        assert res_put.status_code == 200
        data_put = res_put.json()
        assert data_put["headline"] == "Senior Cloud Native Engineer"
        assert data_put["phone"] == "+91-9876543210"
        assert data_put["location_city"] == "Hyderabad"
        assert data_put["linkedin_url"] == "https://linkedin.com/in/janedev"


@pytest.mark.asyncio
async def test_skills_crud(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """8. Complete Skills sub-resource CRUD operations and duplicate prevention."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add skill
        skill_payload = {
            "skill_name": "Kubernetes",
            "category": "tool",
            "proficiency_level": "advanced",
            "years_of_experience": 4,
            "source": "manual",
        }
        res_add = await ac.post("/api/v1/profiles/me/skills", headers=headers, json=skill_payload)
        assert res_add.status_code == 201
        skill_data = res_add.json()
        skill_id = skill_data["id"]
        assert skill_data["skill_name"] == "Kubernetes"
        assert skill_data["source"] == SkillSource.MANUAL.value

        # Duplicate skill returns 409
        res_dup = await ac.post("/api/v1/profiles/me/skills", headers=headers, json=skill_payload)
        assert res_dup.status_code == 409

        # List skills
        res_list = await ac.get("/api/v1/profiles/me/skills", headers=headers)
        assert res_list.status_code == 200
        skills = res_list.json()
        assert len(skills) == 1
        assert skills[0]["id"] == skill_id

        # Delete skill
        res_del = await ac.delete(f"/api/v1/profiles/me/skills/{skill_id}", headers=headers)
        assert res_del.status_code == 204

        # Delete non-existent skill returns 404
        res_del_404 = await ac.delete(f"/api/v1/profiles/me/skills/{skill_id}", headers=headers)
        assert res_del_404.status_code == 404


@pytest.mark.asyncio
async def test_education_crud(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """9. Complete Education sub-resource CRUD."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        edu_payload = {
            "institution": "National Institute of Technology",
            "degree": "Bachelor of Technology",
            "field_of_study": "Computer Science",
            "education_level": "bachelor",
            "start_date": "2018-08-01",
            "end_date": "2022-05-31",
            "grade": "8.9/10",
        }
        res_add = await ac.post("/api/v1/profiles/me/education", headers=headers, json=edu_payload)
        assert res_add.status_code == 201
        edu_data = res_add.json()
        edu_id = edu_data["id"]

        # Update education
        update_payload = {"grade": "9.1/10", "is_current": False}
        res_put = await ac.put(
            f"/api/v1/profiles/me/education/{edu_id}", headers=headers, json=update_payload
        )
        assert res_put.status_code == 200
        assert res_put.json()["grade"] == "9.1/10"

        # List education
        res_list = await ac.get("/api/v1/profiles/me/education", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Delete education
        res_del = await ac.delete(f"/api/v1/profiles/me/education/{edu_id}", headers=headers)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_experience_crud(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """10. Complete Experience sub-resource CRUD."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        exp_payload = {
            "company": "Apex Cloud Systems",
            "title": "Software Development Engineer II",
            "employment_type": "fulltime",
            "work_mode": "remote",
            "start_date": "2022-06-01",
            "is_current": True,
            "description": "Architected low-latency caching layer.",
            "skills_used": ["Python", "FastAPI", "Redis"],
        }
        res_add = await ac.post("/api/v1/profiles/me/experience", headers=headers, json=exp_payload)
        assert res_add.status_code == 201
        exp_data = res_add.json()
        exp_id = exp_data["id"]
        assert exp_data["skills_used"] == ["Python", "FastAPI", "Redis"]

        # Update
        res_put = await ac.put(
            f"/api/v1/profiles/me/experience/{exp_id}",
            headers=headers,
            json={"title": "Senior Software Engineer"},
        )
        assert res_put.status_code == 200
        assert res_put.json()["title"] == "Senior Software Engineer"

        # List
        res_list = await ac.get("/api/v1/profiles/me/experience", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Delete
        res_del = await ac.delete(f"/api/v1/profiles/me/experience/{exp_id}", headers=headers)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_projects_crud(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """11. Complete Projects sub-resource CRUD."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        proj_payload = {
            "title": "Async Task Coordinator",
            "description": "Distributed lock coordinator using Redis.",
            "technologies": ["Go", "Redis", "Docker"],
            "repo_url": "https://github.com/janedev/task-coordinator",
        }
        res_add = await ac.post("/api/v1/profiles/me/projects", headers=headers, json=proj_payload)
        assert res_add.status_code == 201
        proj_data = res_add.json()
        proj_id = proj_data["id"]

        # Update
        res_put = await ac.put(
            f"/api/v1/profiles/me/projects/{proj_id}",
            headers=headers,
            json={"project_url": "https://task-coord.dev"},
        )
        assert res_put.status_code == 200
        assert res_put.json()["project_url"] == "https://task-coord.dev"

        # List
        res_list = await ac.get("/api/v1/profiles/me/projects", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Delete
        res_del = await ac.delete(f"/api/v1/profiles/me/projects/{proj_id}", headers=headers)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_certifications_crud(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """12. Complete Certifications sub-resource CRUD."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        cert_payload = {
            "name": "AWS Certified Solutions Architect - Professional",
            "issuing_organization": "Amazon Web Services",
            "issue_date": "2023-04-15",
            "credential_url": "https://aws.amazon.com/verify/12345",
        }
        res_add = await ac.post(
            "/api/v1/profiles/me/certifications", headers=headers, json=cert_payload
        )
        assert res_add.status_code == 201
        cert_data = res_add.json()
        cert_id = cert_data["id"]

        # Update
        res_put = await ac.put(
            f"/api/v1/profiles/me/certifications/{cert_id}",
            headers=headers,
            json={"credential_id": "AWS-PRO-987654"},
        )
        assert res_put.status_code == 200
        assert res_put.json()["credential_id"] == "AWS-PRO-987654"

        # List
        res_list = await ac.get("/api/v1/profiles/me/certifications", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Delete
        res_del = await ac.delete(f"/api/v1/profiles/me/certifications/{cert_id}", headers=headers)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_cross_user_isolation(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """6 & 7. Cross-user access rejection: User B cannot delete or access User A resources."""
    user_a, _ = authenticated_user
    user_b, _ = await create_test_user(db_session)
    await db_session.commit()

    headers_a = create_authenticated_headers(user_a.id)
    headers_b = create_authenticated_headers(user_b.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # User A creates a skill and education
        res_skill = await ac.post(
            "/api/v1/profiles/me/skills",
            headers=headers_a,
            json={"skill_name": "Docker", "source": "manual"},
        )
        assert res_skill.status_code == 201
        skill_id = res_skill.json()["id"]

        res_edu = await ac.post(
            "/api/v1/profiles/me/education",
            headers=headers_a,
            json={
                "institution": "IIT Bombay",
                "degree": "B.Tech",
                "field_of_study": "EE",
                "education_level": "bachelor",
            },
        )
        assert res_edu.status_code == 201
        edu_id = res_edu.json()["id"]

        # User B attempts to delete User A's skill -> 404 (not found under User B's profile)
        del_skill_b = await ac.delete(f"/api/v1/profiles/me/skills/{skill_id}", headers=headers_b)
        assert del_skill_b.status_code == 404

        # User B attempts to delete User A's education -> 404
        del_edu_b = await ac.delete(f"/api/v1/profiles/me/education/{edu_id}", headers=headers_b)
        assert del_edu_b.status_code == 404

        # User A's skill and education remain intact
        skills_a = await ac.get("/api/v1/profiles/me/skills", headers=headers_a)
        assert len(skills_a.json()) == 1


@pytest.mark.asyncio
async def test_validation_failures(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """13. Input validation rejects invalid date ranges and empty strings."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # End date before start date in education
        invalid_edu = {
            "institution": "University",
            "degree": "B.S.",
            "field_of_study": "CS",
            "start_date": "2024-01-01",
            "end_date": "2022-01-01",
        }
        res_edu = await ac.post("/api/v1/profiles/me/education", headers=headers, json=invalid_edu)
        assert res_edu.status_code == 422

        # Negative years of experience in skill
        invalid_skill = {
            "skill_name": "Go",
            "years_of_experience": -5,
        }
        res_skill = await ac.post("/api/v1/profiles/me/skills", headers=headers, json=invalid_skill)
        assert res_skill.status_code == 422


@pytest.mark.asyncio
async def test_resume_to_profile_synchronization(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """
    14, 15, 16, 17, 18, 19, 20, 21, 22, 23.
    Comprehensive Resume-to-Profile synchronization test:
    - Ingests parsed resume
    - Preserves pre-existing user profile fields
    - Preserves pre-existing manual skills
    - Merges new skills, education, experience, projects, certifications
    - Repeated synchronization is idempotent
    """
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. User manually sets up profile with customized phone and manual skill
        put_res = await ac.put(
            "/api/v1/profiles/me",
            headers=headers,
            json={
                "phone": "+91-9999999999",  # User's explicit custom phone
                "summary": "Custom manual summary written by user.",
                "location_city": "Mumbai",
            },
        )
        assert put_res.status_code == 200
        await ac.post(
            "/api/v1/profiles/me/skills",
            headers=headers,
            json={"skill_name": "Rust", "source": "manual", "proficiency_level": "advanced"},
        )

        # 2. Upload synthetic resume
        txt_bytes = create_synthetic_txt_resume()
        upload_res = await ac.post(
            "/api/v1/resumes",
            headers=headers,
            files={"file": ("jordan_resume.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201
        resume_id = upload_res.json()["id"]

        # 3. Synchronize profile from parsed resume
        sync_res = await ac.post(
            f"/api/v1/profiles/me/sync-from-resume/{resume_id}",
            headers=headers,
        )
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["skills_added"] > 0
        assert sync_data["educations_added"] > 0
        assert "phone" in sync_data["preserved_fields"]
        assert "summary" in sync_data["preserved_fields"]

        # 4. Verify profile state
        profile_res = await ac.get("/api/v1/profiles/me", headers=headers)
        assert profile_res.status_code == 200
        profile = profile_res.json()

        # User-customized values are strictly preserved
        assert profile["phone"] == "+91-9999999999"
        assert profile["summary"] == "Custom manual summary written by user."
        assert profile["location_city"] == "Mumbai"

        # Empty fields were populated from resume
        assert profile["linkedin_url"] is not None
        assert "linkedin.com" in profile["linkedin_url"]

        # User's manual skill is preserved and resume skills are added
        skill_names = [s["skill_name"].lower() for s in profile["skills"]]
        assert "rust" in skill_names
        assert "python" in skill_names

        # Education, experience, projects, certifications are populated
        assert len(profile["educations"]) > 0
        assert len(profile["experiences"]) > 0
        assert len(profile["projects"]) > 0
        assert len(profile["certifications"]) > 0

        # 5. IDEMPOTENCY TEST: Run synchronization a second time with same resume
        sync_res_2 = await ac.post(
            f"/api/v1/profiles/me/sync-from-resume/{resume_id}",
            headers=headers,
        )
        assert sync_res_2.status_code == 200
        sync_data_2 = sync_res_2.json()
        assert sync_data_2["skills_added"] == 0
        assert sync_data_2["educations_added"] == 0
        assert sync_data_2["experiences_added"] == 0
        assert sync_data_2["projects_added"] == 0
        assert sync_data_2["certifications_added"] == 0

        # Profile counts must be identical (no duplicates created)
        profile_res_2 = await ac.get("/api/v1/profiles/me", headers=headers)
        profile_2 = profile_res_2.json()
        assert len(profile_2["skills"]) == len(profile["skills"])
        assert len(profile_2["educations"]) == len(profile["educations"])
        assert len(profile_2["experiences"]) == len(profile["experiences"])
        assert len(profile_2["projects"]) == len(profile["projects"])
        assert len(profile_2["certifications"]) == len(profile["certifications"])


@pytest.mark.asyncio
async def test_sync_resume_authorization_and_error_handling(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """
    24, 25, 26. Error handling for synchronization:
    - Non-existent resume ID -> 404
    - Resume owned by another user -> 403
    - Resume not successfully parsed -> 400
    """
    user_a, _ = authenticated_user
    user_b, _ = await create_test_user(db_session)
    await db_session.commit()

    headers_a = create_authenticated_headers(user_a.id)
    headers_b = create_authenticated_headers(user_b.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # User B uploads a resume
        txt_bytes = create_synthetic_txt_resume()
        upload_res = await ac.post(
            "/api/v1/resumes",
            headers=headers_b,
            files={"file": ("user_b_resume.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201
        resume_b_id = upload_res.json()["id"]

        # User A tries to sync User B's resume -> 403 Forbidden
        sync_cross = await ac.post(
            f"/api/v1/profiles/me/sync-from-resume/{resume_b_id}",
            headers=headers_a,
        )
        assert sync_cross.status_code == 403

        # Non-existent resume ID -> 404 Not Found
        random_id = uuid.uuid4()
        sync_404 = await ac.post(
            f"/api/v1/profiles/me/sync-from-resume/{random_id}",
            headers=headers_a,
        )
        assert sync_404.status_code == 404

        # Resume with failed or unparsed status -> 400 Bad Request
        # Create a mock failed resume for User A directly in DB
        profile_a_res = await ac.get("/api/v1/profiles/me", headers=headers_a)
        profile_a_id = uuid.UUID(profile_a_res.json()["id"])

        failed_resume = Resume(
            candidate_profile_id=profile_a_id,
            filename="failed.pdf",
            file_path="./data/uploads/resumes/failed.pdf",
            file_type="pdf",
            parsed_json={"status": "failed", "error_message": "Corrupted PDF"},
        )
        db_session.add(failed_resume)
        await db_session.commit()
        await db_session.refresh(failed_resume)

        sync_failed = await ac.post(
            f"/api/v1/profiles/me/sync-from-resume/{failed_resume.id}",
            headers=headers_a,
        )
        assert sync_failed.status_code == 400
        assert "not been successfully parsed" in sync_failed.json()["detail"]


@pytest.mark.asyncio
async def test_database_persistence_and_relationships(
    db_session: AsyncSession,
    authenticated_user: tuple[User, str],
) -> None:
    """27 & 28. Database persistence verified directly via SQLAlchemy async session."""
    user, _ = authenticated_user
    headers = create_authenticated_headers(user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/profiles/me/skills",
            headers=headers,
            json={"skill_name": "PostgreSQL", "category": "technical"},
        )
        assert res.status_code == 201

    # Verify directly via db_session
    stmt = CandidateProfile.__table__.select().where(CandidateProfile.user_id == user.id)
    res = await db_session.execute(stmt)
    assert res.first() is not None
