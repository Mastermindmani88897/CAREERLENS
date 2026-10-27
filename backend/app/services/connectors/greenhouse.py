"""
Greenhouse connector for Phase 26.3 Wave 1.

Official API endpoint:
    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

Documentation: https://developers.greenhouse.io/job-board.html
Authentication: None required for public boards.

Usage strategy:
- Configured via GREENHOUSE_BOARD_TOKENS environment variable (comma-separated).
- Each token corresponds to one employer's public board.
- If GREENHOUSE_BOARD_TOKENS is empty or not set, the connector reports NOT_CONFIGURED.
- A missing or invalid individual board token does not break other boards.

Response schema per board:
{
  "jobs": [
    {
      "id": 12345678,
      "title": "Senior Software Engineer",
      "updated_at": "2026-10-01T12:00:00.000Z",
      "requisition_id": "REQ-001",
      "location": {"name": "San Francisco, CA"},
      "departments": [{"id": 1, "name": "Engineering"}],
      "content": "<p>Full job description HTML...</p>",
      "absolute_url": "https://boards.greenhouse.io/company/jobs/12345678",
      "metadata": [],
      "data_compliance": []
    }
  ],
  "meta": {"total": 42}
}

Design decisions:
- Source ID: "gh-{board_token}-{job_id}" for deterministic, board-scoped deduplication.
- Company: inferred from board_token (normalized to title case) unless meta provides it.
- Board failure: logged and skipped; does not abort other board fetches.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    ConnectorRunSummary,
    ConnectorStatus,
    _execute_with_retries,
)

logger = get_logger("connectors.greenhouse")

_API_BASE = "https://boards-api.greenhouse.io/v1/boards"
_BOARDS_ENV_VAR = "GREENHOUSE_BOARD_TOKENS"


def _load_board_tokens() -> list[str]:
    """Load and parse the GREENHOUSE_BOARD_TOKENS environment variable."""
    raw = os.environ.get(_BOARDS_ENV_VAR)
    if raw is None:
        from app.core.config import settings

        raw = getattr(settings, "GREENHOUSE_BOARD_TOKENS", "")
    raw = (raw or "").strip()
    if not raw:
        return []
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    return tokens


def _normalize_company_name(board_token: str) -> str:
    """Convert board token slug to a human-readable company name."""
    # e.g. 'stripe' -> 'Stripe', 'cloudflare' -> 'Cloudflare'
    # e.g. 'my-company' -> 'My Company'
    name = re.sub(r"[-_]+", " ", board_token)
    return name.title()


def _parse_location(location: dict[str, Any] | None) -> str | None:
    """Extract location name from Greenhouse location object."""
    if not isinstance(location, dict):
        return None
    return (location.get("name") or "").strip() or None


def _parse_department(departments: list[Any] | None) -> str | None:
    """Extract first department name from departments list."""
    if not isinstance(departments, list) or not departments:
        return None
    first = departments[0] if departments else {}
    if isinstance(first, dict):
        return (first.get("name") or "").strip() or None
    return None


def _parse_job(
    job: dict[str, Any],
    board_token: str,
    company_name: str,
) -> RawOpportunityRow | None:
    """Map a Greenhouse job dict to a RawOpportunityRow."""
    try:
        job_id = job.get("id")
        if not job_id:
            return None
        source_id = f"gh-{board_token}-{job_id}"

        title = (job.get("title") or "").strip()
        if not title:
            return None

        # Description from 'content' field (rich HTML)
        description = (job.get("content") or "").strip()
        if not description:
            description = f"Greenhouse job listing for {title} at {company_name}."

        job_url = (job.get("absolute_url") or "").strip() or None

        location_raw = _parse_location(job.get("location"))
        city, state, country = _split_location(location_raw)

        department = _parse_department(job.get("departments"))

        # Published/updated date
        updated_at: str | None = job.get("updated_at") or None

        return RawOpportunityRow(
            title=title,
            company=company_name,
            description=description,
            opportunity_type="job",
            employment_type="fulltime",
            work_mode="any",
            location_city=city,
            location_state=state,
            location_country=country,
            job_url=job_url,
            source="greenhouse",
            source_id=source_id,
            posted_date=updated_at,
            required_skills=None,
            preferred_skills=None,
            is_active=True,
            external_metadata={
                "greenhouse_job_id": job_id,
                "board_token": board_token,
                "department": department or "",
                "requisition_id": job.get("requisition_id") or "",
            },
        )
    except Exception as exc:
        logger.debug(
            "Failed to parse Greenhouse job id=%s board=%s: %s",
            job.get("id"),
            board_token,
            exc,
        )
        return None


def _split_location(location_str: str | None) -> tuple[str | None, str | None, str | None]:
    """Split 'City, State, Country' or 'City, Country' into components."""
    if not location_str:
        return None, None, None
    parts = [p.strip() for p in location_str.split(",") if p.strip()]
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return parts[0], parts[1], parts[2]


class GreenhouseConnector(BaseOpportunityConnector):
    """
    Connector for Greenhouse public employer job boards.

    Fetches jobs from one or more Greenhouse board tokens defined in the
    GREENHOUSE_BOARD_TOKENS environment variable (comma-separated list).

    Each board is fetched independently. A failure on one board is logged
    and skipped; other boards continue normally.

    If no board tokens are configured, the connector reports NOT_CONFIGURED.
    """

    source_name = "greenhouse"
    rate_limit_delay = 1.0
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=10.0, pool=10.0)

    def is_configured(self) -> bool:
        """Return True if at least one board token is configured."""
        return len(_load_board_tokens()) > 0

    def get_auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "CareerLens/1.0 (https://github.com/Mastermindmani88897/CAREERLENS)",
        }

    async def _fetch_board(
        self,
        client: httpx.AsyncClient,
        board_token: str,
    ) -> list[RawOpportunityRow]:
        """Fetch all jobs from a single Greenhouse board."""
        url = f"{_API_BASE}/{board_token}/jobs"
        params = {"content": "true"}
        company_name = _normalize_company_name(board_token)

        try:
            response = await _execute_with_retries(
                client=client,
                url=url,
                params=params,
                headers=self.get_auth_headers(),
                max_retries=self.max_retries,
                source_name=f"{self.source_name}[{board_token}]",
            )
        except Exception as exc:
            logger.warning(
                "[greenhouse] Board '%s' failed: %s — skipping board.",
                board_token,
                exc,
            )
            return []

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "[greenhouse] Board '%s' returned invalid JSON: %s — skipping.",
                board_token,
                exc,
            )
            return []

        if not isinstance(payload, dict):
            logger.warning(
                "[greenhouse] Board '%s' returned unexpected payload type %s — skipping.",
                board_token,
                type(payload).__name__,
            )
            return []

        jobs_raw: list[Any] = payload.get("jobs") or []
        if not isinstance(jobs_raw, list):
            logger.warning(
                "[greenhouse] Board '%s' 'jobs' field is not a list — skipping.",
                board_token,
            )
            return []

        records: list[RawOpportunityRow] = []
        for job in jobs_raw:
            if not isinstance(job, dict):
                continue
            row = _parse_job(job, board_token, company_name)
            if row is not None:
                records.append(row)

        logger.info(
            "[greenhouse] Board '%s': fetched %d jobs, parsed %d records.",
            board_token,
            len(jobs_raw),
            len(records),
        )
        return records

    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch all configured Greenhouse boards in sequence.

        The Greenhouse boards-api returns all jobs for a board in one call
        (no pagination). This method fetches all boards and aggregates results.
        cursor is unused.
        """
        if cursor is not None:
            return ConnectorBatchResult(records=[], next_cursor=None)

        board_tokens = _load_board_tokens()
        if not board_tokens:
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error="No board tokens configured (GREENHOUSE_BOARD_TOKENS is empty).",
            )

        all_records: list[RawOpportunityRow] = []

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for i, token in enumerate(board_tokens):
                records = await self._fetch_board(client, token)
                all_records.extend(records)

                # Rate-limit between board requests (not before the first)
                if i < len(board_tokens) - 1 and self.rate_limit_delay > 0:
                    import asyncio

                    await asyncio.sleep(self.rate_limit_delay)

        return ConnectorBatchResult(
            records=all_records,
            next_cursor=None,
            raw_count=len(all_records),
        )

    async def run(self) -> tuple[list[RawOpportunityRow], ConnectorRunSummary]:
        """
        Override run() to provide a clear NOT_CONFIGURED message when no
        board tokens are set.
        """
        if not self.is_configured():
            logger.info(
                "[greenhouse] No board tokens configured (GREENHOUSE_BOARD_TOKENS). "
                "Skipping sync. Configure board tokens to enable Greenhouse integration."
            )
            return [], ConnectorRunSummary(
                source=self.source_name,
                status=ConnectorStatus.NOT_CONFIGURED,
                error_message=(
                    "GREENHOUSE_BOARD_TOKENS is not set or empty. "
                    "Add comma-separated employer board tokens to enable this connector."
                ),
            )
        return await super().run()
