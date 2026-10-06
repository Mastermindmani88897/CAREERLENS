"""
Deterministic resume section detector for Phase 11.
Identifies and segments standard resume sections based on structural headings and patterns.
"""

import re
from typing import NamedTuple

from app.schemas.resume import DetectedSections


class SectionHeaderMatch(NamedTuple):
    section_name: str
    line_index: int
    header_text: str


# Mapping of normalized section name to regex patterns recognizing section headers
SECTION_HEADER_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "summary": [
        re.compile(
            r"^(?:professional\s+summary|executive\s+summary|career\s+summary|summary|career\s+objective|objective|profile|about\s+me)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "skills": [
        re.compile(
            r"^(?:technical\s+skills|core\s+competencies|key\s+skills|skills\s*(?:&|and)\s*technologies|technical\s+proficiencies|technologies|tools\s*(?:&|and)\s*technologies|skills)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "education": [
        re.compile(
            r"^(?:academic\s+background|academic\s+qualifications|educational\s+background|education\s*(?:&|and)\s*qualifications|academic\s+history|education)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "experience": [
        re.compile(
            r"^(?:work\s+experience|professional\s+experience|employment\s+history|work\s+history|professional\s+background|experience|internships?|internship\s+experience)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "projects": [
        re.compile(
            r"^(?:academic\s+projects|personal\s+projects|key\s+projects|projects\s*(?:&|and)\s*coursework|software\s+projects|technical\s+projects|projects)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "certifications": [
        re.compile(
            r"^(?:certifications?\s*(?:&|and)\s*licenses?|licenses?\s*(?:&|and)\s*certifications?|courses?\s*(?:&|and)\s*certifications?|professional\s+certifications?|certifications?|certificates?)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "achievements": [
        re.compile(
            r"^(?:achievements?\s*(?:&|and)\s*awards?|awards?\s*(?:&|and)\s*achievements?|honors?\s*(?:&|and)\s*awards?|key\s+achievements?|achievements?|awards?|honors?)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "publications": [
        re.compile(
            r"^(?:publications?|research\s+papers?|conference\s+papers?)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
    "languages": [
        re.compile(
            r"^(?:languages?\s+known|languages?|language\s+proficiency)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ],
}


def _match_section_header(line: str) -> str | None:
    """
    Check if a trimmed line matches a known section header pattern.
    Only matches lines that look like headings (short, not a complete sentence).
    """
    cleaned = line.strip().strip("#*-_ ").rstrip(":")
    if not cleaned or len(cleaned) > 50:
        return None

    # Check against known section patterns
    for section_name, patterns in SECTION_HEADER_PATTERNS.items():
        for pat in patterns:
            if pat.match(cleaned):
                return section_name

    return None


def detect_sections(normalized_text: str) -> DetectedSections:
    """
    Deterministically segment normalized resume text into structured sections.

    Strategy:
    1. Scan lines for section heading patterns.
    2. Everything before the first heading is treated as the 'contact' / header block.
    3. Content between heading N and heading N+1 belongs to section N.
    4. Lines are assembled and trimmed.
    5. Returns a structured `DetectedSections` model.
    """
    lines = normalized_text.split("\n")
    matches: list[SectionHeaderMatch] = []

    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        section_name = _match_section_header(line_clean)
        if section_name:
            matches.append(SectionHeaderMatch(section_name, i, line_clean))

    sections_dict: dict[str, list[str]] = {}

    if not matches:
        # No section headings found: assign entire text to contact / general
        return DetectedSections(contact=normalized_text.strip(), other=normalized_text.strip())

    # Pre-header block is contact info
    first_match = matches[0]
    if first_match.line_index > 0:
        contact_lines = [lines[idx].strip() for idx in range(first_match.line_index)]
        contact_text = "\n".join(item for item in contact_lines if item).strip()
        if contact_text:
            sections_dict["contact"] = [contact_text]

    # Process each detected section
    for idx, match in enumerate(matches):
        start_line = match.line_index + 1
        end_line = matches[idx + 1].line_index if idx + 1 < len(matches) else len(lines)
        section_content_lines = [lines[j].strip() for j in range(start_line, end_line)]
        content = "\n".join(item for item in section_content_lines if item).strip()

        if match.section_name not in sections_dict:
            sections_dict[match.section_name] = []
        if content:
            sections_dict[match.section_name].append(content)

    # Flatten aggregated section lists
    result_kwargs: dict[str, str | None] = {}
    for key in (
        "contact",
        "summary",
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
        "achievements",
        "publications",
        "languages",
        "other",
    ):
        if key in sections_dict:
            result_kwargs[key] = "\n\n".join(sections_dict[key]).strip()
        else:
            result_kwargs[key] = None

    return DetectedSections(**result_kwargs)
