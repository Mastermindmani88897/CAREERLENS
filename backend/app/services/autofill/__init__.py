"""
Phase 27 External Application Autofill package.
"""

from app.services.autofill.exceptions import (
    AutofillDisabledError,
    AutofillError,
    AutofillSessionNotFoundError,
    CandidateProfileNotFoundError,
    InvalidURLError,
    OpportunityUnavailableError,
    ProhibitedDestinationError,
    ResumeNotFoundError,
    UnsupportedProviderError,
)
from app.services.autofill.payload_builder import (
    build_normalized_autofill_payload,
    derive_names,
)
from app.services.autofill.provider_detector import (
    ProviderDetectionResult,
    detect_ats_provider,
)
from app.services.autofill.session_service import (
    cancel_autofill_session,
    get_autofill_session_by_id,
    prepare_autofill_session,
)
from app.services.autofill.url_validator import (
    is_prohibited_ip,
    resolve_hostname_ips,
    validate_external_application_url,
)

__all__ = [
    "AutofillError",
    "AutofillDisabledError",
    "InvalidURLError",
    "ProhibitedDestinationError",
    "UnsupportedProviderError",
    "OpportunityUnavailableError",
    "CandidateProfileNotFoundError",
    "ResumeNotFoundError",
    "AutofillSessionNotFoundError",
    "is_prohibited_ip",
    "resolve_hostname_ips",
    "validate_external_application_url",
    "ProviderDetectionResult",
    "detect_ats_provider",
    "derive_names",
    "build_normalized_autofill_payload",
    "prepare_autofill_session",
    "get_autofill_session_by_id",
    "cancel_autofill_session",
]
