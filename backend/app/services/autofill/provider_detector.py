"""
ATS Provider Detection Service for Phase 27 External Application Autofill.

Inspects validated external application URLs to identify supported ATS platforms
(Greenhouse, Lever) using strict regex path contracts and domain boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from app.models.enums import ATSProvider

# Greenhouse URL path patterns:
# 1. Standard public board: https://boards.greenhouse.io/{board}/jobs/{id}
# 2. Embedded application: https://boards.greenhouse.io/embed/job_app?for={board}&token={id}
_GREENHOUSE_STANDARD_REGEX = re.compile(r"^/([a-zA-Z0-9_\-]+)/jobs/([a-zA-Z0-9_\-]+)/?$")
_GREENHOUSE_HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io"}

# Lever URL path patterns:
# 1. Hosted job detail: https://jobs.lever.co/{site}/{posting_id}
# 2. Direct apply page: https://jobs.lever.co/{site}/{posting_id}/apply
_LEVER_POSTING_REGEX = re.compile(r"^/([a-zA-Z0-9_\-]+)/([a-f0-9\-]{10,64})(?:/apply)?/?$")
_LEVER_HOSTS = {"jobs.lever.co"}


@dataclass(frozen=True)
class ProviderDetectionResult:
    """Structured detection telemetry for an external application page."""

    provider: ATSProvider
    is_supported: bool
    board_slug: str | None = None
    external_job_id: str | None = None
    is_direct_apply_page: bool = False


def detect_ats_provider(url: str) -> ProviderDetectionResult:
    """
    Analyze parsed URL components to detect supported ATS providers.

    Args:
        url: Sanitized HTTPS application URL.

    Returns:
        ProviderDetectionResult containing provider enum and parsed job identifiers.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return ProviderDetectionResult(
            provider=ATSProvider.UNSUPPORTED,
            is_supported=False,
        )

    hostname = (parsed.hostname or "").lower().strip()
    path = parsed.path.strip()

    # 1. Detect Greenhouse
    if hostname in _GREENHOUSE_HOSTS:
        # Check standard path: /{board}/jobs/{id}
        std_match = _GREENHOUSE_STANDARD_REGEX.match(path)
        if std_match:
            board = std_match.group(1)
            job_id = std_match.group(2)
            return ProviderDetectionResult(
                provider=ATSProvider.GREENHOUSE,
                is_supported=True,
                board_slug=board,
                external_job_id=job_id,
                is_direct_apply_page=True,
            )

        # Check embed path: /embed/job_app?for={board}&token={id}
        if path == "/embed/job_app":
            qs = parse_qs(parsed.query)
            board = qs.get("for", [None])[0]
            token = qs.get("token", [None])[0]
            if board and token:
                return ProviderDetectionResult(
                    provider=ATSProvider.GREENHOUSE,
                    is_supported=True,
                    board_slug=board,
                    external_job_id=token,
                    is_direct_apply_page=True,
                )

    # 2. Detect Lever
    if hostname in _LEVER_HOSTS:
        match = _LEVER_POSTING_REGEX.match(path)
        if match:
            site = match.group(1)
            posting_id = match.group(2)
            is_apply = path.endswith("/apply") or path.endswith("/apply/")
            return ProviderDetectionResult(
                provider=ATSProvider.LEVER,
                is_supported=True,
                board_slug=site,
                external_job_id=posting_id,
                is_direct_apply_page=is_apply,
            )

    return ProviderDetectionResult(
        provider=ATSProvider.UNSUPPORTED,
        is_supported=False,
    )
