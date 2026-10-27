"""
Lever connector for Phase 26.4 Wave 2.

Official public API endpoint:
    GET https://api.lever.co/v0/postings/{company}?mode=json

Documentation: https://hire.lever.co/developer/documentation#get-all-postings
Authentication: None required for public job postings.

Usage strategy:
- Configured via LEVER_SITE_TOKENS environment variable / settings (comma-separated company slugs).
- Each slug represents an employer's Lever public job board (e.g. "spotify", "palantir").
- If LEVER_SITE_TOKENS is empty or not set, connector reports NOT_CONFIGURED.
- Multi-employer aggregation with per-employer fault isolation: failure on one employer
  does not break or abort fetches for other employers.
- Deterministic board-scoped source IDs: "lever-{company_slug}-{id}".
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

logger = get_logger("connectors.lever")

_API_BASE = "https://api.lever.co/v0/postings"
_ENV_VAR = "LEVER_SITE_TOKENS"


def _load_site_tokens() -> list[str]:
    """Load and parse the LEVER_SITE_TOKENS setting/environment variable."""
    raw = os.environ.get(_ENV_VAR)
    if raw is None:
        from app.core.config import settings

        raw = getattr(settings, _ENV_VAR, "")
    raw = (raw or "").strip()
    if not raw:
        return []
    tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return tokens


def _normalize_company_name(slug: str) -> str:
    """Convert company slug to readable company name (e.g. 'my-tech' -> 'My Tech')."""
    cleaned = re.sub(r"[-_]+", " ", slug)
    return cleaned.title()


def _split_location(loc_str: str | None) -> tuple[str | None, str | None, str | None]:
    """Parse city, state, country from Lever location string."""
    if not loc_str:
        return None, None, None
    parts = [p.strip() for p in loc_str.split(",") if p.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return parts[0], None, None


def _infer_work_mode(workplace_type: str | None, title: str, location_str: str) -> WorkMode:
    """Infer work mode from workplaceType, title, or location text."""
    wt = (workplace_type or "").lower().strip()
    if wt == "remote":
        return WorkMode.REMOTE
    if wt == "hybrid":
        return WorkMode.HYBRID
    if wt == "onsite":
        return WorkMode.ONSITE

    combined = f"{title} {location_str}".lower()
    if "remote" in combined or "wfh" in combined:
        return WorkMode.REMOTE
    if "hybrid" in combined:
        return WorkMode.HYBRID
    return WorkMode.ANY


def _infer_employment_type(
    commitment: str | None, title: str
) -> tuple[OpportunityType, EmploymentType]:
    """Infer opportunity type and employment type from categories.commitment and title."""
    title_lower = title.lower()
    if re.search(r"\b(intern|internship|co-?op)\b", title_lower):
        return OpportunityType.INTERNSHIP, EmploymentType.INTERNSHIP

    c = (commitment or "").lower().strip()
    if "intern" in c:
        return OpportunityType.INTERNSHIP, EmploymentType.INTERNSHIP
    if "part-time" in c or "part time" in c:
        return OpportunityType.JOB, EmploymentType.PARTTIME
    if "contract" in c or "freelance" in c:
        return OpportunityType.JOB, EmploymentType.CONTRACT

    return OpportunityType.JOB, EmploymentType.FULLTIME


def _parse_salary(salary_range: dict[str, Any] | None) -> tuple[int | None, int | None, str | None]:
    """Extract salary min, max, and currency from Lever salaryRange object."""
    if not isinstance(salary_range, dict):
        return None, None, None

    raw_min = salary_range.get("min")
    raw_max = salary_range.get("max")
    currency = salary_range.get("currency") or "USD"

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

    return sal_min, sal_max, currency if (sal_min or sal_max) else None


def _parse_posting(posting: dict[str, Any], company_slug: str) -> RawOpportunityRow | None:
    """Parse a single Lever posting dict into a RawOpportunityRow."""
    if not isinstance(posting, dict):
        return None

    job_id = posting.get("id")
    if not job_id:
        return None

    title = (posting.get("text") or "").strip()
    if not title:
        return None

    company = _normalize_company_name(company_slug)

    description = (posting.get("descriptionPlain") or posting.get("description") or "").strip()
    if not description:
        description = f"{title} opportunity at {company}."

    hosted_url = (posting.get("hostedUrl") or posting.get("applyUrl") or "").strip()
    if not hosted_url:
        hosted_url = f"https://jobs.lever.co/{company_slug}/{job_id}"

    categories = posting.get("categories") or {}
    loc_str = ""
    commitment = None
    skills: list[str] = []

    if isinstance(categories, dict):
        loc_str = categories.get("location") or ""
        commitment = categories.get("commitment")
        dept = (categories.get("department") or "").strip()
        team = (categories.get("team") or "").strip()
        if dept and dept.lower() != "all":
            skills.append(dept)
        if team and team != dept:
            skills.append(team)

    city, state, country = _split_location(loc_str)
    work_mode = _infer_work_mode(posting.get("workplaceType"), title, loc_str)
    opp_type, emp_type = _infer_employment_type(commitment, title)
    sal_min, sal_max, currency = _parse_salary(posting.get("salaryRange"))

    # Posted date from epoch milliseconds
    posted_date = None
    created_at = posting.get("createdAt")
    if isinstance(created_at, (int, float)) and created_at > 0:
        try:
            dt = datetime.fromtimestamp(created_at / 1000.0, tz=UTC)
            posted_date = dt.date()
        except (ValueError, OSError):
            pass

    source_id = f"lever-{company_slug}-{job_id}"

    metadata: dict[str, Any] = {
        "lever_id": str(job_id),
        "company_slug": company_slug,
        "workplace_type": posting.get("workplaceType"),
        "department": categories.get("department") if isinstance(categories, dict) else None,
        "team": categories.get("team") if isinstance(categories, dict) else None,
    }

    return RawOpportunityRow(
        title=title,
        company=company,
        description=description,
        opportunity_type=opp_type,
        employment_type=emp_type,
        work_mode=work_mode,
        location_city=city,
        location_state=state,
        location_country=country,
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=currency,
        job_url=hosted_url,
        application_url=posting.get("applyUrl") or hosted_url,
        source=OpportunitySource.LEVER,
        source_id=source_id,
        posted_date=posted_date,
        required_skills=skills if skills else None,
        is_active=True,
        external_metadata=metadata,
    )


class LeverConnector(BaseOpportunityConnector):
    """
    Connector for public Lever job postings across multiple employer company slugs.

    Requires LEVER_SITE_TOKENS in settings/environment.
    Reports NOT_CONFIGURED when no site tokens are present.
    """

    source_name: str = "lever"
    source_enum: OpportunitySource = OpportunitySource.LEVER

    def __init__(self, site_tokens: list[str] | None = None) -> None:
        self._explicit_tokens = (
            [t.strip().lower() for t in site_tokens if t.strip()] if site_tokens else None
        )

    @property
    def target_tokens(self) -> list[str]:
        """Return configured company slugs."""
        if self._explicit_tokens is not None:
            return self._explicit_tokens
        return _load_site_tokens()

    def is_configured(self) -> bool:
        """Return True if at least one company slug is configured."""
        return len(self.target_tokens) > 0

    async def fetch_batch(
        self,
        cursor: Any | None = None,
    ) -> ConnectorBatchResult:
        """
        Fetch postings across all configured company slugs with per-slug error isolation.
        Lever returns all active postings per company slug in a single list call.
        """
        tokens = self.target_tokens
        if not tokens:
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                raw_count=0,
                error=(
                    "Lever connector is not configured. "
                    "No company slugs found in LEVER_SITE_TOKENS."
                ),
            )

        all_records: list[RawOpportunityRow] = []
        total_raw = 0
        slug_errors: list[str] = []

        logger.info("[lever] Starting fetch across %d company sites: %s", len(tokens), tokens)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for slug in tokens:
                url = f"{_API_BASE}/{slug}?mode=json"
                try:
                    response = await _execute_with_retries(
                        client=client,
                        url=url,
                        source_name=self.source_name,
                    )
                except Exception as exc:
                    logger.warning("[lever] Failed to fetch company '%s': %s (skipping)", slug, exc)
                    slug_errors.append(f"{slug}: {exc}")
                    continue

                if response.status_code == 404:
                    logger.warning("[lever] Company '%s' not found (HTTP 404) — skipping.", slug)
                    slug_errors.append(f"{slug}: HTTP 404 Not Found")
                    continue

                if response.status_code != 200:
                    logger.warning(
                        "[lever] Company '%s' returned HTTP %d — skipping.",
                        slug,
                        response.status_code,
                    )
                    slug_errors.append(f"{slug}: HTTP {response.status_code}")
                    continue

                try:
                    data = response.json()
                except Exception as exc:
                    logger.warning("[lever] Company '%s' returned malformed JSON: %s", slug, exc)
                    slug_errors.append(f"{slug}: Invalid JSON")
                    continue

                if not isinstance(data, list):
                    logger.warning(
                        "[lever] Expected JSON list for company '%s', got %s",
                        slug,
                        type(data).__name__,
                    )
                    slug_errors.append(f"{slug}: Expected array")
                    continue

                total_raw += len(data)
                company_records = 0
                for item in data:
                    parsed = _parse_posting(item, slug)
                    if parsed is not None:
                        all_records.append(parsed)
                        company_records += 1

                logger.info(
                    "[lever] Company '%s': fetched %d postings, parsed %d records.",
                    slug,
                    len(data),
                    company_records,
                )

        # Single batch operation across all configured slugs
        error_msg = "; ".join(slug_errors) if (slug_errors and not all_records) else None

        return ConnectorBatchResult(
            records=all_records,
            next_cursor=None,
            raw_count=total_raw,
            error=error_msg,
        )
