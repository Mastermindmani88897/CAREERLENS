"""
Deterministic education extractor for Phase 11.
Extracts: institution, degree, field_of_study, grade (CGPA/percentage), start_year, end_year.
Validates CGPA ranges and avoids fabricating missing fields.
"""

import re

from app.schemas.resume import DetectedSections, ExtractedEducation

# Degree matching patterns
DEGREE_PATTERNS = [
    (r"\b(?:B\.?\s*Tech|Bachelor of Technology)\b", "B.Tech"),
    (r"\b(?:B\.?\s*E\.?|Bachelor of Engineering)\b", "B.E."),
    (r"\b(?:B\.?\s*S\.?|B\.?\s*Sc\.?|Bachelor of Science)\b", "B.Sc"),
    (r"\b(?:B\.?\s*C\.?\s*A\.?|Bachelor of Computer Applications)\b", "BCA"),
    (r"\b(?:M\.?\s*Tech|Master of Technology)\b", "M.Tech"),
    (r"\b(?:M\.?\s*E\.?|Master of Engineering)\b", "M.E."),
    (r"\b(?:M\.?\s*S\.?|M\.?\s*Sc\.?|Master of Science)\b", "M.S."),
    (r"\b(?:M\.?\s*C\.?\s*A\.?|Master of Computer Applications)\b", "MCA"),
    (r"\b(?:M\.?\s*B\.?\s*A\.?|Master of Business Administration)\b", "MBA"),
    (r"\b(?:Ph\.?\s*D\.?|Doctor of Philosophy)\b", "Ph.D"),
    (r"\b(?:Diploma)\b", "Diploma"),
    (r"\b(?:High School|Intermediate|Senior Secondary|12th Standard|CBSE XII)\b", "High School"),
]

# Field of study matching patterns
FIELD_OF_STUDY_PATTERNS = [
    (r"\b(?:Computer Science (?:and|&) Engineering|CSE)\b", "Computer Science and Engineering"),
    (r"\b(?:Computer Science|CS)\b", "Computer Science"),
    (r"\b(?:Information Technology|IT)\b", "Information Technology"),
    (
        r"\b(?:Artificial Intelligence (?:and|&) Machine Learning|AI & ML|AIML)\b",
        "Artificial Intelligence & Machine Learning",
    ),
    (r"\b(?:Data Science)\b", "Data Science"),
    (
        r"\b(?:Electronics (?:and|&) Communication Engineering|ECE)\b",
        "Electronics and Communication Engineering",
    ),
    (
        r"\b(?:Electrical (?:and|&) Electronics Engineering|EEE)\b",
        "Electrical and Electronics Engineering",
    ),
    (r"\b(?:Mechanical Engineering)\b", "Mechanical Engineering"),
    (r"\b(?:Civil Engineering)\b", "Civil Engineering"),
    (r"\b(?:Software Engineering)\b", "Software Engineering"),
]

# Institution keywords
INSTITUTION_KEYWORDS = [
    "university",
    "college",
    "institute",
    "academy",
    "school",
    "polytechnic",
    "iit",
    "nit",
    "iiit",
    "bits",
]

# Grade / CGPA / Percentage patterns
CGPA_REGEX = re.compile(
    r"\b(?:CGPA|GPA|Score|Grade)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)"
    r"(?:\s*(?:/|out of)\s*([0-9]+(?:\.[0-9]+)?))?",
    re.IGNORECASE,
)
PERCENTAGE_REGEX = re.compile(
    r"\b([0-9]{1,3}(?:\.[0-9]+)?)\s*%\s*(?:marks)?",
    re.IGNORECASE,
)
RATIO_CGPA_REGEX = re.compile(
    r"\b([0-9]\.[0-9]{1,2})\s*/\s*10(?:\.0)?\b",
    re.IGNORECASE,
)

