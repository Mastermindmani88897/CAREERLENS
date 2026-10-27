"""
Base connector interface for Phase 26.3 Wave 1 external opportunity connectors.

Provides:
- Abstract base class `BaseOpportunityConnector` defining the connector contract.
- `ConnectorBatchResult` — typed result from a single HTTP fetch.
- `ConnectorRunSummary` — aggregate result after a full connector sync run.
- `ConnectorStatus` — enumeration of connector run outcomes.
- Shared HTTP retry logic with exponential backoff.
- Respect for HTTP 429 / Retry-After headers.
- Structured logging (no credential exposure).
"""

from __future__ import annotations

import asyncio
import enum
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.opportunity import RawOpportunityRow

logger = get_logger("connectors.base")

# ---------------------------------------------------------------------------
# Shared HTTP constants
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2.0
_MAX_BACKOFF_SECONDS = 60.0


class ConnectorStatus(enum.StrEnum):
    """Enumerated outcome states for a connector sync run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    FAILED = "failed"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ConnectorBatchResult:
    """Result of a single HTTP fetch / page from an external source."""

    records: list[RawOpportunityRow] = field(default_factory=list)
    next_cursor: Any | None = None
    raw_count: int = 0
    error: str | None = None


@dataclass
class ConnectorRunSummary:
    """Aggregate result for a complete connector sync (all pages)."""

    source: str
    status: ConnectorStatus
    records_fetched: int = 0
    records_parsed: int = 0
    ingest_result_created: int = 0
    ingest_result_updated: int = 0
    ingest_result_skipped: int = 0
    ingest_result_errors: int = 0
    error_message: str | None = None
    duration_seconds: float = 0.0


def _retry_delay(attempt: int) -> float:
    """Compute exponential backoff delay for a given attempt number (0-indexed)."""
    delay = min(_BASE_BACKOFF_SECONDS * (2**attempt), _MAX_BACKOFF_SECONDS)
    return delay


async def _execute_with_retries(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_retries: int = _MAX_RETRIES,
    source_name: str = "connector",
) -> httpx.Response:
    """
    Execute an HTTP GET with bounded exponential backoff retries.

    Retry conditions:
    - HTTP 429 (Too Many Requests): honour Retry-After header when present.
    - HTTP 5xx (Server Error): transient failures.
    - httpx.TimeoutException / httpx.NetworkError: network-layer issues.

    Raises:
        httpx.HTTPStatusError: on non-retryable 4xx responses.
        RuntimeError: after all retries are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.get(url, params=params, headers=headers)

            if response.status_code == 429:
                retry_after_raw = response.headers.get("Retry-After", "")
                try:
                    wait = float(retry_after_raw)
                except (ValueError, TypeError):
                    wait = _retry_delay(attempt)
                wait = min(wait, _MAX_BACKOFF_SECONDS)
                logger.warning(
                    "[%s] HTTP 429 on attempt %d/%d — sleeping %.1fs before retry",
                    source_name,
                    attempt + 1,
                    max_retries + 1,
                    wait,
                )
                await asyncio.sleep(wait)
                continue

            if response.status_code >= 500:
                wait = _retry_delay(attempt)
                logger.warning(
                    "[%s] HTTP %d on attempt %d/%d — sleeping %.1fs before retry",
                    source_name,
                    response.status_code,
                    attempt + 1,
                    max_retries + 1,
                    wait,
                )
                await asyncio.sleep(wait)
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
                continue

            # Non-5xx, non-429 — raise immediately for 4xx errors
            response.raise_for_status()
            return response

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            wait = _retry_delay(attempt)
            logger.warning(
                "[%s] %s on attempt %d/%d — sleeping %.1fs",
                source_name,
                type(exc).__name__,
                attempt + 1,
                max_retries + 1,
                wait,
            )
            last_exc = exc
            if attempt < max_retries:
                await asyncio.sleep(wait)
            continue

    raise RuntimeError(
        f"[{source_name}] all {max_retries + 1} attempts failed. Last error: {last_exc}"
    )


