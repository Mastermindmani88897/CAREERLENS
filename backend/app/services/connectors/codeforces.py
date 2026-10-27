"""
Codeforces connector for Phase 26.3 Wave 1.

Official API endpoint:
    GET https://codeforces.com/api/contest.list?gym=false

Documentation: https://codeforces.com/apiHelp/methods#contest.list
Authentication: None for public contests.
Rate limits:    Max 5 requests/second; terms explicitly allow non-commercial client use.

Response schema:
{
  "status": "OK",
  "result": [
    {
      "id": 2042,
      "name": "Codeforces Round 970 (Div. 3)",
      "type": "CF",
      "phase": "BEFORE",
      "frozen": false,
      "durationSeconds": 9000,
      "startTimeSeconds": 1795000000,
      "relativeTimeSeconds": -3600
    }
  ]
}

Phase values:
  BEFORE  — contest has not started yet (upcoming)
  CODING  — contest is currently live
  PENDING_SYSTEM_TEST — coding finished, system tests pending
  SYSTEM_TEST — system tests running
  FINISHED — contest is over

Design decisions:
- Fetch all public (gym=false) contests.
- Map BEFORE and CODING phases as active opportunities (is_active=True).
- Map FINISHED/past contests with is_active=False (preserve historical record).
- Contest URL: https://codeforces.com/contest/{id}
- Source ID: "cf-{contest_id}"
- Opportunity type: coding_contest
- Company: "Codeforces"
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.opportunity import RawOpportunityRow
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    _execute_with_retries,
)

logger = get_logger("connectors.codeforces")

_API_URL = "https://codeforces.com/api/contest.list"

# Active phases where the opportunity is still open or upcoming
_ACTIVE_PHASES = {"BEFORE", "CODING"}

# Phases that represent a finished contest
_FINISHED_PHASES = {"PENDING_SYSTEM_TEST", "SYSTEM_TEST", "FINISHED"}

_MAX_CONTESTS = 5000  # Safety cap


def _build_contest_url(contest_id: int) -> str:
    return f"https://codeforces.com/contest/{contest_id}"


def _parse_record(contest: dict[str, Any]) -> RawOpportunityRow | None:
    """Map a Codeforces contest dict to a RawOpportunityRow."""
    try:
        contest_id = contest.get("id")
        if not contest_id or not isinstance(contest_id, int):
            return None
        source_id = f"cf-{contest_id}"

        name = (contest.get("name") or "").strip()
        if not name:
            return None

        phase: str = (contest.get("phase") or "FINISHED").upper()
        is_active = phase in _ACTIVE_PHASES

        duration_seconds: int | None = contest.get("durationSeconds")
        if not isinstance(duration_seconds, int):
            duration_seconds = None

        # Start time (Unix epoch seconds, UTC)
        start_ts = contest.get("startTimeSeconds")
        event_start_time: datetime | None = None
        event_end_time: datetime | None = None

        if isinstance(start_ts, (int, float)) and start_ts > 0:
            try:
                event_start_time = datetime.fromtimestamp(int(start_ts), tz=UTC)
                if duration_seconds and duration_seconds > 0:
                    from datetime import timedelta

                    event_end_time = event_start_time + timedelta(seconds=duration_seconds)
            except (OSError, OverflowError, ValueError):
                event_start_time = None
                event_end_time = None

        contest_url = _build_contest_url(contest_id)
        contest_type: str = (contest.get("type") or "").upper()

        # Build a minimal description
        description_parts = [f"Codeforces contest: {name}."]
        if contest_type:
            description_parts.append(f"Type: {contest_type}.")
        if duration_seconds:
            hours, mins = divmod(duration_seconds // 60, 60)
            if hours:
                description_parts.append(f"Duration: {hours}h {mins}m.")
            else:
                description_parts.append(f"Duration: {mins}m.")
        description_parts.append(f"Phase: {phase}.")
        description = " ".join(description_parts)

        return RawOpportunityRow(
            title=name,
            company="Codeforces",
            description=description,
            opportunity_type="coding_contest",
            employment_type="any",
            work_mode="remote",
            location_city=None,
            location_state=None,
            location_country=None,
            job_url=contest_url,
            source="codeforces",
            source_id=source_id,
            posted_date=None,
            required_skills=None,
            preferred_skills=None,
            is_active=is_active,
            event_start_time=event_start_time,
            event_end_time=event_end_time,
            duration_seconds=duration_seconds,
            registration_deadline=None,
            prize_summary=None,
            external_metadata={
                "contest_id": contest_id,
                "phase": phase,
                "type": contest_type,
                "frozen": bool(contest.get("frozen", False)),
            },
        )
    except Exception as exc:
        logger.debug("Failed to parse Codeforces contest id=%s: %s", contest.get("id"), exc)
        return None


class CodeforcesConnector(BaseOpportunityConnector):
    """
    Connector for the Codeforces public contest list API.

    The contest list endpoint returns all contests in a single response
    (no cursor/page pagination). The connector fetches once and returns
    all records (both active/upcoming and finished).
    """

    source_name = "codeforces"
    rate_limit_delay = 0.0  # Single-request endpoint
    timeout = httpx.Timeout(connect=15.0, read=45.0, write=10.0, pool=10.0)

    def is_configured(self) -> bool:
        """Codeforces public API requires no credentials — always configured."""
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
        Fetch all public Codeforces contests in a single API call.

        cursor is unused (single-page API).
        """
        if cursor is not None:
            return ConnectorBatchResult(records=[], next_cursor=None)

        params = {"gym": "false"}

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
                error=f"Unexpected payload type: {type(payload).__name__}",
            )

        api_status: str = (payload.get("status") or "").upper()
        if api_status != "OK":
            comment = payload.get("comment") or ""
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error=f"Codeforces API status={api_status}: {comment}",
            )

        result: list[Any] = payload.get("result") or []
        if not isinstance(result, list):
            return ConnectorBatchResult(
                records=[],
                next_cursor=None,
                error="'result' field is not a list",
            )

        records: list[RawOpportunityRow] = []
        for contest in result[:_MAX_CONTESTS]:
            if not isinstance(contest, dict):
                continue
            row = _parse_record(contest)
            if row is not None:
                records.append(row)

        active_count = sum(1 for r in records if r.is_active)
        logger.info(
            "[codeforces] Fetched %d contests, parsed %d records (%d active/upcoming).",
            len(result),
            len(records),
            active_count,
        )

        return ConnectorBatchResult(
            records=records,
            next_cursor=None,  # No pagination
            raw_count=len(result),
        )
