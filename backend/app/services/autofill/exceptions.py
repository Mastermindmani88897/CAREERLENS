"""
Exceptions for Phase 27 External Application Autofill Engine.
"""

from __future__ import annotations


class AutofillError(Exception):
    """Base exception for all application autofill operations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AutofillDisabledError(AutofillError):
    """Raised when the autofill feature is disabled via configuration."""


class InvalidURLError(AutofillError):
    """
    Raised when an external application URL is malformed, uses an unsafe scheme,
    or contains embedded credentials.
    """


class ProhibitedDestinationError(AutofillError):
    """Raised when a URL resolves to a private, loopback, link-local, or reserved IP address."""


class UnsupportedProviderError(AutofillError):
    """Raised when an external URL does not match any allowlisted ATS provider."""


class OpportunityUnavailableError(AutofillError):
    """
    Raised when an opportunity does not exist, is inactive, or lacks an external application URL.
    """


class CandidateProfileNotFoundError(AutofillError):
    """Raised when the authenticated user does not have an initialized candidate profile."""


class ResumeNotFoundError(AutofillError):
    """Raised when the requested resume does not exist or does not belong to the candidate."""


class AutofillSessionNotFoundError(AutofillError):
    """Raised when the requested autofill session is not found or not owned by the candidate."""
