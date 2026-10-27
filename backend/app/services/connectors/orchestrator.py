"""
Connector ingestion orchestrator for Phase 26.3.

Bridges the connector layer (BaseOpportunityConnector) and the existing
transactional ingestion service (ingest_raw_records).

Usage:
    orchestrator = ConnectorOrchestrator(db_session)
    summary = await orchestrator.run_connector(RemotiveConnector())
    all_summaries = await orchestrator.run_all(wave1_connectors)

Design:
- Per-connector failure is isolated; one failing connector does not abort others.
- Ingestion results (created/skipped/errors) are merged into ConnectorRunSummary.
- No synthetic test records are ever inserted in production mode.
- The orchestrator does not implement scheduling (Phase 26.5 responsibility).
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.opportunity_ingest_service import ingest_raw_records

logger = get_logger("connectors.orchestrator")


class ConnectorOrchestrator:
    """
    Runs one or more connectors and feeds their records into the ingestion service.

    Each connector run is fully isolated:
    - Connector HTTP failures set status FAILED and do not affect sibling connectors.
    - Per-record ingestion errors are accumulated in the summary but do not abort the batch.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def run_connector(
        self,
        connector: BaseOpportunityConnector,
    ) -> ConnectorRunSummary:
        """
        Execute a single connector: fetch → ingest → return summary.

        Returns ConnectorRunSummary with aggregated telemetry.
        """
        start = time.monotonic()

        try:
            raw_records, fetch_summary = await connector.run()
        except Exception as exc:
            logger.error(
                "[orchestrator] Connector '%s' raised during run(): %s",
                connector.source_name,
                exc,
                exc_info=True,
            )
            return ConnectorRunSummary(
                source=connector.source_name,
                status=ConnectorStatus.FAILED,
                error_message=f"Connector.run() raised: {type(exc).__name__}: {exc}",
                duration_seconds=round(time.monotonic() - start, 2),
            )

        # Pass-through for NOT_CONFIGURED / FAILED with no records
        if fetch_summary.status in (ConnectorStatus.NOT_CONFIGURED, ConnectorStatus.FAILED):
            return fetch_summary

        if not raw_records:
            logger.info(
                "[orchestrator] Connector '%s' returned 0 records — nothing to ingest.",
                connector.source_name,
            )
            fetch_summary.status = ConnectorStatus.SUCCESS
            fetch_summary.duration_seconds = round(time.monotonic() - start, 2)
            return fetch_summary

        # Ingest into the transactional persistence layer
        try:
            ingest_result = await ingest_raw_records(self._db, raw_records)
        except Exception as exc:
            logger.error(
                "[orchestrator] Ingestion failed for connector '%s': %s",
                connector.source_name,
                exc,
                exc_info=True,
            )
            fetch_summary.status = ConnectorStatus.FAILED
            fetch_summary.error_message = f"Ingestion layer error: {type(exc).__name__}: {exc}"
            fetch_summary.duration_seconds = round(time.monotonic() - start, 2)
            return fetch_summary

        # Merge ingestion telemetry
        fetch_summary.ingest_result_created = ingest_result.created
        fetch_summary.ingest_result_skipped = ingest_result.skipped_duplicates
        fetch_summary.ingest_result_errors = len(ingest_result.errors)
        fetch_summary.duration_seconds = round(time.monotonic() - start, 2)

        if ingest_result.errors and ingest_result.created == 0:
            fetch_summary.status = ConnectorStatus.FAILED
        elif ingest_result.errors:
            fetch_summary.status = ConnectorStatus.PARTIAL
        else:
            fetch_summary.status = ConnectorStatus.SUCCESS

        logger.info(
            "[orchestrator] '%s' complete: created=%d skipped=%d errors=%d duration=%.2fs",
            connector.source_name,
            ingest_result.created,
            ingest_result.skipped_duplicates,
            len(ingest_result.errors),
            fetch_summary.duration_seconds,
        )
        return fetch_summary

    async def run_all(
        self,
        connectors: Sequence[BaseOpportunityConnector],
    ) -> list[ConnectorRunSummary]:
        """
        Run each connector sequentially. Returns list of summaries in order.

        Failures in one connector never abort subsequent connectors.
        """
        summaries: list[ConnectorRunSummary] = []
        for connector in connectors:
            summary = await self.run_connector(connector)
            summaries.append(summary)
        return summaries


def get_all_connectors() -> list[BaseOpportunityConnector]:
    """Instantiate and return all registered connectors across Wave 1 and Wave 2."""
    from app.services.connectors.adzuna import AdzunaConnector
    from app.services.connectors.arbeitnow import ArbeitnowConnector
    from app.services.connectors.codeforces import CodeforcesConnector
    from app.services.connectors.greenhouse import GreenhouseConnector
    from app.services.connectors.lever import LeverConnector
    from app.services.connectors.remoteok import RemoteOKConnector
    from app.services.connectors.remotive import RemotiveConnector
    from app.services.connectors.usajobs import USAJOBSConnector

    return [
        RemotiveConnector(),
        ArbeitnowConnector(),
        CodeforcesConnector(),
        GreenhouseConnector(),
        AdzunaConnector(),
        USAJOBSConnector(),
        LeverConnector(),
        RemoteOKConnector(),
    ]
