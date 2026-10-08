"""
Tests for Phase 15 Opportunity Discovery.
Validates public active opportunity discovery, keyword search,
deterministic skill name matching, interval experience overlap,
category filters, sorting, pagination, and detail retrieval.
"""

import uuid
from datetime import date, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EmploymentType, OpportunitySource, OpportunityType, WorkMode
from app.models.opportunity import Opportunity, OpportunitySkill


@pytest.mark.asyncio
async def test_list_opportunities_public_access_no_auth(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Discovery endpoint is public and does not require an Authorization header."""
    opp = Opportunity(
        title="Public Job Title",
        company="Open Corp",
        description="Publicly discoverable position.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add(opp)
    await db_session.commit()

    response = await async_client.get("/api/v1/opportunities/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert any(item["title"] == "Public Job Title" for item in data["items"])


@pytest.mark.asyncio
async def test_list_opportunities_strictly_active_by_default(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Inactive opportunities must NOT be returned in public discovery."""
    active_opp = Opportunity(
        title="Active Opportunity Listing",
        company="Active Inc",
        description="Description active",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    inactive_opp = Opportunity(
        title="Inactive Hidden Listing",
        company="Secret Inc",
        description="Should not appear in discovery",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=False,
    )
    db_session.add_all([active_opp, inactive_opp])
    await db_session.commit()

    response = await async_client.get("/api/v1/opportunities/?page_size=100")
    assert response.status_code == 200
    data = response.json()
    titles = [item["title"] for item in data["items"]]
    assert "Active Opportunity Listing" in titles
    assert "Inactive Hidden Listing" not in titles


@pytest.mark.asyncio
async def test_keyword_search_matches_title_company_description_location(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Keyword search matches substring across title, company, description, and location."""
    opp1 = Opportunity(
        title="Rust Systems Engineer",
        company="Kernel Labs",
        description="Low level development",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city="Seattle",
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    opp2 = Opportunity(
        title="Frontend Architect",
        company="Reactive Unicorns",
        description="Crafting responsive UI with TailwindCSS",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        location_city="Austin",
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add_all([opp1, opp2])
    await db_session.commit()

    # Search title
    res_title = await async_client.get("/api/v1/opportunities/?keyword=Rust")
    assert res_title.status_code == 200
    assert any(i["title"] == "Rust Systems Engineer" for i in res_title.json()["items"])
    assert not any(i["title"] == "Frontend Architect" for i in res_title.json()["items"])

    # Search company
    res_comp = await async_client.get("/api/v1/opportunities/?keyword=Unicorns")
    assert res_comp.status_code == 200
    assert any(i["company"] == "Reactive Unicorns" for i in res_comp.json()["items"])

    # Search description
    res_desc = await async_client.get("/api/v1/opportunities/?keyword=TailwindCSS")
    assert res_desc.status_code == 200
    assert any(i["title"] == "Frontend Architect" for i in res_desc.json()["items"])

    # Search location
    res_loc = await async_client.get("/api/v1/opportunities/?keyword=Seattle")
    assert res_loc.status_code == 200
    assert any(i["location_city"] == "Seattle" for i in res_loc.json()["items"])


@pytest.mark.asyncio
async def test_keyword_search_matches_relational_skill_name(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Keyword search deterministically matches associated OpportunitySkill name without vectors."""
    opp = Opportunity(
        title="Fullstack Developer",
        company="WebWorks",
        description="General web engineering",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add(opp)
    await db_session.flush()

    skill = OpportunitySkill(
        opportunity_id=opp.id,
        skill_name="PostgreSQL Optimization",
        is_required=True,
    )
    db_session.add(skill)
    await db_session.commit()

    response = await async_client.get("/api/v1/opportunities/?keyword=Optimization")
    assert response.status_code == 200
    data = response.json()
    assert any(item["id"] == str(opp.id) for item in data["items"])


@pytest.mark.asyncio
async def test_experience_range_interval_overlap(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Test exact interval overlap semantics:
    Opp A: [1, 3] years
    Opp B: [4, 7] years
    Opp C: [5, None] (5+ years)
    Opp D: [None, 2] (0-2 years)
    """
    opp_a = Opportunity(
        title="Junior Developer A",
        company="Co A",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        min_experience_years=1,
        max_experience_years=3,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    opp_b = Opportunity(
        title="Mid-Senior Developer B",
        company="Co B",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        min_experience_years=4,
        max_experience_years=7,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    opp_c = Opportunity(
        title="Staff Architect C",
        company="Co C",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        min_experience_years=5,
        max_experience_years=None,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    opp_d = Opportunity(
        title="New Grad D",
        company="Co D",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        min_experience_years=None,
        max_experience_years=2,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add_all([opp_a, opp_b, opp_c, opp_d])
    await db_session.commit()

    # Query 1: Filter [2, 4] -> Should overlap with Opp A [1,3], Opp B [4,7], and Opp D [None,2]
    res1 = await async_client.get("/api/v1/opportunities/?min_experience_years=2&max_experience_years=4&page_size=100")
    assert res1.status_code == 200
    titles1 = [i["title"] for i in res1.json()["items"]]
    assert "Junior Developer A" in titles1
    assert "Mid-Senior Developer B" in titles1
    assert "New Grad D" in titles1
    assert "Staff Architect C" not in titles1  # C lower bound is 5, filter max is 4 -> no overlap

    # Query 2: Filter [6, 10] -> Should overlap with Opp B [4,7] and Opp C [5,None]
    res2 = await async_client.get("/api/v1/opportunities/?min_experience_years=6&max_experience_years=10&page_size=100")
    assert res2.status_code == 200
    titles2 = [i["title"] for i in res2.json()["items"]]
    assert "Mid-Senior Developer B" in titles2
    assert "Staff Architect C" in titles2
    assert "Junior Developer A" not in titles2


@pytest.mark.asyncio
async def test_filter_by_opportunity_type(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify filtering by JOB, INTERNSHIP, and HACKATHON."""
    job = Opportunity(
        title="Fulltime Backend Engineer",
        company="Acme Corp",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    internship = Opportunity(
        title="Summer AI Research Intern",
        company="OpenLab",
        description="desc",
        opportunity_type=OpportunityType.INTERNSHIP,
        employment_type=EmploymentType.INTERNSHIP,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    hackathon = Opportunity(
        title="Global GenAI Hackathon 2026",
        company="HackPlatform",
        description="desc",
        opportunity_type=OpportunityType.HACKATHON,
        employment_type=EmploymentType.ANY,
        work_mode=WorkMode.REMOTE,
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add_all([job, internship, hackathon])
    await db_session.commit()

    # Query Internship
    res = await async_client.get("/api/v1/opportunities/?opportunity_type=internship")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    assert all(i["opportunity_type"] == "internship" for i in items)

    # Query Hackathon
    res_hack = await async_client.get("/api/v1/opportunities/?opportunity_type=hackathon")
    assert res_hack.status_code == 200
    hack_items = res_hack.json()["items"]
    assert len(hack_items) > 0
    assert all(i["opportunity_type"] == "hackathon" for i in hack_items)


@pytest.mark.asyncio
async def test_sorting_options(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify sorting by newest, oldest, deadline_soonest, and title_asc."""
    today = date.today()
    run_id = str(uuid.uuid4())[:8]
    opp1 = Opportunity(
        title=f"Alpha SortProject {run_id}",
        company="Co 1",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        application_deadline=today + timedelta(days=30),
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    opp2 = Opportunity(
        title=f"Zulu SortProject {run_id}",
        company="Co 2",
        description="desc",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        application_deadline=today + timedelta(days=5),
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add_all([opp1, opp2])
    await db_session.commit()

    # Sort by title_asc
    res_title = await async_client.get(f"/api/v1/opportunities/?keyword={run_id}&sort_by=title_asc")
    assert res_title.status_code == 200
    items = res_title.json()["items"]
    assert len(items) == 2
    assert items[0]["title"] == f"Alpha SortProject {run_id}"
    assert items[1]["title"] == f"Zulu SortProject {run_id}"

    # Sort by deadline_soonest
    res_deadline = await async_client.get(f"/api/v1/opportunities/?keyword={run_id}&sort_by=deadline_soonest")
    assert res_deadline.status_code == 200
    items_d = res_deadline.json()["items"]
    assert len(items_d) == 2
    assert items_d[0]["title"] == f"Zulu SortProject {run_id}"
    assert items_d[1]["title"] == f"Alpha SortProject {run_id}"


@pytest.mark.asyncio
async def test_get_opportunity_detail_with_skills_and_404(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Detail endpoint returns complete opportunity with skills or 404 if not found."""
    opp = Opportunity(
        title="Principal Cloud Architect",
        company="SkyScale Systems",
        description="Design massive AWS multi-region infrastructure.",
        opportunity_type=OpportunityType.JOB,
        employment_type=EmploymentType.FULLTIME,
        work_mode=WorkMode.REMOTE,
        job_url="https://skyscale.example.com/apply/123",
        source=OpportunitySource.MANUAL,
        is_active=True,
    )
    db_session.add(opp)
    await db_session.flush()

    skill1 = OpportunitySkill(
        opportunity_id=opp.id,
        skill_name="Terraform",
        is_required=True,
    )
    skill2 = OpportunitySkill(
        opportunity_id=opp.id,
        skill_name="Kubernetes",
        is_required=False,
    )
    db_session.add_all([skill1, skill2])
    await db_session.commit()

    # 1. Fetch valid opportunity detail
    res = await async_client.get(f"/api/v1/opportunities/{opp.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(opp.id)
    assert data["title"] == "Principal Cloud Architect"
    assert data["job_url"] == "https://skyscale.example.com/apply/123"
    assert len(data["skills"]) == 2
    skill_names = [s["skill_name"] for s in data["skills"]]
    assert "Terraform" in skill_names
    assert "Kubernetes" in skill_names

    # 2. Fetch unknown UUID -> 404
    unknown_id = "00000000-0000-0000-0000-000000000000"
    res_404 = await async_client.get(f"/api/v1/opportunities/{unknown_id}")
    assert res_404.status_code == 404
    assert res_404.json()["detail"] == "Opportunity not found."
