"""
Deterministic normalization service for Phase 14 Opportunity Ingestion.
Normalizes text, URLs, dates, salaries, enums, locations, and organizations
while preserving clean display capitalization.
"""

import re
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models.enums import (
    EducationLevel,
    EmploymentType,
    OpportunitySource,
    OpportunityType,
    WorkMode,
)

# Control characters excluding standard newline and tab
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "fbclid",
    "gclid",
    "mc_eid",
    "src",
}


def sanitize_text(text: str | None, allow_multiline: bool = False) -> str:
    """
    Sanitize text input by removing control characters and collapsing whitespace.
    Preserves display capitalization (e.g. 'PostgreSQL', 'San Francisco').
    """
    if not text:
        return ""
    # Strip dangerous non-printable control characters
    cleaned = _CONTROL_CHAR_RE.sub("", text)
    if allow_multiline:
        # Normalize carriage returns and collapse excessive blank lines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines()]
        return "\n".join(line for line in lines if line or line == "")
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_url(url: str | None) -> str | None:
    """
    Validate and normalize HTTP/HTTPS URLs.
    Strips tracking query parameters and lowercase hostname.
    Rejects dangerous/executable schemes (javascript:, data:, file:, etc.).
    """
    if not url:
        return None
    trimmed = url.strip()
    if not trimmed:
        return None

    # Scheme check
    lower_start = trimmed.lower()
    if not (lower_start.startswith("http://") or lower_start.startswith("https://")):
        return None

    try:
        parts = urlsplit(trimmed)
    except Exception:
        return None

    if parts.scheme.lower() not in ("http", "https"):
        return None
    if not parts.netloc:
        return None

    # Lowercase scheme and hostname
    netloc = parts.netloc.lower()

    # Filter out tracking query params while preserving meaningful application params
    filtered_query = ""
    if parts.query:
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        kept_pairs = [(k, v) for k, v in query_pairs if k.lower() not in _TRACKING_PARAMS]
        filtered_query = urlencode(kept_pairs)

    return urlunsplit((parts.scheme.lower(), netloc, parts.path, filtered_query, parts.fragment))


def parse_flexible_date(val: Any) -> date | None:
    """
    Parse date from date instance or string in common formats:
    YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, YYYY/MM/DD.
    """
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()

    text_val = str(val).strip()
    if not text_val:
        return None

    # Common format patterns
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text_val, fmt).date()
        except ValueError:
            continue
    return None


def normalize_numeric_int(val: Any) -> int | None:
    """Parse integer from number or string (handles '120,000', '150k')."""
    if val is None:
        return None
    if isinstance(val, int):
        return max(0, val)
    if isinstance(val, float):
        return max(0, int(round(val)))

    text_val = str(val).strip().replace(",", "")
    if not text_val:
        return None

    # Handle 'k' / 'K' suffix (e.g. 150k -> 150000)
    multiplier = 1
    if text_val.lower().endswith("k"):
        multiplier = 1000
        text_val = text_val[:-1].strip()

    try:
        num = float(text_val)
        return max(0, int(round(num * multiplier)))
    except (ValueError, TypeError):
        return None


def normalize_currency(curr: str | None) -> str | None:
    """Normalize 3-letter currency code to uppercase."""
    if not curr:
        return None
    cleaned = re.sub(r"[^A-Za-z]", "", curr).upper()
    return cleaned[:10] if cleaned else None


def normalize_opportunity_type(raw: str | None) -> OpportunityType:
    """Normalize string to OpportunityType enum, default JOB."""
    if not raw:
        return OpportunityType.JOB
    norm = raw.strip().lower()
    for opt in OpportunityType:
        if opt.value == norm:
            return opt
    if "intern" in norm:
        return OpportunityType.INTERNSHIP
    if "hack" in norm:
        return OpportunityType.HACKATHON
    return OpportunityType.JOB


