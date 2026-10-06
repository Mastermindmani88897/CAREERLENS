"""
Abstract base class for format-specific text extractors.
"""

from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """Abstract interface for format-specific resume text extractors."""

    @abstractmethod
    def extract_text(self, content: bytes) -> str:
        """
        Extract raw text content from file bytes.

        Args:
            content: Raw byte contents of the file.

        Returns:
            Extracted text string.

        Raises:
            ResumeParsingError / NoExtractableTextError on extraction issues.
        """
