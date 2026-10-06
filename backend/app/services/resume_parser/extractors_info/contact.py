"""
Deterministic contact information extractor for Phase 11.
Extracts: full_name, email, phone, linkedin_url, github_url, portfolio_url.
Defensively avoids fabricating values. If uncertain, leaves fields None.
"""

import re

from app.schemas.resume import ContactInfo

# Regex patterns for deterministic contact information extraction
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Phone formats: international (+91, +1), dashes, spaces, parentheses
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}")

LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)

GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)

GENERIC_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)",
    re.IGNORECASE,
)

# Header words that must not be mistaken for personal names
NAME_STOPWORDS = {
    "resume",
    "curriculum",
    "vitae",
    "cv",
    "page",
    "contact",
    "profile",
    "summary",
    "education",
    "skills",
    "experience",
    "projects",
    "phone",
    "email",
    "address",
    "github",
    "linkedin",
    "portfolio",
    "engineer",
    "developer",
}


def _extract_name_candidate(contact_text: str, full_text: str) -> str | None:
    """
    Extract a candidate full name from the top lines of the resume.
    Looks for a line with 2 to 4 words where each word starts with a capital letter.
    """
    source_lines = (contact_text or "").split("\n") + full_text.split("\n")[:10]
    for line in source_lines:
        line = line.strip().strip("#*-_ ")
        if not line:
            continue
        # Skip if contains email, phone digits, or URL symbols
        if "@" in line or "http" in line or "www." in line or ".com" in line:
            continue
        if re.search(r"\d{3,}", line):
            continue

        words = line.split()
        if not (2 <= len(words) <= 4):
            continue

        # Check if words look like a name
        is_name_candidate = True
        for w in words:
            # Strip trailing punctuation
            clean_w = w.strip(".,()")
            if not clean_w.isalpha():
                is_name_candidate = False
                break
            if clean_w.lower() in NAME_STOPWORDS:
                is_name_candidate = False
                break
            if not clean_w[0].isupper():
                is_name_candidate = False
                break

        if is_name_candidate:
            return " ".join(w.strip(".,()") for w in words)

    return None


def extract_contact_info(contact_section_text: str | None, full_text: str) -> ContactInfo:
    """
    Extract contact details from the contact section or the full document text.
    """
    search_text = (contact_section_text or "") + "\n" + full_text

    # 1. Email extraction
    email_match = EMAIL_PATTERN.search(search_text)
    email = email_match.group(0).strip().lower() if email_match else None

    # 2. Phone extraction
    phone: str | None = None
    for p_match in PHONE_PATTERN.finditer(search_text):
        candidate_phone = p_match.group(0).strip()
        # Ensure candidate has at least 10 digits
        digits = re.sub(r"\D", "", candidate_phone)
        if 7 <= len(digits) <= 15:
            phone = candidate_phone
            break

    # 3. LinkedIn extraction
    linkedin_match = LINKEDIN_PATTERN.search(search_text)
    linkedin_url = f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else None

    # 4. GitHub extraction
    github_match = GITHUB_PATTERN.search(search_text)
    github_url = f"https://github.com/{github_match.group(1)}" if github_match else None

    # 5. Portfolio URL extraction (any other valid URL not linkedin or github)
    portfolio_url: str | None = None
    for url_match in GENERIC_URL_PATTERN.finditer(search_text):
        raw_url = url_match.group(0).strip().rstrip(".,;)")
        if "linkedin.com" not in raw_url.lower() and "github.com" not in raw_url.lower():
            portfolio_url = raw_url
            break

    # 6. Full Name extraction
    full_name = _extract_name_candidate(contact_section_text or "", full_text)

    return ContactInfo(
        full_name=full_name,
        email=email,
        phone=phone,
        linkedin_url=linkedin_url,
        github_url=github_url,
        portfolio_url=portfolio_url,
    )
