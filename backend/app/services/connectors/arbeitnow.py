"""
Arbeitnow connector for Phase 26.3 Wave 1.

Official public API endpoint:
    GET https://www.arbeitnow.com/api/job-board-api

Documentation: https://www.arbeitnow.com/blog/a-free-api-to-search-for-remote-jobs
Authentication: None required.
Rate limits:    Standard HTTP caching headers honored; no documented rate cap.
Attribution:    Canonical Arbeitnow slug URL must be preserved.

Response schema (as of 2026):
{
  "data": [
    {
      "slug": "senior-backend-engineer-at-company-123456",
      "company_name": "Company Name",
      "title": "Senior Backend Engineer",
      "description": "...",
      "remote": true,
      "url": "https://www.arbeitnow.com/jobs/...",
      "tags": ["python", "docker"],
      "job_types": ["full_time"],
      "location": "Berlin, Germany",
      "visa_sponsorship": false,
      "created_at": 1696000000
    }
  ],
  "links": {
    "first": "...",
    "last": "...",
    "prev": null,
    "next": "https://www.arbeitnow.com/api/job-board-api?page=2"
  },
  "meta": {
    "current_page": 1,
    "from": 1,
    "last_page": 5,
    "per_page": 100
  }
}
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx

from app.core.logging import get_logger
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    _execute_with_retries,
)

logger = get_logger("connectors.arbeitnow")

_API_URL = "https://www.arbeitnow.com/api/job-board-api"

_JOB_TYPE_MAP: dict[str, str] = {
    "full_time": "fulltime",
    "part_time": "parttime",
    "contract": "contract",
    "internship": "internship",
    "freelance": "contract",
    "other": "any",
}

_MAX_PAGES = 20  # Safety cap to avoid unbounded crawl


def _extract_page_number(next_url: str | None) -> int | None:
    """Extract the page number from a pagination 'next' URL."""
    if not next_url:
        return None
    try:
        parsed = urlsplit(next_url)
        qs = parse_qs(parsed.query)
        pages = qs.get("page", [])
        if pages:
            return int(pages[0])
    except Exception:
        pass
    return None


def _resolve_employment_type(job_types: list[str]) -> str:
    """Resolve the first recognized employment type from the job_types list."""
    for jt in job_types:
        mapped = _JOB_TYPE_MAP.get(jt.lower())
        if mapped:
            return mapped
    return "fulltime"


def _resolve_opportunity_type(job_types: list[str]) -> str:
    """Determine opportunity type from job_types (intern check)."""
    for jt in job_types:
        if "intern" in jt.lower():
            return "internship"
    return "job"


def _parse_location(location_str: str | None) -> tuple[str | None, str | None, str | None]:
    """
    Parse 'City, Country' or 'City, State, Country' style location string.
    Returns (city, state, country).
    """
    if not location_str or not location_str.strip():
        return None, None, None
    parts = [p.strip() for p in location_str.split(",") if p.strip()]
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return parts[0], parts[1], parts[2]


def _parse_record(job: dict[str, Any]) -> RawOpportunityRow | None:
    """Map a single Arbeitnow job dict to RawOpportunityRow."""
    try:
        slug = (job.get("slug") or "").strip()
        if not slug:
            return None
        source_id = slug

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

        job_types: list[str] = job.get("job_types") or []
        employment_type = _resolve_employment_type(job_types)
        opportunity_type = _resolve_opportunity_type(job_types)

        is_remote: bool = bool(job.get("remote", False))
        work_mode = "remote" if is_remote else "any"

        location_str = job.get("location") or ""
        city, state, country = _parse_location(location_str)

        tags: list[str] = job.get("tags") or []
        skills = [t.strip() for t in tags if t and t.strip()]

        # Visa sponsorship — only use the explicit flag, never infer from description
        visa_sponsorship: bool | None = job.get("visa_sponsorship")
        if not isinstance(visa_sponsorship, bool):
            visa_sponsorship = None

        # Published date (epoch timestamp)
        created_at = job.get("created_at")
        posted_date: str | None = None
        if isinstance(created_at, (int, float)):
            posted_date = str(int(created_at))

        ext_meta: dict[str, Any] = {"slug": slug}
        if visa_sponsorship is not None:
            ext_meta["visa_sponsorship"] = visa_sponsorship

        return RawOpportunityRow(
            title=title,
            company=company,
            description=description,
            opportunity_type=opportunity_type,
            employment_type=employment_type,
            work_mode=work_mode,
            location_city=city,
            location_state=state,
            location_country=country,
            job_url=job_url,
            source="arbeitnow",
            source_id=source_id,
            posted_date=posted_date,
            required_skills=skills if skills else None,
            preferred_skills=None,
            is_active=True,
            external_metadata=ext_meta,
        )
    except Exception as exc:
        logger.debug("Failed to parse Arbeitnow record slug=%s: %s", job.get("slug"), exc)
        return None


class ArbeitnowConnector(BaseOpportunityConnector):
    """
    Connector for the Arbeitnow public job board API.

    Supports cursor-based pagination via the 'links.next' URL field.
    Inter-page delay: 1 second to respect public API guidelines.
    """

    source_name = "arbeitnow"
    rate_limit_delay = 1.0
    timeout = httpx.Timeout(connect=15.0, read=45.0, write=10.0, pool=10.0)

    def is_configured(self) -> bool:
        """Arbeitnow requires no credentials — always configured."""
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
        Fetch one page of Arbeitnow job listings.

        Args:
            cursor: Integer page number (1-indexed). None defaults to page 1.
        """
        page = int(cursor) if cursor is not None else 1

        if page > _MAX_PAGES:
            logger.info("[arbeitnow] Reached page cap (%d) — stopping pagination.", _MAX_PAGES)
            return ConnectorBatchResult(records=[], next_cursor=None)

        params: dict[str, Any] = {"page": page}

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            try:
                response = await _execute_with_retries(
                    client=client,
                    url=_API_URL,
                    params=params,
                    headers=self.get_auth_headers(),
                    max_retries=self.max_retries,
                    source_name=self.source_name,
                )
            except Exception as exc:
                return ConnectorBatchResult(
                    records=[],
                    next_cursor=None,
                    error=f"HTTP error on page {page}: {exc}",
                )

        try:
            payload = response.json()
        except Exception as exc:
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error=f"Invalid JSON on page {page}: {exc}",
            )

        if not isinstance(payload, dict):
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error=f"Unexpected payload type: {type(payload).__name__}",
            )

        data: list[Any] = payload.get("data") or []
        if not isinstance(data, list):
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error="'data' field is not a list",
            )

        records: list[RawOpportunityRow] = []
        for job in data:
            if not isinstance(job, dict):
                continue
            row = _parse_record(job)
            if row is not None:
                records.append(row)

        # Determine next page from links
        links: dict[str, Any] = payload.get("links") or {}
        next_url: str | None = links.get("next") or None
        next_cursor: int | None = _extract_page_number(next_url)

        # Also check meta for last_page
        meta: dict[str, Any] = payload.get("meta") or {}
        current_page: int = int(meta.get("current_page") or page)
        last_page: int = int(meta.get("last_page") or 1)
        if current_page >= last_page:
            next_cursor = None

        logger.info(
            "[arbeitnow] Page %d/%d: fetched %d raw jobs, parsed %d records.",
            current_page,
            last_page,
            len(data),
            len(records),
        )

        return ConnectorBatchResult(
            records=records,
            next_cursor=next_cursor,
            raw_count=len(data),
        )
