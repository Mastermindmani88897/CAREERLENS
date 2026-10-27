"""
Unit and integration test suite for Phase 26.5:
Background Synchronization, Checkpoints, and Connector Status.

Tests:
1. Error sanitization and secret redaction.
2. Initialization of persistent status rows in connector_sync_status.
3. Atomic claim acquisition, overlapping run prevention, disabled rejection, stale crash recovery.
4. Release of claim with persistent telemetry updates (SUCCESS, PARTIAL, FAILED, SKIPPED).
5. Due-connector calculation and next scheduled synchronization calculation.
6. ConnectorScheduler lifecycle, bounded concurrency, timeout handling, and fault isolation.
7. ConnectorOrchestrator integration with persistent checkpoints and rollback safety.
8. Status API (GET /api/v1/connectors/status) and manual sync endpoint.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.connector import ConnectorSyncStatus
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.connectors.checkpoint import (
    ALL_REGISTERED_SOURCES,
    acquire_connector_claim,
    calculate_next_scheduled_sync,
    ensure_connector_status_rows,
    is_connector_due,
    release_connector_claim,
    sanitize_error_summary,
)
from app.services.connectors.orchestrator import ConnectorOrchestrator
from app.services.connectors.scheduler import ConnectorScheduler
from tests.helpers.auth import create_authenticated_headers, create_test_user


# ---------------------------------------------------------------------------
# Dummy Mock Connector for Scheduler & Orchestrator Testing
# ---------------------------------------------------------------------------
class DummyTestConnector(BaseOpportunityConnector):
    """Configurable mock connector for unit and integration testing."""

    source_name = "remotive"

    def __init__(
        self,
        source_name: str = "remotive",
        records: list[Any] | None = None,
        should_fail: bool = False,
        sleep_seconds: float = 0.0,
    ) -> None:
        self.source_name = source_name
        self._records = records or []
        self._should_fail = should_fail
        self._sleep_seconds = sleep_seconds

    def is_configured(self) -> bool:
        return True

    async def fetch_batch(self, cursor: Any = None) -> ConnectorBatchResult:
        if self._sleep_seconds > 0:
            await asyncio.sleep(self._sleep_seconds)
        if self._should_fail:
            raise RuntimeError(f"Simulated provider failure for {self.source_name}")
        return ConnectorBatchResult(
            records=self._records, next_cursor=None, raw_count=len(self._records)
        )


# ---------------------------------------------------------------------------
# 1. Error Sanitization & Secret Redaction Tests
# ---------------------------------------------------------------------------
class TestSanitizeErrorSummary:
    """Validate that error summaries never leak credentials, tokens, or raw secrets."""

    def test_sanitize_none_and_empty(self) -> None:
        assert sanitize_error_summary(None) is None
        assert sanitize_error_summary("") is None

    def test_sanitize_query_param_credentials(self) -> None:
        raw = "HTTP error at https://api.adzuna.com/v1/jobs?app_id=12345&app_key=secret987&what=dev"
        sanitized = sanitize_error_summary(raw)
        assert sanitized is not None
        assert "12345" not in sanitized
        assert "secret987" not in sanitized
        assert "app_id=[REDACTED]" in sanitized
        assert "app_key=[REDACTED]" in sanitized
        assert "what=dev" in sanitized

    def test_sanitize_auth_headers(self) -> None:
        raw = "Request failed: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
        sanitized = sanitize_error_summary(raw)
        assert sanitized is not None
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_usajobs_header(self) -> None:
        raw = "Failed with headers Authorization-Key: super-secret-api-key-value"
        sanitized = sanitize_error_summary(raw)
        assert sanitized is not None
        assert "super-secret-api-key-value" not in sanitized
        assert "Authorization-Key: [REDACTED]" in sanitized

    def test_sanitize_truncation(self) -> None:
        long_traceback = "Error: " + ("x" * 1000)
        sanitized = sanitize_error_summary(long_traceback, max_length=100)
        assert sanitized is not None
        assert len(sanitized) <= 100
        assert sanitized.endswith("...")


# ---------------------------------------------------------------------------
# 2. Checkpoint Initialization & Row Management Tests
# ---------------------------------------------------------------------------
class TestEnsureConnectorStatusRows:
    """Verify database initialization of connector_sync_status rows."""

    async def test_ensure_rows_creates_all_registered(self, db_session: AsyncSession) -> None:
        unique_test_source = f"test_custom_{uuid.uuid4().hex[:6]}"
        rows = await ensure_connector_status_rows(db_session, [unique_test_source])
        assert len(rows) == 1
        r = rows[0]
        assert r.source == unique_test_source
        assert r.is_enabled is True
        assert r.refresh_interval_minutes == settings.CONNECTOR_DEFAULT_REFRESH_MINUTES
        assert r.consecutive_failures == 0
        assert r.total_fetched == 0
        assert (r.sync_state or {}).get("current_status") == "idle"

        # Also ensure all standard registered sources are present
        all_rows = await ensure_connector_status_rows(db_session)
        assert len(all_rows) >= len(ALL_REGISTERED_SOURCES)
        sources = {row.source for row in all_rows}
        for src in ALL_REGISTERED_SOURCES:
            assert src in sources

    async def test_ensure_rows_is_idempotent(self, db_session: AsyncSession) -> None:
        rows1 = await ensure_connector_status_rows(db_session)
        count1 = len(rows1)

        rows2 = await ensure_connector_status_rows(db_session)
        count2 = len(rows2)

        assert count1 == count2


# ---------------------------------------------------------------------------
# 3. Atomic Claim & Overlapping-Run Prevention Tests
# ---------------------------------------------------------------------------
class TestAcquireConnectorClaim:
    """Verify exclusive claim acquisition, overlapping run prevention, and stale recovery."""

    async def test_acquire_claim_success(self, db_session: AsyncSession) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        # Reset to idle
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.sync_state = {"current_status": "idle"}
        row.is_enabled = True
        await db_session.commit()

        acquired, msg = await acquire_connector_claim(
            db_session, "remotive", worker_id="worker-test-1"
        )
        assert acquired is True
        assert "Claim acquired" in msg

        # Verify row updated in DB
        await db_session.refresh(row)
        assert (row.sync_state or {}).get("current_status") == "running"
        assert (row.sync_state or {}).get("worker_id") == "worker-test-1"
        assert row.last_sync_started_at is not None

    async def test_acquire_claim_prevents_overlapping_run(self, db_session: AsyncSession) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        # Set status to running with recent timestamp
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.sync_state = {"current_status": "running"}
        row.last_sync_started_at = datetime.now(UTC)
        row.is_enabled = True
        await db_session.commit()

        # Second attempt should be rejected
        acquired, msg = await acquire_connector_claim(
            db_session, "remotive", stale_lock_minutes=30, worker_id="worker-test-2"
        )
        assert acquired is False
        assert "already running" in msg.lower()

    async def test_acquire_claim_rejects_disabled_connector(self, db_session: AsyncSession) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.is_enabled = False
        row.sync_state = {"current_status": "idle"}
        await db_session.commit()

        acquired, msg = await acquire_connector_claim(db_session, "remotive")
        assert acquired is False
        assert "disabled" in msg.lower()

    async def test_acquire_claim_recovers_stale_lock(self, db_session: AsyncSession) -> None:
        """Simulate a crashed worker: running lock older than stale threshold is reclaimed."""
        await ensure_connector_status_rows(db_session, ["remotive"])

        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.is_enabled = True
        row.sync_state = {"current_status": "running", "worker_id": "crashed-worker"}
        # Started 45 minutes ago (older than 30-min threshold)
        row.last_sync_started_at = datetime.now(UTC) - timedelta(minutes=45)
        await db_session.commit()

        acquired, msg = await acquire_connector_claim(
            db_session, "remotive", stale_lock_minutes=30, worker_id="recovering-worker"
        )
        assert acquired is True
        assert "Claim acquired" in msg

        await db_session.refresh(row)
        assert (row.sync_state or {}).get("current_status") == "running"
        assert (row.sync_state or {}).get("worker_id") == "recovering-worker"


# ---------------------------------------------------------------------------
# 4. Release Claim & Persistent Outcome Tests
# ---------------------------------------------------------------------------
class TestReleaseConnectorClaim:
    """Verify persistence of run outcomes, failure counters, and timestamp preservation."""

    async def test_release_success_updates_success_timestamp(
        self, db_session: AsyncSession
    ) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        summary = ConnectorRunSummary(
            source="remotive",
            status=ConnectorStatus.SUCCESS,
            records_fetched=10,
            ingest_result_created=8,
            ingest_result_skipped=2,
            duration_seconds=1.5,
        )

        row = await release_connector_claim(db_session, summary)
        assert row.last_successful_sync_at is not None
        assert row.consecutive_failures == 0
        assert row.last_error_summary is None
        assert row.total_created >= 8
        assert row.total_skipped >= 2
        assert (row.sync_state or {}).get("current_status") == "success"

    async def test_release_failed_preserves_previous_success_and_increments_failures(
        self, db_session: AsyncSession
    ) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        # Seed an established successful sync timestamp
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        established_success_time = datetime.now(UTC) - timedelta(days=2)
        row.last_successful_sync_at = established_success_time
        row.consecutive_failures = 1
        await db_session.commit()

        # Run fails with a secret in error message
        summary = ConnectorRunSummary(
            source="remotive",
            status=ConnectorStatus.FAILED,
            error_message="HTTP 500 Server Error at https://api.remotive.com?api_key=secret-token-123",
            duration_seconds=0.8,
        )

        updated_row = await release_connector_claim(db_session, summary)

        # Success timestamp preserved
        assert updated_row.last_successful_sync_at == established_success_time
        # Consecutive failures incremented
        assert updated_row.consecutive_failures == 2
        # Error summary recorded and sanitized
        assert updated_row.last_error_summary is not None
        assert "secret-token-123" not in updated_row.last_error_summary
        assert "api_key=[REDACTED]" in updated_row.last_error_summary
        assert (updated_row.sync_state or {}).get("current_status") == "failed"

    async def test_release_partial_does_not_update_success_timestamp(
        self, db_session: AsyncSession
    ) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        previous_success = datetime.now(UTC) - timedelta(hours=5)
        row.last_successful_sync_at = previous_success
        await db_session.commit()

        summary = ConnectorRunSummary(
            source="remotive",
            status=ConnectorStatus.PARTIAL,
            records_fetched=10,
            ingest_result_created=5,
            ingest_result_errors=1,
            error_message="Ingestion warning: 1 malformed record skipped.",
            duration_seconds=2.0,
        )

        updated_row = await release_connector_claim(db_session, summary)
        # Success timestamp must NOT be updated for partial results
        assert updated_row.last_successful_sync_at == previous_success
        assert (updated_row.sync_state or {}).get("current_status") == "partial"


# ---------------------------------------------------------------------------
# 5. Due-Connector & Next Scheduled Sync Logic Tests
# ---------------------------------------------------------------------------
class TestDueConnectorCalculations:
    """Verify schedule evaluation and next-sync calculations."""

    def test_disabled_connector_is_not_due(self) -> None:
        row = ConnectorSyncStatus(source="test", is_enabled=False, refresh_interval_minutes=60)
        assert is_connector_due(row) is False
        assert calculate_next_scheduled_sync(row) is None

    def test_never_synced_connector_is_due(self) -> None:
        row = ConnectorSyncStatus(
            source="test",
            is_enabled=True,
            refresh_interval_minutes=60,
            last_sync_completed_at=None,
            sync_state={"current_status": "idle"},
        )
        assert is_connector_due(row) is True
        next_sync = calculate_next_scheduled_sync(row)
        assert next_sync is not None

    def test_connector_within_interval_is_not_due(self) -> None:
        now = datetime.now(UTC)
        row = ConnectorSyncStatus(
            source="test",
            is_enabled=True,
            refresh_interval_minutes=60,
            last_sync_completed_at=now - timedelta(minutes=20),
            sync_state={"current_status": "idle"},
        )
        assert is_connector_due(row, now=now) is False
        next_sync = calculate_next_scheduled_sync(row, now=now)
        assert next_sync == (now - timedelta(minutes=20)) + timedelta(minutes=60)

    def test_connector_past_interval_is_due(self) -> None:
        now = datetime.now(UTC)
        row = ConnectorSyncStatus(
            source="test",
            is_enabled=True,
            refresh_interval_minutes=60,
            last_sync_completed_at=now - timedelta(minutes=75),
            sync_state={"current_status": "idle"},
        )
        assert is_connector_due(row, now=now) is True

    def test_actively_running_connector_is_not_due(self) -> None:
        now = datetime.now(UTC)
        row = ConnectorSyncStatus(
            source="test",
            is_enabled=True,
            refresh_interval_minutes=60,
            last_sync_started_at=now - timedelta(minutes=5),
            sync_state={"current_status": "running"},
        )
        assert is_connector_due(row, stale_lock_minutes=30, now=now) is False
        assert calculate_next_scheduled_sync(row) is None

    def test_stale_running_connector_is_due_for_recovery(self) -> None:
        now = datetime.now(UTC)
        row = ConnectorSyncStatus(
            source="test",
            is_enabled=True,
            refresh_interval_minutes=60,
            last_sync_started_at=now - timedelta(minutes=45),
            sync_state={"current_status": "running"},
        )
        assert is_connector_due(row, stale_lock_minutes=30, now=now) is True


# ---------------------------------------------------------------------------
# 6. Background Scheduler Tests
# ---------------------------------------------------------------------------
class TestConnectorScheduler:
    """Verify background scheduler lifecycle, timeout protection, and concurrency."""

    async def test_scheduler_start_and_graceful_stop(self) -> None:
        scheduler = ConnectorScheduler(interval_seconds=10, max_concurrency=2)
        assert scheduler.is_running is False

        await scheduler.start()
        assert scheduler.is_running is True

        await scheduler.stop(timeout=2.0)
        assert scheduler.is_running is False

    async def test_scheduler_times_out_hanging_connector(self, db_session: AsyncSession) -> None:
        """A connector that hangs beyond timeout must be aborted without crashing scheduler."""
        hanging_connector = DummyTestConnector(
            source_name="remotive",
            sleep_seconds=10.0,
        )

        scheduler = ConnectorScheduler(
            session_factory=async_session_factory,
            timeout_seconds=1,
            max_concurrency=1,
        )

        with patch(
            "app.services.connectors.scheduler.get_all_connectors",
            return_value=[hanging_connector],
        ):
            summary = await scheduler._run_single_connector(hanging_connector)
            assert summary.status == ConnectorStatus.FAILED
            assert "timed out" in (summary.error_message or "").lower()

    async def test_scheduler_continues_when_one_connector_fails(self) -> None:
        """Failures in one connector must not abort sibling connectors."""
        failing_connector = DummyTestConnector(source_name="arbeitnow", should_fail=True)
        successful_connector = DummyTestConnector(source_name="codeforces", records=[])

        scheduler = ConnectorScheduler(
            session_factory=async_session_factory,
            max_concurrency=2,
        )

        with patch(
            "app.services.connectors.scheduler.ConnectorScheduler.get_due_connectors",
            new=AsyncMock(return_value=[failing_connector, successful_connector]),
        ):
            summaries = await scheduler.run_due_connectors()
            assert len(summaries) == 2
            statuses = {s.source: s.status for s in summaries}
            assert statuses["arbeitnow"] == ConnectorStatus.FAILED
            assert statuses["codeforces"] == ConnectorStatus.SUCCESS


# ---------------------------------------------------------------------------
# 7. ConnectorOrchestrator Checkpoint Integration Tests
# ---------------------------------------------------------------------------
class TestConnectorOrchestratorCheckpoint:
    """Verify orchestrator execution with persistent claim locking and checkpoint updates."""

    async def test_orchestrator_run_with_checkpoint_persists_status(
        self, db_session: AsyncSession
    ) -> None:
        connector = DummyTestConnector(source_name="remotive", records=[])
        orchestrator = ConnectorOrchestrator(db_session)

        summary = await orchestrator.run_connector_with_checkpoint(connector)
        assert summary.status == ConnectorStatus.SUCCESS

        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        assert (row.sync_state or {}).get("current_status") == "success"
        assert row.last_successful_sync_at is not None

    async def test_orchestrator_skips_when_claim_cannot_be_acquired(
        self, db_session: AsyncSession
    ) -> None:
        await ensure_connector_status_rows(db_session, ["remotive"])

        # Manually lock connector
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.sync_state = {"current_status": "running"}
        row.last_sync_started_at = datetime.now(UTC)
        await db_session.commit()

        connector = DummyTestConnector(source_name="remotive")
        orchestrator = ConnectorOrchestrator(db_session)

        summary = await orchestrator.run_connector_with_checkpoint(connector)
        assert summary.status == ConnectorStatus.SKIPPED
        assert "already running" in (summary.error_message or "").lower()


# ---------------------------------------------------------------------------
# 8. Status API Endpoint Tests (GET & POST)
# ---------------------------------------------------------------------------
class TestConnectorApiEndpoints:
    """Verify auth, role checks, response structure, and secret safety on API endpoints."""

    async def test_get_status_requires_authentication(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/v1/connectors/status")
        assert response.status_code == 401

    async def test_get_status_requires_admin_role(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Create non-admin user
        user, _ = await create_test_user(db_session, is_admin=False)
        await db_session.commit()

        headers = create_authenticated_headers(user.id)
        response = await async_client.get("/api/v1/connectors/status", headers=headers)
        assert response.status_code == 403
        assert "Administrative privileges required" in response.text

    async def test_get_status_success_for_admin(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Create admin user
        admin_user, _ = await create_test_user(db_session, is_admin=True)
        await db_session.commit()

        headers = create_authenticated_headers(admin_user.id)
        response = await async_client.get("/api/v1/connectors/status", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "connectors" in data
        assert "total_connectors" in data
        assert data["total_connectors"] == 8

        sources = {item["source"] for item in data["connectors"]}
        assert "remotive" in sources
        assert "adzuna" in sources
        assert "usajobs" in sources

        # Ensure no secrets or API keys are returned in response
        body_str = response.text
        assert "ADZUNA_APP_KEY" not in body_str
        assert "USAJOBS_API_KEY" not in body_str
        assert "JWT_SECRET" not in body_str

    async def test_trigger_manual_sync_requires_admin(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user, _ = await create_test_user(db_session, is_admin=False)
        await db_session.commit()

        headers = create_authenticated_headers(user.id)
        response = await async_client.post("/api/v1/connectors/remotive/sync", headers=headers)
        assert response.status_code == 403

    async def test_trigger_manual_sync_unknown_source_returns_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_user, _ = await create_test_user(db_session, is_admin=True)
        await db_session.commit()

        headers = create_authenticated_headers(admin_user.id)
        response = await async_client.post(
            "/api/v1/connectors/non_existent_source/sync",
            headers=headers,
        )
        assert response.status_code == 404
        assert "not recognized" in response.text

    async def test_trigger_manual_sync_conflict_when_running(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_user, _ = await create_test_user(db_session, is_admin=True)
        await ensure_connector_status_rows(db_session, ["remotive"])

        # Set status to running
        stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source == "remotive")
        row = (await db_session.execute(stmt)).scalar_one()
        row.sync_state = {"current_status": "running"}
        row.last_sync_started_at = datetime.now(UTC)
        await db_session.commit()

        headers = create_authenticated_headers(admin_user.id)
        response = await async_client.post("/api/v1/connectors/remotive/sync", headers=headers)
        assert response.status_code == 409
        assert "currently running" in response.text
