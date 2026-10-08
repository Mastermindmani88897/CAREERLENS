"""
Deterministic skill normalization for Phase 14 Opportunity Ingestion.
Leverages the canonical skill catalog from Phase 11 without any ML or embedding models.
Ensures skills are normalized, deduplicated per opportunity, and distinguished by is_required.
"""

import re
from collections.abc import Sequence

from app.services.resume_parser.extractors_info.skills import SKILL_CATALOG


def _split_raw_skills(skills_input: Sequence[str] | str | None) -> list[str]:
    """Split string or list of skill inputs by commas, semicolons, or pipes."""
    if not skills_input:
        return []

    raw_items: list[str] = []
    if isinstance(skills_input, str):
        # Split on comma, semicolon, pipe, or newline
        tokens = re.split(r"[,;|\n]+", skills_input)
        raw_items.extend(t.strip() for t in tokens if t.strip())
    else:
        for item in skills_input:
            if not item:
                continue
            if isinstance(item, str):
                tokens = re.split(r"[,;|\n]+", item)
                raw_items.extend(t.strip() for t in tokens if t.strip())
            else:
                raw_items.append(str(item).strip())

    return raw_items


def normalize_skill_name(raw_name: str) -> str:
    """
    Deterministically normalize skill name against the canonical skill catalog.
    If match found in catalog (e.g. 'postgres' -> 'PostgreSQL', 'k8s' -> 'Kubernetes'),
    returns the canonical name. Otherwise returns clean sanitized text.
    """
    cleaned = re.sub(r"\s+", " ", raw_name).strip()
    if not cleaned:
        return ""

    key = cleaned.lower()
    if key in SKILL_CATALOG:
        return SKILL_CATALOG[key]["canonical"]

    # Special common terms or retain cleaned form
    term_replacements = {
        "c++": "C++",
        "c#": "C#",
        ".net": ".NET",
        "node.js": "Node.js",
        "nodejs": "Node.js",
        "vue.js": "Vue.js",
        "vuejs": "Vue.js",
        "react.js": "React",
        "reactjs": "React",
        "next.js": "Next.js",
        "nextjs": "Next.js",
    }
    if key in term_replacements:
        return term_replacements[key]

    return cleaned


def normalize_opportunity_skills(
    required_skills_input: Sequence[str] | str | None,
    preferred_skills_input: Sequence[str] | str | None,
) -> tuple[list[str], list[str], list[tuple[str, bool]]]:
    """
    Normalize required and preferred skills, ensuring deterministic deduplication.
    Required skills take precedence if a skill appears in both.

    Returns:
    (normalized_required_list, normalized_preferred_list, combined_skill_tuples_with_is_required)
    """
    raw_required = _split_raw_skills(required_skills_input)
    raw_preferred = _split_raw_skills(preferred_skills_input)

    seen_lower: set[str] = set()
    norm_required: list[str] = []
    norm_preferred: list[str] = []
    skill_tuples: list[tuple[str, bool]] = []

    # 1. Process required skills first
    for raw in raw_required:
        norm = normalize_skill_name(raw)
        if not norm:
            continue
        lower_key = norm.lower()
        if lower_key not in seen_lower:
            seen_lower.add(lower_key)
            norm_required.append(norm)
            skill_tuples.append((norm, True))

    # 2. Process preferred skills (skip if already in required)
    for raw in raw_preferred:
        norm = normalize_skill_name(raw)
        if not norm:
            continue
        lower_key = norm.lower()
        if lower_key not in seen_lower:
            seen_lower.add(lower_key)
            norm_preferred.append(norm)
            skill_tuples.append((norm, False))

    return norm_required, norm_preferred, skill_tuples
