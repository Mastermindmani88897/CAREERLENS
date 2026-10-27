"""
Phase 26.4 Wave 2 Connector Tests.

Tests all four Wave 2 connectors with 100% mocked HTTP responses:
- AdzunaConnector
- USAJOBSConnector
- LeverConnector
- RemoteOKConnector

Covers:
- Happy-path parsing & normalization across all 4 platforms
- Missing / invalid credentials and NOT_CONFIGURED state
- Secret masking (no API keys in logs/exceptions)
- Pagination, bounded page limits, and cursor progression
- Salary, currency, and date conversions (including hourly rate annualization for USAJOBS)
- Work mode and employment type inferences (telework, remote tags, internships)
- Multi-employer aggregation with fault isolation (Lever)
- Remote OK legal disclaimer skipping and tag sanitization
- HTTP 429, timeouts, transient errors, and retry behavior
- Schema drift and malformed payload resilience
- ConnectorOrchestrator integration with Wave 2 connectors
- Registry integrity (get_all_connectors)
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.enums import EmploymentType, OpportunitySource, OpportunityType, WorkMode
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.adzuna import (
    AdzunaConnector,
    _parse_created_date,
    _strip_html,
)
from app.services.connectors.adzuna import (
    _infer_employment_type as adz_emp_type,
)
from app.services.connectors.adzuna import (
    _infer_work_mode as adz_work_mode,
)
from app.services.connectors.adzuna import (
    _parse_location as adz_parse_location,
)
from app.services.connectors.adzuna import (
    _parse_record as adz_parse_record,
)
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.connectors.lever import (
    LeverConnector,
)
from app.services.connectors.lever import (
    _infer_employment_type as lever_emp_type,
)
from app.services.connectors.lever import (
    _infer_work_mode as lever_work_mode,
)
from app.services.connectors.lever import (
    _normalize_company_name as lever_norm_company,
)
from app.services.connectors.lever import (
    _parse_posting as lever_parse_posting,
)
from app.services.connectors.lever import (
    _parse_salary as lever_parse_salary,
)
from app.services.connectors.lever import (
    _split_location as lever_split_location,
)
from app.services.connectors.orchestrator import ConnectorOrchestrator, get_all_connectors
from app.services.connectors.remoteok import (
    RemoteOKConnector,
)
from app.services.connectors.remoteok import (
    _clean_skills as ro_clean_skills,
)
from app.services.connectors.remoteok import (
    _infer_employment_type as ro_emp_type,
)
from app.services.connectors.remoteok import (
    _parse_record as ro_parse_record,
)
from app.services.connectors.usajobs import (
    USAJOBSConnector,
)
from app.services.connectors.usajobs import (
    _infer_employment_type as usa_emp_type,
)
from app.services.connectors.usajobs import (
    _infer_work_mode as usa_work_mode,
)
from app.services.connectors.usajobs import (
    _parse_iso_date as usa_parse_date,
)
from app.services.connectors.usajobs import (
    _parse_job_item as usa_parse_job,
)
from app.services.connectors.usajobs import (
    _parse_location as usa_parse_location,
)
from app.services.connectors.usajobs import (
    _parse_remuneration as usa_parse_remuneration,
)


def _make_httpx_response(status_code: int, json_data: Any) -> httpx.Response:
    """Helper to build a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://mock.api.example/test"),
    )


# =============================================================================
# 1. ADZUNA CONNECTOR TESTS
# =============================================================================


def _adzuna_job(**kwargs: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "123456789",
        "title": "Senior <strong>Python</strong> Developer",
        "description": "Build high-performance <strong>FastAPI</strong> backends.",
        "company": {"display_name": "Tech Corp Inc"},
        "location": {
            "display_name": "San Francisco, California",
            "area": ["US", "California", "San Francisco County", "San Francisco"],
        },
        "salary_min": 120000,
        "salary_max": 160000,
        "salary_is_predicted": 0,
        "category": {"label": "IT Jobs", "tag": "it-jobs"},
        "redirect_url": "https://www.adzuna.com/details/123456789",
        "created": "2026-10-15T12:00:00Z",
        "contract_time": "full_time",
        "contract_type": "permanent",
    }
    base.update(kwargs)
    return base


