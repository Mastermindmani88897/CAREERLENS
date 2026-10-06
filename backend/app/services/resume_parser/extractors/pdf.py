"""
Deterministic PDF text extractor for Phase 11 using pypdf.
Extracts text across all pages without invoking OCR.
Defensively handles empty PDFs, password protection, malformed files, and scanned PDFs.
"""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import EmptyFileError, PdfReadError

from app.services.resume_parser.exceptions import (
    MalformedFileError,
    NoExtractableTextError,
    PasswordProtectedFileError,
)
from app.services.resume_parser.extractors.base import BaseExtractor


class PDFExtractor(BaseExtractor):
    """Safe, deterministic PDF text extractor."""

    def extract_text(self, content: bytes) -> str:
        """
        Extract text from PDF bytes.

        Raises:
            PasswordProtectedFileError: If the PDF is encrypted/password-protected.
            MalformedFileError: If the PDF data is corrupted or cannot be read.
            NoExtractableTextError: If the PDF contains no extractable text
                                    (e.g. empty or scanned document).
        """
        if not content:
            raise NoExtractableTextError(
                "PDF file is empty. No extractable text found.",
                safe_message=(
                    "PDF contains no extractable text. "
                    "Scanned-PDF OCR is not supported in Phase 11."
                ),
            )

        stream = BytesIO(content)

        try:
            reader = PdfReader(stream)
        except (PdfReadError, EmptyFileError) as e:
            raise MalformedFileError(
                f"Malformed or corrupted PDF file: {e}",
                safe_message="Uploaded PDF file is malformed or corrupted.",
            ) from e
        except Exception as e:
            raise MalformedFileError(
                f"Failed to read PDF structure: {e}",
                safe_message="Uploaded PDF file is malformed or corrupted.",
            ) from e

        # Handle password-protected / encrypted PDFs
        if reader.is_encrypted:
            try:
                # Attempt decrypt with empty password in case of standard unencrypted restriction
                decrypt_success = reader.decrypt("")
                if not decrypt_success or reader.is_encrypted:
                    raise PasswordProtectedFileError(
                        "PDF document is password-protected or encrypted.",
                        safe_message=(
                            "Password-protected PDFs are not supported. "
                            "Please upload an unprotected document."
                        ),
                    )
            except Exception as e:
                raise PasswordProtectedFileError(
                    f"Encrypted PDF cannot be read: {e}",
                    safe_message=(
                        "Password-protected PDFs are not supported. "
                        "Please upload an unprotected document."
                    ),
                ) from e

        pages_text: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(text)
            except Exception:
                # Tolerate individual page extraction issues, continue with other pages
                continue

        extracted_text = "\n\n".join(pages_text).strip()

        if not extracted_text:
            raise NoExtractableTextError(
                "PDF contains no extractable text. Scanned-PDF OCR is not supported in Phase 11.",
                safe_message=(
                    "PDF contains no extractable text. "
                    "Scanned-PDF OCR is not supported in Phase 11."
                ),
            )

        return extracted_text
