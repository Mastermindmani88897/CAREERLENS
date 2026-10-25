"""
Phase 26.2 Regression and Verification Tests.
Validates:
1. OpportunityType enum extension ('coding_contest').
2. OpportunitySource enum extension (platform sources: Remotive, Arbeitnow, Codeforces, etc.).
3. Normalization logic for contests, flexible datetimes, and platform sources.
4. Backward compatibility with existing opportunity types, sources, and null event fields.
5. ConnectorSyncStatus ORM model constraints, telemetry defaults, and unique index.
6. Ingestion, persistence, and deduplication of contests and event metadata.
7. Matching and application tracking compatibility with new opportunity types and sources.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile
from app.models.connector import ConnectorSyncStatus
from app.models.enums import (
    ApplicationStatus,
    EmploymentType,
    OpportunitySource,
    OpportunityType,
)
from app.models.opportunity import Opportunity
from app.models.tracking import Application
from app.schemas.opportunity import RawOpportunityRow
from app.services.opportunity_ingest_service import ingest_raw_records, parse_csv_to_raw_rows
from app.services.opportunity_normalizer import (
    normalize_employment_type,
    normalize_opportunity_type,
    normalize_source,
    parse_flexible_datetime,
)


def test_enum_opportunity_type_coding_contest() -> None:
    """Verify coding_contest is present in OpportunityType enum alongside existing types."""
    assert OpportunityType.CODING_CONTEST.value == "coding_contest"
    assert OpportunityType.JOB.value == "job"
    assert OpportunityType.INTERNSHIP.value == "internship"
    assert OpportunityType.HACKATHON.value == "hackathon"


def test_enum_opportunity_sources_multi_platform() -> None:
    """Verify planned platform sources are present alongside synthetic, manual, and api."""
    assert OpportunitySource.SYNTHETIC.value == "synthetic"
    assert OpportunitySource.MANUAL.value == "manual"
    assert OpportunitySource.API.value == "api"

    expected_platforms = {
        "remotive": OpportunitySource.REMOTIVE,
        "arbeitnow": OpportunitySource.ARBEITNOW,
        "codeforces": OpportunitySource.CODEFORCES,
        "greenhouse": OpportunitySource.GREENHOUSE,
        "lever": OpportunitySource.LEVER,
        "adzuna": OpportunitySource.ADZUNA,
        "usajobs": OpportunitySource.USAJOBS,
        "remoteok": OpportunitySource.REMOTEOK,
        "devpost": OpportunitySource.DEVPOST,
    }
    for val_str, enum_val in expected_platforms.items():
        assert enum_val.value == val_str


def test_normalizer_contest_and_sources() -> None:
    """Verify normalization mapping for coding contests and platform sources."""
    assert normalize_opportunity_type("coding_contest") == OpportunityType.CODING_CONTEST
    assert normalize_opportunity_type("contest") == OpportunityType.CODING_CONTEST
    assert normalize_opportunity_type("programming contest") == OpportunityType.CODING_CONTEST
    assert normalize_opportunity_type("competitive programming") == OpportunityType.CODING_CONTEST
    assert normalize_opportunity_type("coding competition") == OpportunityType.CODING_CONTEST

    # Contests default to employment type ANY
    assert normalize_employment_type(None, OpportunityType.CODING_CONTEST) == EmploymentType.ANY

    # Platform source normalization
    assert normalize_source("codeforces") == OpportunitySource.CODEFORCES
    assert normalize_source("CodeForces") == OpportunitySource.CODEFORCES
    assert normalize_source("REMOTIVE") == OpportunitySource.REMOTIVE
    assert normalize_source("greenhouse") == OpportunitySource.GREENHOUSE
    assert normalize_source("unknown_xyz") == OpportunitySource.MANUAL  # Fallback


def test_parse_flexible_datetime() -> None:
    """Verify datetime parser handles ISO strings, UNIX timestamps, and naive dates."""
    # ISO string with UTC Z
    dt1 = parse_flexible_datetime("2026-11-15T14:30:00Z")
    assert dt1 is not None
    assert dt1.year == 2026 and dt1.month == 11 and dt1.day == 15
    assert dt1.tzinfo is not None

    # Epoch timestamp in seconds
    dt2 = parse_flexible_datetime(1795000000)
    assert dt2 is not None
    assert dt2.tzinfo is not None

    # Epoch timestamp as string
    dt3 = parse_flexible_datetime("1795000000")
    assert dt3 is not None

    # Invalid string
    assert parse_flexible_datetime("not-a-date") is None
    assert parse_flexible_datetime(None) is None


@pytest.mark.asyncio
async def test_connector_sync_status_model_persistence(db_session: AsyncSession) -> None:
    """Verify ConnectorSyncStatus model creation, defaults, unique constraint, and updates."""
    unique_src = f"source_{uuid.uuid4().hex[:8]}"
    status = ConnectorSyncStatus(
        id=uuid.uuid4(),
        source=unique_src,
        is_enabled=True,
        refresh_interval_minutes=30,
        sync_state={"last_cursor": 12345},
    )
    db_session.add(status)
    await db_session.commit()

    # Query back
    result = await db_session.execute(
        select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == unique_src)
    )
    fetched = result.scalar_one()
    assert fetched.source == unique_src
    assert fetched.is_enabled is True
    assert fetched.refresh_interval_minutes == 30
    assert fetched.total_fetched == 0
    assert fetched.consecutive_failures == 0
    assert fetched.sync_state == {"last_cursor": 12345}

    # Update operational telemetry
    fetched.total_fetched = 25
    fetched.total_created = 15
    fetched.last_sync_completed_at = datetime.now(UTC)
    await db_session.commit()

    result2 = await db_session.execute(
        select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == unique_src)
    )
    updated = result2.scalar_one()
    assert updated.total_fetched == 25
    assert updated.total_created == 15
    assert updated.last_sync_completed_at is not None

    # Verify unique constraint on source
    duplicate = ConnectorSyncStatus(
        id=uuid.uuid4(),
        source=unique_src,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_opportunity_event_metadata_persistence(db_session: AsyncSession) -> None:
    """Verify persisting opportunity with contest type, platform source, and event fields."""
    event_start = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
    event_end = datetime(2026, 11, 20, 17, 0, tzinfo=UTC)
    reg_deadline = date(2026, 11, 19)
    unique_id = uuid.uuid4().hex[:8]

    opp = Opportunity(
        id=uuid.uuid4(),
        opportunity_type=OpportunityType.CODING_CONTEST,
        title=f"Codeforces Global Round {unique_id}",
        company="Codeforces",
        description="Competitive programming round featuring 8 algorithmic challenges.",
        source=OpportunitySource.CODEFORCES,
        source_id=f"cf-gr-{unique_id}",
        job_url=f"https://codeforces.com/contest/{unique_id}",
        event_start_time=event_start,
        event_end_time=event_end,
        registration_deadline=reg_deadline,
        duration_seconds=7200,
        prize_summary="$5,000 Prize Pool and Rating Points",
        external_metadata={"contest_id": 9999, "phase": "BEFORE", "type": "CF"},
        employment_type=EmploymentType.ANY,
        is_active=True,
    )
    db_session.add(opp)
    await db_session.commit()

    # Query back
    result = await db_session.execute(select(Opportunity).where(Opportunity.id == opp.id))
    persisted = result.scalar_one()
    assert persisted.opportunity_type == OpportunityType.CODING_CONTEST
    assert persisted.source == OpportunitySource.CODEFORCES
    assert persisted.duration_seconds == 7200
    assert persisted.prize_summary == "$5,000 Prize Pool and Rating Points"
    assert persisted.external_metadata == {"contest_id": 9999, "phase": "BEFORE", "type": "CF"}
    assert persisted.event_start_time == event_start
    assert persisted.event_end_time == event_end
    assert persisted.registration_deadline == reg_deadline
    assert persisted.first_seen_at is not None
    assert persisted.last_seen_at is not None


@pytest.mark.asyncio
async def test_backward_compatibility_existing_job_records(db_session: AsyncSession) -> None:
    """Verify legacy job and internship records persist with null event fields."""
    unique_id = uuid.uuid4().hex[:8]
    legacy_job = Opportunity(
        id=uuid.uuid4(),
        opportunity_type=OpportunityType.JOB,
        title=f"Senior Python Engineer {unique_id}",
        company="TechCorp Inc",
        description="Senior backend engineer specializing in FastAPI and PostgreSQL.",
        source=OpportunitySource.MANUAL,
        source_id=f"manual-{unique_id}",
        is_active=True,
    )
    db_session.add(legacy_job)
    await db_session.commit()

    result = await db_session.execute(select(Opportunity).where(Opportunity.id == legacy_job.id))
    fetched = result.scalar_one()
    assert fetched.opportunity_type == OpportunityType.JOB
    assert fetched.source == OpportunitySource.MANUAL
    assert fetched.event_start_time is None
    assert fetched.event_end_time is None
    assert fetched.registration_deadline is None
    assert fetched.duration_seconds is None
    assert fetched.prize_summary is None
    assert fetched.external_metadata == {}
    assert fetched.first_seen_at is not None
    assert fetched.last_seen_at is not None


@pytest.mark.asyncio
async def test_opportunity_ingestion_and_deduplication_with_contest(
    db_session: AsyncSession,
) -> None:
    """Verify ingest_raw_records normalizes and deduplicates contests with platform sources."""
    unique_suffix = uuid.uuid4().hex[:8]
    raw_record = RawOpportunityRow(
        title=f"Algorithmic Sprint {unique_suffix}",
        company="Codeforces",
        description="Two-hour contest covering dynamic programming and graphs.",
        opportunity_type="coding_contest",
        source="codeforces",
        source_id=f"cf-sprint-{unique_suffix}",
        job_url=f"https://codeforces.com/contest/{unique_suffix}",
        event_start_time="2026-12-01T10:00:00Z",
        event_end_time="2026-12-01T12:00:00Z",
        registration_deadline="2026-11-30",
        duration_seconds=7200,
        prize_summary="T-shirts and badges",
        external_metadata={"sprint_id": unique_suffix},
    )

    result = await ingest_raw_records(db_session, [raw_record])
    assert result.created == 1
    assert result.skipped_duplicates == 0
    assert len(result.errors) == 0

    # Ingest the same record again -> should be skipped as duplicate
    dup_result = await ingest_raw_records(db_session, [raw_record])
    assert dup_result.created == 0
    assert dup_result.skipped_duplicates == 1


def test_csv_parsing_with_event_metadata() -> None:
    """Verify parse_csv_to_raw_rows extracts event metadata columns."""
    csv_text = (
        "title,company,description,opportunity_type,source,source_id,duration_seconds,prize_summary\n"
        "Winter Hackathon,Global Dev,Build next-gen AI tools,hackathon,devpost,dp-1,"
        "86400,$10k prizes\n"
    )
    raw_rows = parse_csv_to_raw_rows(csv_text)
    assert len(raw_rows) == 1
    row = raw_rows[0]
    assert row.title == "Winter Hackathon"
    assert row.company == "Global Dev"
    assert row.opportunity_type == "hackathon"
    assert row.source == "devpost"
    assert row.source_id == "dp-1234"
    assert str(row.duration_seconds) == "86400"
    assert row.prize_summary == "$10k prizes"


@pytest.mark.asyncio
async def test_matching_and_application_tracking_compatibility(
    db_session: AsyncSession,
) -> None:
    """Verify candidate application tracking works with new contest opportunity type."""
    # 1. Create a contest opportunity
    opp = Opportunity(
        id=uuid.uuid4(),
        opportunity_type=OpportunityType.CODING_CONTEST,
        title="Spring Coding Cup 2026",
        company="Codeforces",
        description="Competitive programming championship.",
        source=OpportunitySource.CODEFORCES,
        source_id=f"cf-spring-{uuid.uuid4().hex[:6]}",
        employment_type=EmploymentType.ANY,
        is_active=True,
    )
    db_session.add(opp)

    # 2. Query an existing candidate profile or create one
    result = await db_session.execute(select(CandidateProfile).limit(1))
    profile = result.scalars().first()

    if profile is None:
        from app.models.user import User, UserRole

        test_user = User(
            id=uuid.uuid4(),
            email=f"candidate_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="hashed_pw_dummy",
            role=UserRole.CANDIDATE,
            is_active=True,
        )
        db_session.add(test_user)
        await db_session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=test_user.id,
            first_name="Alice",
            last_name="Coder",
        )
        db_session.add(profile)
        await db_session.flush()

    # 3. Create Application record linking profile to the contest opportunity
    application = Application(
        id=uuid.uuid4(),
        candidate_profile_id=profile.id,
        opportunity_id=opp.id,
        status=ApplicationStatus.APPLIED,
    )
    db_session.add(application)
    await db_session.commit()

    # 4. Verify application query
    app_query = await db_session.execute(
        select(Application).where(Application.id == application.id)
    )
    fetched_app = app_query.scalar_one()
    assert fetched_app.opportunity_id == opp.id
    assert fetched_app.status == ApplicationStatus.APPLIED