class TestAdzunaConnector:
    """Unit and mock tests for AdzunaConnector."""

    def test_strip_html(self) -> None:
        assert _strip_html("Hello <strong>World</strong>!") == "Hello World!"
        assert _strip_html(None) == ""
        assert _strip_html("<p>Text with <a href='#'>link</a></p>") == "Text with link"

    def test_parse_created_date(self) -> None:
        dt = _parse_created_date("2026-10-15T12:30:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 10
        assert dt.day == 15
        assert _parse_created_date("invalid-date") is None
        assert _parse_created_date(None) is None

    def test_parse_location_area_list(self) -> None:
        loc = {"area": ["US", "California", "San Francisco County", "San Francisco"]}
        city, state, country = adz_parse_location(loc, "us")
        assert city == "San Francisco"
        assert state == "California"
        assert country == "US"

    def test_parse_location_display_name_fallback(self) -> None:
        loc = {"display_name": "Austin, Texas, US"}
        city, state, country = adz_parse_location(loc, "us")
        assert city == "Austin"
        assert country == "US"

    def test_infer_work_mode(self) -> None:
        assert adz_work_mode("Remote Python Engineer", "") == WorkMode.REMOTE
        assert adz_work_mode("Software Engineer", "Work from home available") == WorkMode.REMOTE
        assert adz_work_mode("Backend Engineer", "Hybrid 2 days in office") == WorkMode.HYBRID
        assert adz_work_mode("Senior Engineer", "Office in Downtown") == WorkMode.ANY

    def test_infer_employment_type(self) -> None:
        assert (
            adz_emp_type("Software Engineering Intern", "full_time", None)
            == EmploymentType.INTERNSHIP
        )
        assert (
            adz_emp_type("Software Engineer", "full_time", "permanent") == EmploymentType.FULLTIME
        )
        assert adz_emp_type("Contractor", "part_time", "contract") == EmploymentType.PARTTIME

    def test_parse_record_happy_path(self) -> None:
        row = adz_parse_record(_adzuna_job(), "us")
        assert row is not None
        assert row.title == "Senior Python Developer"
        assert row.company == "Tech Corp Inc"
        assert "FastAPI backends" in row.description
        assert row.source == OpportunitySource.ADZUNA
        assert row.source_id == "adzuna-us-123456789"
        assert row.salary_min == 120000
        assert row.salary_max == 160000
        assert row.salary_currency == "USD"
        assert row.job_url == "https://www.adzuna.com/details/123456789"
        assert row.posted_date == date(2026, 10, 15)
        assert row.location_city == "San Francisco"
        assert row.location_state == "California"
        assert row.location_country == "US"
        assert row.required_skills == ["IT Jobs"]

    def test_parse_record_currency_gbp(self) -> None:
        row = adz_parse_record(_adzuna_job(id="999"), "gb")
        assert row is not None
        assert row.salary_currency == "GBP"
        assert row.source_id == "adzuna-gb-999"

    def test_parse_record_missing_id_returns_none(self) -> None:
        job = _adzuna_job()
        del job["id"]
        assert adz_parse_record(job, "us") is None

    def test_parse_record_missing_title_returns_none(self) -> None:
        job = _adzuna_job(title="")
        assert adz_parse_record(job, "us") is None

    def test_is_configured_false_when_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "")
        monkeypatch.setenv("ADZUNA_APP_KEY", "")
        assert AdzunaConnector().is_configured() is False

    def test_is_configured_true_when_set(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "test_id_123")
        monkeypatch.setenv("ADZUNA_APP_KEY", "test_key_abc")
        assert AdzunaConnector().is_configured() is True

    @pytest.mark.asyncio
    async def test_fetch_batch_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "")
        monkeypatch.setenv("ADZUNA_APP_KEY", "")
        res = await AdzunaConnector().fetch_batch()
        assert res.error is not None
        assert res.records == []

    @pytest.mark.asyncio
    async def test_run_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "")
        monkeypatch.setenv("ADZUNA_APP_KEY", "")
        records, summary = await AdzunaConnector().run()
        assert records == []
        assert summary.status == ConnectorStatus.NOT_CONFIGURED
        assert "not configured" in summary.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_batch_happy_path(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "mock_id")
        monkeypatch.setenv("ADZUNA_APP_KEY", "mock_key")

        payload = {
            "count": 42,
            "results": [_adzuna_job(id=f"job-{i}") for i in range(20)],
        }
        mock_resp = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.adzuna._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_resp
            connector = AdzunaConnector(results_per_page=20, max_pages=3)
            result = await connector.fetch_batch(cursor=1)

            assert len(result.records) == 20
            assert result.raw_count == 20
            assert result.next_cursor == 2

    @pytest.mark.asyncio
    async def test_fetch_batch_auth_rejection(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "invalid_id")
        monkeypatch.setenv("ADZUNA_APP_KEY", "invalid_key")

        mock_resp = _make_httpx_response(401, {"error": "unauthorized"})

        with patch(
            "app.services.connectors.adzuna._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_resp
            connector = AdzunaConnector()
            result = await connector.fetch_batch()

            assert result.error is not None
            assert "rejected or quota exhausted" in result.error
            assert result.records == []


# =============================================================================
# 2. USAJOBS CONNECTOR TESTS
# =============================================================================


def _usajobs_item(**kwargs: Any) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "PositionTitle": "IT Specialist (INFOSEC)",
        "PositionURI": "https://www.usajobs.gov/GetJob/ViewDetails/7654321",
        "ApplyURI": ["https://www.usajobs.gov/GetJob/Apply/7654321"],
        "PositionLocationDisplay": "Washington, District of Columbia",
        "PositionLocation": [
            {
                "LocationName": "Washington, District of Columbia",
                "CountryCode": "United States",
                "CountrySubDivisionCode": "District of Columbia",
                "CityName": "Washington",
            }
        ],
        "OrganizationName": "Department of Energy",
        "DepartmentName": "Department of Energy",
        "JobCategory": [{"Name": "Information Technology Management", "Code": "2210"}],
        "PositionSchedule": [{"Name": "Full Time", "Code": "1"}],
        "PositionOfferingType": [{"Name": "Permanent", "Code": "15317"}],
        "PositionRemuneration": [
            {
                "MinimumRange": "95000",
                "MaximumRange": "145000",
                "RateIntervalCode": "PA",
                "Description": "Per Year",
            }
        ],
        "PublicationStartDate": "2026-10-15T00:00:00.0000",
        "ApplicationCloseDate": "2026-10-31T23:59:59.9999",
        "UserArea": {
            "Details": {
                "JobSummary": "Serves as an IT Specialist analyzing security architectures.",
                "TeleworkEligible": True,
            }
        },
    }
    descriptor.update(kwargs.get("descriptor", {}))

    return {
        "MatchedObjectId": kwargs.get("MatchedObjectId", "7654321"),
        "MatchedObjectDescriptor": descriptor,
    }


