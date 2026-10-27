"""
Configurable background synchronization scheduler for Phase 26.5.

Guarantees:
- Bounded concurrency with asyncio.Semaphore.
- Per-connector execution timeout with asyncio.wait_for.
- Cross-worker coordination using database-backed atomic claim checks.
- Continuous operation: failures in one connector never halt or delay sibling connectors.
- Graceful startup and shutdown lifecycle hooks.
- Safe manual execution triggers for administration and testing.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.connectors.checkpoint import (
    get_connector_sync_statuses,
    is_connector_due,
)
from app.services.connectors.orchestrator import ConnectorOrchestrator, get_all_connectors

logger = get_logger("connectors.scheduler")


class ConnectorScheduler:
    """
    Background worker loop that periodically checks for and runs due external connectors.

    Features:
    - Non-blocking cooperative concurrency via asyncio.
    - Concurrency bounded by max_concurrency semaphore.
    - Isolated per-connector timeout protection.
    - Distributed locking via connector_sync_status atomic claims.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        interval_seconds: int | None = None,
        max_concurrency: int | None = None,
        timeout_seconds: int | None = None,
        stale_lock_minutes: int | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_factory
        self.interval_seconds = (
            interval_seconds
            if interval_seconds is not None
            else settings.SCHEDULER_INTERVAL_SECONDS
        )
        self.max_concurrency = (
            max_concurrency
            if max_concurrency is not None
            else settings.SCHEDULER_MAX_CONCURRENCY
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.CONNECTOR_TIMEOUT_SECONDS
        )
        self.stale_lock_minutes = (
            stale_lock_minutes
            if stale_lock_minutes is not None
            else settings.CONNECTOR_STALE_LOCK_MINUTES
        )

        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._stop_event = asyncio.Event()
        self._loop_task: asyncio.Task[None] | None = None
        self._active_tasks: set[asyncio.Task[Any]] = set()

    @property
    def is_running(self) -> bool:
        """Return True if the background scheduler loop is active."""
        return self._loop_task is not None and not self._loop_task.done()

    async def start(self) -> None:
        """Start the background scheduler task if not already running."""
        if self.is_running:
            logger.warning("[scheduler] Scheduler is already running.")
            return

        self._stop_event.clear()
        self._loop_task = asyncio.create_task(self._scheduler_loop(), name="connector-scheduler")
        logger.info(
            "[scheduler] Started background scheduler (interval=%ds, concurrency=%d, timeout=%ds)",
            self.interval_seconds,
            self.max_concurrency,
            self.timeout_seconds,
        )

    async def stop(self, timeout: float = 10.0) -> None:
        """Signal the scheduler to stop and wait for active tasks to complete gracefully."""
        if not self.is_running:
            return

        logger.info("[scheduler] Shutting down connector background scheduler...")
        self._stop_event.set()

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._loop_task), timeout=timeout)
            except (asyncio.CancelledError, TimeoutError):
                pass
            self._loop_task = None

        # Wait for any active in-flight connector tasks
        if self._active_tasks:
            logger.info(
                "[scheduler] Waiting for %d active connector tasks...",
                len(self._active_tasks),
            )
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    "[scheduler] In-flight tasks did not complete within %.1fs timeout",
                    timeout,
                )
            self._active_tasks.clear()

        logger.info("[scheduler] Connector background scheduler shutdown complete.")

    async def _scheduler_loop(self) -> None:
        """Main periodic polling loop."""
        while not self._stop_event.is_set():
            try:
                await self.run_due_connectors()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[scheduler] Error during run_due_connectors: %s", exc, exc_info=True)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
                break  # stop_event was signaled
            except TimeoutError:
                pass  # Timer interval expired, continue next loop iteration

    async def get_due_connectors(self) -> list[BaseOpportunityConnector]:
        """
        Query connector status records and return connector instances that are due to run.
        """
        async with self._session_factory() as session:
            statuses = await get_connector_sync_statuses(session)

        # Build map of due source identifiers
        due_sources = {
            s.source for s in statuses if is_connector_due(s, self.stale_lock_minutes)
        }

        if not due_sources:
            return []

        # Find registered connector instances matching due sources
        all_connectors = get_all_connectors()
        return [c for c in all_connectors if c.source_name in due_sources]

    async def _run_single_connector(
        self,
        connector: BaseOpportunityConnector,
    ) -> ConnectorRunSummary:
        """Execute a single connector with bounded concurrency and isolated timeout."""
        async with self._semaphore:
            async with self._session_factory() as session:
                orchestrator = ConnectorOrchestrator(session)
                try:
                    return await asyncio.wait_for(
                        orchestrator.run_connector_with_checkpoint(
                            connector,
                            stale_lock_minutes=self.stale_lock_minutes,
                        ),
                        timeout=self.timeout_seconds,
                    )
                except TimeoutError:
                    logger.error(
                        "[scheduler] Connector '%s' timed out after %ds",
                        connector.source_name,
                        self.timeout_seconds,
                    )
                    from app.services.connectors.checkpoint import release_connector_claim

                    timed_out_summary = ConnectorRunSummary(
                        source=connector.source_name,
                        status=ConnectorStatus.FAILED,
                        error_message=(
                            f"Connector execution timed out after {self.timeout_seconds} seconds."
                        ),
                        duration_seconds=float(self.timeout_seconds),
                    )
                    try:
                        await release_connector_claim(session, timed_out_summary)
                    except Exception:
                        pass
                    return timed_out_summary
                except Exception as exc:
                    logger.error(
                        "[scheduler] Unexpected exception for connector '%s': %s",
                        connector.source_name,
                        exc,
                        exc_info=True,
                    )
                    return ConnectorRunSummary(
                        source=connector.source_name,
                        status=ConnectorStatus.FAILED,
                        error_message=f"Scheduler task raised: {type(exc).__name__}: {exc}",
                    )

    async def run_due_connectors(self) -> list[ConnectorRunSummary]:
        """
        Identify due connectors and execute them concurrently up to max_concurrency.

        Failures in one connector never abort others.
        """
        due_connectors = await self.get_due_connectors()
        if not due_connectors:
            logger.debug("[scheduler] No connectors currently due for synchronization.")
            return []

        logger.info(
            "[scheduler] Found %d connectors due for synchronization: %s",
            len(due_connectors),
            [c.source_name for c in due_connectors],
        )

        tasks: list[asyncio.Task[ConnectorRunSummary]] = []
        for connector in due_connectors:
            task = asyncio.create_task(
                self._run_single_connector(connector),
                name=f"sync-{connector.source_name}",
            )
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)
            tasks.append(task)

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        summaries: list[ConnectorRunSummary] = []
        for result, connector in zip(raw_results, due_connectors, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "[scheduler] Task for '%s' raised unhandled error: %s",
                    connector.source_name,
                    result,
                )
                summaries.append(
                    ConnectorRunSummary(
                        source=connector.source_name,
                        status=ConnectorStatus.FAILED,
                        error_message=f"Task error: {type(result).__name__}: {result}",
                    )
                )
            else:
                summaries.append(result)

        return summaries

    async def trigger_connector_sync(
        self,
        source: str,
        force: bool = False,
    ) -> ConnectorRunSummary:
        """
        Trigger an on-demand manual synchronization for a single connector.

        Bypasses refresh interval checks, but still enforces the atomic claim lock.
        """
        all_connectors = {c.source_name: c for c in get_all_connectors()}
        connector = all_connectors.get(source)
        if connector is None:
            return ConnectorRunSummary(
                source=source,
                status=ConnectorStatus.FAILED,
                error_message=f"Unknown connector source: '{source}'.",
            )

        return await self._run_single_connector(connector)


# Process-level singleton instance
_global_scheduler: ConnectorScheduler | None = None


def get_connector_scheduler() -> ConnectorScheduler:
    """Return or initialize the singleton ConnectorScheduler instance."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = ConnectorScheduler()
    return _global_scheduler
