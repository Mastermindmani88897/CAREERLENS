"""
Resume parsing and extraction module (Phase 11).
"""

from app.services.resume_parser.exceptions import (
    MalformedFileError,
    NoExtractableTextError,
    PasswordProtectedFileError,
    ResumeParsingError,
    ResumeValidationError,
)
from app.services.resume_parser.extractors import get_extractor
from app.services.resume_parser.normalizer import normalize_resume_text
from app.services.resume_parser.parser import ResumeParser
from app.services.resume_parser.section_detector import detect_sections
from app.services.resume_parser.validator import (
    generate_secure_storage_path,
    sanitize_filename,
    validate_resume_file,
)

__all__ = [
    "MalformedFileError",
    "NoExtractableTextError",
    "PasswordProtectedFileError",
    "ResumeParser",
    "ResumeParsingError",
    "ResumeValidationError",
    "detect_sections",
    "generate_secure_storage_path",
    "get_extractor",
    "normalize_resume_text",
    "sanitize_filename",
    "validate_resume_file",
]