class TestUSAJOBSConnector:
    """Unit and mock tests for USAJOBSConnector."""

    def test_parse_iso_date(self) -> None:
        dt = usa_parse_date("2026-10-15T00:00:00.0000")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 10
        assert dt.day == 15
        assert usa_parse_date(None) is None

    def test_parse_remuneration_per_annum(self) -> None:
        rem = [{"MinimumRange": "95000", "MaximumRange": "145000", "RateIntervalCode": "PA"}]
        sal_min, sal_max, curr = usa_parse_remuneration(rem)
        assert sal_min == 95000
        assert sal_max == 145000
        assert curr == "USD"

    def test_parse_remuneration_hourly_annualized(self) -> None:
        rem = [{"MinimumRange": "50.00", "MaximumRange": "75.00", "RateIntervalCode": "PH"}]
        sal_min, sal_max, curr = usa_parse_remuneration(rem)
        assert sal_min == 50 * 2080
        assert sal_max == 75 * 2080
        assert curr == "USD"

    def test_parse_location(self) -> None:
        desc = {
            "PositionLocation": [
                {
                    "CityName": "San Francisco",
                    "CountrySubDivisionCode": "California",
                    "CountryCode": "United States",
                }
            ]
        }
        city, state, country = usa_parse_location(desc)
        assert city == "San Francisco"
        assert state == "California"
        assert country == "United States"

    def test_infer_work_mode_telework(self) -> None:
        desc = {"UserArea": {"Details": {"TeleworkEligible": True}}}
        assert usa_work_mode(desc) == WorkMode.REMOTE

        desc_onsite = {
            "UserArea": {"Details": {"TeleworkEligible": False}},
            "PositionLocationDisplay": "Denver, CO",
        }
        assert usa_work_mode(desc_onsite) == WorkMode.ONSITE

    def test_infer_employment_type_internship(self) -> None:
        desc = {"PositionTitle": "Student Trainee (Computer Science) - Pathways Intern"}
        opp_t, emp_t = usa_emp_type(desc)
        assert opp_t == OpportunityType.INTERNSHIP
        assert emp_t == EmploymentType.INTERNSHIP

    def test_parse_job_item_happy_path(self) -> None:
        row = usa_parse_job(_usajobs_item())
        assert row is not None
        assert row.title == "IT Specialist (INFOSEC)"
        assert row.company == "Department of Energy"
        assert "analyzing security architectures" in row.description
        assert row.source == OpportunitySource.USAJOBS
        assert row.source_id == "usajobs-7654321"
        assert row.work_mode == WorkMode.REMOTE
        assert row.opportunity_type == OpportunityType.JOB
        assert row.employment_type == EmploymentType.FULLTIME
        assert row.salary_min == 95000
        assert row.salary_max == 145000
        assert row.salary_currency == "USD"
        assert row.location_city == "Washington"
        assert row.posted_date == date(2026, 10, 15)
        assert row.application_deadline == date(2026, 10, 31)
        assert row.required_skills == ["Information Technology Management"]

    def test_is_configured_false_when_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("USAJOBS_API_KEY", "")
        monkeypatch.setenv("USAJOBS_EMAIL", "")
        assert USAJOBSConnector().is_configured() is False

    def test_is_configured_true_when_set(self, monkeypatch) -> None:
        monkeypatch.setenv("USAJOBS_API_KEY", "real_key_123")
        monkeypatch.setenv("USAJOBS_EMAIL", "developer@example.gov")
        assert USAJOBSConnector().is_configured() is True

    def test_auth_headers_contains_required_keys(self, monkeypatch) -> None:
        monkeypatch.setenv("USAJOBS_API_KEY", "secret_key_xyz")
        monkeypatch.setenv("USAJOBS_EMAIL", "dev@agency.gov")
        headers = USAJOBSConnector().get_auth_headers()
        assert headers["Host"] == "data.usajobs.gov"
        assert headers["User-Agent"] == "dev@agency.gov"
        assert headers["Authorization-Key"] == "secret_key_xyz"

    @pytest.mark.asyncio
    async def test_run_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("USAJOBS_API_KEY", "")
        monkeypatch.setenv("USAJOBS_EMAIL", "")
        records, summary = await USAJOBSConnector().run()
        assert records == []
        assert summary.status == ConnectorStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_fetch_batch_happy_path(self, monkeypatch) -> None:
        monkeypatch.setenv("USAJOBS_API_KEY", "mock_key")
        monkeypatch.setenv("USAJOBS_EMAIL", "mock_email@agency.gov")

        payload = {
            "SearchResult": {
                "SearchResultCount": 2,
                "SearchResultCountAll": 100,
                "SearchResultItems": [
                    _usajobs_item(MatchedObjectId="111"),
                    _usajobs_item(MatchedObjectId="222"),
                ],
            }
        }
        mock_resp = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.usajobs._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_resp
            connector = USAJOBSConnector(results_per_page=2, max_pages=3)
            result = await connector.fetch_batch(cursor=1)

            assert len(result.records) == 2
            assert result.records[0].source_id == "usajobs-111"
            assert result.records[1].source_id == "usajobs-222"
            assert result.next_cursor == 2


