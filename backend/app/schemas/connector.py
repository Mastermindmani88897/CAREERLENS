"""
Pydantic schemas for Phase 26.5 Connector Synchronization and Status Monitoring.
Provides typed models for operational telemetry, scheduled synchronization, and manual triggers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConnectorStatusItem(BaseModel):
    """Sanitized operational telemetry for a single registered connector."""

    source: str = Field(description="Connector source identifier matching OpportunitySource")
    is_enabled: bool = Field(description="Whether synchronization is enabled for this source")
    is_configured: bool = Field(description="Whether required credentials/tokens are configured")
    refresh_interval_minutes: int = Field(description="Configured polling interval in minutes")
    current_status: str = Field(
        default="idle",
        description="Current operational state: idle, running, success, partial, failed, skipped",
    )
    last_sync_started_at: datetime | None = Field(
        default=None,
        description="Timestamp when the most recent synchronization began",
    )
    last_sync_completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the most recent synchronization completed",
    )
    last_successful_sync_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent fully successful synchronization",
    )
    next_scheduled_sync_at: datetime | None = Field(
        default=None,
        description="Calculated timestamp when the connector is next due to run",
    )
    duration_seconds: float | None = Field(
        default=None,
        description="Execution duration in seconds of the most recent run",
    )
    records_fetched: int = Field(default=0, description="Cumulative records fetched across runs")
    records_created: int = Field(default=0, description="Cumulative new records inserted")
    records_updated: int = Field(default=0, description="Cumulative records updated")
    records_skipped: int = Field(default=0, description="Cumulative duplicate records skipped")
    consecutive_failures: int = Field(
        default=0,
        description="Number of consecutive run failures since last success",
    )
    error_summary: str | None = Field(
        default=None,
        description="Sanitized summary of the most recent run error without secrets",
    )
    sync_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized operational metadata (cursor, last run metrics)",
    )

    model_config = ConfigDict(from_attributes=True)


class ConnectorStatusResponse(BaseModel):
    """Aggregate operational status response across all registered connectors."""

    connectors: list[ConnectorStatusItem] = Field(description="List of all connector statuses")
    total_connectors: int = Field(description="Total count of registered connectors")
    total_enabled: int = Field(description="Count of currently enabled connectors")
    active_runs: int = Field(description="Count of connectors currently in running state")


class ConnectorSyncTriggerResponse(BaseModel):
    """Response returned when triggering a manual connector synchronization."""

    source: str = Field(description="Connector source identifier")
    status: str = Field(description="Execution outcome or claim status")
    message: str = Field(description="Human-readable execution outcome summary")
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Detailed run summary telemetry if executed",
    )
