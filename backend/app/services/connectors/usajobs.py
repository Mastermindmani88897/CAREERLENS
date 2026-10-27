"""
USAJOBS connector for Phase 26.4 Wave 2.

Official API endpoint:
    GET https://data.usajobs.gov/api/search

Documentation: https://developer.usajobs.gov/api-reference/get-api-search
Authentication:
    HTTP Headers:
        Authorization-Key: <USAJOBS_API_KEY>
        User-Agent: <USAJOBS_EMAIL>
        Host: data.usajobs.gov
Terms & Guidelines:
    US Office of Personnel Management guidelines limit requests to max 10,000/day.
    Requires user-agent attribution with the registered developer email.

Usage strategy:
- Credentials loaded from Pydantic settings: settings.USAJOBS_API_KEY, settings.USAJOBS_EMAIL.
- If either is missing, connector reports NOT_CONFIGURED.
- Headers are passed securely and sanitized from logs and error strings.
- 1-based page navigation with configurable max_pages (default 5).
- Normalizes federal GS pay grades, telework eligibility, and application close dates.
"""

from __future__ import annotations

import os
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

logger = get_logger("connectors.usajobs")

_API_URL = "https://data.usajobs.gov/api/search"
_DEFAULT_KEYWORD = "technology"
_DEFAULT_RESULTS_PER_PAGE = 25
_DEFAULT_MAX_PAGES = 5


def _parse_iso_date(date_str: str | None) -> datetime | None:
    """Parse ISO date format returned by USAJOBS (e.g. 2026-10-31T23:59:59.9999)."""
    if not date_str:
        return None
    try:
        # USAJOBS timestamps often omit timezone or end in microseconds
        clean = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def _parse_remuneration(remuneration_list: list[Any] | None) -> tuple[int | None, int | None, str]:
    """
    Parse salary minimum, maximum, and currency from PositionRemuneration array.
    USAJOBS remuneration item:
        {
            "MinimumRange": "95000",
            "MaximumRange": "145000",
            "RateIntervalCode": "PA",  # PA = Per Annum, PH = Per Hour
            "Description": "Per Year"
        }
    """
    if not isinstance(remuneration_list, list) or not remuneration_list:
        return None, None, "USD"

    item = remuneration_list[0]
    if not isinstance(item, dict):
        return None, None, "USD"

    sal_min: int | None = None
    sal_max: int | None = None

    raw_min = item.get("MinimumRange")
    raw_max = item.get("MaximumRange")
    interval = (item.get("RateIntervalCode") or "PA").upper()

    try:
        if raw_min is not None:
            val_min = float(raw_min)
            if val_min > 0:
                # If hourly, annualize conservatively assuming 2080 hours/year
                sal_min = int(val_min * 2080) if interval == "PH" else int(val_min)
    except (ValueError, TypeError):
        pass

    try:
        if raw_max is not None:
            val_max = float(raw_max)
            if val_max > 0:
                sal_max = int(val_max * 2080) if interval == "PH" else int(val_max)
    except (ValueError, TypeError):
        pass

    return sal_min, sal_max, "USD"