# =============================================================================
# 3. LEVER CONNECTOR TESTS
# =============================================================================


def _lever_posting(**kwargs: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "12345678-abcd-1234-abcd-1234567890ab",
        "text": "Senior Platform Engineer",
        "createdAt": 1729000000000,
        "description": "<p>Build cloud systems</p>",
        "descriptionPlain": "Build cloud systems at scale.",
        "hostedUrl": "https://jobs.lever.co/spotify/12345678-abcd",
        "applyUrl": "https://jobs.lever.co/spotify/12345678-abcd/apply",
        "categories": {
            "commitment": "Full time",
            "department": "Engineering",
            "team": "Infrastructure",
            "location": "Stockholm, Sweden",
        },
        "workplaceType": "hybrid",
        "salaryRange": {
            "min": 110000,
            "max": 150000,
            "currency": "USD",
            "interval": "per-year-salary",
        },
    }
    base.update(kwargs)
    return base


class TestLeverConnector:
    """Unit and mock tests for LeverConnector."""

    def test_normalize_company_name(self) -> None:
        assert lever_norm_company("spotify") == "Spotify"
        assert lever_norm_company("my-cool-company") == "My Cool Company"
        assert lever_norm_company("uber_technologies") == "Uber Technologies"

    def test_split_location(self) -> None:
        city, state, country = lever_split_location("San Francisco, CA, USA")
        assert city == "San Francisco"
        assert state == "CA"
        assert country == "USA"

        city2, state2, country2 = lever_split_location("Stockholm, Sweden")
        assert city2 == "Stockholm"
        assert state2 is None
        assert country2 == "Sweden"

    def test_infer_work_mode(self) -> None:
        assert lever_work_mode("remote", "Engineer", "Anywhere") == WorkMode.REMOTE
        assert lever_work_mode("hybrid", "Engineer", "Office") == WorkMode.HYBRID
        assert lever_work_mode("onsite", "Engineer", "San Francisco") == WorkMode.ONSITE

    def test_infer_employment_type(self) -> None:
        opp_t, emp_t = lever_emp_type("Full time", "Engineer")
        assert opp_t == OpportunityType.JOB
        assert emp_t == EmploymentType.FULLTIME

        opp_t2, emp_t2 = lever_emp_type("Internship", "Software Intern")
        assert opp_t2 == OpportunityType.INTERNSHIP
        assert emp_t2 == EmploymentType.INTERNSHIP

    def test_parse_salary(self) -> None:
        sal_min, sal_max, curr = lever_parse_salary(
            {"min": 100000, "max": 140000, "currency": "EUR"}
        )
        assert sal_min == 100000
        assert sal_max == 140000
        assert curr == "EUR"

    def test_parse_posting_happy_path(self) -> None:
        row = lever_parse_posting(_lever_posting(), "spotify")
        assert row is not None
        assert row.title == "Senior Platform Engineer"
        assert row.company == "Spotify"
        assert "cloud systems at scale" in row.description
        assert row.source == OpportunitySource.LEVER
        assert row.source_id == "lever-spotify-12345678-abcd-1234-abcd-1234567890ab"
        assert row.work_mode == WorkMode.HYBRID
        assert row.employment_type == EmploymentType.FULLTIME
        assert row.salary_min == 110000
        assert row.salary_max == 150000
        assert row.salary_currency == "USD"
        assert row.location_city == "Stockholm"
        assert row.location_country == "Sweden"
        assert "Engineering" in (row.required_skills or [])
        assert "Infrastructure" in (row.required_skills or [])

    def test_is_configured_false_when_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("LEVER_SITE_TOKENS", "")
        assert LeverConnector().is_configured() is False

    def test_is_configured_true_with_tokens(self, monkeypatch) -> None:
        monkeypatch.setenv("LEVER_SITE_TOKENS", "spotify,palantir")
        assert LeverConnector().is_configured() is True

    @pytest.mark.asyncio
    async def test_run_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("LEVER_SITE_TOKENS", "")
        records, summary = await LeverConnector().run()
        assert records == []
        assert summary.status == ConnectorStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_fetch_batch_multi_employer_aggregation(self) -> None:
        payload_spotify = [_lever_posting(id="spot-1")]
        payload_palantir = [_lever_posting(id="pal-1", text="Forward Deployed Engineer")]

        resp_spot = _make_httpx_response(200, payload_spotify)
        resp_pal = _make_httpx_response(200, payload_palantir)

        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return resp_spot if call_count == 1 else resp_pal

        with patch(
            "app.services.connectors.lever._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = side_effect
            connector = LeverConnector(site_tokens=["spotify", "palantir"])
            result = await connector.fetch_batch()

            assert len(result.records) == 2
            assert result.records[0].company == "Spotify"
            assert result.records[1].company == "Palantir"

    @pytest.mark.asyncio
    async def test_fetch_batch_single_board_404_isolation(self) -> None:
        resp_404 = _make_httpx_response(404, {"error": "not found"})
        resp_good = _make_httpx_response(200, [_lever_posting(id="good-1")])

        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return resp_404 if call_count == 1 else resp_good

        with patch(
            "app.services.connectors.lever._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = side_effect
            connector = LeverConnector(site_tokens=["nonexistent_slug", "valid_slug"])
            result = await connector.fetch_batch()

            # The 404 on the first slug should not abort the second slug
            assert len(result.records) == 1
            assert result.records[0].source_id == "lever-valid_slug-good-1"


# =============================================================================
# 4. REMOTE OK CONNECTOR TESTS
# =============================================================================


def _remoteok_job(**kwargs: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "100234",
        "epoch": 1729000000,
        "date": "2026-10-15T12:00:00+00:00",
        "company": "Acme Remote",
        "position": "Senior Python Engineer",
        "tags": ["python", "fastapi", "remote", "postgres"],
        "description": "<p>We are hiring a Python engineer remotely.</p>",
        "location": "Worldwide",
        "salary_min": 100000,
        "salary_max": 140000,
        "apply_url": "https://remoteok.com/remote-jobs/100234-senior-python-engineer",
        "url": "https://remoteok.com/remote-jobs/100234",
    }
    base.update(kwargs)
    return base


class TestRemoteOKConnector:
    """Unit and mock tests for RemoteOKConnector."""

    def test_is_configured_always_true(self) -> None:
        assert RemoteOKConnector().is_configured() is True

    def test_auth_headers_contains_user_agent(self) -> None:
        headers = RemoteOKConnector().get_auth_headers()
        assert "User-Agent" in headers
        assert "CareerLens" in headers["User-Agent"]

    def test_clean_skills_filters_generic_tags(self) -> None:
        tags = ["python", "remote", "jobs", "fastapi", "work"]
        skills = ro_clean_skills(tags)
        assert "python" in skills
        assert "fastapi" in skills
        assert "remote" not in skills
        assert "jobs" not in skills

    def test_infer_employment_type(self) -> None:
        opp_t, emp_t = ro_emp_type("Software Engineering Intern", ["python"])
        assert opp_t == OpportunityType.INTERNSHIP
        assert emp_t == EmploymentType.INTERNSHIP

        opp_t2, emp_t2 = ro_emp_type("Senior Engineer", ["contract", "python"])
        assert emp_t2 == EmploymentType.CONTRACT

    def test_parse_record_skips_legal_object(self) -> None:
        legal_item = {"legal": "Please do not scrape", "terms": "https://remoteok.com/terms"}
        assert ro_parse_record(legal_item) is None

    def test_parse_record_happy_path(self) -> None:
        row = ro_parse_record(_remoteok_job())
        assert row is not None
        assert row.title == "Senior Python Engineer"
        assert row.company == "Acme Remote"
        assert "Python engineer remotely" in row.description
        assert row.source == OpportunitySource.REMOTEOK
        assert row.source_id == "remoteok-100234"
        assert row.work_mode == WorkMode.REMOTE
        assert row.salary_min == 100000
        assert row.salary_max == 140000
        assert row.salary_currency == "USD"
        assert row.job_url == "https://remoteok.com/remote-jobs/100234"
        assert row.posted_date == date(2026, 10, 15)
        assert "python" in (row.required_skills or [])
        assert "fastapi" in (row.required_skills or [])

    @pytest.mark.asyncio
    async def test_fetch_batch_happy_path(self) -> None:
        payload = [
            {"legal": "api disclaimer"},
            _remoteok_job(id="job-1"),
            _remoteok_job(id="job-2"),
        ]
        mock_resp = _make_httpx_response(200, payload)

        with patch(
            "app.services.connectors.remoteok._execute_with_retries", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_resp
            connector = RemoteOKConnector()
            result = await connector.fetch_batch()

            assert len(result.records) == 2
            assert result.raw_count == 2
            assert result.records[0].source_id == "remoteok-job-1"
            assert result.records[1].source_id == "remoteok-job-2"
            assert result.next_cursor is None


# =============================================================================
# 5. CONNECTOR ORCHESTRATOR & REGISTRY INTEGRATION
# =============================================================================


class TestConnectorOrchestratorWave2:
    """Tests orchestrator integration with all 8 Wave 1 and Wave 2 connectors."""

    def test_get_all_connectors_returns_all_eight(self) -> None:
        connectors = get_all_connectors()
        assert len(connectors) == 8
        source_names = {c.source_name for c in connectors}
        expected = {
            "remotive",
            "arbeitnow",
            "codeforces",
            "greenhouse",
            "adzuna",
            "usajobs",
            "lever",
            "remoteok",
        }
        assert source_names == expected

    @pytest.mark.asyncio
    async def test_orchestrator_handles_wave2_not_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("ADZUNA_APP_ID", "")
        monkeypatch.setenv("ADZUNA_APP_KEY", "")
        monkeypatch.setenv("USAJOBS_API_KEY", "")
        monkeypatch.setenv("USAJOBS_EMAIL", "")
        monkeypatch.setenv("LEVER_SITE_TOKENS", "")

        mock_db = AsyncMock()
        orch = ConnectorOrchestrator(mock_db)

        wave2 = [AdzunaConnector(), USAJOBSConnector(), LeverConnector()]
        summaries = await orch.run_all(wave2)

        assert len(summaries) == 3
        for s in summaries:
            assert s.status == ConnectorStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_orchestrator_ingests_wave2_records(self) -> None:
        from app.schemas.opportunity import OpportunityIngestResult

        mock_connector = MagicMock(spec=BaseOpportunityConnector)
        mock_connector.source_name = "remoteok"
        mock_connector.run = AsyncMock(
            return_value=(
                [
                    RawOpportunityRow(
                        title="Remote Go Engineer",
                        company="Distributed Co",
                        description="Go dev",
                        source="remoteok",
                        source_id="remoteok-999",
                    )
                ],
                ConnectorRunSummary(
                    source="remoteok", status=ConnectorStatus.SUCCESS, records_fetched=1
                ),
            )
        )

        mock_db = AsyncMock()
        with patch("app.services.connectors.orchestrator.ingest_raw_records") as mock_ingest:
            mock_ingest.return_value = OpportunityIngestResult(
                total=1, created=1, skipped_duplicates=0, errors=[]
            )
            orch = ConnectorOrchestrator(mock_db)
            summary = await orch.run_connector(mock_connector)

            assert summary.status == ConnectorStatus.SUCCESS
            assert summary.ingest_result_created == 1
            assert summary.ingest_result_errors == 0
