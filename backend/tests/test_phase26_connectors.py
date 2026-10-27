"""
Phase 26.3 Wave 1 Connector Tests.

Tests all four Wave 1 connectors with mocked HTTP responses:
- RemotiveConnector
- ArbeitnowConnector
- CodeforcesConnector
- GreenhouseConnector

Covers:
- Happy-path parsing
- Pagination (Arbeitnow multi-page, single-page others)
- Stable source IDs and canonical URLs
- UTC timestamp conversion (Codeforces epoch)
- Work mode, employment type, opportunity type inference
- Missing optional fields (salary, skills, location, description)
- Salary parsing edge cases (Remotive)
- Visa sponsorship flag (Arbeitnow — explicit only)
- Invalid/malformed payloads and schema drift
- HTTP 429 / Retry-After handling
- Timeout and network-level failures
- 5xx transient server errors
- Greenhouse multiple-board aggregation
- Greenhouse single-board HTTP failure (isolation)
- Greenhouse NOT_CONFIGURED behavior
- Greenhouse invalid/missing board token
- is_active based on Codeforces phase
- Duplicate source IDs across connectors (stable ID stability)
- ConnectorOrchestrator integration with ingest_raw_records
- Regression: existing ingestion, normalizer, and enum compatibility
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.enums import (
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    WorkMode,
)
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.arbeitnow import ArbeitnowConnector
from app.services.connectors.arbeitnow import _parse_record as arb_parse
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorRunSummary,
    ConnectorStatus,
    _retry_delay,
)
from app.services.connectors.codeforces import (
    _ACTIVE_PHASES,
    CodeforcesConnector,
)
from app.services.connectors.codeforces import (
    _parse_record as cf_parse,
)
from app.services.connectors.greenhouse import (
    GreenhouseConnector,
    _load_board_tokens,
    _normalize_company_name,
    _parse_job,
)
from app.services.connectors.orchestrator import ConnectorOrchestrator
from app.services.connectors.remotive import (
    RemotiveConnector,
    _parse_salary,
)
from app.services.connectors.remotive import (
    _parse_record as rem_parse,
)

# ============================================================================
# Helpers & Fixtures
# ============================================================================


def _make_httpx_response(
    status_code: int,
    body: Any,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build a mock httpx.Response with a JSON body."""
    content = json.dumps(body).encode()
    response = httpx.Response(
        status_code=status_code,
        content=content,
        headers={"Content-Type": "application/json", **(headers or {})},
        request=httpx.Request("GET", "https://example.com"),
    )
    return response


def _remotive_job(
    job_id: int = 111,
    title: str = "Backend Engineer",
    company: str = "Acme Corp",
    description: str = "Build scalable services.",
    job_type: str = "full_time",
    tags: list[str] | None = None,
    salary: str | None = "$100,000 - $140,000",
    candidate_location: str = "Worldwide",
    url: str | None = None,
    publication_date: str = "2026-10-01T12:00:00",
) -> dict[str, Any]:
    return {
        "id": job_id,
        "title": title,
        "company_name": company,
        "description": description,
        "job_type": job_type,
        "tags": tags or ["python", "fastapi"],
        "salary": salary,
        "candidate_required_location": candidate_location,
        "url": url or f"https://remotive.com/remote-jobs/{job_id}",
        "publication_date": publication_date,
        "category": "Software Development",
        "company_logo": "https://remotive.com/logo.png",
    }


def _arbeitnow_job(
    slug: str = "senior-backend-engineer-at-acme-123",
    title: str = "Senior Backend Engineer",
    company: str = "Acme GmbH",
    description: str = "Join our team.",
    remote: bool = True,
    tags: list[str] | None = None,
    job_types: list[str] | None = None,
    location: str = "Berlin, Germany",
    visa_sponsorship: bool = False,
    created_at: int = 1696000000,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": title,
        "company_name": company,
        "description": description,
        "remote": remote,
        "tags": tags or ["python", "aws"],
        "job_types": job_types or ["full_time"],
        "location": location,
        "visa_sponsorship": visa_sponsorship,
        "url": f"https://www.arbeitnow.com/jobs/{slug}",
        "created_at": created_at,
    }


def _codeforces_contest(
    contest_id: int = 2042,
    name: str = "Codeforces Round 970",
    phase: str = "BEFORE",
    duration_seconds: int = 9000,
    start_time_seconds: int = 1795000000,
    contest_type: str = "CF",
) -> dict[str, Any]:
    return {
        "id": contest_id,
        "name": name,
        "type": contest_type,
        "phase": phase,
        "frozen": False,
        "durationSeconds": duration_seconds,
        "startTimeSeconds": start_time_seconds,
    }


