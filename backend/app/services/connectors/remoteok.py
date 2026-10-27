"""
Remote OK connector for Phase 26.4 Wave 2.

Official public API endpoint:
    GET https://remoteok.com/api

Documentation: https://remoteok.com/api
Authentication: None required for public feed.
Terms & Attribution:
    Explicit requirement to credit Remote OK and provide direct, un-redirected
    canonical links to the original Remote OK listing.
    A descriptive User-Agent header must be sent to comply with fair-use access.

Response structure:
    JSON array where element 0 is a legal / disclaimer object:
    [
        {"legal": "...", "terms": "..."},
        {
            "id": "100234",
            "epoch": 1729000000,
            "date": "2026-10-15T12:00:00+00:00",
            "company": "Acme Remote",
            "position": "Senior Python Engineer",
            "tags": ["python", "fastapi", "postgres"],
            "description": "<p>Description...</p>",
            "location": "Worldwide",
            "salary_min": 100000,
            "salary_max": 140000,
            "apply_url": "https://remoteok.com/remote-jobs/100234-senior-python-engineer",
            "url": "https://remoteok.com/remote-jobs/100234"
        }
    ]
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.logging import get_logger
from app.models.enums import EmploymentType, OpportunitySource, OpportunityType, WorkMode
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    _execute_with_retries,
)

logger = get_logger("connectors.remoteok")

_API_URL = "https://remoteok.com/api"
_USER_AGENT = "CareerLens/0.5.0 (https://github.com/Mastermindmani88897/CAREERLENS)"


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse ISO date format returned by Remote OK."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def _clean_skills(tags: list[Any] | None) -> list[str]:
    """Filter generic keywords and format technical skills from Remote OK tags."""
    if not isinstance(tags, list):
        return []

    generic = {"remote", "jobs", "work", "full time", "tech", "dev"}
    skills: list[str] = []
    for tag in tags:
        if isinstance(tag, str):
            clean = tag.strip().lower()
            if clean and clean not in generic:
                skills.append(clean)
    return skills


def _infer_employment_type(title: str, tags: list[str]) -> tuple[OpportunityType, EmploymentType]:
    """Infer opportunity and employment types from job title and tags."""
    title_lower = title.lower()
    tag_set = {t.lower() for t in tags}

    if (
        re.search(r"\b(intern|internship|co-?op)\b", title_lower)
        or "intern" in tag_set
        or "internship" in tag_set
    ):
        return OpportunityType.INTERNSHIP, EmploymentType.INTERNSHIP

    if "part-time" in tag_set or "part time" in tag_set:
        return OpportunityType.JOB, EmploymentType.PARTTIME
    if "contract" in tag_set or "freelance" in tag_set:
        return OpportunityType.JOB, EmploymentType.CONTRACT

    return OpportunityType.JOB, EmploymentType.FULLTIME


def _parse_salary(item: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
    """Extract salary min, max, and currency from Remote OK item."""
    raw_min = item.get("salary_min")
    raw_max = item.get("salary_max")

    sal_min: int | None = None
    sal_max: int | None = None

    if raw_min is not None:
        try:
            val = float(raw_min)
            if val > 0:
                sal_min = int(val)
        except (ValueError, TypeError):
            pass

    if raw_max is not None:
        try:
            val = float(raw_max)
            if val > 0:
                sal_max = int(val)
        except (ValueError, TypeError):
            pass

    # Remote OK salaries are listed in USD
    currency = "USD" if (sal_min or sal_max) else None
    return sal_min, sal_max, currency


def _parse_record(item: dict[str, Any]) -> RawOpportunityRow | None:
    """
    Parse a single Remote OK item into a RawOpportunityRow.
    Skips the legal/metadata disclaimer object and incomplete entries.
    """
    if not isinstance(item, dict):
        return None

    # Skip legal disclaimer object
    if "legal" in item or "terms" in item:
        return None

    raw_id = item.get("id")
    if not raw_id:
        return None

    title = (item.get("position") or "").strip()
    if not title:
        return None

    company = (item.get("company") or "").strip()
    if not company:
        company = "Company Unspecified"

    description = (item.get("description") or "").strip()
    if not description:
        description = f"{title} remote position at {company}."

    canonical_url = (item.get("url") or item.get("apply_url") or "").strip()
    if not canonical_url:
        canonical_url = f"https://remoteok.com/remote-jobs/{raw_id}"

    location_str = (item.get("location") or "").strip() or "Remote / Worldwide"

    # Dates
    dt = _parse_date(item.get("date"))
    posted_date = dt.date() if dt else None

    # Skills & types
    skills = _clean_skills(item.get("tags"))
    opp_type, emp_type = _infer_employment_type(title, skills)
    sal_min, sal_max, currency = _parse_salary(item)

    source_id = f"remoteok-{raw_id}"

    metadata: dict[str, Any] = {
        "remoteok_id": str(raw_id),
        "epoch": item.get("epoch"),
        "raw_location": location_str,
        "attribution": "Remote OK (https://remoteok.com)",
    }

    return RawOpportunityRow(
        title=title,
        company=company,
        description=description,
        opportunity_type=opp_type,
        employment_type=emp_type,
        work_mode=WorkMode.REMOTE,  # All Remote OK jobs are remote
        location_city=None,
        location_state=None,
        location_country=location_str if location_str != "Remote / Worldwide" else None,
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=currency,
        job_url=canonical_url,
        application_url=item.get("apply_url") or canonical_url,
        source=OpportunitySource.REMOTEOK,
        source_id=source_id,
        posted_date=posted_date,
        required_skills=skills if skills else None,
        is_active=True,
        external_metadata=metadata,
    )


class RemoteOKConnector(BaseOpportunityConnector):
    """
    Connector for the public Remote OK JSON feed.

    Operates without API keys. Requires user-agent attribution.
    Automatically filters the feed disclaimer header.
    """

    source_name: str = "remoteok"
    source_enum: OpportunitySource = OpportunitySource.REMOTEOK

    def __init__(self, limit: int | None = None) -> None:
        self.limit = limit

    def is_configured(self) -> bool:
        """Remote OK is a zero-credential public feed, always configured."""
        return True

    def get_auth_headers(self) -> dict[str, str]:
        """Return honest user-agent header required by Remote OK."""
        return {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch the entire public feed in a single batch (Remote OK does not support pagination).
        """
        headers = self.get_auth_headers()
        logger.info("[remoteok] Fetching public remote jobs feed from %s", _API_URL)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await _execute_with_retries(
                    client=client,
                    url=_API_URL,
                    headers=headers,
                    source_name=self.source_name,
                )
        except Exception as exc:
            logger.error("[remoteok] HTTP fetch failed: %s", exc)
            return ConnectorBatchResult(records=[], next_cursor=None, raw_count=0, error=str(exc))

        if response.status_code != 200:
            logger.warning("[remoteok] Feed returned HTTP %d", response.status_code)
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=f"Remote OK feed returned HTTP {response.status_code}",
            )

        try:
            payload = response.json()
        except Exception as exc:
            logger.error("[remoteok] Failed to parse JSON response: %s", exc)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error=f"Invalid JSON: {exc}"
            )

        if not isinstance(payload, list):
            logger.error("[remoteok] Expected JSON array root, got %s", type(payload).__name__)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error="Malformed JSON structure"
            )

        records: list[RawOpportunityRow] = []
        raw_items_count = 0

        for item in payload:
            if isinstance(item, dict) and "id" in item:
                raw_items_count += 1
                parsed = _parse_record(item)
                if parsed is not None:
                    records.append(parsed)
                    if self.limit and len(records) >= self.limit:
                        break

        logger.info("[remoteok] Parsed %d/%d job records from feed.", len(records), raw_items_count)

        return ConnectorBatchResult(
            records=records,
            next_cursor=None,
            raw_count=raw_items_count,
        )
