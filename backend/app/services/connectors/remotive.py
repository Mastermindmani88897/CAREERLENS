"""
Remotive connector for Phase 26.3 Wave 1.

Official public API endpoint:
    GET https://remotive.com/api/remote-jobs
    GET https://remotive.com/api/remote-jobs?category=<slug>

Documentation: https://remotive.com/api/remote-jobs
Authentication: None required.
Rate limits:    Max ~4 requests per minute; <=4 syncs/day recommended.
Attribution:    Canonical Remotive listing URL must be preserved.

Response schema (as of 2026):
{
  "job-count": 1234,
  "jobs": [
    {
      "id": 123456,
      "url": "https://remotive.com/remote-jobs/...",
      "title": "...",
      "company_name": "...",
      "company_logo": "https://...",
      "category": "Software Development",
      "tags": ["python", "django"],
      "job_type": "full_time",
      "publication_date": "2026-10-01T12:00:00",
      "candidate_required_location": "Worldwide",
      "salary": "$80,000 - $120,000",
      "description": "<p>...</p>"
    }
  ]
}

Note: Remotive does not support cursor/offset pagination — the full list is returned
in one call. The `limit` parameter is not documented. Category filtering is available
via ?category=<slug> but for full ingestion we call without category filter.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    _execute_with_retries,
)

logger = get_logger("connectors.remotive")

_API_URL = "https://remotive.com/api/remote-jobs"

# Map Remotive job_type strings to canonical employment type strings
_JOB_TYPE_MAP: dict[str, str] = {
    "full_time": "fulltime",
    "part_time": "parttime",
    "contract": "contract",
    "internship": "internship",
    "freelance": "contract",
    "other": "any",
}

# Reasonable upper bound on records fetched per run to avoid hammering
_MAX_RECORDS = 2000


def _parse_salary(salary_str: str | None) -> tuple[int | None, int | None, str | None]:
    """
    Parse Remotive salary string (e.g. '$80,000 - $120,000 a year') into
    (salary_min, salary_max, currency).

    Returns (None, None, None) when parsing fails or salary is missing.
    """
    if not salary_str or not salary_str.strip():
        return None, None, None

    # Detect currency symbol
    currency: str | None = None
    if "$" in salary_str:
        currency = "USD"
    elif "€" in salary_str:
        currency = "EUR"
    elif "£" in salary_str:
        currency = "GBP"

    # Extract numeric values (handles commas and k-suffix patterns)
    nums = re.findall(r"[\d,]+(?:k)?", salary_str.lower())
    parsed: list[int] = []
    for n in nums:
        raw = n.replace(",", "")
        multiplier = 1
        if raw.endswith("k"):
            multiplier = 1000
            raw = raw[:-1]
        try:
            parsed.append(int(float(raw) * multiplier))
        except ValueError:
            continue

    if len(parsed) == 0:
        return None, None, currency
    if len(parsed) == 1:
        return parsed[0], parsed[0], currency
    return min(parsed[0], parsed[1]), max(parsed[0], parsed[1]), currency


def _parse_record(job: dict[str, Any]) -> RawOpportunityRow | None:
    """
    Map a single Remotive job dict to a RawOpportunityRow.

    Returns None on critical field failures.
    """
    try:
        job_id = job.get("id")
        if not job_id:
            return None
        source_id = str(job_id)

        title = (job.get("title") or "").strip()
        if not title:
            return None

        company = (job.get("company_name") or "").strip()
        if not company:
            return None

        description = (job.get("description") or "").strip()
        if not description:
            return None

        job_url = (job.get("url") or "").strip() or None

        # Employment type
        job_type_raw = job.get("job_type") or ""
        employment_type = _JOB_TYPE_MAP.get(job_type_raw.lower(), "fulltime")

        # Opportunity type
        opportunity_type = "job"
        if employment_type == "internship":
            opportunity_type = "internship"

        # Work mode — Remotive is exclusively remote
        work_mode = "remote"

        # Candidate required location → location field
        candidate_location = (job.get("candidate_required_location") or "").strip() or None

        # Salary
        salary_min, salary_max, salary_currency = _parse_salary(job.get("salary"))

        # Tags → skills
        tags: list[str] = job.get("tags") or []
        skills: list[str] = [t.strip() for t in tags if t and t.strip()]

        # Published date
        posted_date: str | None = job.get("publication_date") or None

        return RawOpportunityRow(
            title=title,
            company=company,
            description=description,
            opportunity_type=opportunity_type,
            employment_type=employment_type,
            work_mode=work_mode,
            location_city=None,
            location_state=None,
            # Treat candidate_required_location as city-level if present
            location_country=candidate_location,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            job_url=job_url,
            source="remotive",
            source_id=source_id,
            posted_date=posted_date,
            required_skills=skills if skills else None,
            preferred_skills=None,
            is_active=True,
            external_metadata={
                "remotive_id": job_id,
                "category": job.get("category") or "",
                "company_logo": job.get("company_logo") or "",
            },
        )
    except Exception as exc:
        logger.debug("Failed to parse Remotive record id=%s: %s", job.get("id"), exc)
        return None


class RemotiveConnector(BaseOpportunityConnector):
    """
    Connector for the Remotive public job listing API.

    Remotive returns its complete listing in a single API call (no pagination).
    The connector fetches once and returns all records.

    Rate limit: 1 request per sync run (full listing, no per-page cursor).
    """

    source_name = "remotive"
    rate_limit_delay = 0.0  # Single request — no inter-page delay needed
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=10.0, pool=10.0)

    def is_configured(self) -> bool:
        """Remotive requires no credentials — always configured."""
        return True

    def get_auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "CareerLens/1.0 (https://github.com/Mastermindmani88897/CAREERLENS)",
        }

    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch the full Remotive job listing in a single request.

        Remotive does not support pagination; cursor is unused.
        """
        # Remotive returns all records in one call — skip if already fetched
        if cursor is not None:
            # We signal completion by returning no next cursor
            return ConnectorBatchResult(records=[], next_cursor=None)

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            try:
                response = await _execute_with_retries(
                    client=client,
                    url=_API_URL,
                    headers=self.get_auth_headers(),
                    max_retries=self.max_retries,
                    source_name=self.source_name,
                )
            except Exception as exc:
                return ConnectorBatchResult(
                    records=[],
                    next_cursor=None,
                    error=f"HTTP error: {exc}",
                )

        try:
            payload = response.json()
        except Exception as exc:
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error=f"Invalid JSON response: {exc}",
            )

        if not isinstance(payload, dict):
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error=f"Unexpected top-level type: {type(payload).__name__}",
            )

        jobs_raw: list[Any] = payload.get("jobs") or []
        if not isinstance(jobs_raw, list):
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error="'jobs' field is not a list",
            )

        records: list[RawOpportunityRow] = []
        for job in jobs_raw[:_MAX_RECORDS]:
            if not isinstance(job, dict):
                continue
            row = _parse_record(job)
            if row is not None:
                records.append(row)

        logger.info(
            "[remotive] Fetched %d raw jobs, parsed %d valid records.",
            len(jobs_raw),
            len(records),
        )

        # No next cursor — single-page API
        return ConnectorBatchResult(
            records=records,
            next_cursor=None,
            raw_count=len(jobs_raw),
        )
