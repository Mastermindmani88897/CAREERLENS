"""
Unit tests for Phase 11 format extractors, normalizer, section detector, and information extractors.
"""

import pytest

from app.schemas.resume import DetectedSections
from app.services.resume_parser.exceptions import (
    MalformedFileError,
    NoExtractableTextError,
)
from app.services.resume_parser.extractors.docx import DOCXExtractor
from app.services.resume_parser.extractors.pdf import PDFExtractor
from app.services.resume_parser.extractors.txt import TXTExtractor
from app.services.resume_parser.extractors_info.certifications import extract_certifications
from app.services.resume_parser.extractors_info.contact import extract_contact_info
from app.services.resume_parser.extractors_info.education import extract_education
from app.services.resume_parser.extractors_info.experience import extract_experience
from app.services.resume_parser.extractors_info.projects import extract_projects
from app.services.resume_parser.extractors_info.skills import extract_skills
from app.services.resume_parser.normalizer import normalize_resume_text
from app.services.resume_parser.parser import ResumeParser
from app.services.resume_parser.section_detector import detect_sections
from tests.helpers.synthetic_resumes import (
    create_malformed_docx,
    create_malformed_pdf,
    create_no_text_pdf,
    create_resume_missing_sections,
    create_resume_multi_skills,
    create_synthetic_docx_resume,
    create_synthetic_pdf_resume,
    create_synthetic_txt_resume,
)


def test_txt_extractor_success() -> None:
    """TXTExtractor extracts clean string from utf-8 bytes."""
    extractor = TXTExtractor()
    content = create_synthetic_txt_resume()
    text = extractor.extract_text(content)
    assert "Alex Morgan" in text
    assert "Python" in text
    assert "FastAPI" in text


def test_pdf_extractor_success() -> None:
    """PDFExtractor extracts text from normal PDF."""
    extractor = PDFExtractor()
    content = create_synthetic_pdf_resume()
    text = extractor.extract_text(content)
    assert "Taylor Swiftness" in text
    assert "Python" in text


def test_pdf_extractor_no_text_raises_error() -> None:
    """PDF containing no text raises NoExtractableTextError with OCR clarification."""
    extractor = PDFExtractor()
    no_text_content = create_no_text_pdf()
    with pytest.raises(
        NoExtractableTextError, match="Scanned-PDF OCR is not supported in Phase 11"
    ):
        extractor.extract_text(no_text_content)


def test_pdf_extractor_malformed() -> None:
    """Malformed PDF raises MalformedFileError."""
    extractor = PDFExtractor()
    with pytest.raises(MalformedFileError):
        extractor.extract_text(create_malformed_pdf())


def test_docx_extractor_success() -> None:
    """DOCXExtractor extracts text from paragraphs."""
    extractor = DOCXExtractor()
    content = create_synthetic_docx_resume()
    text = extractor.extract_text(content)
    assert "Jordan Lee" in text
    assert "TypeScript" in text


def test_docx_extractor_malformed() -> None:
    """Malformed DOCX archive raises MalformedFileError."""
    extractor = DOCXExtractor()
    with pytest.raises(MalformedFileError):
        extractor.extract_text(create_malformed_docx())


def test_normalize_resume_text() -> None:
    """Normalizer standardizes line breaks, collapses multiple spaces and blank lines."""
    raw = "Line 1  with   spaces\r\n\r\n\r\n\r\nLine 2\twith tabs"
    normalized = normalize_resume_text(raw)
    assert "Line 1 with spaces" in normalized
    assert "Line 2 with tabs" in normalized
    assert "\r" not in normalized
    assert "\n\n\n" not in normalized


def test_section_detector_identifies_sections() -> None:
    """Section detector identifies skills, education, experience, and projects."""
    text = """John Doe
john@example.com

PROFESSIONAL SUMMARY
Experienced engineer.

TECHNICAL SKILLS
Python, SQL, Docker

EDUCATION
B.Tech CSE from Aditya Engineering College

WORK EXPERIENCE
Software Engineer at Acme Corp

PROJECTS
CareerLens Platform
"""
    sections = detect_sections(text)
    assert sections.skills is not None and "Python" in sections.skills
    assert sections.education is not None and "Aditya Engineering College" in sections.education
    assert sections.experience is not None and "Acme Corp" in sections.experience
    assert sections.projects is not None and "CareerLens" in sections.projects


def test_contact_extractor() -> None:
    """Contact extractor extracts email, phone, links, and name."""
    text = """Alex Morgan
alex.morgan@example.com | +1-555-0144
https://linkedin.com/in/alexmorgan | https://github.com/alexmorgan | https://alexmorgan.dev
"""
    contact = extract_contact_info(text, text)
    assert contact.full_name == "Alex Morgan"
    assert contact.email == "alex.morgan@example.com"
    assert contact.phone is not None and "555-0144" in contact.phone
    assert contact.linkedin_url == "https://linkedin.com/in/alexmorgan"
    assert contact.github_url == "https://github.com/alexmorgan"
    assert contact.portfolio_url == "https://alexmorgan.dev"


