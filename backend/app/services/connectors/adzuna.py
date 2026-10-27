"""
Adzuna connector for Phase 26.4 Wave 2.

Official API endpoint:
    GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}

Documentation: https://developer.adzuna.com/overview
Authentication:
    Passed as query parameters: ?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}
Terms & Attribution:
    Explicit requirement to preserve the original Adzuna canonical redirect_url
    and attribute results to Adzuna.

Usage strategy:
- Credentials loaded from Pydantic settings: settings.ADZUNA_APP_ID, settings.ADZUNA_APP_KEY.
- If credentials are empty or missing, connector reports NOT_CONFIGURED.
- Bounded pagination with configurable max_pages (default 5) to respect monthly API quotas.
- Default country is configurable (default "us"). Supports "gb", "in", "ca", "au", etc.
- Safe parsing of salary ranges, location hierarchies, and employment types.
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

logger = get_logger("connectors.adzuna")

_API_BASE = "https://api.adzuna.com/v1/api/jobs"
_DEFAULT_COUNTRY = "us"
_DEFAULT_PAGE_SIZE = 20
_DEFAULT_MAX_PAGES = 5

_CURRENCY_BY_COUNTRY: dict[str, str] = {
    "us": "USD",
    "gb": "GBP",
    "uk": "GBP",
    "in": "INR",
    "ca": "CAD",
    "au": "AUD",
    "nz": "NZD",
    "de": "EUR",
    "fr": "EUR",
    "nl": "EUR",
    "it": "EUR",
    "es": "EUR",
    "at": "EUR",
    "be": "EUR",
    "pl": "PLN",
    "br": "BRL",
    "sg": "SGD",
    "za": "ZAR",
}


def _strip_html(text: str | None) -> str:
    """Remove HTML tags (e.g. <strong>) returned in Adzuna highlight snippets."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return " ".join(clean.split()).strip()


def _parse_created_date(created: str | None) -> datetime | None:
    """Parse ISO date format returned by Adzuna (e.g. 2026-10-15T12:00:00Z)."""
    if not created:
        return None
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def _parse_location(
    location_data: dict[str, Any] | None,
    default_country: str,
) -> tuple[str | None, str | None, str | None]:
    """
    Extract (city, state, country) from Adzuna location object.
    Adzuna returns:
        location: {
            "display_name": "San Francisco, San Francisco County, California",
            "area": ["US", "California", "San Francisco County", "San Francisco"]
        }
    """
    if not isinstance(location_data, dict):
        return None, None, default_country.upper()

    area = location_data.get("area") or []
    if isinstance(area, list) and len(area) >= 2:
        country = str(area[0]).strip() if len(area) > 0 else default_country.upper()
        state = str(area[1]).strip() if len(area) > 1 else None
        city = str(area[-1]).strip() if len(area) > 2 else None
        return city, state, country

    display = (location_data.get("display_name") or "").strip()
    if display:
        parts = [p.strip() for p in display.split(",") if p.strip()]
        if len(parts) >= 3:
            return parts[0], parts[-1], default_country.upper()
        if len(parts) == 2:
            return parts[0], None, parts[1]
        return parts[0], None, default_country.upper()

    return None, None, default_country.upper()


def _infer_work_mode(title: str, description: str, location_str: str = "") -> WorkMode:
    """Infer work mode from job title, description, or location text."""
    combined = f"{title} {location_str} {description[:300]}".lower()
    if re.search(r"\b(remote|work from home|wfh|telecommute|anywhere)\b", combined):
        return WorkMode.REMOTE
    if re.search(r"\b(hybrid)\b", combined):
        return WorkMode.HYBRID
    return WorkMode.ANY


def _infer_employment_type(
    title: str, contract_time: str | None, contract_type: str | None
) -> EmploymentType:
    """Infer employment type from Adzuna contract fields and job title."""
    title_lower = title.lower()
    if re.search(r"\b(intern|internship|co-?op)\b", title_lower):
        return EmploymentType.INTERNSHIP

    ct = (contract_time or "").lower().strip()
    c_type = (contract_type or "").lower().strip()

    if ct == "full_time" or c_type == "permanent":
        return EmploymentType.FULLTIME
    if ct == "part_time":
        return EmploymentType.PARTTIME
    if c_type == "contract":
        return EmploymentType.CONTRACT

    return EmploymentType.FULLTIME


