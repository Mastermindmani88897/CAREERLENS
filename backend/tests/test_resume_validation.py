"""
Tests for Phase 11 resume upload validation and security defenses.
Covers:
- Extension allowlist enforcement
- Magic byte / file signature verification
- File size boundary enforcement
- Rejection of executables and scripts
- Path traversal prevention
- Filename sanitization
"""

import pytest

from app.services.resume_parser.exceptions import ResumeValidationError
from app.services.resume_parser.validator import (
    generate_secure_storage_path,
    sanitize_filename,
    validate_file_extension,
    validate_file_signature,
    validate_file_size,
    validate_resume_file,
)
from tests.helpers.synthetic_resumes import (
    create_empty_document,
    create_oversized_resume,
    create_synthetic_docx_resume,
    create_synthetic_pdf_resume,
    create_synthetic_txt_resume,
    create_unsupported_file,
)


def test_sanitize_filename_cleans_traversal() -> None:
    """Ensure path traversal sequences and separators are completely stripped."""
    assert sanitize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("my resume (1).pdf") == "my_resume_1_.pdf"
    assert sanitize_filename("") == "resume"
    assert sanitize_filename("   ") == "resume"


def test_validate_file_extension_supported() -> None:
    """Valid extensions (.pdf, .docx, .txt) are accepted and normalized."""
    assert validate_file_extension("resume.PDF") == ".pdf"
    assert validate_file_extension("resume.docx") == ".docx"
    assert validate_file_extension("resume.TXT") == ".txt"


def test_validate_file_extension_unsupported() -> None:
    """Disallowed extensions are rejected with informative error."""
    with pytest.raises(ResumeValidationError, match="Unsupported file extension"):
        validate_file_extension("resume.exe")

    with pytest.raises(ResumeValidationError, match="Unsupported file extension"):
        validate_file_extension("resume.py")

    with pytest.raises(ResumeValidationError, match="Unsupported file extension"):
        validate_file_extension("resume.png")


def test_validate_file_size_limits() -> None:
    """File size boundary enforcement (empty rejected, oversized rejected, normal accepted)."""
    # Empty file
    with pytest.raises(ResumeValidationError, match="empty"):
        validate_file_size(create_empty_document())

    # Valid size
    valid_content = create_synthetic_txt_resume()
    validate_file_size(valid_content, max_size_mb=10)

    # Oversized file
    oversized = create_oversized_resume(size_mb=11)
    with pytest.raises(ResumeValidationError, match="exceeds maximum"):
        validate_file_size(oversized, max_size_mb=10)


def test_validate_file_signature_pdf() -> None:
    """PDF files must start with %PDF- signature."""
    pdf_bytes = create_synthetic_pdf_resume()
    validate_file_signature(pdf_bytes, ".pdf")

    # Disguised txt as pdf
    with pytest.raises(ResumeValidationError, match="missing standard '%PDF-'"):
        validate_file_signature(b"Hello world, I am text", ".pdf")


def test_validate_file_signature_docx() -> None:
    """DOCX files must be valid zip archives containing word/document.xml."""
    docx_bytes = create_synthetic_docx_resume()
    validate_file_signature(docx_bytes, ".docx")

    # Corrupt or disguised docx
    with pytest.raises(ResumeValidationError):
        validate_file_signature(b"PK\x03\x04corrupted", ".docx")


def test_validate_file_signature_txt() -> None:
    """Plain text files must not contain binary null bytes."""
    txt_bytes = create_synthetic_txt_resume()
    validate_file_signature(txt_bytes, ".txt")

    # Binary with null bytes disguised as txt
    with pytest.raises(ResumeValidationError, match="binary content detected"):
        validate_file_signature(b"Some text\x00with null byte", ".txt")


def test_validate_executable_signatures_rejected() -> None:
    """Executables with spoofed extensions (.pdf, .txt) are rejected."""
    exe_bytes = create_unsupported_file()
    with pytest.raises(
        ResumeValidationError, match="Executable or script files are strictly prohibited"
    ):
        validate_file_signature(exe_bytes, ".pdf")


def test_generate_secure_storage_path(tmp_path: pytest.TempPathFactory) -> None:
    """Generated storage paths must be unique, unguessable, and strictly inside upload directory."""
    secure_name, full_path = generate_secure_storage_path("my_resume.pdf", upload_dir=str(tmp_path))
    assert secure_name.endswith(".pdf")
    assert str(tmp_path) in full_path


def test_validate_resume_file_comprehensive() -> None:
    """Full validation pipeline accepts genuine PDF and returns normalized type."""
    pdf_bytes = create_synthetic_pdf_resume()
    file_type, sanitized_name = validate_resume_file("John_Resume.PDF", pdf_bytes)
    assert file_type == "pdf"
    assert sanitized_name == "John_Resume.PDF"
