"""
Deterministic work and internship experience extractor for Phase 11.
Extracts: company, role, start_date, end_date, description, skills_used.
Defensively avoids fabricating dates or company names.
"""

import re

from app.schemas.resume import DetectedSections, ExtractedExperience

# Common role/job title keywords
ROLE_KEYWORDS = [
    r"\b(?:Software Engineer|Software Developer|Frontend Developer|Backend Developer)\b",
    r"\b(?:Full[- ]?Stack Developer|Full[- ]?Stack Engineer|Web Developer)\b",
    r"\b(?:Data Scientist|Data Analyst|Data Engineer|ML Engineer|Machine Learning Engineer)\b",
    r"\b(?:DevOps Engineer|Cloud Engineer|System Administrator|QA Engineer)\b",
    r"\b(?:Software Engineering Intern|Software Developer Intern|Intern|Internship)\b",
    r"\b(?:Research Intern|Graduate Intern|Engineering Intern)\b",
]

DATE_SPAN_REGEX = re.compile(
    r"\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|\d{4})\s*(?:[-–—to]+\s*)((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|\d{4}|present|current)\b",
    re.IGNORECASE,
)


def _split_experience_blocks(text: str) -> list[str]:
    """Split text into distinct experience blocks."""
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if len(chunks) > 1:
        return chunks

    lines = [line_txt.strip() for line_txt in text.split("\n") if line_txt.strip()]
    if not lines:
        return []

    date_matches = list(DATE_SPAN_REGEX.finditer(text))
    if len(date_matches) <= 1:
        return ["\n".join(lines)]

    blocks: list[str] = []
    cur_block: list[str] = []
    for line in lines:
        has_role = any(re.search(pat, line, re.IGNORECASE) for pat in ROLE_KEYWORDS)
        if has_role and cur_block and len(cur_block) >= 2:
            blocks.append("\n".join(cur_block))
            cur_block = [line]
        else:
            cur_block.append(line)
    if cur_block:
        blocks.append("\n".join(cur_block))

    return blocks if blocks else ["\n".join(lines)]


def extract_experience(
    sections: DetectedSections,
    full_text: str,
) -> list[ExtractedExperience]:
    """
    Extract structured experience entries from experience and internship sections.
    """
    target_text = sections.experience
    if not target_text:
        return []

    blocks = _split_experience_blocks(target_text)
    experiences: list[ExtractedExperience] = []

    for block in blocks:
        lines = [line_txt.strip() for line_txt in block.split("\n") if line_txt.strip()]
        if not lines:
            continue

        # 1. Date extraction
        start_date: str | None = None
        end_date: str | None = None
        date_match = DATE_SPAN_REGEX.search(block)
        if date_match:
            start_date = date_match.group(1).strip()
            end_date = date_match.group(2).strip()

        # 2. Role extraction
        role: str | None = None
        for pattern_str in ROLE_KEYWORDS:
            m = re.search(pattern_str, block, re.IGNORECASE)
            if m:
                role = m.group(0).strip()
                break

        # 3. Company heuristic (first line or line before date)
        company: str | None = None
        for line in lines[:3]:
            # If line is not purely a date and not the role
            if date_match and line == date_match.group(0):
                continue
            if role and line.lower() == role.lower():
                continue
            # Check if line contains company separator (e.g. "Software Engineer at Google")
            if " at " in line:
                parts = line.split(" at ", 1)
                if not role:
                    role = parts[0].strip()
                company = parts[1].split("|")[0].split("-")[0].strip()
                break
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                company = parts[0]
                break
            if len(line.split()) <= 6 and not any(
                kw in line.lower() for kw in ("developed", "implemented", "worked")
            ):
                company = line.strip("-*• ")
                break

        # 4. Description lines
        desc_lines = [
            line_txt
            for line_txt in lines
            if line_txt != company
            and (not role or role.lower() not in line_txt.lower())
            and (not date_match or date_match.group(0) not in line_txt)
        ]
        description = "\n".join(desc_lines).strip() if desc_lines else None

        if company or role:
            experiences.append(
                ExtractedExperience(
                    company=company,
                    role=role,
                    start_date=start_date,
                    end_date=end_date,
                    description=description,
                    evidence=block[:160].strip(),
                )
            )

    return experiences