def _parse_record(job: dict[str, Any], country: str) -> RawOpportunityRow | None:
    """
    Parse a single Adzuna job result into RawOpportunityRow.
    Returns None if mandatory fields (title, id) are absent.
    """
    if not isinstance(job, dict):
        return None

    raw_id = job.get("id")
    if not raw_id:
        return None

    raw_title = job.get("title") or ""
    clean_title = _strip_html(raw_title)
    if not clean_title:
        return None

    company_data = job.get("company")
    company_name = ""
    if isinstance(company_data, dict):
        company_name = (company_data.get("display_name") or "").strip()
    if not company_name:
        company_name = "Company Unspecified"

    raw_desc = job.get("description") or ""
    clean_desc = _strip_html(raw_desc)
    if not clean_desc:
        clean_desc = f"{clean_title} opportunity at {company_name}."

    redirect_url = (job.get("redirect_url") or "").strip()
    if not redirect_url:
        redirect_url = f"https://www.adzuna.com/details/{raw_id}"

    # Location parsing
    location_data = job.get("location")
    city, state, parsed_country = _parse_location(location_data, country)

    # Salary parsing
    salary_min: int | None = None
    salary_max: int | None = None
    raw_min = job.get("salary_min")
    raw_max = job.get("salary_max")

    if raw_min is not None:
        try:
            val = float(raw_min)
            if val > 0:
                salary_min = int(val)
        except (ValueError, TypeError):
            pass

    if raw_max is not None:
        try:
            val = float(raw_max)
            if val > 0:
                salary_max = int(val)
        except (ValueError, TypeError):
            pass

    currency = _CURRENCY_BY_COUNTRY.get(country.lower(), "USD")

    # Dates
    created_dt = _parse_created_date(job.get("created"))
    posted_date = created_dt.date() if created_dt else None

    # Work mode & employment type
    loc_display = (
        (location_data.get("display_name") or "") if isinstance(location_data, dict) else ""
    )
    work_mode = _infer_work_mode(clean_title, clean_desc, loc_display)
    emp_type = _infer_employment_type(
        clean_title, job.get("contract_time"), job.get("contract_type")
    )

    # Skills from category
    category_data = job.get("category")
    skills: list[str] = []
    if isinstance(category_data, dict):
        cat_tag = (category_data.get("tag") or "").strip()
        cat_label = (category_data.get("label") or "").strip()
        if cat_label and cat_label.lower() != "jobs":
            skills.append(cat_label)
        elif cat_tag:
            skills.append(cat_tag.replace("-", " ").title())

    # Deterministic source ID scoped by country
    source_id = f"adzuna-{country.lower()}-{raw_id}"

    external_metadata: dict[str, Any] = {
        "adzuna_id": str(raw_id),
        "country": country.lower(),
        "salary_is_predicted": job.get("salary_is_predicted"),
        "contract_time": job.get("contract_time"),
        "contract_type": job.get("contract_type"),
    }
    if isinstance(category_data, dict):
        external_metadata["category"] = category_data.get("tag")

    return RawOpportunityRow(
        title=clean_title,
        company=company_name,
        description=clean_desc,
        opportunity_type=OpportunityType.JOB
        if emp_type != EmploymentType.INTERNSHIP
        else OpportunityType.INTERNSHIP,
        employment_type=emp_type,
        work_mode=work_mode,
        location_city=city,
        location_state=state,
        location_country=parsed_country or country.upper(),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=currency if (salary_min or salary_max) else None,
        job_url=redirect_url,
        source=OpportunitySource.ADZUNA,
        source_id=source_id,
        posted_date=posted_date,
        required_skills=skills if skills else None,
        is_active=True,
        external_metadata=external_metadata,
    )


