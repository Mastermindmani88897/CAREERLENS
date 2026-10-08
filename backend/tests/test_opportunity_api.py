"""
Automated tests for Opportunity API endpoints (Phase 14).
Covers CSV/JSON ingestion endpoints, authentication enforcement,
pagination, filtering, and single-item detail retrieval.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import async_session_factory
from app.main import app
from app.models.enums import EmploymentType, OpportunitySource, OpportunityType, WorkMode
from app.models.opportunity import Opportunity, OpportunitySkill
from tests.helpers.auth import create_authenticated_headers, create_test_user


@pytest.fixture
async def async_api_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client targeting the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_ingest_unauthenticated_rejected(async_api_client: AsyncClient):
    """Verify that unauthenticated access to /ingest returns 401."""
    response = await async_api_client.post("/api/v1/opportunities/ingest")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_csv_file_success(async_api_client: AsyncClient):
    """Verify authenticated user can ingest opportunities via CSV file upload."""
    async with async_session_factory() as session:
        user, _ = await create_test_user(session)
        await session.commit()
        headers = create_authenticated_headers(user.id)

    sid1 = f"api_test_1_{uuid.uuid4().hex[:6]}"
    sid2 = f"api_test_2_{uuid.uuid4().hex[:6]}"
    csv_data = (
        "title,company,description,opportunity_type,source,source_id\n"
        f"Lead SRE,CloudNet,Manage site reliability.,job,synthetic,{sid1}\n"
        f"Data Science Intern,DataCorp,Model training.,internship,synthetic,{sid2}\n"
    )
    files = {"file": ("jobs.csv", csv_data.encode("utf-8"), "text/csv")}

    response = await async_api_client.post(
        "/api/v1/opportunities/ingest",
        headers=headers,
        files=files,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["created"] == 2
    assert data["skipped_duplicates"] == 0


@pytest.mark.asyncio
async def test_ingest_json_records_success(async_api_client: AsyncClient):
    """Verify authenticated user can ingest opportunities via JSON body."""
    async with async_session_factory() as session:
        user, _ = await create_test_user(session)
        await session.commit()
        headers = create_authenticated_headers(user.id)

    payload = [
        {
            "title": "Quantum Algorithm Researcher",
            "company": "Qubit Labs",
            "description": "Develop quantum simulation algorithms.",
            "opportunity_type": "job",
            "source": "api",
            "source_id": f"json_test_{uuid.uuid4().hex[:6]}",
            "required_skills": ["python", "qiskit", "linear algebra"],
        }
    ]

    response = await async_api_client.post(
        "/api/v1/opportunities/ingest",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["created"] == 1


@pytest.mark.asyncio
async def test_ingest_invalid_file_extension_rejected(async_api_client: AsyncClient):
    """Verify non-csv file extension is rejected with 400 Bad Request."""
    async with async_session_factory() as session:
        user, _ = await create_test_user(session)
        await session.commit()
        headers = create_authenticated_headers(user.id)

    files = {"file": ("data.txt", b"some text", "text/plain")}
    response = await async_api_client.post(
        "/api/v1/opportunities/ingest",
        headers=headers,
        files=files,
    )
    assert response.status_code == 400
    assert "must be a .csv format file" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_opportunities_with_filtering_and_pagination(async_api_client: AsyncClient):
    """Verify listing opportunities with opportunity_type, work_mode filters and pagination."""
    unique_suffix = uuid.uuid4().hex[:6]

    async with async_session_factory() as session:
        opp_job = Opportunity(
            opportunity_type=OpportunityType.JOB,
            title=f"Backend Lead {unique_suffix}",
            company="Filter Co",
            description="Backend role description.",
            work_mode=WorkMode.REMOTE,
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.SYNTHETIC,
        )
        opp_hack = Opportunity(
            opportunity_type=OpportunityType.HACKATHON,
            title=f"AI Codeathon {unique_suffix}",
            company="Hack Org",
            description="Hackathon challenge.",
            work_mode=WorkMode.REMOTE,
            employment_type=EmploymentType.ANY,
            source=OpportunitySource.SYNTHETIC,
        )
        session.add_all([opp_job, opp_hack])
        await session.commit()

    # 1. Filter by opportunity_type=hackathon
    resp_hack = await async_api_client.get(
        "/api/v1/opportunities/?opportunity_type=hackathon",
    )
    assert resp_hack.status_code == 200
    data_hack = resp_hack.json()
    assert data_hack["total"] >= 1
    for item in data_hack["items"]:
        assert item["opportunity_type"] == "hackathon"

    # 2. Filter by work_mode=remote
    resp_remote = await async_api_client.get(
        "/api/v1/opportunities/?work_mode=remote",
    )
    assert resp_remote.status_code == 200
    data_remote = resp_remote.json()
    assert data_remote["total"] >= 1
    for item in data_remote["items"]:
        assert item["work_mode"] == "remote"

    # 3. Pagination verification
    resp_page = await async_api_client.get(
        "/api/v1/opportunities/?page=1&page_size=1",
    )
    assert resp_page.status_code == 200
    data_page = resp_page.json()
    assert len(data_page["items"]) <= 1
    assert data_page["page"] == 1
    assert data_page["page_size"] == 1


@pytest.mark.asyncio
async def test_get_opportunity_detail_and_not_found(async_api_client: AsyncClient):
    """Verify single opportunity detail endpoint returns relational skills and 404 on missing ID."""
    unique_suffix = uuid.uuid4().hex[:6]
    opp_id = uuid.uuid4()

    async with async_session_factory() as session:
        opp = Opportunity(
            id=opp_id,
            opportunity_type=OpportunityType.JOB,
            title=f"Full Stack Architect {unique_suffix}",
            company="Apex Technologies",
            description="Lead architectural decisions across teams.",
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.MANUAL,
        )
        skill1 = OpportunitySkill(
            id=uuid.uuid4(),
            opportunity_id=opp_id,
            skill_name="Python",
            is_required=True,
        )
        skill2 = OpportunitySkill(
            id=uuid.uuid4(),
            opportunity_id=opp_id,
            skill_name="Docker",
            is_required=False,
        )
        session.add(opp)
        session.add_all([skill1, skill2])
        await session.commit()

    # 1. Successful detail retrieval
    resp_detail = await async_api_client.get(f"/api/v1/opportunities/{opp_id}")
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    assert detail_data["id"] == str(opp_id)
    assert detail_data["title"] == f"Full Stack Architect {unique_suffix}"
    assert len(detail_data["skills"]) == 2
    skills_map = {s["skill_name"]: s["is_required"] for s in detail_data["skills"]}
    assert skills_map["Python"] is True
    assert skills_map["Docker"] is False

    # 2. Non-existent UUID
    missing_id = uuid.uuid4()
    resp_missing = await async_api_client.get(f"/api/v1/opportunities/{missing_id}")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"] == "Opportunity not found."