# Year range pattern: 2023 - 2027 or 2020 – 2024
YEAR_RANGE_REGEX = re.compile(
    r"\b(19\d{2}|20\d{2})\s*(?:[-–—to]+\s*(19\d{2}|20\d{2}|present|expected))\b",
    re.IGNORECASE,
)
SINGLE_YEAR_REGEX = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _extract_grade(text: str) -> str | None:
    """Extract and validate CGPA or percentage score."""
    # Check explicit CGPA pattern
    cgpa_m = CGPA_REGEX.search(text)
    if cgpa_m:
        val_str = cgpa_m.group(1)
        scale_str = cgpa_m.group(2)
        try:
            val = float(val_str)
            # Ensure valid CGPA range
            if 0.0 <= val <= 10.0:
                scale = scale_str or "10"
                return f"CGPA: {val}/{scale}"
            if 10.0 < val <= 100.0:
                return f"{val}%"
        except ValueError:
            pass

    # Check ratio pattern e.g. 8.6/10
    ratio_m = RATIO_CGPA_REGEX.search(text)
    if ratio_m:
        try:
            val = float(ratio_m.group(1))
            if 0.0 <= val <= 10.0:
                return f"CGPA: {val}/10"
        except ValueError:
            pass

    # Check percentage pattern e.g. 85.5%
    pct_m = PERCENTAGE_REGEX.search(text)
    if pct_m:
        try:
            val = float(pct_m.group(1))
            if 30.0 <= val <= 100.0:
                return f"{val}%"
        except ValueError:
            pass

    return None


def _extract_year_range(text: str) -> tuple[int | None, int | None]:
    """Extract start and graduation year."""
    range_m = YEAR_RANGE_REGEX.search(text)
    if range_m:
        start_yr = int(range_m.group(1))
        end_str = range_m.group(2).lower()
        end_yr = int(end_str) if end_str.isdigit() else None
        return start_yr, end_yr

    # Single year fallback
    years = [int(y) for y in SINGLE_YEAR_REGEX.findall(text)]
    if len(years) == 1:
        return None, years[0]
    if len(years) >= 2:
        return sorted(years)[0], sorted(years)[-1]

    return None, None


def _split_education_blocks(text: str) -> list[str]:
    """Split text into distinct education blocks."""
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if len(chunks) > 1:
        return chunks

    lines = [line_txt.strip() for line_txt in text.split("\n") if line_txt.strip()]
    if not lines:
        return []

    # Check for multiple degree lines
    degree_line_indices: list[int] = []
    for idx, line in enumerate(lines):
        for pattern_str, _ in DEGREE_PATTERNS:
            if re.search(pattern_str, line, re.IGNORECASE):
                degree_line_indices.append(idx)
                break

    if len(degree_line_indices) > 1:
        blocks: list[str] = []
        for i, start_idx in enumerate(degree_line_indices):
            end_idx = degree_line_indices[i + 1] if i + 1 < len(degree_line_indices) else len(lines)
            block_lines = lines[start_idx:end_idx]
            blocks.append("\n".join(block_lines))
        return blocks

    return ["\n".join(lines)]


def extract_education(
    sections: DetectedSections,
    full_text: str,
) -> list[ExtractedEducation]:
    """
    Extract structured educational credentials.
    Focuses on the education section lines.
    """
    target_text = sections.education or full_text
    blocks = _split_education_blocks(target_text)

    records: list[ExtractedEducation] = []

    for block in blocks:
        # Check degree
        matched_degree: str | None = None
        for pattern_str, canonical_degree in DEGREE_PATTERNS:
            if re.search(pattern_str, block, re.IGNORECASE):
                matched_degree = canonical_degree
                break

        # Check field of study
        matched_field: str | None = None
        for pattern_str, canonical_field in FIELD_OF_STUDY_PATTERNS:
            if re.search(pattern_str, block, re.IGNORECASE):
                matched_field = canonical_field
                break

        # Check institution
        institution: str | None = None
        for line in block.split("\n"):
            line_lower = line.lower()
            if any(kw in line_lower for kw in INSTITUTION_KEYWORDS):
                # Clean line as institution
                cleaned_inst = line.strip().strip("-*• ")
                if len(cleaned_inst) < 100:
                    institution = cleaned_inst
                    break

        # Check grade & years
        grade = _extract_grade(block)
        start_year, end_year = _extract_year_range(block)

        # Only register record if we matched at least degree or institution
        if matched_degree or institution:
            records.append(
                ExtractedEducation(
                    institution=institution,
                    degree=matched_degree,
                    field_of_study=matched_field,
                    grade=grade,
                    start_year=start_year,
                    end_year=end_year,
                    evidence=block[:160].strip(),
                )
            )

    return records