def normalize_employment_type(
    raw: str | None,
    opportunity_type: OpportunityType = OpportunityType.JOB,
) -> EmploymentType:
    """
    Normalize employment type based on raw string and opportunity type semantics.
    For HACKATHON, defaults to ANY.
    For INTERNSHIP, defaults to INTERNSHIP.
    """
    if raw:
        norm = re.sub(r"[\s\-_]+", "", raw.strip().lower())
        mapping = {
            "fulltime": EmploymentType.FULLTIME,
            "ft": EmploymentType.FULLTIME,
            "permanent": EmploymentType.FULLTIME,
            "parttime": EmploymentType.PARTTIME,
            "pt": EmploymentType.PARTTIME,
            "internship": EmploymentType.INTERNSHIP,
            "intern": EmploymentType.INTERNSHIP,
            "contract": EmploymentType.CONTRACT,
            "contractor": EmploymentType.CONTRACT,
            "temp": EmploymentType.CONTRACT,
            "any": EmploymentType.ANY,
        }
        if norm in mapping:
            return mapping[norm]

    # Defaults based on opportunity type semantics
    if opportunity_type == OpportunityType.HACKATHON:
        return EmploymentType.ANY
    if opportunity_type == OpportunityType.INTERNSHIP:
        return EmploymentType.INTERNSHIP
    return EmploymentType.FULLTIME


def normalize_work_mode(raw: str | None) -> WorkMode:
    """Normalize work mode string to WorkMode enum, default ANY."""
    if not raw:
        return WorkMode.ANY
    norm = re.sub(r"[\s\-_]+", "", raw.strip().lower())
    mapping = {
        "remote": WorkMode.REMOTE,
        "wfh": WorkMode.REMOTE,
        "hybrid": WorkMode.HYBRID,
        "onsite": WorkMode.ONSITE,
        "inoffice": WorkMode.ONSITE,
        "office": WorkMode.ONSITE,
        "any": WorkMode.ANY,
    }
    return mapping.get(norm, WorkMode.ANY)


def normalize_education_level(raw: str | None) -> EducationLevel:
    """Normalize education level string to EducationLevel enum, default ANY."""
    if not raw:
        return EducationLevel.ANY
    norm = re.sub(r"[\s\-_.]+", "", raw.strip().lower())
    mapping = {
        "none": EducationLevel.NONE,
        "diploma": EducationLevel.DIPLOMA,
        "bachelor": EducationLevel.BACHELOR,
        "bachelors": EducationLevel.BACHELOR,
        "bs": EducationLevel.BACHELOR,
        "ba": EducationLevel.BACHELOR,
        "btech": EducationLevel.BACHELOR,
        "master": EducationLevel.MASTER,
        "masters": EducationLevel.MASTER,
        "ms": EducationLevel.MASTER,
        "mtech": EducationLevel.MASTER,
        "phd": EducationLevel.PHD,
        "doctorate": EducationLevel.PHD,
        "any": EducationLevel.ANY,
    }
    return mapping.get(norm, EducationLevel.ANY)


def normalize_source(raw: str | None) -> OpportunitySource:
    """Normalize opportunity source string, default MANUAL."""
    if not raw:
        return OpportunitySource.MANUAL
    norm = raw.strip().lower()
    for src in OpportunitySource:
        if src.value == norm:
            return src
    return OpportunitySource.MANUAL


def parse_location_string(
    loc_str: str | None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """
    Resolve city, state, country from discrete fields or composite location string
    e.g. 'San Francisco, CA, USA' or 'Bengaluru, India'.
    """
    clean_city = sanitize_text(city) or None
    clean_state = sanitize_text(state) or None
    clean_country = sanitize_text(country) or None

    if (not clean_city or not clean_country) and loc_str:
        parts = [p.strip() for p in loc_str.split(",") if p.strip()]
        if len(parts) == 1:
            clean_city = clean_city or parts[0]
        elif len(parts) == 2:
            clean_city = clean_city or parts[0]
            clean_country = clean_country or parts[1]
        elif len(parts) >= 3:
            clean_city = clean_city or parts[0]
            clean_state = clean_state or parts[1]
            clean_country = clean_country or parts[2]

    return clean_city, clean_state, clean_country