class AdzunaConnector(BaseOpportunityConnector):
    """
    Connector for the official Adzuna job search API.

    Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in settings or environment.
    Reports NOT_CONFIGURED when credentials are not supplied.
    """

    source_name: str = "adzuna"
    source_enum: OpportunitySource = OpportunitySource.ADZUNA

    def __init__(
        self,
        country: str = _DEFAULT_COUNTRY,
        what: str | None = None,
        where: str | None = None,
        results_per_page: int = _DEFAULT_PAGE_SIZE,
        max_pages: int = _DEFAULT_MAX_PAGES,
    ) -> None:
        self.country = country.lower().strip() or _DEFAULT_COUNTRY
        self.what = what
        self.where = where
        self.results_per_page = max(1, min(results_per_page, 50))
        self.max_pages = max(1, max_pages)

    def _get_credentials(self) -> tuple[str, str]:
        """Retrieve App ID and App Key from settings or environment without logging secrets."""
        app_id = os.environ.get("ADZUNA_APP_ID")
        app_key = os.environ.get("ADZUNA_APP_KEY")
        if app_id is None or app_key is None:
            from app.core.config import settings

            if app_id is None:
                app_id = getattr(settings, "ADZUNA_APP_ID", "")
            if app_key is None:
                app_key = getattr(settings, "ADZUNA_APP_KEY", "")

        return (app_id or "").strip(), (app_key or "").strip()

    def is_configured(self) -> bool:
        """Return True if both App ID and App Key are provided."""
        app_id, app_key = self._get_credentials()
        return bool(
            app_id
            and app_key
            and not app_id.startswith("your_")
            and not app_key.startswith("your_")
        )

    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch a single page of results from the Adzuna API.

        Args:
            cursor: 1-indexed page number (defaults to 1 if None).
        """
        if not self.is_configured():
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=(
                    "Adzuna connector is not configured. Missing ADZUNA_APP_ID or ADZUNA_APP_KEY."
                ),
            )

        app_id, app_key = self._get_credentials()
        page = int(cursor) if cursor else 1

        url = f"{_API_BASE}/{self.country}/search/{page}"
        params: dict[str, Any] = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": self.results_per_page,
            "content-type": "application/json",
        }
        if self.what:
            params["what"] = self.what
        if self.where:
            params["where"] = self.where

        logger.info(
            "[adzuna] Fetching page %d (country=%s, results_per_page=%d)",
            page,
            self.country,
            self.results_per_page,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await _execute_with_retries(
                    client=client,
                    url=url,
                    params=params,
                    source_name=self.source_name,
                )
        except Exception as exc:
            logger.error("[adzuna] HTTP fetch failed on page %d: %s", page, exc)
            return ConnectorBatchResult(records=[], next_cursor=None, raw_count=0, error=str(exc))

        if response.status_code in (401, 403):
            logger.error("[adzuna] Authentication or quota error: HTTP %d", response.status_code)
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=(
                    "Adzuna API credentials rejected or quota exhausted "
                    f"(HTTP {response.status_code})."
                ),
            )

        if response.status_code != 200:
            logger.warning(
                "[adzuna] Unexpected HTTP status %d on page %d", response.status_code, page
            )
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=f"Adzuna API returned HTTP {response.status_code}",
            )

        try:
            payload = response.json()
        except Exception as exc:
            logger.error("[adzuna] Failed to parse JSON response: %s", exc)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error=f"Invalid JSON: {exc}"
            )

        if not isinstance(payload, dict):
            logger.error("[adzuna] Expected dict root in response, got %s", type(payload).__name__)
            return ConnectorBatchResult(
                records=[], next_cursor=None, raw_count=0, error="Malformed JSON response structure"
            )

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            logger.error("[adzuna] Missing 'results' array in payload")
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error="Missing 'results' array in response",
            )

        records: list[RawOpportunityRow] = []
        for item in raw_results:
            parsed = _parse_record(item, self.country)
            if parsed is not None:
                records.append(parsed)

        total_available = payload.get("count", 0)
        logger.info(
            "[adzuna] Page %d: parsed %d/%d items (total available: %d)",
            page,
            len(records),
            len(raw_results),
            total_available,
        )

        # Determine next cursor
        has_more = page < self.max_pages and len(raw_results) >= self.results_per_page
        next_cursor = page + 1 if has_more else None

        return ConnectorBatchResult(
            records=records,
            next_cursor=next_cursor,
            raw_count=len(raw_results),
        )
