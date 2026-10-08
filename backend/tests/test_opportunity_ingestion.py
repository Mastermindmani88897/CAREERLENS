"""
Automated integration tests for Opportunity Ingestion Service (Phase 14).
Covers CSV parsing, skill normalization, deduplication, error handling,
opportunity type classification, and synthetic dataset loading.
"""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.session import async_session_factory
from app.models.enums import EmploymentType, OpportunityType
from app.models.opportunity import Opportunity
from app.schemas.opportunity import RawOpportunityRow
from app.services.opportunity_ingest_service import (
    ingest_csv_content,
    ingest_raw_records,
)
from app.services.opportunity_skill_normalizer import (
    normalize_opportunity_skills,
    normalize_skill_name,
)


def test_canonical_skill_name_mapping():
    """Verify deterministic canonical skill mapping."""
    assert normalize_skill_name("postgres") == "PostgreSQL"
    assert normalize_skill_name("postgresql") == "PostgreSQL"
    assert normalize_skill_name("k8s") == "Kubernetes"
    assert normalize_skill_name("kubernetes") == "Kubernetes"
    assert normalize_skill_name("react.js") == "React"
    assert normalize_skill_name("fastapi") == "FastAPI"
    assert normalize_skill_name("docker") == "Docker"
    assert normalize_skill_name("custom-tool-123") == "custom-tool-123"


def test_normalize_opportunity_skills_required_and_preferred():
    """Verify skill normalization separates required vs preferred and avoids duplicates."""
    req_input = "python, postgres, docker, fastAPI"
    pref_input = "kubernetes, docker, redis"  # docker is already in required

    req_list, pref_list, tuples = normalize_opportunity_skills(req_input, pref_input)

    assert "Python" in req_list
    assert "PostgreSQL" in req_list
    assert "Docker" in req_list
    assert "FastAPI" in req_list

    # Docker must not be repeated in preferred
    assert "Docker" not in pref_list
    assert "Kubernetes" in pref_list
    assert "Redis" in pref_list

    # Verify tuple flags
    tuple_dict = dict(tuples)
    assert tuple_dict["Docker"] is True
    assert tuple_dict["Kubernetes"] is False


@pytest.mark.asyncio
async def test_csv_ingestion_valid_and_creates_records():
    """Verify ingesting a valid CSV creates Opportunity and OpportunitySkill records."""
    s1 = f"test_csv_1_{uuid.uuid4().hex[:6]}"
    s2 = f"test_csv_2_{uuid.uuid4().hex[:6]}"
    s3 = f"test_csv_3_{uuid.uuid4().hex[:6]}"

    header = (
        "title,company,description,opportunity_type,work_mode,employment_type,"
        "salary_min,salary_max,salary_currency,required_skills,preferred_skills,source,source_id"
    )
    row1 = (
        "Cloud Systems Engineer,Nova Corp,Build resilient cloud backend.,job,hybrid,fulltime,"
        f'140000,180000,USD,"python, postgres","k8s",synthetic,{s1}'
    )
    row2 = (
        "AI Research Intern,Brain Labs,Explore neural architectures.,internship,onsite,internship,"
        f'30000,45000,INR,"python, pytorch","git",synthetic,{s2}'
    )
    row3 = (
        "Open Web Hackathon,Web Alliance,48 hour web security challenge.,hackathon,remote,any,"
        f'0,10000,USD,"python, cryptography","docker",synthetic,{s3}'
    )
    csv_data = "\n".join([header, row1, row2, row3])
    async with async_session_factory() as session:
        result = await ingest_csv_content(session, csv_data)

        assert result.total == 3
        assert result.created == 3
        assert result.skipped_duplicates == 0
        assert len(result.errors) == 0

    # Verify records in database
    async with async_session_factory() as session:
        stmt = (
            select(Opportunity)
            .options(selectinload(Opportunity.skills))
            .where(Opportunity.source_id.in_([s1, s2, s3]))
            .order_by(Opportunity.source_id)
        )
        res = await session.execute(stmt)
        opps = res.scalars().all()
        assert len(opps) == 3

        # Check Job
        opp_job = next(o for o in opps if o.source_id == s1)
        assert opp_job.opportunity_type == OpportunityType.JOB
        assert opp_job.employment_type == EmploymentType.FULLTIME
        assert opp_job.salary_min == 140000
        skills_job = {s.skill_name: s.is_required for s in opp_job.skills}
        assert skills_job.get("PostgreSQL") is True
        assert skills_job.get("Kubernetes") is False

        # Check Internship
        opp_intern = next(o for o in opps if o.source_id == s2)
        assert opp_intern.opportunity_type == OpportunityType.INTERNSHIP
        assert opp_intern.employment_type == EmploymentType.INTERNSHIP

        # Check Hackathon
        opp_hack = next(o for o in opps if o.source_id == s3)
        assert opp_hack.opportunity_type == OpportunityType.HACKATHON
        assert opp_hack.employment_type == EmploymentType.ANY


@pytest.mark.asyncio
async def test_csv_ingestion_duplicate_handling():
    """Verify duplicate records with identical source and source_id are skipped."""
    sid = f"test_dup_{uuid.uuid4().hex[:6]}"
    csv_data = f"""title,company,description,opportunity_type,source,source_id
DevOps Engineer,Orbit Tech,Manage pipelines.,job,synthetic,{sid}
DevOps Engineer Duplicate,Orbit Tech,Duplicate posting.,job,synthetic,{sid}
"""
    async with async_session_factory() as session:
        result = await ingest_csv_content(session, csv_data)
        assert result.total == 2
        assert result.created == 1
        assert result.skipped_duplicates == 1


@pytest.mark.asyncio
async def test_csv_ingestion_empty_and_malformed():
    """Verify empty and headerless CSV return appropriate error results."""
    async with async_session_factory() as session:
        empty_res = await ingest_csv_content(session, "")
        assert empty_res.total == 0
        assert len(empty_res.errors) > 0

        header_only_res = await ingest_csv_content(session, "title,company,description\n")
        assert header_only_res.total == 0


@pytest.mark.asyncio
async def test_ingest_raw_records_validation_errors():
    """Verify raw rows with missing mandatory fields report errors without crashing."""
    raw_rows = [
        RawOpportunityRow(title="", company="Acme", description="Missing title"),
        RawOpportunityRow(title="Engineer", company="", description="Missing company"),
        RawOpportunityRow(title="Engineer", company="Acme", description=""),
    ]
    async with async_session_factory() as session:
        result = await ingest_raw_records(session, raw_rows)
        assert result.total == 3
        assert result.created == 0
        assert len(result.errors) == 3


@pytest.mark.asyncio
async def test_synthetic_csv_file_ingestion():
    """Verify the project sample file data/sample/opportunities_synthetic.csv ingests cleanly."""
    csv_path = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "sample"
        / "opportunities_synthetic.csv"
    )
    assert csv_path.is_file(), f"Expected synthetic CSV file at {csv_path}"

    content = csv_path.read_text(encoding="utf-8")
    # Clean previously inserted synthetic records from test DB to guarantee idempotence
    async with async_session_factory() as session:
        await session.execute(delete(Opportunity).where(Opportunity.source_id.like("syn_%")))
        await session.commit()

    async with async_session_factory() as session:
        result = await ingest_csv_content(session, content)
        # Synthetic CSV has 14 rows, 1 intentional duplicate -> 13 created, 1 skipped
        assert result.total == 14
        assert result.created >= 12
        assert result.skipped_duplicates >= 1
        assert len(result.errors) == 0
