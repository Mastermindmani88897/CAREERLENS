"""
Custom exceptions for Resume Parsing & Extraction Pipeline (Phase 11).
"""


class ResumeParsingError(Exception):
    """Base exception for resume ingestion and parsing errors."""

    def __init__(self, message: str, safe_message: str | None = None) -> None:
        super().__init__(message)
        self.safe_message = safe_message or message


class ResumeValidationError(ResumeParsingError):
    """Raised when an uploaded file fails security or format validation."""


class NoExtractableTextError(ResumeParsingError):
    """Raised when a valid document has no extractable text (e.g. empty or scanned PDF)."""


class PasswordProtectedFileError(ResumeParsingError):
    """Raised when a document is encrypted or password-protected."""


class MalformedFileError(ResumeParsingError):
    """Raised when a document cannot be parsed due to file corruption."""