def test_skills_extractor() -> None:
    """Skills extractor matches normalized taxonomy and preserves category and evidence."""
    sections = DetectedSections(
        skills="Python, FastAPI, PostgreSQL, Docker, Git",
        experience="Built microservices using Kubernetes and Redis.",
    )
    skills = extract_skills(sections, "")
    skill_names = [s.skill for s in skills]
    assert "Python" in skill_names
    assert "FastAPI" in skill_names
    assert "PostgreSQL" in skill_names
    assert "Docker" in skill_names
    assert "Kubernetes" in skill_names
    assert "Redis" in skill_names

    # Check evidence preservation
    python_skill = next(s for s in skills if s.skill == "Python")
    assert python_skill.source_section == "skills"
    assert python_skill.evidence is not None and "Python" in python_skill.evidence


def test_skills_extractor_multi_skills() -> None:
    """Extract dense skills accurately from synthetic multi-skill fixture."""
    txt_content = create_resume_multi_skills().decode("utf-8")
    sections = detect_sections(txt_content)
    skills = extract_skills(sections, txt_content)
    names = {s.skill for s in skills}
    assert "Python" in names
    assert "JavaScript" in names
    assert "React" in names
    assert "Machine Learning" in names


def test_resume_parser_handles_missing_sections() -> None:
    """Parser gracefully handles resumes with missing sections."""
    txt_content = create_resume_missing_sections().decode("utf-8")
    normalized, parsed = ResumeParser.parse(txt_content)
    assert parsed.contact.full_name == "Morgan Riley"
    assert len(parsed.skills) > 0
    assert len(parsed.projects) > 0
    assert len(parsed.education) == 0
    assert len(parsed.experience) == 0
    assert len(parsed.certifications) == 0


def test_education_extractor() -> None:
    """Education extractor extracts degree, institution, and CGPA accurately."""
    edu_text = (
        "B.Tech Computer Science and Engineering\n"
        "Aditya Engineering College\n"
        "CGPA: 8.6/10\n"
        "2020 - 2024"
    )
    sections = DetectedSections(education=edu_text)
    edu_list = extract_education(sections, "")
    assert len(edu_list) >= 1
    edu = edu_list[0]
    assert edu.degree == "B.Tech"
    assert edu.field_of_study == "Computer Science and Engineering"
    assert "Aditya Engineering College" in str(edu.institution)
    assert edu.grade == "CGPA: 8.6/10"
    assert edu.start_year == 2020
    assert edu.end_year == 2024


def test_experience_extractor() -> None:
    """Experience extractor extracts role, company, and date spans."""
    sections = DetectedSections(
        experience="Acme Corp | Software Engineer\nJan 2024 - Present\nDeveloped backend APIs."
    )
    exp_list = extract_experience(sections, "")
    assert len(exp_list) >= 1
    exp = exp_list[0]
    assert exp.role == "Software Engineer"
    assert exp.company == "Acme Corp"
    assert exp.start_date == "Jan 2024"
    assert exp.end_date == "Present"


def test_projects_extractor() -> None:
    """Project extractor extracts title, technologies, and URLs."""
    proj_text = (
        "CareerLens Platform\n"
        "https://github.com/alexmorgan/careerlens\n"
        "Built web app with FastAPI and PostgreSQL."
    )
    sections = DetectedSections(projects=proj_text)
    proj_list = extract_projects(sections, "")
    assert len(proj_list) >= 1
    proj = proj_list[0]
    assert "CareerLens" in proj.name
    assert proj.url == "https://github.com/alexmorgan/careerlens"
    assert "FastAPI" in proj.technologies
    assert "PostgreSQL" in proj.technologies


def test_certifications_extractor() -> None:
    """Certification extractor extracts name, issuer, and date."""
    sections = DetectedSections(
        certifications="AWS Certified Solutions Architect - Amazon Web Services - 2023"
    )
    cert_list = extract_certifications(sections, "")
    assert len(cert_list) >= 1
    cert = cert_list[0]
    assert "AWS Certified Solutions Architect" in cert.name
    assert cert.issuing_organization == "Amazon Web Services"
    assert cert.issue_date == "2023"


def test_resume_parser_full_pipeline() -> None:
    """Complete ResumeParser execution produces valid ParsedResumeData."""
    txt_content = create_synthetic_txt_resume().decode("utf-8")
    normalized, parsed = ResumeParser.parse(txt_content)
    assert parsed.contact.full_name == "Alex Morgan"
    assert len(parsed.skills) > 0
    assert len(parsed.education) > 0
    assert len(parsed.experience) > 0
    assert len(parsed.projects) > 0
    assert len(parsed.certifications) > 0
    assert parsed.error_message is None