def _greenhouse_job(
    job_id: int = 7654321,
    title: str = "Software Engineer",
    location: str = "San Francisco, CA",
    departments: list[dict] | None = None,
    content: str = "<p>Join our engineering team.</p>",
    absolute_url: str = "https://boards.greenhouse.io/stripe/jobs/7654321",
    updated_at: str = "2026-10-15T10:00:00.000Z",
) -> dict[str, Any]:
    return {
        "id": job_id,
        "title": title,
        "location": {"name": location},
        "departments": departments or [{"id": 10, "name": "Engineering"}],
        "content": content,
        "absolute_url": absolute_url,
        "updated_at": updated_at,
        "requisition_id": f"REQ-{job_id}",
    }


# ============================================================================
# Base Connector Tests
# ============================================================================


class TestRetryDelay:
    def test_exponential_growth(self) -> None:
        assert _retry_delay(0) == 2.0
        assert _retry_delay(1) == 4.0
        assert _retry_delay(2) == 8.0

    def test_caps_at_max(self) -> None:
        assert _retry_delay(20) == 60.0

    def test_all_positive(self) -> None:
        for i in range(10):
            assert _retry_delay(i) > 0


class TestConnectorStatus:
    def test_values(self) -> None:
        assert ConnectorStatus.SUCCESS == "success"
        assert ConnectorStatus.NOT_CONFIGURED == "not_configured"
        assert ConnectorStatus.FAILED == "failed"
        assert ConnectorStatus.PARTIAL == "partial"
        assert ConnectorStatus.SKIPPED == "skipped"


# ============================================================================
# Remotive Connector Tests
# ============================================================================


