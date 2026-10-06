"""
Extractor registry and factory for format-specific text extractors.
"""

from app.services.resume_parser.exceptions import ResumeValidationError
from app.services.resume_parser.extractors.base import BaseExtractor
from app.services.resume_parser.extractors.docx import DOCXExtractor
from app.services.resume_parser.extractors.pdf import PDFExtractor
from app.services.resume_parser.extractors.txt import TXTExtractor

_EXTRACTORS: dict[str, type[BaseExtractor]] = {
    "pdf": PDFExtractor,
    "docx": DOCXExtractor,
    "txt": TXTExtractor,
}


def get_extractor(file_type: str) -> BaseExtractor:
    """
    Retrieve the appropriate extractor instance for the given file type.

    Args:
        file_type: File extension without leading dot (e.g. 'pdf', 'docx', 'txt').

    Returns:
        BaseExtractor instance.

    Raises:
        ResumeValidationError: If file type is unsupported.
    """
    normalized_type = file_type.lower().lstrip(".")
    extractor_cls = _EXTRACTORS.get(normalized_type)
    if not extractor_cls:
        raise ResumeValidationError(
            f"No extractor registered for file type '{file_type}'. Supported: pdf, docx, txt."
        )
    return extractor_cls()


__all__ = [
    "BaseExtractor",
    "DOCXExtractor",
    "PDFExtractor",
    "TXTExtractor",
    "get_extractor",
]
