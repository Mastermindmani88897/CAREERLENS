"""
Deterministic TXT text extractor for Phase 11.
Safely extracts plain text, handling UTF-8, UTF-16, and Latin-1 encodings with fallback.
"""

from app.services.resume_parser.exceptions import (
    NoExtractableTextError,
    ResumeParsingError,
)
from app.services.resume_parser.extractors.base import BaseExtractor


class TXTExtractor(BaseExtractor):
    """Safe plain text extractor."""

    def extract_text(self, content: bytes) -> str:
        """
        Extract plain text from bytes.

        Raises:
            NoExtractableTextError: If the document is empty or contains only whitespace.
            ResumeParsingError: If encoding cannot be resolved.
        """
        if not content:
            raise NoExtractableTextError(
                "Text document is empty.",
                safe_message="TXT document contains no text.",
            )

        text = None
        # Try UTF-8 first (with or without BOM)
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
            try:
                text = content.decode(encoding)
                break
            except (UnicodeDecodeError, Exception):
                continue

        if text is None:
            # Fallback with replacement to avoid failing
            try:
                text = content.decode("utf-8", errors="replace")
            except Exception as e:
                raise ResumeParsingError(
                    f"Failed to decode text document: {e}",
                    safe_message="Failed to read text document due to unsupported encoding.",
                ) from e

        # Remove any null characters or control artifacts
        text = text.replace("\x00", "")
        cleaned = text.strip()

        if not cleaned:
            raise NoExtractableTextError(
                "Text document contains only whitespace.",
                safe_message="TXT document contains no text.",
            )

        return cleaned
