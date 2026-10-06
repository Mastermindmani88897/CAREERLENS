"""
Deterministic project extractor for Phase 11.
Extracts: name, description, technologies, url, evidence.
Preserves verifiable technologies and urls.
"""

import re

from app.schemas.resume import DetectedSections, ExtractedProject
from app.services.resume_parser.extractors_info.skills import SKILL_CATALOG

URL_REGEX = re.compile(
    r"https?://(?:[a-zA-Z0-9.-]+)(?:/[^\s]*)?",
    re.IGNORECASE,
)


def extract_projects(
    sections: DetectedSections,
    full_text: str,
) -> list[ExtractedProject]:
    """
    Extract project records from the projects section.
    """
    target_text = sections.projects
    if not target_text:
        return []

    blocks = [b.strip() for b in target_text.split("\n\n") if b.strip()]
    if len(blocks) <= 1:
        # Split by bullet lines starting with bold or dashed titles
        raw_lines = target_text.split("\n")
        new_blocks: list[str] = []
        cur_block: list[str] = []
        for line in raw_lines:
            line_str = line.strip()
            if not line_str:
                continue
            # If line looks like a title (starts with dash or bullet or uppercase words)
            if (
                (line_str.startswith(("-", "•", "*")) or ":" in line_str)
                and cur_block
                and len(cur_block) >= 2
            ):
                new_blocks.append("\n".join(cur_block))
                cur_block = [line_str]
            else:
                cur_block.append(line_str)
        if cur_block:
            new_blocks.append("\n".join(cur_block))
        blocks = new_blocks if len(new_blocks) > 1 else blocks

    projects: list[ExtractedProject] = []

    for block in blocks:
        lines = [line_txt.strip() for line_txt in block.split("\n") if line_txt.strip()]
        if not lines:
            continue

        first_line = lines[0].strip("-*• ")
        # Project title
        title = first_line.split("|")[0].split("–")[0].split("-")[0].strip()
        if ":" in title and len(title.split(":")[0]) < 40:
            title = title.split(":")[0].strip()

        # Extract URL if present
        url_match = URL_REGEX.search(block)
        url = url_match.group(0).rstrip(".,;)") if url_match else None

        # Extract technologies mentioned directly in the project block
        techs: list[str] = []
        block_lower = block.lower()
        for skill_key, meta in SKILL_CATALOG.items():
            if re.search(rf"\b{re.escape(skill_key)}\b", block_lower):
                canonical = meta["canonical"]
                if canonical not in techs:
                    techs.append(canonical)

        # Description lines
        desc_lines = lines[1:] if len(lines) > 1 else lines
        description = "\n".join(desc_lines).strip()

        if title and len(title) <= 100:
            projects.append(
                ExtractedProject(
                    name=title,
                    description=description if description else None,
                    technologies=techs,
                    url=url,
                    evidence=block[:160].strip(),
                )
            )

    return projects