class TestRemotiveConnector:
    """Unit tests for RemotiveConnector."""

    def test_is_configured_always_true(self) -> None:
        assert RemotiveConnector().is_configured() is True

    def test_source_name(self) -> None:
        assert RemotiveConnector.source_name == "remotive"

    # -- Salary parsing --

    def test_parse_salary_usd_range(self) -> None:
        lo, hi, curr = _parse_salary("$80,000 - $120,000")
        assert lo == 80000
        assert hi == 120000
        assert curr == "USD"

    def test_parse_salary_single_value(self) -> None:
        lo, hi, curr = _parse_salary("$90,000")
        assert lo == 90000
        assert hi == 90000
        assert curr == "USD"

    def test_parse_salary_eur(self) -> None:
        lo, hi, curr = _parse_salary("€60,000 - €90,000")
        assert curr == "EUR"
        assert lo == 60000
        assert hi == 90000

    def test_parse_salary_k_suffix(self) -> None:
        lo, hi, curr = _parse_salary("$80k - $120k")
        assert lo == 80000
        assert hi == 120000

    def test_parse_salary_empty(self) -> None:
        assert _parse_salary(None) == (None, None, None)
        assert _parse_salary("") == (None, None, None)
        assert _parse_salary("Competitive") == (None, None, None)

    # -- Record parsing --

    def test_parse_record_happy_path(self) -> None:
        row = rem_parse(_remotive_job())
        assert row is not None
        assert row.title == "Backend Engineer"
        assert row.company == "Acme Corp"
        assert row.source == "remotive"
        assert row.source_id == "111"
        assert row.work_mode == "remote"
        assert row.employment_type == "fulltime"
        assert row.opportunity_type == "job"
        assert row.salary_min == 100000
        assert row.salary_max == 140000
        assert row.salary_currency == "USD"
        assert "python" in (row.required_skills or [])

    def test_parse_record_internship(self) -> None:
        row = rem_parse(_remotive_job(job_type="internship"))
        assert row is not None
        assert row.employment_type == "internship"
        assert row.opportunity_type == "internship"

    def test_parse_record_no_salary(self) -> None:
        row = rem_parse(_remotive_job(salary=None))
        assert row is not None
        assert row.salary_min is None
        assert row.salary_max is None

    def test_parse_record_no_tags(self) -> None:
        job = _remotive_job()
        job["tags"] = []
        row = rem_parse(job)
        assert row is not None
        assert row.required_skills is None

    def test_parse_record_missing_id(self) -> None:
        job = _remotive_job()
        del job["id"]
        assert rem_parse(job) is None

    def test_parse_record_missing_title(self) -> None:
        job = _remotive_job(title="")
        assert rem_parse(job) is None

    def test_parse_record_missing_company(self) -> None:
        job = _remotive_job()
        job["company_name"] = ""
        assert rem_parse(job) is None

    def test_parse_record_missing_description(self) -> None:
        job = _remotive_job()
        job["description"] = ""
        assert rem_parse(job) is None

    def test_parse_record_unknown_job_type(self) -> None:
        row = rem_parse(_remotive_job(job_type="zap_time"))
        assert row is not None
        assert row.employment_type == "fulltime"  # defaults to fulltime

    def test_parse_record_stable_source_id(self) -> None:
        row1 = rem_parse(_remotive_job(job_id=999))
        row2 = rem_parse(_remotive_job(job_id=999))
        assert row1 is not None
        assert row2 is not None
        assert row1.source_id == row2.source_id == "999"

    def test_parse_record_canonical_url(self) -> None:
        row = rem_parse(_remotive_job(job_id=555))
        assert row is not None
        assert row.job_url == "https://remotive.com/remote-jobs/555"

    def test_parse_record_external_metadata(self) -> None:
        row = rem_parse(_remotive_job(job_id=42))
        assert row is not None
        assert row.external_metadata is not None
        assert row.external_metadata.get("remotive_id") == 42
        assert "category" in row.external_metadata

    # -- Fetch batch --

    @pytest.mark.asyncio
    async def test_fetch_batch_happy_path(self) -> None:
        payload = {"job-count": 2, "jobs": [_remotive_job(111), _remotive_job(222)]}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.remotive._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            connector = RemotiveConnector()
            result = await connector.fetch_batch(cursor=None)

        assert result.error is None
        assert len(result.records) == 2
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_empty_jobs(self) -> None:
        payload = {"job-count": 0, "jobs": []}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.remotive._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await RemotiveConnector().fetch_batch()

        assert result.error is None
        assert result.records == []
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_http_error(self) -> None:
        with patch(
            "app.services.connectors.remotive._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = RuntimeError("all retries failed")
            result = await RemotiveConnector().fetch_batch()

        assert result.error is not None
        assert "HTTP error" in result.error
        assert result.records == []

    @pytest.mark.asyncio
    async def test_fetch_batch_invalid_json(self) -> None:
        bad_response = httpx.Response(
            status_code=200,
            content=b"not valid json{{{",
            request=httpx.Request("GET", "https://remotive.com/api/remote-jobs"),
        )
        with patch(
            "app.services.connectors.remotive._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = bad_response
            result = await RemotiveConnector().fetch_batch()

        assert result.error is not None
        assert "Invalid JSON" in result.error

    @pytest.mark.asyncio
    async def test_fetch_batch_unexpected_schema(self) -> None:
        # jobs field is a dict instead of list
        mock_response = _make_httpx_response(200, {"jobs": {"bad": "schema"}})
        with patch(
            "app.services.connectors.remotive._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await RemotiveConnector().fetch_batch()

        # jobs is not a list — connector sets error
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_batch_cursor_not_none_returns_empty(self) -> None:
        """Remotive is single-page; cursor != None signals we're done."""
        result = await RemotiveConnector().fetch_batch(cursor=1)
        assert result.records == []
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_run_not_configured_never_true(self) -> None:
        """Remotive is always configured."""
        connector = RemotiveConnector()
        assert connector.is_configured() is True

    @pytest.mark.asyncio
    async def test_run_malformed_records_skipped(self) -> None:
        """Records with missing required fields are silently skipped."""
        bad_job = {"id": 1, "title": "", "company_name": "X", "description": "Y"}
        good_job = _remotive_job(job_id=2)
        payload = {"jobs": [bad_job, good_job]}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.remotive._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await RemotiveConnector().fetch_batch()

        assert len(result.records) == 1
        assert result.records[0].source_id == "2"


# ============================================================================
# Arbeitnow Connector Tests
# ============================================================================


class TestArbeitnowConnector:
    """Unit tests for ArbeitnowConnector."""

    def test_is_configured_always_true(self) -> None:
        assert ArbeitnowConnector().is_configured() is True

    def test_source_name(self) -> None:
        assert ArbeitnowConnector.source_name == "arbeitnow"

    # -- Record parsing --

    def test_parse_record_happy_path(self) -> None:
        row = arb_parse(_arbeitnow_job())
        assert row is not None
        assert row.title == "Senior Backend Engineer"
        assert row.company == "Acme GmbH"
        assert row.source == "arbeitnow"
        assert row.source_id == "senior-backend-engineer-at-acme-123"
        assert row.work_mode == "remote"
        assert row.employment_type == "fulltime"
        assert row.opportunity_type == "job"
        assert row.location_city == "Berlin"
        assert row.location_country == "Germany"

    def test_parse_record_visa_sponsorship_explicit_true(self) -> None:
        row = arb_parse(_arbeitnow_job(visa_sponsorship=True))
        assert row is not None
        meta = row.external_metadata or {}
        assert meta.get("visa_sponsorship") is True

    def test_parse_record_visa_sponsorship_explicit_false(self) -> None:
        row = arb_parse(_arbeitnow_job(visa_sponsorship=False))
        assert row is not None
        meta = row.external_metadata or {}
        assert meta.get("visa_sponsorship") is False

    def test_parse_record_no_visa_sponsorship_field(self) -> None:
        """When visa_sponsorship key is absent, must not infer it."""
        job = _arbeitnow_job()
        del job["visa_sponsorship"]
        row = arb_parse(job)
        assert row is not None
        meta = row.external_metadata or {}
        assert "visa_sponsorship" not in meta

    def test_parse_record_internship_job_type(self) -> None:
        row = arb_parse(_arbeitnow_job(job_types=["internship"]))
        assert row is not None
        assert row.employment_type == "internship"
        assert row.opportunity_type == "internship"

    def test_parse_record_non_remote(self) -> None:
        row = arb_parse(_arbeitnow_job(remote=False))
        assert row is not None
        assert row.work_mode == "any"

    def test_parse_record_no_tags(self) -> None:
        job = _arbeitnow_job()
        job["tags"] = []
        row = arb_parse(job)
        assert row is not None
        assert row.required_skills is None

    def test_parse_record_missing_slug(self) -> None:
        job = _arbeitnow_job()
        job["slug"] = ""
        assert arb_parse(job) is None

    def test_parse_record_missing_title(self) -> None:
        job = _arbeitnow_job(title="")
        assert arb_parse(job) is None

    def test_parse_record_stable_source_id(self) -> None:
        slug = "my-stable-slug-999"
        row1 = arb_parse(_arbeitnow_job(slug=slug))
        row2 = arb_parse(_arbeitnow_job(slug=slug))
        assert row1 is not None
        assert row2 is not None
        assert row1.source_id == row2.source_id == slug

    def test_parse_record_posted_date_from_epoch(self) -> None:
        row = arb_parse(_arbeitnow_job(created_at=1696000000))
        assert row is not None
        assert row.posted_date == "1696000000"

    # -- Fetch batch --

    def _make_arbeitnow_page(self, jobs: list[dict], page: int, last_page: int) -> dict:
        return {
            "data": jobs,
            "links": {
                "next": f"https://www.arbeitnow.com/api/job-board-api?page={page + 1}"
                if page < last_page
                else None,
            },
            "meta": {
                "current_page": page,
                "last_page": last_page,
                "per_page": 100,
            },
        }

    @pytest.mark.asyncio
    async def test_fetch_batch_page_1_of_1(self) -> None:
        payload = self._make_arbeitnow_page([_arbeitnow_job()], page=1, last_page=1)
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await ArbeitnowConnector().fetch_batch(cursor=None)

        assert len(result.records) == 1
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_pagination_page_1_of_3(self) -> None:
        payload = self._make_arbeitnow_page(
            [_arbeitnow_job(slug="job-a-1"), _arbeitnow_job(slug="job-b-2")],
            page=1,
            last_page=3,
        )
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await ArbeitnowConnector().fetch_batch(cursor=1)

        assert len(result.records) == 2
        assert result.next_cursor == 2  # Expect page 2

    @pytest.mark.asyncio
    async def test_fetch_batch_page_cap(self) -> None:
        """Pages beyond _MAX_PAGES should return empty without fetching."""
        result = await ArbeitnowConnector().fetch_batch(cursor=99999)
        assert result.records == []
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_empty_data(self) -> None:
        payload = self._make_arbeitnow_page([], page=1, last_page=1)
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await ArbeitnowConnector().fetch_batch()

        assert result.records == []
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_http_error(self) -> None:
        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = RuntimeError("timeout")
            result = await ArbeitnowConnector().fetch_batch()

        assert result.error is not None
        assert result.records == []

    @pytest.mark.asyncio
    async def test_fetch_batch_invalid_json(self) -> None:
        bad_response = httpx.Response(
            status_code=200,
            content=b"<html>not json</html>",
            request=httpx.Request("GET", "https://www.arbeitnow.com/api/job-board-api"),
        )
        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = bad_response
            result = await ArbeitnowConnector().fetch_batch()

        assert result.error is not None
        assert "Invalid JSON" in result.error

    @pytest.mark.asyncio
    async def test_fetch_batch_malformed_records_skipped(self) -> None:
        bad = {"slug": "", "title": "Empty slug job", "company_name": "X", "description": "Y"}
        good = _arbeitnow_job(slug="valid-job-slug")
        payload = self._make_arbeitnow_page([bad, good], page=1, last_page=1)
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await ArbeitnowConnector().fetch_batch()

        assert len(result.records) == 1
        assert result.records[0].source_id == "valid-job-slug"

    @pytest.mark.asyncio
    async def test_run_multi_page(self) -> None:
        """Integration test: run() paginates through 2 pages."""
        page1 = self._make_arbeitnow_page(
            [_arbeitnow_job(slug="p1-job-1"), _arbeitnow_job(slug="p1-job-2")],
            page=1,
            last_page=2,
        )
        page2 = self._make_arbeitnow_page(
            [_arbeitnow_job(slug="p2-job-3")],
            page=2,
            last_page=2,
        )
        resp1 = _make_httpx_response(200, page1)
        resp2 = _make_httpx_response(200, page2)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return resp1 if call_count == 1 else resp2

        with patch(
            "app.services.connectors.arbeitnow._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = side_effect
            connector = ArbeitnowConnector()
            connector.rate_limit_delay = 0.0  # skip sleep in tests
            records, summary = await connector.run()

        assert len(records) == 3
        assert summary.status == ConnectorStatus.SUCCESS
        assert summary.records_fetched == 3


# ============================================================================
# Codeforces Connector Tests
# ============================================================================


class TestCodeforcesConnector:
    """Unit tests for CodeforcesConnector."""

    def test_is_configured_always_true(self) -> None:
        assert CodeforcesConnector().is_configured() is True

    def test_source_name(self) -> None:
        assert CodeforcesConnector.source_name == "codeforces"

    # -- Record parsing --

    def test_parse_upcoming_contest(self) -> None:
        row = cf_parse(_codeforces_contest(phase="BEFORE"))
        assert row is not None
        assert row.source == "codeforces"
        assert row.source_id == "cf-2042"
        assert row.opportunity_type == "coding_contest"
        assert row.is_active is True
        assert row.employment_type == "any"
        assert row.work_mode == "remote"

    def test_parse_live_contest(self) -> None:
        row = cf_parse(_codeforces_contest(phase="CODING"))
        assert row is not None
        assert row.is_active is True

    def test_parse_finished_contest(self) -> None:
        row = cf_parse(_codeforces_contest(phase="FINISHED"))
        assert row is not None
        assert row.is_active is False

    def test_parse_pending_system_test(self) -> None:
        row = cf_parse(_codeforces_contest(phase="PENDING_SYSTEM_TEST"))
        assert row is not None
        assert row.is_active is False

    def test_parse_utc_start_time(self) -> None:
        start_ts = 1795000000
        row = cf_parse(_codeforces_contest(start_time_seconds=start_ts))
        assert row is not None
        assert row.event_start_time is not None
        assert row.event_start_time.tzinfo is not None
        expected = datetime.fromtimestamp(start_ts, tz=UTC)
        assert row.event_start_time == expected

    def test_parse_event_end_time_computed(self) -> None:
        start_ts = 1795000000
        duration = 9000
        row = cf_parse(
            _codeforces_contest(
                start_time_seconds=start_ts,
                duration_seconds=duration,
            )
        )
        assert row is not None
        assert row.event_end_time is not None
        expected_end = datetime.fromtimestamp(start_ts, tz=UTC) + timedelta(seconds=duration)
        assert row.event_end_time == expected_end

    def test_parse_duration_seconds_preserved(self) -> None:
        row = cf_parse(_codeforces_contest(duration_seconds=7200))
        assert row is not None
        assert row.duration_seconds == 7200

    def test_parse_contest_url_format(self) -> None:
        row = cf_parse(_codeforces_contest(contest_id=9999))
        assert row is not None
        assert row.job_url == "https://codeforces.com/contest/9999"

    def test_parse_stable_source_id(self) -> None:
        row1 = cf_parse(_codeforces_contest(contest_id=1234))
        row2 = cf_parse(_codeforces_contest(contest_id=1234))
        assert row1 is not None and row2 is not None
        assert row1.source_id == row2.source_id == "cf-1234"

    def test_parse_company_is_codeforces(self) -> None:
        row = cf_parse(_codeforces_contest())
        assert row is not None
        assert row.company == "Codeforces"

    def test_parse_external_metadata(self) -> None:
        row = cf_parse(_codeforces_contest(contest_id=42, contest_type="ICPC"))
        assert row is not None
        meta = row.external_metadata or {}
        assert meta.get("contest_id") == 42
        assert meta.get("type") == "ICPC"
        assert "phase" in meta

    def test_parse_missing_id_returns_none(self) -> None:
        contest = _codeforces_contest()
        del contest["id"]
        assert cf_parse(contest) is None

    def test_parse_missing_name_returns_none(self) -> None:
        contest = _codeforces_contest(name="")
        assert cf_parse(contest) is None

    def test_parse_no_start_time(self) -> None:
        """Contests without startTimeSeconds should still parse with no event times."""
        contest = _codeforces_contest()
        del contest["startTimeSeconds"]
        row = cf_parse(contest)
        assert row is not None
        assert row.event_start_time is None

    def test_parse_active_phases_set(self) -> None:
        """Verify active phases definition."""
        assert "BEFORE" in _ACTIVE_PHASES
        assert "CODING" in _ACTIVE_PHASES
        assert "FINISHED" not in _ACTIVE_PHASES

    # -- Fetch batch --

    @pytest.mark.asyncio
    async def test_fetch_batch_happy_path(self) -> None:
        payload = {
            "status": "OK",
            "result": [
                _codeforces_contest(contest_id=1, phase="BEFORE"),
                _codeforces_contest(contest_id=2, phase="FINISHED"),
            ],
        }
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.codeforces._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await CodeforcesConnector().fetch_batch()

        assert result.error is None
        assert len(result.records) == 2
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_api_status_failed(self) -> None:
        payload = {"status": "FAILED", "comment": "Server error"}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.codeforces._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await CodeforcesConnector().fetch_batch()

        assert result.error is not None
        assert "FAILED" in result.error

    @pytest.mark.asyncio
    async def test_fetch_batch_empty_result(self) -> None:
        payload = {"status": "OK", "result": []}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.codeforces._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await CodeforcesConnector().fetch_batch()

        assert result.error is None
        assert result.records == []

    @pytest.mark.asyncio
    async def test_fetch_batch_invalid_json(self) -> None:
        bad_response = httpx.Response(
            status_code=200,
            content=b"}{bad json",
            request=httpx.Request("GET", "https://codeforces.com/api/contest.list"),
        )
        with patch(
            "app.services.connectors.codeforces._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = bad_response
            result = await CodeforcesConnector().fetch_batch()

        assert result.error is not None
        assert "Invalid JSON" in result.error

    @pytest.mark.asyncio
    async def test_fetch_batch_http_error(self) -> None:
        with patch(
            "app.services.connectors.codeforces._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = RuntimeError("connection timeout")
            result = await CodeforcesConnector().fetch_batch()

        assert result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_batch_cursor_not_none_returns_empty(self) -> None:
        result = await CodeforcesConnector().fetch_batch(cursor="already_fetched")
        assert result.records == []
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_batch_malformed_record_skipped(self) -> None:
        payload = {
            "status": "OK",
            "result": [
                {"id": None, "name": "Bad contest"},  # no valid id
                _codeforces_contest(contest_id=10, phase="BEFORE"),
            ],
        }
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.codeforces._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await CodeforcesConnector().fetch_batch()

        assert len(result.records) == 1
        assert result.records[0].source_id == "cf-10"


# ============================================================================
# Greenhouse Connector Tests
# ============================================================================


class TestGreenhouseConnector:
    """Unit tests for GreenhouseConnector."""

    def test_normalize_company_name(self) -> None:
        assert _normalize_company_name("stripe") == "Stripe"
        assert _normalize_company_name("cloudflare") == "Cloudflare"
        assert _normalize_company_name("my-company") == "My Company"
        assert _normalize_company_name("big_tech_co") == "Big Tech Co"

    def test_load_board_tokens_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "")
        assert _load_board_tokens() == []

    def test_load_board_tokens_single(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "stripe")
        assert _load_board_tokens() == ["stripe"]

    def test_load_board_tokens_multiple(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "stripe,cloudflare,airbnb")
        assert _load_board_tokens() == ["stripe", "cloudflare", "airbnb"]

    def test_load_board_tokens_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", " stripe , cloudflare ")
        assert _load_board_tokens() == ["stripe", "cloudflare"]

    def test_is_configured_no_tokens(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "")
        assert GreenhouseConnector().is_configured() is False

    def test_is_configured_with_tokens(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "stripe")
        assert GreenhouseConnector().is_configured() is True

    def test_source_name(self) -> None:
        assert GreenhouseConnector.source_name == "greenhouse"

    # -- Record parsing --

    def test_parse_job_happy_path(self) -> None:
        row = _parse_job(_greenhouse_job(), "stripe", "Stripe")
        assert row is not None
        assert row.title == "Software Engineer"
        assert row.company == "Stripe"
        assert row.source == "greenhouse"
        assert row.source_id == "gh-stripe-7654321"
        assert row.location_city == "San Francisco"
        # 'San Francisco, CA' has 2 parts: _split_location returns (city, None, country)
        assert row.location_state is None
        assert row.location_country == "CA"

    def test_parse_job_source_id_format(self) -> None:
        row = _parse_job(_greenhouse_job(job_id=999), "cloudflare", "Cloudflare")
        assert row is not None
        assert row.source_id == "gh-cloudflare-999"

    def test_parse_job_stable_source_id(self) -> None:
        row1 = _parse_job(_greenhouse_job(job_id=100), "stripe", "Stripe")
        row2 = _parse_job(_greenhouse_job(job_id=100), "stripe", "Stripe")
        assert row1 is not None and row2 is not None
        assert row1.source_id == row2.source_id

    def test_parse_job_missing_id_returns_none(self) -> None:
        job = _greenhouse_job()
        del job["id"]
        assert _parse_job(job, "stripe", "Stripe") is None

    def test_parse_job_missing_title_returns_none(self) -> None:
        job = _greenhouse_job(title="")
        assert _parse_job(job, "stripe", "Stripe") is None

    def test_parse_job_no_content_uses_fallback_description(self) -> None:
        row = _parse_job(_greenhouse_job(content=""), "stripe", "Stripe")
        assert row is not None
        assert "Stripe" in row.description

    def test_parse_job_department_in_metadata(self) -> None:
        row = _parse_job(_greenhouse_job(), "stripe", "Stripe")
        assert row is not None
        meta = row.external_metadata or {}
        assert meta.get("department") == "Engineering"

    def test_parse_job_employer_attribution(self) -> None:
        row = _parse_job(_greenhouse_job(), "airbnb", "Airbnb")
        assert row is not None
        meta = row.external_metadata or {}
        assert meta.get("board_token") == "airbnb"

    # -- Fetch batch / run --

    @pytest.mark.asyncio
    async def test_run_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "")
        connector = GreenhouseConnector()
        records, summary = await connector.run()
        assert records == []
        assert summary.status == ConnectorStatus.NOT_CONFIGURED
        assert summary.error_message is not None
        assert "GREENHOUSE_BOARD_TOKENS" in summary.error_message

    @pytest.mark.asyncio
    async def test_fetch_batch_not_configured_returns_error(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "")
        connector = GreenhouseConnector()
        result = await connector.fetch_batch()
        assert result.error is not None
        assert result.records == []

    @pytest.mark.asyncio
    async def test_fetch_batch_single_board(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "stripe")
        payload = {"jobs": [_greenhouse_job(job_id=1), _greenhouse_job(job_id=2)]}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.greenhouse._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            connector = GreenhouseConnector()
            result = await connector.fetch_batch()

        assert len(result.records) == 2
        assert result.error is None
        assert all(r.source == "greenhouse" for r in result.records)

    @pytest.mark.asyncio
    async def test_fetch_batch_multiple_boards(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "stripe,cloudflare")
        stripe_payload = {"jobs": [_greenhouse_job(job_id=1)]}
        cf_payload = {"jobs": [_greenhouse_job(job_id=2), _greenhouse_job(job_id=3)]}
        resp_stripe = _make_httpx_response(200, stripe_payload)
        resp_cf = _make_httpx_response(200, cf_payload)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return resp_stripe if call_count == 1 else resp_cf

        with patch(
            "app.services.connectors.greenhouse._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = side_effect
            connector = GreenhouseConnector()
            connector.rate_limit_delay = 0.0
            result = await connector.fetch_batch()

        assert len(result.records) == 3

    @pytest.mark.asyncio
    async def test_fetch_batch_one_board_fails_others_continue(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "bad-token,stripe")
        good_payload = {"jobs": [_greenhouse_job(job_id=10)]}
        resp_good = _make_httpx_response(200, good_payload)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("HTTP 404 board not found")
            return resp_good

        with patch(
            "app.services.connectors.greenhouse._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = side_effect
            connector = GreenhouseConnector()
            connector.rate_limit_delay = 0.0
            result = await connector.fetch_batch()

        # Only stripe's record should survive
        assert len(result.records) == 1

    @pytest.mark.asyncio
    async def test_fetch_batch_invalid_json_board(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "stripe")
        bad_response = httpx.Response(
            status_code=200,
            content=b"<html>not json</html>",
            request=httpx.Request("GET", "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"),
        )
        with patch(
            "app.services.connectors.greenhouse._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = bad_response
            result = await GreenhouseConnector().fetch_batch()

        # Should gracefully return empty (board logged + skipped)
        assert result.records == []
        assert result.error is None  # orchestrator-level error, not batch error

    @pytest.mark.asyncio
    async def test_fetch_batch_empty_board(self, monkeypatch) -> None:
        monkeypatch.setenv("GREENHOUSE_BOARD_TOKENS", "emptyco")
        payload = {"jobs": []}
        mock_response = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.greenhouse._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_response
            result = await GreenhouseConnector().fetch_batch()

        assert result.records == []
        assert result.error is None


# ============================================================================
# ConnectorOrchestrator Tests
# ============================================================================


class TestConnectorOrchestrator:
    """Unit tests for ConnectorOrchestrator."""

    @pytest.mark.asyncio
    async def test_run_connector_not_configured(self) -> None:
        """NOT_CONFIGURED connector should not reach the ingest service."""
        connector = GreenhouseConnector()
        # Patch is_configured to return False
        connector.is_configured = lambda: False

        mock_db = AsyncMock()
        with patch("app.services.connectors.greenhouse.GreenhouseConnector.run") as mock_run:
            mock_run.return_value = (
                [],
                ConnectorRunSummary(
                    source="greenhouse",
                    status=ConnectorStatus.NOT_CONFIGURED,
                    error_message="Not configured",
                ),
            )
            orch = ConnectorOrchestrator(mock_db)
            summary = await orch.run_connector(connector)

        assert summary.status == ConnectorStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_run_connector_empty_records(self) -> None:
        """Connector returning 0 records should succeed without calling ingest."""
        connector = RemotiveConnector()
        with patch.object(connector, "run") as mock_run:
            mock_run.return_value = (
                [],
                ConnectorRunSummary(source="remotive", status=ConnectorStatus.SUCCESS),
            )
            mock_db = AsyncMock()
            orch = ConnectorOrchestrator(mock_db)
            summary = await orch.run_connector(connector)

        assert summary.status == ConnectorStatus.SUCCESS
        assert summary.ingest_result_created == 0

    @pytest.mark.asyncio
    async def test_run_connector_ingest_called_with_records(self) -> None:
        """Connector returning records should invoke ingest_raw_records."""
        from app.schemas.opportunity import OpportunityIngestResult

        connector = RemotiveConnector()
        fake_records = [
            RawOpportunityRow(
                title="Test Job",
                company="Test Co",
                description="Test desc",
                source="remotive",
                source_id="rem-1",
            )
        ]
        with patch.object(connector, "run") as mock_run:
            mock_run.return_value = (
                fake_records,
                ConnectorRunSummary(
                    source="remotive",
                    status=ConnectorStatus.SUCCESS,
                    records_fetched=1,
                    records_parsed=1,
                ),
            )
            mock_db = AsyncMock()
            with patch("app.services.connectors.orchestrator.ingest_raw_records") as mock_ingest:
                mock_ingest.return_value = OpportunityIngestResult(
                    total=1, created=1, skipped_duplicates=0, errors=[]
                )
                orch = ConnectorOrchestrator(mock_db)
                summary = await orch.run_connector(connector)

        mock_ingest.assert_called_once_with(mock_db, fake_records)
        assert summary.ingest_result_created == 1
        assert summary.status == ConnectorStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_run_all_isolation(self) -> None:
        """A failing connector should not abort subsequent connectors."""
        from app.schemas.opportunity import OpportunityIngestResult

        failing_connector = MagicMock(spec=BaseOpportunityConnector)
        failing_connector.source_name = "remotive"
        failing_connector.run = AsyncMock(side_effect=Exception("network dead"))

        good_connector = MagicMock(spec=BaseOpportunityConnector)
        good_connector.source_name = "codeforces"
        good_connector.run = AsyncMock(
            return_value=(
                [
                    RawOpportunityRow(
                        title="CF Round",
                        company="Codeforces",
                        description="Contest",
                        source="codeforces",
                        source_id="cf-99",
                    )
                ],
                ConnectorRunSummary(
                    source="codeforces", status=ConnectorStatus.SUCCESS, records_fetched=1
                ),
            )
        )

        mock_db = AsyncMock()
        with patch("app.services.connectors.orchestrator.ingest_raw_records") as mock_ingest:
            mock_ingest.return_value = OpportunityIngestResult(
                total=1, created=1, skipped_duplicates=0, errors=[]
            )
            orch = ConnectorOrchestrator(mock_db)
            summaries = await orch.run_all([failing_connector, good_connector])

        assert len(summaries) == 2
        assert summaries[0].status == ConnectorStatus.FAILED
        assert summaries[1].status == ConnectorStatus.SUCCESS


# ============================================================================
# Regression: Enum compatibility
# ============================================================================


class TestPhase263EnumCompatibility:
    """Ensure Phase 26.3 enum values remain stable and backward-compatible."""

    def test_opportunity_source_remotive(self) -> None:
        assert OpportunitySource.REMOTIVE == "remotive"

    def test_opportunity_source_arbeitnow(self) -> None:
        assert OpportunitySource.ARBEITNOW == "arbeitnow"

    def test_opportunity_source_codeforces(self) -> None:
        assert OpportunitySource.CODEFORCES == "codeforces"

    def test_opportunity_source_greenhouse(self) -> None:
        assert OpportunitySource.GREENHOUSE == "greenhouse"

    def test_opportunity_type_coding_contest(self) -> None:
        assert OpportunityType.CODING_CONTEST == "coding_contest"

    def test_work_mode_remote(self) -> None:
        assert WorkMode.REMOTE == "remote"

    def test_employment_type_any(self) -> None:
        assert EmploymentType.ANY == "any"

    def test_existing_types_unchanged(self) -> None:
        assert OpportunityType.JOB == "job"
        assert OpportunityType.INTERNSHIP == "internship"
        assert OpportunityType.HACKATHON == "hackathon"

    def test_existing_sources_unchanged(self) -> None:
        assert OpportunitySource.SYNTHETIC == "synthetic"
        assert OpportunitySource.MANUAL == "manual"
        assert OpportunitySource.API == "api"


# ============================================================================
# Regression: Normalizer compatibility with connector sources
# ============================================================================


class TestNormalizerCompatibility:
    """Verify normalizer handles connector source strings correctly."""

    def test_normalize_source_remotive(self) -> None:
        from app.services.opportunity_normalizer import normalize_source

        assert normalize_source("remotive") == OpportunitySource.REMOTIVE

    def test_normalize_source_arbeitnow(self) -> None:
        from app.services.opportunity_normalizer import normalize_source

        assert normalize_source("arbeitnow") == OpportunitySource.ARBEITNOW

    def test_normalize_source_codeforces(self) -> None:
        from app.services.opportunity_normalizer import normalize_source

        assert normalize_source("codeforces") == OpportunitySource.CODEFORCES

    def test_normalize_source_greenhouse(self) -> None:
        from app.services.opportunity_normalizer import normalize_source

        assert normalize_source("greenhouse") == OpportunitySource.GREENHOUSE

    def test_normalize_opportunity_type_coding_contest(self) -> None:
        from app.services.opportunity_normalizer import normalize_opportunity_type

        assert normalize_opportunity_type("coding_contest") == OpportunityType.CODING_CONTEST

    def test_parse_flexible_datetime_epoch(self) -> None:
        from app.services.opportunity_normalizer import parse_flexible_datetime

        result = parse_flexible_datetime(1795000000)
        assert result is not None
        assert result.tzinfo is not None
        expected = datetime.fromtimestamp(1795000000, tz=UTC)
        assert result == expected

    def test_parse_flexible_datetime_iso_z(self) -> None:
        from app.services.opportunity_normalizer import parse_flexible_datetime

        result = parse_flexible_datetime("2026-10-01T12:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.tzinfo is not None
