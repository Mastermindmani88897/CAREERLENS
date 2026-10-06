"""
Deterministic skill extraction engine for Phase 11.
Uses an extensible, normalized vocabulary and alias mapping with boundary-safe matching.
Preserves evidence context and source section without fabricating skills.
"""

import re

from app.schemas.resume import DetectedSections, ExtractedSkill

# Canonical skill catalog organized by category
SKILL_CATALOG: dict[str, dict[str, str]] = {
    # Programming Languages
    "python": {"canonical": "Python", "category": "technical"},
    "javascript": {"canonical": "JavaScript", "category": "technical"},
    "typescript": {"canonical": "TypeScript", "category": "technical"},
    "java": {"canonical": "Java", "category": "technical"},
    "c++": {"canonical": "C++", "category": "technical"},
    "c#": {"canonical": "C#", "category": "technical"},
    "c": {"canonical": "C", "category": "technical"},
    "go": {"canonical": "Go", "category": "technical"},
    "golang": {"canonical": "Go", "category": "technical"},
    "rust": {"canonical": "Rust", "category": "technical"},
    "ruby": {"canonical": "Ruby", "category": "technical"},
    "php": {"canonical": "PHP", "category": "technical"},
    "swift": {"canonical": "Swift", "category": "technical"},
    "kotlin": {"canonical": "Kotlin", "category": "technical"},
    "scala": {"canonical": "Scala", "category": "technical"},
    "r": {"canonical": "R", "category": "technical"},
    "matlab": {"canonical": "MATLAB", "category": "technical"},
    "sql": {"canonical": "SQL", "category": "technical"},
    "html": {"canonical": "HTML", "category": "technical"},
    "html5": {"canonical": "HTML5", "category": "technical"},
    "css": {"canonical": "CSS", "category": "technical"},
    "css3": {"canonical": "CSS3", "category": "technical"},
    # Frameworks & Libraries
    "fastapi": {"canonical": "FastAPI", "category": "technical"},
    "flask": {"canonical": "Flask", "category": "technical"},
    "django": {"canonical": "Django", "category": "technical"},
    "react": {"canonical": "React", "category": "technical"},
    "reactjs": {"canonical": "React", "category": "technical"},
    "react.js": {"canonical": "React", "category": "technical"},
    "vue": {"canonical": "Vue.js", "category": "technical"},
    "vue.js": {"canonical": "Vue.js", "category": "technical"},
    "angular": {"canonical": "Angular", "category": "technical"},
    "next.js": {"canonical": "Next.js", "category": "technical"},
    "nextjs": {"canonical": "Next.js", "category": "technical"},
    "node.js": {"canonical": "Node.js", "category": "technical"},
    "nodejs": {"canonical": "Node.js", "category": "technical"},
    "node": {"canonical": "Node.js", "category": "technical"},
    "express": {"canonical": "Express.js", "category": "technical"},
    "express.js": {"canonical": "Express.js", "category": "technical"},
    "spring": {"canonical": "Spring", "category": "technical"},
    "spring boot": {"canonical": "Spring Boot", "category": "technical"},
    "pytorch": {"canonical": "PyTorch", "category": "technical"},
    "tensorflow": {"canonical": "TensorFlow", "category": "technical"},
    "pandas": {"canonical": "Pandas", "category": "technical"},
    "numpy": {"canonical": "NumPy", "category": "technical"},
    "scikit-learn": {"canonical": "Scikit-Learn", "category": "technical"},
    "sklearn": {"canonical": "Scikit-Learn", "category": "technical"},
    # Databases & Storage
    "postgresql": {"canonical": "PostgreSQL", "category": "tool"},
    "postgres": {"canonical": "PostgreSQL", "category": "tool"},
    "mysql": {"canonical": "MySQL", "category": "tool"},
    "sqlite": {"canonical": "SQLite", "category": "tool"},
    "mongodb": {"canonical": "MongoDB", "category": "tool"},
    "redis": {"canonical": "Redis", "category": "tool"},
    "pgvector": {"canonical": "pgvector", "category": "tool"},
    "cassandra": {"canonical": "Cassandra", "category": "tool"},
    # DevOps, Cloud & Tools
    "docker": {"canonical": "Docker", "category": "tool"},
    "kubernetes": {"canonical": "Kubernetes", "category": "tool"},
    "k8s": {"canonical": "Kubernetes", "category": "tool"},
    "git": {"canonical": "Git", "category": "tool"},
    "github": {"canonical": "GitHub", "category": "tool"},
    "gitlab": {"canonical": "GitLab", "category": "tool"},
    "aws": {"canonical": "AWS", "category": "tool"},
    "azure": {"canonical": "Azure", "category": "tool"},
    "gcp": {"canonical": "GCP", "category": "tool"},
    "linux": {"canonical": "Linux", "category": "tool"},
    "nginx": {"canonical": "Nginx", "category": "tool"},
    "postman": {"canonical": "Postman", "category": "tool"},
    "ci/cd": {"canonical": "CI/CD", "category": "tool"},
    "jenkins": {"canonical": "Jenkins", "category": "tool"},
    # Soft & Domain Competencies
    "machine learning": {"canonical": "Machine Learning", "category": "domain"},
    "deep learning": {"canonical": "Deep Learning", "category": "domain"},
    "rest api": {"canonical": "REST API", "category": "technical"},
    "restful apis": {"canonical": "REST API", "category": "technical"},
    "graphql": {"canonical": "GraphQL", "category": "technical"},
    "microservices": {"canonical": "Microservices", "category": "domain"},
    "agile": {"canonical": "Agile", "category": "soft"},
    "scrum": {"canonical": "Scrum", "category": "soft"},
    "problem solving": {"canonical": "Problem Solving", "category": "soft"},
}


