"""
Resume parser pipeline coordinator for Phase 11.
Transforms normalized text and detected sections into a validated ParsedResumeData model.
"""

from datetime import datetime

from app.schemas.resume import ParsedResumeData, ResumeStatus
from app.services.resume_parser.extractors_info.certifications import extract_certifications
from app.services.resume_parser.extractors_info.contact import extract_contact_info
from app.services.resume_parser.extractors_info.education import extract_education
from app.services.resume_parser.extractors_info.experience import extract_experience
from app.services.resume_parser.extractors_info.projects import extract_projects
from app.services.resume_parser.extractors_info.skills import extract_skills
from app.services.resume_parser.normalizer import normalize_resume_text
from app.services.resume_parser.section_detector import detect_sections


class ResumeParser:
    """Deterministic resume parsing pipeline."""

    @classmethod
    def parse(cls, raw_text: str) -> tuple[str, ParsedResumeData]:
        """
        Execute deterministic parsing pipeline on raw extracted text.

        Returns:
            tuple[normalized_text, parsed_data_model]
        """
        # 1. Text normalization
        normalized_text = normalize_resume_text(raw_text)

        # 2. Section detection
        detected_sections = detect_sections(normalized_text)

        # Convert detected sections to serializable dictionary (omitting None)
        sections_dict = {k: v for k, v in detected_sections.model_dump().items() if v is not None}

        # 3. Entity extractions
        contact = extract_contact_info(detected_sections.contact, normalized_text)
        skills = extract_skills(detected_sections, normalized_text)
        education = extract_education(detected_sections, normalized_text)
        experience = extract_experience(detected_sections, normalized_text)
        projects = extract_projects(detected_sections, normalized_text)
        certifications = extract_certifications(detected_sections, normalized_text)

        parsed_data = ParsedResumeData(
            status=ResumeStatus.PARSED,
            contact=contact,
            skills=skills,
            education=education,
            experience=experience,
            projects=projects,
            certifications=certifications,
            sections=sections_dict,
            summary=detected_sections.summary,
            raw_character_count=len(raw_text),
            normalized_character_count=len(normalized_text),
            extracted_at=datetime.utcnow(),
            error_message=None,
        )

        return normalized_text, parsed_data
