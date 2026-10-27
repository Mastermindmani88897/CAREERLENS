"""
Phase 26.6 End-to-End Verification and Multi-Platform Sourcing Acceptance Suite.

Validates:
1. Multi-platform opportunity ingestion and persistence across all 8 connector types.
2. Ingestion of coding contests with event-specific dates and duration.
3. Deduplication and idempotency (running ingestion twice produces zero duplicates).
4. Non-destructive field updates (missing optional fields do not overwrite stored data).
5. Automatic embedding generation and vector persistence.
6. Compatibility with Opportunity Discovery API (filtering, type lookup, text search).
7. Compatibility with Recommendation and Hybrid Matching Engine.
8. Persistent synchronization checkpoints, distributed locking, and stale claim recovery.
9. Connector Status API (GET /status) and Manual Sync (POST /{source}/sync) with admin auth.
10. Secret redaction and zero credential leakage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import ConnectorSyncStatus
from app.models.enums import OpportunitySource, OpportunityType
from app.models.opportunity import Opportunity
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.base import (
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.connectors.checkpoint import (
    ALL_REGISTERED_SOURCES,
    acquire_connector_claim,
    ensure_connector_status_rows,
    release_connector_claim,
)
from app.services.opportunity_ingest_service import ingest_raw_records
from tests.factories.candidate_factory import CandidateProfileFactory
from tests.helpers.auth import create_authenticated_headers, create_test_user


def _build_sample_wave_records(test_uuid: str) -> list[RawOpportunityRow]:
    """Generate 8 distinct sample records representing all 8 connector platforms."""
    return [
        RawOpportunityRow(
            title=f"Senior Python Engineer - {test_uuid}",
            company="Remotive Global Tech",
            description="Remote backend engineer specializing in FastAPI and PostgreSQL.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="remote",
            location_country="United States",
            salary_min=130000,
            salary_max=160000,
            salary_currency="USD",
            job_url=f"https://remotive.com/jobs/python-{test_uuid}",
            source=OpportunitySource.REMOTIVE.value,
            source_id=f"remotive-{test_uuid}",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
        ),
        RawOpportunityRow(
            title=f"DevOps Platform Engineer - {test_uuid}",
            company="Arbeitnow Enterprise",
            description="Kubernetes, Terraform, and CI/CD pipelines in Berlin.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="hybrid",
            location_city="Berlin",
            location_country="Germany",
            salary_min=75000,
            salary_max=95000,
            salary_currency="EUR",
            job_url=f"https://arbeitnow.com/jobs/devops-{test_uuid}",
            source=OpportunitySource.ARBEITNOW.value,
            source_id=f"arbeitnow-{test_uuid}",
            required_skills=["Docker", "Kubernetes", "Terraform"],
        ),
        RawOpportunityRow(
            title=f"Codeforces Global Round {test_uuid[:6]}",
            company="Codeforces",
            organization="Codeforces",
            description="Competitive programming contest featuring algorithmic problems.",
            opportunity_type="coding_contest",
            work_mode="remote",
            event_start_time=datetime.now(UTC) + timedelta(days=2),
            event_end_time=datetime.now(UTC) + timedelta(days=2, hours=2),
            duration_seconds=7200,
            job_url=f"https://codeforces.com/contest/{test_uuid[:6]}",
            source=OpportunitySource.CODEFORCES.value,
            source_id=f"cf-{test_uuid}",
            required_skills=["Algorithms", "Data Structures", "C++"],
        ),
        RawOpportunityRow(
            title=f"Backend Software Architect - {test_uuid}",
            company="Greenhouse Partner Corp",
            description="Distributed microservices architecture on AWS cloud.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="remote",
            job_url=f"https://boards.greenhouse.io/partner/jobs/{test_uuid}",
            application_url=f"https://boards.greenhouse.io/partner/jobs/{test_uuid}/apply",
            source=OpportunitySource.GREENHOUSE.value,
            source_id=f"gh-{test_uuid}",
            required_skills=["Python", "Architecture", "AWS"],
        ),
        RawOpportunityRow(
            title=f"Data Scientist ML Engineer - {test_uuid}",
            company="Adzuna Analytics",
            description="Machine learning model training and inference pipelines.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="remote",
            salary_min=120000,
            salary_max=150000,
            salary_currency="USD",
            job_url=f"https://adzuna.com/land/ad/{test_uuid}",
            source=OpportunitySource.ADZUNA.value,
            source_id=f"adzuna-{test_uuid}",
            required_skills=["Python", "Machine Learning", "PyTorch"],
        ),
        RawOpportunityRow(
            title=f"Cybersecurity Specialist - {test_uuid}",
            company="USAJOBS Federal Agency",
            organization="Department of Technology",
            description="Federal information security compliance and vulnerability analysis.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="remote",
            salary_min=95000,
            salary_max=125000,
            salary_currency="USD",
            job_url=f"https://usajobs.gov/job/{test_uuid}",
            application_url=f"https://usajobs.gov/job/{test_uuid}",
            source=OpportunitySource.USAJOBS.value,
            source_id=f"usajobs-{test_uuid}",
            required_skills=["Cybersecurity", "Network Security", "Compliance"],
        ),
        RawOpportunityRow(
            title=f"Site Reliability Engineer - {test_uuid}",
            company="Lever Hosted Systems",
            description="Infrastructure monitoring, incident response, and automation.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="remote",
            job_url=f"https://jobs.lever.co/systems/{test_uuid}",
            application_url=f"https://jobs.lever.co/systems/{test_uuid}/apply",
            source=OpportunitySource.LEVER.value,
            source_id=f"lever-{test_uuid}",
            required_skills=["Linux", "Kubernetes", "Prometheus"],
        ),
        RawOpportunityRow(
            title=f"Full Stack TypeScript Developer - {test_uuid}",
            company="RemoteOK Distributed Team",
            description="React frontend and Node/FastAPI backend engineering.",
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="remote",
            salary_min=100000,
            salary_max=130000,
            salary_currency="USD",
            job_url=f"https://remoteok.com/remote-jobs/{test_uuid}",
            application_url=f"https://remoteok.com/remote-jobs/{test_uuid}",
            source=OpportunitySource.REMOTEOK.value,
            source_id=f"remoteok-{test_uuid}",
            required_skills=["TypeScript", "React", "Node.js"],
        ),
    ]


# ---------------------------------------------------------------------------
# 1. End-to-End Ingestion, Persistence, and Deduplication Verification
# ---------------------------------------------------------------------------
class TestE2EMultiPlatformIngestionAndPersistence:
    """Validate full multi-platform record ingestion into PostgreSQL with pgvector embeddings."""

    async def test_all_eight_sources_persist_correctly(self, db_session: AsyncSession) -> None:
        test_uuid = uuid.uuid4().hex[:8]
        raw_records = _build_sample_wave_records(test_uuid)

        # 1. Ingest all 8 records
        result = await ingest_raw_records(db_session, raw_records)
        assert result.created == 8
        assert result.skipped_duplicates == 0
        assert len(result.errors) == 0

        # 2. Confirm records exist in PostgreSQL
        for r in raw_records:
            stmt = select(Opportunity).where(
                Opportunity.source == r.source,
                Opportunity.source_id == r.source_id,
            )
            opp = (await db_session.execute(stmt)).scalar_one_or_none()
            assert opp is not None
            assert opp.title == r.title
            assert opp.company == r.company
            assert opp.job_url == r.job_url

            # Verify embedding generation
            assert opp.job_embedding is not None

            # Verify contest event fields
            if opp.source == OpportunitySource.CODEFORCES.value:
                assert opp.opportunity_type == OpportunityType.CODING_CONTEST
                assert opp.event_start_time is not None
                assert opp.duration_seconds == 7200

    async def test_deduplication_is_idempotent(self, db_session: AsyncSession) -> None:
        """Running identical ingestion twice produces 0 new records and 8 skipped duplicates."""
        test_uuid = uuid.uuid4().hex[:8]
        raw_records = _build_sample_wave_records(test_uuid)

        # First run: 8 created
        res1 = await ingest_raw_records(db_session, raw_records)
        assert res1.created == 8

        # Second run: 0 created, 8 duplicates skipped
        res2 = await ingest_raw_records(db_session, raw_records)
        assert res2.created == 0
        assert res2.skipped_duplicates == 8
        assert len(res2.errors) == 0

    async def test_missing_optional_fields_do_not_destroy_data(
        self, db_session: AsyncSession
    ) -> None:
        """Confirm that subsequent updates with missing fields preserve existing stored values."""
        test_uuid = uuid.uuid4().hex[:8]
        initial = RawOpportunityRow(
            title=f"Lead Architect - {test_uuid}",
            company="Preservation Corp",
            description="High salary position with rich metadata.",
            salary_min=180000,
            salary_max=220000,
            salary_currency="USD",
            location_city="San Francisco",
            location_country="United States",
            job_url=f"https://example.com/jobs/{test_uuid}",
            source=OpportunitySource.REMOTIVE.value,
            source_id=f"preserve-{test_uuid}",
            required_skills=["Python", "Cloud"],
        )
        await ingest_raw_records(db_session, [initial])

        # Second ingestion with salary_min=None and location_city=None
        sparse_update = RawOpportunityRow(
            title=f"Lead Architect - {test_uuid}",
            company="Preservation Corp",
            description="Updated description with missing salary and city fields.",
            salary_min=None,
            salary_max=None,
            location_city=None,
            source=OpportunitySource.REMOTIVE.value,
            source_id=f"preserve-{test_uuid}",
        )
        res = await ingest_raw_records(db_session, [sparse_update])
        # Treated as duplicate/skipped rather than destructive overwrite
        assert res.skipped_duplicates == 1

        # Verify initial values are preserved in DB
        stmt = select(Opportunity).where(
            Opportunity.source == OpportunitySource.REMOTIVE.value,
            Opportunity.source_id == f"preserve-{test_uuid}",
        )
        opp = (await db_session.execute(stmt)).scalar_one()
        assert opp.salary_min == 180000
        assert opp.location_city == "San Francisco"


# ---------------------------------------------------------------------------
# 2. Opportunity Discovery & Recommendation Integration Verification
# ---------------------------------------------------------------------------
class TestE2EDiscoveryAndRecommendationIntegration:
    """Validate that ingested multi-platform opportunities integrate seamlessly into APIs."""

    async def test_discovery_filtering_by_type_and_source(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        test_uuid = uuid.uuid4().hex[:8]
        raw_records = _build_sample_wave_records(test_uuid)
        await ingest_raw_records(db_session, raw_records)

        # Create user to authenticate for discovery API
        user, _ = await create_test_user(db_session)
        await db_session.commit()
        headers = create_authenticated_headers(user.id)

        # Query coding contest via discovery API
        resp = await async_client.get(
            "/api/v1/opportunities/?opportunity_type=coding_contest",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        contest_items = [item for item in data["items"] if item["source_id"] == f"cf-{test_uuid}"]
        assert len(contest_items) == 1
        contest = contest_items[0]
        assert contest["opportunity_type"] == "coding_contest"
        assert contest["source"] == OpportunitySource.CODEFORCES.value
        assert contest["duration_seconds"] == 7200

        # Query Remotive source via discovery API
        resp_remotive = await async_client.get(
            f"/api/v1/opportunities/?source={OpportunitySource.REMOTIVE.value}",
            headers=headers,
        )
        assert resp_remotive.status_code == 200
        remotive_data = resp_remotive.json()
        assert any(it["source_id"] == f"remotive-{test_uuid}" for it in remotive_data["items"])

    async def test_recommendation_matching_engine_evaluates_ingested_opportunities(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Verify candidate profile matching against multi-platform ingested opportunities."""
        test_uuid = uuid.uuid4().hex[:8]
        raw_records = _build_sample_wave_records(test_uuid)
        await ingest_raw_records(db_session, raw_records)

        # Create a candidate profile skilled in Python and FastAPI
        user, _ = await create_test_user(db_session)
        await CandidateProfileFactory.create(
            db_session,
            user_id=user.id,
            headline="Senior Python Developer",
        )
        await db_session.commit()

        # Retrieve the ingested Remotive opportunity
        stmt = select(Opportunity).where(
            Opportunity.source == OpportunitySource.REMOTIVE.value,
            Opportunity.source_id == f"remotive-{test_uuid}",
        )
        opp = (await db_session.execute(stmt)).scalar_one()

        # Evaluate match via the matching API endpoint
        headers = create_authenticated_headers(user.id)
        resp = await async_client.post(
            "/api/v1/matches/",
            json={"opportunity_id": str(opp.id)},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["opportunity_id"] == str(opp.id)
        assert data["final_score"] >= 0.0
        assert data["score_breakdown"] is not None


# ---------------------------------------------------------------------------
# 3. Persistent Checkpoints, Locking & Stale Recovery Verification
# ---------------------------------------------------------------------------
class TestE2ECheckpointPersistenceAndLocking:
    """Validate database claim locks, stale crash recovery, and outcome persistence."""

    async def test_multi_worker_claim_locking(self, db_session: AsyncSession) -> None:
        """Worker A acquires claim; Worker B is blocked from overlapping execution."""
        await ensure_connector_status_rows(db_session, ["adzuna"])

        # Reset to idle
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "adzuna")
        row = (await db_session.execute(stmt)).scalar_one()
        row.sync_state = {"current_status": "idle"}
        row.is_enabled = True
        await db_session.commit()

        # Worker A acquires claim
        acquired_a, msg_a = await acquire_connector_claim(
            db_session, "adzuna", worker_id="worker-node-1"
        )
        assert acquired_a is True

        # Worker B attempts claim simultaneously -> rejected
        acquired_b, msg_b = await acquire_connector_claim(
            db_session, "adzuna", worker_id="worker-node-2"
        )
        assert acquired_b is False
        assert "already running" in msg_b.lower()

        # Worker A completes run -> updates status
        summary = ConnectorRunSummary(
            source="adzuna",
            status=ConnectorStatus.SUCCESS,
            records_fetched=20,
            ingest_result_created=15,
            ingest_result_skipped=5,
            duration_seconds=1.2,
        )
        updated_row = await release_connector_claim(db_session, summary)
        assert updated_row.last_successful_sync_at is not None
        assert (updated_row.sync_state or {}).get("current_status") == "success"

        # Worker B can now acquire claim after Worker A finishes
        acquired_b_retry, _ = await acquire_connector_claim(
            db_session, "adzuna", worker_id="worker-node-2"
        )
        assert acquired_b_retry is True

        # Clean up by releasing Worker B claim
        await release_connector_claim(
            db_session,
            ConnectorRunSummary(source="adzuna", status=ConnectorStatus.SUCCESS),
        )

    async def test_stale_claim_recovery_after_worker_crash(self, db_session: AsyncSession) -> None:
        """Crashed worker lock older than stale threshold is reclaimed automatically."""
        await ensure_connector_status_rows(db_session, ["usajobs"])

        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "usajobs")
        row = (await db_session.execute(stmt)).scalar_one()
        row.is_enabled = True
        row.sync_state = {"current_status": "running", "worker_id": "crashed-pod-99"}
        # Lock acquired 60 minutes ago (stale timeout = 30 mins)
        row.last_sync_started_at = datetime.now(UTC) - timedelta(minutes=60)
        await db_session.commit()

        # New worker detects stale claim and recovers
        acquired, msg = await acquire_connector_claim(
            db_session, "usajobs", stale_lock_minutes=30, worker_id="healthy-pod-01"
        )
        assert acquired is True
        assert "Claim acquired" in msg

        await db_session.refresh(row)
        assert (row.sync_state or {}).get("worker_id") == "healthy-pod-01"

        # Release claim
        await release_connector_claim(
            db_session,
            ConnectorRunSummary(source="usajobs", status=ConnectorStatus.SUCCESS),
        )


