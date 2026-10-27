"""
Connector status and synchronization management API endpoints for Phase 26.5.

Provides:
- GET /api/v1/connectors/status: Detailed operational telemetry, schedules, and health.
- POST /api/v1/connectors/{source}/sync: Manual synchronization trigger with claim locking.

Security:
- Protected with get_current_admin_user dependency (admin privileges required).
- Operational data sanitized to exclude API credentials, authorization headers, and secrets.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.connector import (
    ConnectorStatusItem,
    ConnectorStatusResponse,
    ConnectorSyncTriggerResponse,
)
from app.services.connectors.base import ConnectorStatus
from app.services.connectors.checkpoint import (
    calculate_next_scheduled_sync,
    ensure_connector_status_rows,
    get_connector_sync_statuses,
    sanitize_error_summary,
)
from app.services.connectors.orchestrator import ConnectorOrchestrator, get_all_connectors

router = APIRouter()


def _sanitize_sync_state(raw_state: dict[str, Any] | None) -> dict[str, Any]:
    """Strip or redact any potentially sensitive keys from the JSONB sync state."""
    if not raw_state:
        return {}

    sanitized: dict[str, Any] = {}
    sensitive_substrings = ("key", "token", "secret", "auth", "password", "credential")

    for k, v in raw_state.items():
        if any(sub in k.lower() for sub in sensitive_substrings):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, str):
            sanitized[k] = sanitize_error_summary(v)
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_sync_state(v)
        else:
            sanitized[k] = v

    return sanitized


@router.get(
    "/status",
    response_model=ConnectorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve operational telemetry and health status across all registered connectors",
)
async def get_connectors_status(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectorStatusResponse:
    """
    Return sanitized operational telemetry for all registered external connectors.

    Includes:
    - Connector source name
    - Enabled and configured status
    - Timestamps of last attempt and last successful synchronization
    - Current operational state (idle, running, success, partial, failed, not_configured)
    - Execution duration of the most recent run
    - Counts of fetched, created, updated, and skipped records
    - Consecutive failure count
    - Sanitized error summary without credentials
    - Calculated next scheduled synchronization time
    """
    all_connectors_map = {c.source_name: c for c in get_all_connectors()}
    registered_sources = list(all_connectors_map.keys())

    # Ensure all registered connectors have status rows initialized
    await ensure_connector_status_rows(db, registered_sources)
    db_rows = await get_connector_sync_statuses(db)

    items: list[ConnectorStatusItem] = []
    active_runs = 0
    total_enabled = 0

    for row in db_rows:
        if row.source not in all_connectors_map:
            continue

        connector = all_connectors_map[row.source]
        is_configured = connector.is_configured()
        sync_state = dict(row.sync_state or {})
        current_status = sync_state.get("current_status", "idle")

        if not is_configured and current_status == "idle":
            current_status = "not_configured"

        if current_status == "running":
            active_runs += 1

        if row.is_enabled:
            total_enabled += 1

        next_sync = calculate_next_scheduled_sync(row)

        item = ConnectorStatusItem(
            source=row.source,
            is_enabled=row.is_enabled,
            is_configured=is_configured,
            refresh_interval_minutes=row.refresh_interval_minutes,
            current_status=current_status,
            last_sync_started_at=row.last_sync_started_at,
            last_sync_completed_at=row.last_sync_completed_at,
            last_successful_sync_at=row.last_successful_sync_at,
            next_scheduled_sync_at=next_sync,
            duration_seconds=sync_state.get("last_run_duration_seconds"),
            records_fetched=row.total_fetched,
            records_created=row.total_created,
            records_updated=row.total_updated,
            records_skipped=row.total_skipped,
            consecutive_failures=row.consecutive_failures,
            error_summary=sanitize_error_summary(row.last_error_summary),
            sync_state=_sanitize_sync_state(sync_state),
        )
        items.append(item)

    return ConnectorStatusResponse(
        connectors=items,
        total_connectors=len(items),
        total_enabled=total_enabled,
        active_runs=active_runs,
    )


@router.post(
    "/{source}/sync",
    response_model=ConnectorSyncTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger an on-demand manual synchronization for a single connector",
)
async def trigger_manual_sync(
    source: str,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: bool = Query(default=False, description="Force execution bypassing schedule"),
) -> ConnectorSyncTriggerResponse:
    """
    Trigger manual execution of a single external opportunity connector.

    Guarantees:
    - Verifies source against registered connectors (returns 404 if invalid).
    - Prevents overlapping runs: returns 409 Conflict if connector is already running.
    - Records persistent checkpoint in connector_sync_status.
    - Sanitizes error outputs before returning.
    """
    all_connectors_map = {c.source_name: c for c in get_all_connectors()}
    normalized_source = source.strip().lower()

    if normalized_source not in all_connectors_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Connector source '{source}' is not recognized. "
                f"Valid sources: {sorted(list(all_connectors_map.keys()))}"
            ),
        )

    connector = all_connectors_map[normalized_source]
    orchestrator = ConnectorOrchestrator(db)
    summary = await orchestrator.run_connector_with_checkpoint(connector)

    if (
        summary.status == ConnectorStatus.SKIPPED
        and "running" in (summary.error_message or "").lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Connector '{normalized_source}' is currently running and locked."
            ),
        )

    return ConnectorSyncTriggerResponse(
        source=normalized_source,
        status=summary.status.value,
        message=(
            f"Connector '{normalized_source}' run completed with status '{summary.status.value}'."
        ),
        summary={
            "records_fetched": summary.records_fetched,
            "records_created": summary.ingest_result_created,
            "records_updated": summary.ingest_result_updated,
            "records_skipped": summary.ingest_result_skipped,
            "errors": summary.ingest_result_errors,
            "duration_seconds": summary.duration_seconds,
            "error_message": sanitize_error_summary(summary.error_message),
        },
    )
