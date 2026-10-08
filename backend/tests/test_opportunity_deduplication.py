"""
Automated tests for deterministic opportunity deduplication (Phase 14).
Covers primary (source+source_id) and fallback (company+title+url/location) deduplication,
ensuring false-positive duplicates are never triggered for distinct opportunities.
"""

import uuid

import pytest

from app.db.session import async_session_factory
from app.models.enums import EmploymentType, OpportunitySource, OpportunityType
from app.models.opportunity import Opportunity
from app.services.opportunity_ingest_service import check_is_duplicate


@pytest.mark.asyncio
async def test_primary_deduplication_source_and_source_id():
    """Verify that identical (source, source_id) triggers primary deduplication."""
    unique_sid = f"syn_dedup_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as session:
        opp = Opportunity(
            opportunity_type=OpportunityType.JOB,
            title="Senior Platform Engineer",
            company="Cloud Inc",
            description="Build scalable distributed cloud services.",
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.SYNTHETIC,
            source_id=unique_sid,
        )
        session.add(opp)
        await session.commit()

    async with async_session_factory() as session:
        # Same source and source_id must report True (duplicate)
        is_dup = await check_is_duplicate(
            db=session,
            source=OpportunitySource.SYNTHETIC,
            source_id=unique_sid,
            company="Different Company Name",
            title="Different Title",
            job_url=None,
            city=None,
            country=None,
        )
        assert is_dup is True

        # Different source_id must report False
        is_not_dup = await check_is_duplicate(
            db=session,
            source=OpportunitySource.SYNTHETIC,
            source_id=f"unique_{uuid.uuid4().hex[:8]}",
            company="Different Company Name",
            title="Different Title",
            job_url=None,
            city=None,
            country=None,
        )
        assert is_not_dup is False


@pytest.mark.asyncio
async def test_fallback_deduplication_by_company_title_and_url():
    """Verify fallback deduplication when source_id is None but company, title, and URL match."""
    unique_suffix = uuid.uuid4().hex[:6]
    company_name = f"AlphaCorp {unique_suffix}"
    role_title = "Staff Machine Learning Engineer"
    url = f"https://alphacorp.example.com/jobs/{unique_suffix}"

    async with async_session_factory() as session:
        opp = Opportunity(
            opportunity_type=OpportunityType.JOB,
            title=role_title,
            company=company_name,
            description="Lead machine learning engineering teams.",
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.MANUAL,
            source_id=None,
            job_url=url,
        )
        session.add(opp)
        await session.commit()

    async with async_session_factory() as session:
        # Case-insensitive match on company, title, and URL
        is_dup = await check_is_duplicate(
            db=session,
            source=OpportunitySource.MANUAL,
            source_id=None,
            company=company_name.lower(),
            title=role_title.upper(),
            job_url=url,
            city=None,
            country=None,
        )
        assert is_dup is True


@pytest.mark.asyncio
async def test_different_companies_same_title_not_duplicate():
    """Verify that different companies posting the same title are NOT flagged as duplicates."""
    unique_suffix = uuid.uuid4().hex[:6]
    title = f"Principal DevOps Engineer {unique_suffix}"

    async with async_session_factory() as session:
        opp = Opportunity(
            opportunity_type=OpportunityType.JOB,
            title=title,
            company="Company One",
            description="Manage Kubernetes clusters.",
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.MANUAL,
            source_id=None,
            location_city="Bengaluru",
            location_country="India",
        )
        session.add(opp)
        await session.commit()

    async with async_session_factory() as session:
        is_dup = await check_is_duplicate(
            db=session,
            source=OpportunitySource.MANUAL,
            source_id=None,
            company="Company Two",  # Different company
            title=title,
            job_url=None,
            city="Bengaluru",
            country="India",
        )
        assert is_dup is False


@pytest.mark.asyncio
async def test_same_company_same_title_different_urls_not_duplicate():
    """Verify distinct job postings at the same company with different URLs are NOT duplicates."""
    unique_suffix = uuid.uuid4().hex[:6]
    company = f"Omni Tech {unique_suffix}"
    title = "Backend Developer"
    url_a = "https://omni.example.com/careers/backend-team-a"
    url_b = "https://omni.example.com/careers/backend-team-b"

    async with async_session_factory() as session:
        opp = Opportunity(
            opportunity_type=OpportunityType.JOB,
            title=title,
            company=company,
            description="Backend developer for payments team.",
            employment_type=EmploymentType.FULLTIME,
            source=OpportunitySource.MANUAL,
            source_id=None,
            job_url=url_a,
        )
        session.add(opp)
        await session.commit()

    async with async_session_factory() as session:
        is_dup = await check_is_duplicate(
            db=session,
            source=OpportunitySource.MANUAL,
            source_id=None,
            company=company,
            title=title,
            job_url=url_b,  # Different URL
            city=None,
            country=None,
        )
        assert is_dup is False