# ---------------------------------------------------------------------------
# 4. Connector Status API & Secret Non-Leakage Verification
# ---------------------------------------------------------------------------
class TestE2EConnectorStatusApiVerification:
    """Validate administrative status endpoints, role authorization, and secret redaction."""

    async def test_status_endpoint_returns_all_eight_connectors(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_user, _ = await create_test_user(db_session, is_admin=True)
        await db_session.commit()

        headers = create_authenticated_headers(admin_user.id)
        resp = await async_client.get("/api/v1/connectors/status", headers=headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["total_connectors"] == 8
        returned_sources = {c["source"] for c in data["connectors"]}
        for src in ALL_REGISTERED_SOURCES:
            assert src in returned_sources

        # Strict secret redaction assertion: zero credentials in response body
        raw_body = resp.text
        assert "password" not in raw_body.lower()
        assert "app_id=" not in raw_body
        assert "app_key=" not in raw_body
        assert "api_key=" not in raw_body
        assert "jwt_secret" not in raw_body.lower()

    async def test_manual_trigger_executes_and_returns_clean_telemetry(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_user, _ = await create_test_user(db_session, is_admin=True)
        await ensure_connector_status_rows(db_session, ["remotive"])

        # Reset remotive to idle in case a previous test left it running
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.sync_state = {"current_status": "idle"}
        row.is_enabled = True
        await db_session.commit()

        headers = create_authenticated_headers(admin_user.id)
        mock_summary = ConnectorRunSummary(
            source="remotive",
            status=ConnectorStatus.SUCCESS,
            records_fetched=10,
            ingest_result_created=5,
        )
        with patch(
            "app.services.connectors.remotive.RemotiveConnector.run",
            new=AsyncMock(return_value=([], mock_summary)),
        ):
            resp = await async_client.post("/api/v1/connectors/remotive/sync", headers=headers)
            assert resp.status_code == 200

            data = resp.json()
            assert data["source"] == "remotive"
            assert data["status"] in ("success", "partial", "failed", "skipped")
            assert "summary" in data
            assert "records_fetched" in data["summary"]
            assert "records_created" in data["summary"]
