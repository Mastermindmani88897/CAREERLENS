"""
Persistent synchronization checkpoints and distributed locking for Phase 26.5.

Guarantees:
- Database-backed persistence using the existing connector_sync_status table.
- Overlapping execution prevention across multiple workers via SELECT FOR UPDATE locking.
- Stale lock detection and crash recovery for interrupted processes.
- Atomic state transitions: updates last_successful_sync_at only on full SUCCESS.
- Failure preservation: preserves previous successful timestamp on failure.
- Strict error sanitization: redacts query parameters, authorization headers, and secrets.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.connector import ConnectorSyncStatus
from app.services.connectors.base import ConnectorRunSummary, ConnectorStatus

logger = get_logger("connectors.checkpoint")

# Canonical registered source identifiers across Wave 1 and Wave 2
ALL_REGISTERED_SOURCES: list[str] = [
    "remotive",
    "arbeitnow",
    "codeforces",
    "greenhouse",
    "adzuna",
    "usajobs",
    "lever",
    "remoteok",
]

# Regex patterns for redacting sensitive credentials and auth tokens from error summaries
_SECRET_QUERY_PARAM_REGEX = re.compile(
    r"(?i)(api[_-]?key|app[_-]?id|app[_-]?key|token|secret|password|auth|authorization)"
    r"(=|%3D)([^&\s]+)"
)
_AUTH_HEADER_REGEX = re.compile(
    r"(?i)(authorization|authorization-key|api-key):\s*([^\r\n,]+)"
)
_BEARER_TOKEN_REGEX = re.compile(r"(?i)(bearer|basic)\s+([a-zA-Z0-9_\-\.\~]+)")


def sanitize_error_summary(error: str | None, max_length: int = 500) -> str | None:
    """
    Sanitize an error summary or traceback string before persisting to the database.

    Redacts:
    - Query parameter credentials (app_id, app_key, api_key, token, secret)
    - Authorization and API-Key headers
    - Bearer and Basic tokens
    - Any active secrets loaded into application settings
    - Truncates to max_length characters
    """
    if not error:
        return None

    sanitized = str(error)

    # Redact query string credentials
    sanitized = _SECRET_QUERY_PARAM_REGEX.sub(r"\1\2[REDACTED]", sanitized)

    # Redact Authorization and API-Key headers
    sanitized = _AUTH_HEADER_REGEX.sub(r"\1: [REDACTED]", sanitized)

    # Redact Bearer and Basic tokens
    sanitized = _BEARER_TOKEN_REGEX.sub(r"\1 [REDACTED]", sanitized)

    # Redact specific known secrets from settings if configured
    known_secrets = [
        settings.ADZUNA_APP_ID,
        settings.ADZUNA_APP_KEY,
        settings.USAJOBS_API_KEY,
        settings.effective_jwt_secret,
    ]
    for secret in known_secrets:
        if secret and len(secret) >= 4 and secret in sanitized:
            sanitized = sanitized.replace(secret, "[REDACTED]")

    # Normalize whitespace and limit length
    sanitized = " ".join(sanitized.split())
    if len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."

    return sanitized


async def ensure_connector_status_rows(
    db: AsyncSession,
    sources: Sequence[str] | None = None,
) -> list[ConnectorSyncStatus]:
    """
    Ensure all registered connectors have a corresponding row in connector_sync_status.

    Initializes missing connectors with default refresh interval and 'idle' status.
    Idempotent and safe for concurrent invocations.
    """
    target_sources = list(sources) if sources is not None else ALL_REGISTERED_SOURCES

    # Query existing rows
    stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source.in_(target_sources))
    result = await db.execute(stmt)
    existing_rows = {row.source: row for row in result.scalars().all()}

    new_rows: list[ConnectorSyncStatus] = []
    for source in target_sources:
        if source not in existing_rows:
            new_row = ConnectorSyncStatus(
                source=source,
                is_enabled=True,
                refresh_interval_minutes=settings.CONNECTOR_DEFAULT_REFRESH_MINUTES,
                sync_state={"current_status": "idle"},
            )
            db.add(new_row)
            new_rows.append(new_row)

    if new_rows:
        try:
            await db.commit()
            for r in new_rows:
                existing_rows[r.source] = r
            logger.info(
                "[checkpoint] Initialized %d new connector_sync_status rows: %s",
                len(new_rows),
                [r.source for r in new_rows],
            )
        except Exception:
            await db.rollback()
            # Retry reading in case another concurrent worker inserted them
            stmt = select(ConnectorSyncStatus).where(ConnectorSyncStatus.source.in_(target_sources))
            result = await db.execute(stmt)
            existing_rows = {row.source: row for row in result.scalars().all()}

    return [existing_rows[src] for src in target_sources if src in existing_rows]


async def acquire_connector_claim(
    db: AsyncSession,
    source: str,
    stale_lock_minutes: int | None = None,
    worker_id: str | None = None,
) -> tuple[bool, str]:
    """
    Attempt to atomically acquire an exclusive execution claim on a connector.

    Uses PostgreSQL SELECT ... FOR UPDATE to serialize concurrent workers.
    Returns:
        (True, message) if claim acquired successfully.
        (False, message) if already running, disabled, or locked by another worker.
    """
    stale_minutes = stale_lock_minutes or settings.CONNECTOR_STALE_LOCK_MINUTES
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(minutes=stale_minutes)

    # First ensure the row exists
    await ensure_connector_status_rows(db, [source])

    # Lock the row for update
    stmt = (
        select(ConnectorSyncStatus)
        .where(ConnectorSyncStatus.source == source)
        .with_for_update()
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        await db.rollback()
        return False, f"Connector '{source}' record not found."

    if not row.is_enabled:
        await db.rollback()
        return False, f"Connector '{source}' is currently disabled."

    sync_state = dict(row.sync_state or {})
    current_status = sync_state.get("current_status", "idle")

    # Check for active non-stale run
    if current_status == "running":
        started_at = row.last_sync_started_at
        if started_at and started_at > stale_cutoff:
            await db.rollback()
            return False, (
                f"Connector '{source}' is already running "
                f"(started at {started_at.isoformat()})."
            )
        logger.warning(
            "[checkpoint] Reclaiming stale lock for connector '%s' (started at %s, timeout=%dm)",
            source,
            started_at,
            stale_minutes,
        )

    # Claim the lock
    row.last_sync_started_at = now
    sync_state["current_status"] = "running"
    sync_state["claimed_at"] = now.isoformat()
    if worker_id:
        sync_state["worker_id"] = worker_id
    row.sync_state = sync_state

    await db.commit()
    logger.debug("[checkpoint] Acquired claim for connector '%s'", source)
    return True, f"Claim acquired for connector '{source}'."


async def release_connector_claim(
    db: AsyncSession,
    summary: ConnectorRunSummary,
    pagination_cursor: Any = None,
) -> ConnectorSyncStatus:
    """
    Release an execution claim and persist synchronization outcome and telemetry.

    Adheres strictly to Phase 26.5 persistence rules:
    - Updates last_successful_sync_at ONLY on full SUCCESS.
    - Preserves previous last_successful_sync_at on failure, partial, or skipped.
    - Increments consecutive_failures only on FAILED; resets to 0 on SUCCESS.
    - Sanitizes any error message before writing to last_error_summary.
    - Updates cumulative fetched, created, updated, and skipped totals.
    - Records last run metrics and pagination cursor in sync_state.
    """
    now = datetime.now(UTC)

    # Lock the row for update
    stmt = (
        select(ConnectorSyncStatus)
        .where(ConnectorSyncStatus.source == summary.source)
        .with_for_update()
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        # Fallback creation if row was missing
        row = ConnectorSyncStatus(
            source=summary.source,
            is_enabled=True,
            refresh_interval_minutes=settings.CONNECTOR_DEFAULT_REFRESH_MINUTES,
        )
        db.add(row)

    row.last_sync_completed_at = now

    # Status-specific state updates
    if summary.status == ConnectorStatus.SUCCESS:
        row.last_successful_sync_at = now
        row.consecutive_failures = 0
        row.last_error_summary = None
    elif summary.status == ConnectorStatus.PARTIAL:
        # Do NOT update last_successful_sync_at on partial results
        row.last_error_summary = sanitize_error_summary(
            summary.error_message or "Partial synchronization completed with ingestion warnings."
        )
    elif summary.status == ConnectorStatus.FAILED:
        # Preserve previous last_successful_sync_at and increment failure counter
        row.consecutive_failures = (row.consecutive_failures or 0) + 1
        row.last_error_summary = sanitize_error_summary(
            summary.error_message or "Connector synchronization failed."
        )
    elif summary.status in (ConnectorStatus.SKIPPED, ConnectorStatus.NOT_CONFIGURED):
        if summary.error_message:
            row.last_error_summary = sanitize_error_summary(summary.error_message)

    # Cumulative totals
    row.total_fetched = (row.total_fetched or 0) + summary.records_fetched
    row.total_created = (row.total_created or 0) + summary.ingest_result_created
    row.total_updated = (row.total_updated or 0) + summary.ingest_result_updated
    row.total_skipped = (row.total_skipped or 0) + summary.ingest_result_skipped

    # Operational telemetry in sync_state
    state = dict(row.sync_state or {})
    state["current_status"] = summary.status.value
    state["last_run_duration_seconds"] = summary.duration_seconds
    state["last_run_fetched"] = summary.records_fetched
    state["last_run_created"] = summary.ingest_result_created
    state["last_run_updated"] = summary.ingest_result_updated
    state["last_run_skipped"] = summary.ingest_result_skipped
    state["last_run_errors"] = summary.ingest_result_errors
    if pagination_cursor is not None:
        state["pagination_cursor"] = pagination_cursor
    state.pop("claimed_at", None)
    state.pop("worker_id", None)
    row.sync_state = state

    await db.commit()
    logger.info(
        "[checkpoint] Persisted '%s' outcome: status=%s created=%d skipped=%d failures=%d",
        summary.source,
        summary.status.value,
        summary.ingest_result_created,
        summary.ingest_result_skipped,
        row.consecutive_failures,
    )
    return row


def calculate_next_scheduled_sync(
    row: ConnectorSyncStatus,
    now: datetime | None = None,
) -> datetime | None:
    """
    Calculate the next scheduled synchronization datetime for a connector.

    Returns:
    - None if connector is disabled or actively running.
    - now (due immediately) if the connector has never completed a sync.
    - last_sync_completed_at + refresh_interval_minutes otherwise.
    """
    if not row.is_enabled:
        return None

    state = row.sync_state or {}
    if state.get("current_status") == "running":
        return None

    current_time = now or datetime.now(UTC)
    if row.last_sync_completed_at is None:
        return current_time

    interval = timedelta(minutes=max(1, row.refresh_interval_minutes or 60))
    return row.last_sync_completed_at + interval


def is_connector_due(
    row: ConnectorSyncStatus,
    stale_lock_minutes: int | None = None,
    now: datetime | None = None,
) -> bool:
    """
    Determine whether a connector is due for synchronization.

    A connector is due when:
    1. It is enabled (is_enabled is True).
    2. It is not currently running (or its running claim is stale and needs recovery).
    3. Either it has never completed a synchronization, OR the refresh interval has elapsed.
    """
    if not row.is_enabled:
        return False

    current_time = now or datetime.now(UTC)
    state = row.sync_state or {}
    current_status = state.get("current_status", "idle")

    if current_status == "running":
        stale_minutes = stale_lock_minutes or settings.CONNECTOR_STALE_LOCK_MINUTES
        if row.last_sync_started_at and (
            current_time - row.last_sync_started_at
        ) > timedelta(minutes=stale_minutes):
            return True  # Stale lock: due for recovery run
        return False

    if row.last_sync_completed_at is None:
        return True

    interval = timedelta(minutes=max(1, row.refresh_interval_minutes or 60))
    return current_time >= (row.last_sync_completed_at + interval)


async def get_connector_sync_statuses(db: AsyncSession) -> list[ConnectorSyncStatus]:
    """Retrieve all connector status rows ordered alphabetically by source name."""
    await ensure_connector_status_rows(db)
    stmt = select(ConnectorSyncStatus).order_by(ConnectorSyncStatus.source.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
