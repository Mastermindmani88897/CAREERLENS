"""
Deterministic DOCX text extractor for Phase 11 using python-docx.
Extracts text from paragraphs and tables, preserving document ordering.
Defensively handles empty DOCX, malformed archives, and missing content.
"""

from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.services.resume_parser.exceptions import (
    MalformedFileError,
    NoExtractableTextError,
)
from app.services.resume_parser.extractors.base import BaseExtractor


class DOCXExtractor(BaseExtractor):
    """Safe DOCX text extractor."""

    def extract_text(self, content: bytes) -> str:
        """
        Extract text from DOCX bytes.

        Raises:
            MalformedFileError: If the DOCX package is corrupted or invalid.
            NoExtractableTextError: If the DOCX file contains no extractable text.
        """
        if not content:
            raise NoExtractableTextError(
                "DOCX file is empty.",
                safe_message="DOCX document contains no extractable text.",
            )

        stream = BytesIO(content)

        try:
            doc = Document(stream)
        except (PackageNotFoundError, Exception) as e:
            raise MalformedFileError(
                f"Malformed or corrupted DOCX file: {e}",
                safe_message="Uploaded DOCX document is malformed or corrupted.",
            ) from e

        text_blocks: list[str] = []

        # Iterate through paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                text_blocks.append(text)

        # Iterate through tables and extract cells
        for table in doc.tables:
            for row in table.rows:
                row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                # Deduplicate repeated text from merged cells in same row
                seen: set[str] = set()
                unique_row_texts: list[str] = []
                for cell_txt in row_texts:
                    if cell_txt not in seen:
                        seen.add(cell_txt)
                        unique_row_texts.append(cell_txt)
                if unique_row_texts:
                    text_blocks.append(" | ".join(unique_row_texts))

        extracted_text = "\n".join(text_blocks).strip()

        if not extracted_text:
            raise NoExtractableTextError(
                "DOCX contains no extractable text.",
                safe_message="DOCX document contains no extractable text.",
            )

        return extracted_text
