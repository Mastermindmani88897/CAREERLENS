"""
Text normalization service for resume extraction (Phase 11).
Normalizes raw extracted text deterministically while preserving original text integrity.
"""

import re
import unicodedata


def normalize_resume_text(raw_text: str) -> str:
    """
    Apply deterministic text normalization to raw extracted resume text.

    Steps:
    1. Unicode normalization (NFKC) to unify composed forms and compatibility symbols.
    2. Normalize line breaks (CRLF and CR to LF).
    3. Replace non-breaking spaces, zero-width spaces, and control characters.
    4. Normalize tabs and multiple consecutive horizontal spaces to a single space.
    5. Reduce 3+ consecutive newlines to at most 2 newlines (preserve paragraph separation).
    6. Strip trailing spaces from each line and strip document boundaries.

    Does NOT modify the input `raw_text`.
    """
    if not raw_text:
        return ""

    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", raw_text)

    # 2. Line ending normalization
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Clean common non-printable / encoding artifacts
    # Replace non-breaking spaces and zero-width spaces
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")

    # Remove non-standard control characters (keep \n and \t)
    text = "".join(ch for ch in text if ch in ("\n", "\t") or (ord(ch) >= 32 and ord(ch) != 127))

    # 4. Normalize horizontal whitespace per line
    lines = text.split("\n")
    cleaned_lines: list[str] = []
    for line in lines:
        # Replace tabs with spaces
        line = line.replace("\t", "    ")
        # Collapse multiple horizontal spaces to single space
        line = re.sub(r"[ ]{2,}", " ", line)
        cleaned_lines.append(line.strip())

    text = "\n".join(cleaned_lines)

    # 5. Collapse repeated empty lines (allow at most 1 empty line between blocks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