def _build_skill_pattern(term: str) -> re.Pattern[str]:
    """Compile a regex pattern with appropriate word boundaries."""
    # Special character handling (C++, C#, .js, /)
    escaped = re.escape(term)
    if re.match(r"^\w", term) and re.search(r"\w$", term):
        pattern_str = rf"(?<!\w){escaped}(?!\w)"
    elif re.match(r"^\w", term):
        pattern_str = rf"(?<!\w){escaped}"
    elif re.search(r"\w$", term):
        pattern_str = rf"{escaped}(?!\w)"
    else:
        pattern_str = escaped
    return re.compile(pattern_str, re.IGNORECASE)


# Precompile search patterns sorted by length descending (longest term first)
COMPILED_SKILL_PATTERNS: list[tuple[str, re.Pattern[str], str, str]] = []
for term, meta in sorted(SKILL_CATALOG.items(), key=lambda item: len(item[0]), reverse=True):
    pat = _build_skill_pattern(term)
    COMPILED_SKILL_PATTERNS.append((term, pat, meta["canonical"], meta["category"]))


def extract_skills(
    sections: DetectedSections,
    full_text: str,
) -> list[ExtractedSkill]:
    """
    Extract skills with section awareness and evidence preservation.

    Priority order:
    1. Skills section (highest confidence)
    2. Projects & Experience sections
    3. Other sections / full document
    """
    found_skills: dict[str, ExtractedSkill] = {}

    def scan_section(text: str | None, section_name: str) -> None:
        if not text:
            return
        lines = text.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            for _term, pat, canonical, category in COMPILED_SKILL_PATTERNS:
                if canonical in found_skills:
                    continue
                match = pat.search(line_str)
                if match:
                    # Capture concise evidence snippet (line or surrounding context)
                    evidence = line_str[:120].strip()
                    found_skills[canonical] = ExtractedSkill(
                        skill=canonical,
                        category=category,
                        source_section=section_name,
                        evidence=evidence,
                    )

    # 1. Scan dedicated skills section first
    scan_section(sections.skills, "skills")

    # 2. Scan projects and experience sections
    scan_section(sections.projects, "projects")
    scan_section(sections.experience, "experience")

    # 3. Scan summary and education sections
    scan_section(sections.summary, "summary")
    scan_section(sections.education, "education")

    # Return sorted alphabetically by skill name
    return sorted(found_skills.values(), key=lambda s: s.skill.lower())
