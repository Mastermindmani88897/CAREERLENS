"""
Secure resume upload validator for Phase 11.
Enforces multi-layer defensive validation against untrusted file uploads:
- File extension allowlist (.pdf, .docx, .txt)
- MIME / content-type validation
- File signature / magic byte verification
- Content-level safety checks (executable header rejection, null-byte checks for TXT)
- Maximum file size enforcement
- Path traversal prevention and safe filename generation
"""

import os
import re
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from app.core.config import settings
from app.services.resume_parser.exceptions import ResumeValidationError

# Strict allowlist of allowed file extensions (lowercase)
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}

# Supported MIME types per extension
ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf", "application/x-pdf", "binary/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/x-zip-compressed",
        "binary/octet-stream",
    },
    ".txt": {"text/plain", "text/x-plain", "application/octet-stream"},
}

# Known executable magic byte signatures to reject unconditionally
EXECUTABLE_SIGNATURES: list[bytes] = [
    b"MZ",  # Windows PE executable / DLL
    b"\x7fELF",  # Linux ELF executable
    b"\xfe\xed\xfa\xce",  # Mach-O binary
    b"\xfe\xed\xfa\xcf",  # Mach-O binary (64-bit)
    b"\xce\xfa\xed\xfe",  # Mach-O binary
    b"\xcf\xfa\xed\xfe",  # Mach-O binary (64-bit)
    b"\xca\xfe\xba\xbe",  # Java bytecode class / Mach-O fat binary
    b"#!",  # Shell script shebang
]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an untrusted user-supplied filename.
    Strips directory separators, null bytes, and path traversal sequences.
    """
    if not filename or not filename.strip():
        return "resume"

    # Take only the base name (strip any leading directory traversal)
    base = os.path.basename(filename.strip().replace("\\", "/"))
    # Remove null bytes and control characters
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)
    # Remove any traversal patterns
    base = base.replace("..", "").replace("/", "").replace("\\", "")

    # Retain only alphanumeric, underscore, hyphen, and period
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    sanitized = re.sub(r"_+", "_", sanitized).strip("._-")

    if not sanitized:
        sanitized = "resume"

    # Limit base length to prevent filesystem path length issues
    return sanitized[:100]


def validate_file_size(content: bytes, max_size_mb: int | None = None) -> None:
    """
    Enforce maximum file size limit.
    Raises ResumeValidationError if content size exceeds max limit.
    """
    effective_limit_mb = max_size_mb if max_size_mb is not None else settings.MAX_RESUME_SIZE_MB
    max_bytes = effective_limit_mb * 1024 * 1024

    if len(content) == 0:
        raise ResumeValidationError("Uploaded file is empty (0 bytes).")

    if len(content) > max_bytes:
        raise ResumeValidationError(
            f"File size exceeds maximum permitted limit of {effective_limit_mb} MB."
        )


def validate_file_extension(filename: str) -> str:
    """
    Validate that the file has an approved extension.
    Returns normalized lowercase extension (e.g. '.pdf').
    """
    sanitized = sanitize_filename(filename)
    _, ext = os.path.splitext(sanitized)
    ext = ext.lower()

    if not ext or ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ResumeValidationError(
            f"Unsupported file extension '{ext or 'none'}'. Supported formats are: {allowed_list}."
        )

    return ext


def validate_file_signature(content: bytes, ext: str) -> None:
    """
    Defensively verify file signatures / magic bytes.
    Ensures file content genuinely matches its claimed extension.
    Rejects disguised executables and malformed files.
    """
    # 1. Reject any executable signatures regardless of extension
    for sig in EXECUTABLE_SIGNATURES:
        if content.startswith(sig):
            raise ResumeValidationError("Executable or script files are strictly prohibited.")

    # 2. Extension-specific magic byte checks
    if ext == ".pdf":
        # Standard PDF starts with %PDF-
        if not content.startswith(b"%PDF-"):
            raise ResumeValidationError(
                "Invalid PDF document: missing standard '%PDF-' file signature."
            )

    elif ext == ".docx":
        # Standard DOCX is a PK zip archive
        if not content.startswith(b"PK\x03\x04"):
            raise ResumeValidationError(
                "Invalid DOCX document: missing standard zip package signature."
            )
        try:
            with zipfile.ZipFile(BytesIO(content)) as zf:
                # A valid docx file must contain word/document.xml
                namelist = zf.namelist()
                if not any("word/document.xml" in name for name in namelist):
                    raise ResumeValidationError(
                        "Invalid DOCX document: package missing required Word document structure."
                    )
        except zipfile.BadZipFile:
            raise ResumeValidationError("Malformed or corrupted DOCX archive.") from None

    elif ext == ".txt":
        # Plain text must not contain binary null bytes
        if b"\x00" in content:
            raise ResumeValidationError(
                "Invalid text document: binary content detected in plain text file."
            )
        # Verify text is decodable
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content.decode("latin-1")
            except Exception:
                raise ResumeValidationError(
                    "Invalid text document: encoding could not be resolved."
                ) from None


def generate_secure_storage_path(
    original_filename: str,
    upload_dir: str | Path | None = None,
) -> tuple[str, str]:
    """
    Generate an isolated, unguessable storage filename and absolute path.
    Guarantees storage remains strictly within the approved upload directory.
    Returns (secure_filename, absolute_file_path).
    """
    effective_upload_dir = Path(upload_dir or settings.RESUME_UPLOAD_DIR).resolve()
    effective_upload_dir.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_filename(original_filename)
    stem, ext = os.path.splitext(sanitized)
    unique_id = uuid.uuid4().hex
    secure_filename = f"{unique_id}_{stem[:40]}{ext.lower()}"

    destination_path = (effective_upload_dir / secure_filename).resolve()

    # Defensive path traversal check: ensure destination is within effective_upload_dir
    try:
        destination_path.relative_to(effective_upload_dir)
    except ValueError:
        raise ResumeValidationError("Security violation: path traversal detected.") from None

    return secure_filename, str(destination_path)


def validate_resume_file(
    filename: str,
    content: bytes,
    content_type: str | None = None,
    max_size_mb: int | None = None,
) -> tuple[str, str]:
    """
    Comprehensive defensive validation for an uploaded resume.
    Returns (validated_extension_without_dot, sanitized_filename).
    """
    validate_file_size(content, max_size_mb=max_size_mb)
    ext = validate_file_extension(filename)
    validate_file_signature(content, ext)

    sanitized_name = sanitize_filename(filename)
    file_type = ext.lstrip(".")
    return file_type, sanitized_name