def _parse_location(descriptor: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Extract city, state, country from USAJOBS descriptor."""
    locations = descriptor.get("PositionLocation")
    if isinstance(locations, list) and locations:
        loc = locations[0]
        if isinstance(loc, dict):
            city = loc.get("CityName") or None
            state = loc.get("CountrySubDivisionCode") or None
            country = loc.get("CountryCode") or "United States"
            return city, state, country

    display = descriptor.get("PositionLocationDisplay") or ""
    if display:
        parts = [p.strip() for p in display.split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1], "United States"
        return parts[0], None, "United States"

    return None, None, "United States"


def _infer_work_mode(descriptor: dict[str, Any]) -> WorkMode:
    """Determine work mode using TeleworkEligible flag and location display."""
    user_area = descriptor.get("UserArea") or {}
    details = user_area.get("Details") or {} if isinstance(user_area, dict) else {}
    telework = details.get("TeleworkEligible")

    if telework is True:
        return WorkMode.REMOTE

    loc_display = (descriptor.get("PositionLocationDisplay") or "").lower()
    title = (descriptor.get("PositionTitle") or "").lower()

    if "remote" in loc_display or "remote" in title:
        return WorkMode.REMOTE
    if "hybrid" in loc_display or "hybrid" in title:
        return WorkMode.HYBRID

    return WorkMode.ONSITE


def _infer_employment_type(descriptor: dict[str, Any]) -> tuple[OpportunityType, EmploymentType]:
    """Infer opportunity type and employment type from offerings and title."""
    title = (descriptor.get("PositionTitle") or "").lower()

    # Check for internships / pathways
    if re.search(r"\b(intern|internship|student trainee|pathways intern)\b", title):
        return OpportunityType.INTERNSHIP, EmploymentType.INTERNSHIP

    schedules = descriptor.get("PositionSchedule") or []
    if isinstance(schedules, list):
        for s in schedules:
            if isinstance(s, dict):
                s_name = (s.get("Name") or "").lower()
                if "part-time" in s_name or "part time" in s_name:
                    return OpportunityType.JOB, EmploymentType.PARTTIME

    offerings = descriptor.get("PositionOfferingType") or []
    if isinstance(offerings, list):
        for off in offerings:
            if isinstance(off, dict):
                off_name = (off.get("Name") or "").lower()
                if "internship" in off_name:
                    return OpportunityType.INTERNSHIP, EmploymentType.INTERNSHIP
                if "temporary" in off_name or "contract" in off_name:
                    return OpportunityType.JOB, EmploymentType.CONTRACT

    return OpportunityType.JOB, EmploymentType.FULLTIME


def _parse_job_item(item: dict[str, Any]) -> RawOpportunityRow | None:
    """Parse a single USAJOBS SearchResultItem into RawOpportunityRow."""
    if not isinstance(item, dict):
        return None

    matched_id = item.get("MatchedObjectId")
    if not matched_id:
        return None

    descriptor = item.get("MatchedObjectDescriptor")
    if not isinstance(descriptor, dict):
        return None

    title = (descriptor.get("PositionTitle") or "").strip()
    if not title:
        return None

    # Organization
    dept = (descriptor.get("DepartmentName") or "").strip()
    org = (descriptor.get("OrganizationName") or "").strip()
    company = dept or org or "U.S. Federal Government"

    # Description
    user_area = descriptor.get("UserArea") or {}
    details = user_area.get("Details") or {} if isinstance(user_area, dict) else {}
    summary_text = (details.get("JobSummary") or "").strip()
    if not summary_text:
        duties = details.get("MajorDuties") or []
        if isinstance(duties, list) and duties:
            summary_text = " ".join(str(d) for d in duties)
    if not summary_text:
        summary_text = f"{title} position with {company}."

    # URL
    position_uri = descriptor.get("PositionURI") or ""
    apply_uris = descriptor.get("ApplyURI") or []
    job_url = ""
    if isinstance(apply_uris, list) and apply_uris:
        job_url = str(apply_uris[0]).strip()
    if not job_url:
        job_url = position_uri.strip() or f"https://www.usajobs.gov/GetJob/ViewDetails/{matched_id}"

    # Location
    city, state, country = _parse_location(descriptor)

    # Remuneration / Salary
    salary_min, salary_max, currency = _parse_remuneration(descriptor.get("PositionRemuneration"))

    # Dates
    pub_dt = _parse_iso_date(descriptor.get("PublicationStartDate"))
    posted_date = pub_dt.date() if pub_dt else None

    close_dt = _parse_iso_date(descriptor.get("ApplicationCloseDate"))
    deadline_date = close_dt.date() if close_dt else None

    # Work mode & Employment type
    work_mode = _infer_work_mode(descriptor)
    opp_type, emp_type = _infer_employment_type(descriptor)

    # Skills / Categories
    job_categories = descriptor.get("JobCategory") or []
    skills: list[str] = []
    if isinstance(job_categories, list):
        for cat in job_categories:
            if isinstance(cat, dict):
                cat_name = (cat.get("Name") or "").strip()
                if cat_name:
                    skills.append(cat_name)

    source_id = f"usajobs-{matched_id}"

    metadata: dict[str, Any] = {
        "position_id": descriptor.get("PositionID"),
        "telework_eligible": details.get("TeleworkEligible"),
        "job_grade": descriptor.get("JobGrade"),
        "department": dept,
        "organization": org,
    }

    return RawOpportunityRow(
        title=title,
        company=company,
        description=summary_text,
        opportunity_type=opp_type,
        employment_type=emp_type,
        work_mode=work_mode,
        location_city=city,
        location_state=state,
        location_country=country,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=currency if (salary_min or salary_max) else None,
        job_url=job_url,
        application_url=job_url,
        source=OpportunitySource.USAJOBS,
        source_id=source_id,
        posted_date=posted_date,
        application_deadline=deadline_date,
        required_skills=skills if skills else None,
        is_active=True,
        external_metadata=metadata,
    )


class USAJOBSConnector(BaseOpportunityConnector):
    """
    Connector for the official USAJOBS Search REST API.

    Requires USAJOBS_API_KEY and USAJOBS_EMAIL configured in settings or environment.
    Reports NOT_CONFIGURED when either credential is missing.
    """

    source_name: str = "usajobs"
    source_enum: OpportunitySource = OpportunitySource.USAJOBS

    def __init__(
        self,
        keyword: str = _DEFAULT_KEYWORD,
        results_per_page: int = _DEFAULT_RESULTS_PER_PAGE,
        max_pages: int = _DEFAULT_MAX_PAGES,
    ) -> None:
        self.keyword = keyword
        self.results_per_page = max(1, min(results_per_page, 100))
        self.max_pages = max(1, max_pages)

    def _get_credentials(self) -> tuple[str, str]:
        """Retrieve API key and email safely without logging values."""
        api_key = os.environ.get("USAJOBS_API_KEY")
        email = os.environ.get("USAJOBS_EMAIL")
        if api_key is None or email is None:
            from app.core.config import settings

            if api_key is None:
                api_key = getattr(settings, "USAJOBS_API_KEY", "")
            if email is None:
                email = getattr(settings, "USAJOBS_EMAIL", "")

        return (api_key or "").strip(), (email or "").strip()

    def is_configured(self) -> bool:
        """Return True if both API key and developer email are configured."""
        api_key, email = self._get_credentials()
        return bool(
            api_key and email and not api_key.startswith("your_") and not email.startswith("your_")
        )

    def get_auth_headers(self) -> dict[str, str]:
        """Return required USAJOBS API headers with developer credentials."""
        api_key, email = self._get_credentials()
        return {
            "Host": "data.usajobs.gov",
            "User-Agent": email,
            "Authorization-Key": api_key,
        }

    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch a single page of results from the USAJOBS API.

        Args:
            cursor: 1-indexed page number (defaults to 1).
        """
        if not self.is_configured():
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=(
                    "USAJOBS connector is not configured. Missing USAJOBS_API_KEY or USAJOBS_EMAIL."
                ),
            )

        page = int(cursor) if cursor else 1
        headers = self.get_auth_headers()
        params: dict[str, Any] = {
            "Keyword": self.keyword,
            "ResultsPerPage": self.results_per_page,
            "Page": page,
        }

        logger.info(
            "[usajobs] Fetching page %d (keyword=%s, results_per_page=%d)",
            page,
            self.keyword,
            self.results_per_page,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await _execute_with_retries(
                    client=client,
                    url=_API_URL,
                    params=params,
                    headers=headers,
                    source_name=self.source_name,
                )
        except Exception as exc:
            # Mask any accidental header leaks in exception string
            sanitized_err = re.sub(
                r"Authorization-Key:\s*\S+", "Authorization-Key: [REDACTED]", str(exc)
            )
            logger.error("[usajobs] HTTP fetch failed on page %d: %s", page, sanitized_err)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error=sanitized_err
            )

        if response.status_code in (401, 403):
            logger.error("[usajobs] Authentication error: HTTP %d", response.status_code)
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=(
                    f"USAJOBS API credentials rejected (HTTP {response.status_code}). "
                    "Verify USAJOBS_API_KEY and USAJOBS_EMAIL."
                ),
            )

        if response.status_code != 200:
            logger.warning(
                "[usajobs] Unexpected HTTP status %d on page %d", response.status_code, page
            )
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=f"USAJOBS API returned HTTP {response.status_code}",
            )

        try:
            payload = response.json()
        except Exception as exc:
            logger.error("[usajobs] Failed to parse JSON response: %s", exc)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error=f"Invalid JSON: {exc}"
            )

        if not isinstance(payload, dict):
            logger.error("[usajobs] Expected dict root in response, got %s", type(payload).__name__)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error="Malformed JSON structure"
            )

        search_result = payload.get("SearchResult")
        if not isinstance(search_result, dict):
            logger.error("[usajobs] Missing 'SearchResult' in payload")
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error="Missing 'SearchResult' object"
            )

        items = search_result.get("SearchResultItems")
        if not isinstance(items, list):
            logger.error("[usajobs] Missing 'SearchResultItems' in SearchResult")
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error="Missing 'SearchResultItems' array"
            )

        records: list[RawOpportunityRow] = []
        for item in items:
            parsed = _parse_job_item(item)
            if parsed is not None:
                records.append(parsed)

        total_count = search_result.get("SearchResultCountAll", 0)
        logger.info(
            "[usajobs] Page %d: parsed %d/%d items (total count: %d)",
            page,
            len(records),
            len(items),
            total_count,
        )

        has_more = page < self.max_pages and len(items) >= self.results_per_page
        next_cursor = page + 1 if has_more else None

        return ConnectorBatchResult(
            records=records,
            next_cursor=next_cursor,
            raw_count=len(items),
        )