class BaseOpportunityConnector(ABC):
    """
    Abstract base class for all external opportunity source connectors.

    Subclasses must implement:
    - `source_name` class attribute (string identifier, matches OpportunitySource value).
    - `fetch_batch(cursor)` — fetch one page of data, returning ConnectorBatchResult.
    - `is_configured()` — return True if all required settings are available.

    Subclasses may override:
    - `get_auth_headers()` — return per-source authentication headers.
    - `rate_limit_delay` — inter-request delay in seconds.
    - `timeout` — httpx.Timeout configuration.
    - `max_retries` — maximum HTTP retry attempts.
    """

    #: Human-readable source identifier (must match OpportunitySource enum value)
    source_name: str = ""

    #: Seconds to sleep between consecutive paginated requests (rate limiting)
    rate_limit_delay: float = 1.0

    #: httpx timeout configuration
    timeout: httpx.Timeout = _DEFAULT_TIMEOUT

    #: Maximum retry attempts for transient failures
    max_retries: int = _MAX_RETRIES

    def get_auth_headers(self) -> dict[str, str]:
        """Return authentication headers. Override in subclasses requiring credentials."""
        return {}

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this connector has all required configuration to run."""
        ...

    @abstractmethod
    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch a single page of raw opportunity data from the external source.

        Args:
            cursor: Page cursor/offset/number from the previous batch, or None for first page.

        Returns:
            ConnectorBatchResult with parsed RawOpportunityRow records and next cursor.
        """
        ...

    async def run(self) -> tuple[list[RawOpportunityRow], ConnectorRunSummary]:
        """
        Execute a full sync: paginate through all available records.

        Returns:
            Tuple of (all_raw_rows, ConnectorRunSummary).
        """
        if not self.is_configured():
            logger.info("[%s] Connector is not configured — skipping sync.", self.source_name)
            return [], ConnectorRunSummary(
                source=self.source_name,
                status=ConnectorStatus.NOT_CONFIGURED,
                error_message="Connector is not configured. Check required environment variables.",
            )

        all_records: list[RawOpportunityRow] = []
        cursor: Any = None
        page_num = 0
        start_time = time.monotonic()
        had_error = False

        logger.info("[%s] Starting sync.", self.source_name)

        while True:
            page_num += 1
            try:
                batch = await self.fetch_batch(cursor)
            except Exception as exc:
                logger.error(
                    "[%s] Unhandled error fetching page %d: %s",
                    self.source_name,
                    page_num,
                    exc,
                    exc_info=True,
                )
                had_error = True
                break

            if batch.error:
                logger.warning(
                    "[%s] Batch error on page %d: %s",
                    self.source_name,
                    page_num,
                    batch.error,
                )
                had_error = True
                break

            all_records.extend(batch.records)
            logger.debug(
                "[%s] Page %d: fetched %d records (running total: %d).",
                self.source_name,
                page_num,
                len(batch.records),
                len(all_records),
            )

            if batch.next_cursor is None:
                break

            cursor = batch.next_cursor

            if self.rate_limit_delay > 0:
                await asyncio.sleep(self.rate_limit_delay)

        duration = time.monotonic() - start_time
        status = (
            ConnectorStatus.FAILED
            if (had_error and not all_records)
            else (ConnectorStatus.PARTIAL if had_error else ConnectorStatus.SUCCESS)
        )

        summary = ConnectorRunSummary(
            source=self.source_name,
            status=status,
            records_fetched=len(all_records),
            records_parsed=len(all_records),
            duration_seconds=round(duration, 2),
        )

        logger.info(
            "[%s] Sync complete: status=%s records=%d pages=%d duration=%.2fs",
            self.source_name,
            status,
            len(all_records),
            page_num,
            duration,
        )
        return all_records, summary
