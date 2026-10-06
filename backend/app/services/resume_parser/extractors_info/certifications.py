"""
Deterministic certification extractor for Phase 11.
Extracts: name, issuing_organization, issue_date, credential_url, evidence.
"""

import re

from app.schemas.resume import DetectedSections, ExtractedCertification

ISSUER_KEYWORDS = [
    (r"\b(?:AWS|Amazon Web Services)\b", "Amazon Web Services"),
    (r"\b(?:Microsoft|Azure)\b", "Microsoft"),
    (r"\b(?:Google Cloud|GCP|Google)\b", "Google"),
    (r"\b(?:Coursera)\b", "Coursera"),
    (r"\b(?:Udemy)\b", "Udemy"),
    (r"\b(?:HackerRank)\b", "HackerRank"),
    (r"\b(?:Cisco)\b", "Cisco"),
    (r"\b(?:Oracle)\b", "Oracle"),
    (r"\b(?:IBM)\b", "IBM"),
    (r"\b(?:Meta)\b", "Meta"),
]

YEAR_REGEX = re.compile(r"\b(20\d{2}|19\d{2})\b")
URL_REGEX = re.compile(r"https?://(?:[a-zA-Z0-9.-]+)(?:/[^\s]*)?", re.IGNORECASE)


def extract_certifications(
    sections: DetectedSections,
    full_text: str,
) -> list[ExtractedCertification]:
    """
    Extract certification entries from certifications section.
    """
    target_text = sections.certifications
    if not target_text:
        return []

    lines = [line_str.strip() for line_str in target_text.split("\n") if line_str.strip()]
    certs: list[ExtractedCertification] = []

    for line in lines:
        cleaned_line = line.strip("-*• ")
        if not cleaned_line or len(cleaned_line) < 3:
            continue

        # Check issuer
        issuer: str | None = None
        for pattern_str, canonical_issuer in ISSUER_KEYWORDS:
            if re.search(pattern_str, cleaned_line, re.IGNORECASE):
                issuer = canonical_issuer
                break

        # Check date/year
        year_m = YEAR_REGEX.search(cleaned_line)
        issue_date = year_m.group(0) if year_m else None

        # Check URL
        url_m = URL_REGEX.search(cleaned_line)
        cred_url = url_m.group(0).rstrip(".,;)") if url_m else None

        # Name is the line or title portion
        name = cleaned_line.split(" - ")[0].split(" | ")[0].strip()
        if "(" in name and ")" in name and not issuer:
            name_parts = name.split("(")
            name = name_parts[0].strip()

        certs.append(
            ExtractedCertification(
                name=name,
                issuing_organization=issuer,
                issue_date=issue_date,
                credential_url=cred_url,
                evidence=cleaned_line[:140].strip(),
            )
        )

    return certs
