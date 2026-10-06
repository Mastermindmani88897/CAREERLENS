"""
Synthetic resume fixtures for deterministic, non-PVI testing.
Generates synthetic resumes across PDF, DOCX, and TXT formats for Phase 11.
Zero real personal data is contained in any fixture.
"""

from io import BytesIO

from docx import Document


def make_minimal_pdf(text_lines: list[str]) -> bytes:
    """Construct a compliant PDF binary payload with embedded text stream."""
    stream_content = "BT\n/F1 12 Tf\n15 TL\n50 750 Td\n"
    for line in text_lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({safe_line}) Tj T*\n"
    stream_content += "ET\n"
    stream_bytes = stream_content.encode("latin-1")

    body = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"5 0 obj\n<< /Length "
        + str(len(stream_bytes)).encode("ascii")
        + b" >>\nstream\n"
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    xref_pos = len(body)
    pdf = body + (
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000317 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode("ascii")
        + b"\n%%EOF\n"
    )
    return pdf


def create_synthetic_txt_resume() -> bytes:
    """Standard synthetic resume in plain text format."""
    text = """Alex Morgan
alex.morgan@example.com | +1-555-0144
https://linkedin.com/in/alexmorgan | https://github.com/alexmorgan | https://alexmorgan.dev

PROFESSIONAL SUMMARY
Full-stack software engineer with 3+ years experience building cloud services and web applications.

TECHNICAL SKILLS
Python, FastAPI, React, PostgreSQL, Docker, Kubernetes, Git, TypeScript, Linux, Redis

EDUCATION
B.Tech Computer Science and Engineering
Aditya Engineering College
CGPA: 8.6/10
2020 - 2024

WORK EXPERIENCE
Nexus Tech | Software Engineer
Jan 2024 - Present
- Engineered high-throughput REST APIs using Python and FastAPI.
- Deployed microservices using Docker and Kubernetes.

PROJECTS
CareerLens Platform
https://github.com/alexmorgan/careerlens
- Built career recommendation backend with FastAPI and PostgreSQL.

CERTIFICATIONS
AWS Certified Solutions Architect
Amazon Web Services - 2023
https://aws.amazon.com/verify/sample123
"""
    return text.encode("utf-8")


def create_synthetic_pdf_resume() -> bytes:
    """Standard synthetic resume in PDF format."""
    lines = [
        "Taylor Swiftness",
        "taylor.swiftness@example.com | +1-555-0188",
        "https://linkedin.com/in/taylorswiftness | https://github.com/taylorswiftness",
        "",
        "PROFESSIONAL SUMMARY",
        "Backend developer specializing in distributed systems and high-concurrency APIs.",
        "",
        "TECHNICAL SKILLS",
        "Python, FastAPI, SQL, PostgreSQL, Docker, Git, Redis, Linux",
        "",
        "EDUCATION",
        "B.Tech Computer Science and Engineering",
        "Aditya Engineering College",
        "CGPA: 9.1/10",
        "2019 - 2023",
        "",
        "WORK EXPERIENCE",
        "Innovate Labs | Backend Developer",
        "Feb 2023 - Present",
        "Implemented high-performance asynchronous data pipelines using Python and PostgreSQL.",
        "",
        "PROJECTS",
        "Distributed Task Queue",
        "https://github.com/taylorswiftness/taskqueue",
        "Built resilient job scheduler using Python and Redis.",
        "",
        "CERTIFICATIONS",
        "Google Cloud Associate Cloud Engineer",
        "Google - 2023",
    ]
    return make_minimal_pdf(lines)


def create_synthetic_docx_resume() -> bytes:
    """Standard synthetic resume in DOCX format."""
    doc = Document()
    doc.add_paragraph("Jordan Lee")
    doc.add_paragraph("jordan.lee@example.com | +1-555-0177")
    doc.add_paragraph("https://linkedin.com/in/jordanlee | https://github.com/jordanlee")

    doc.add_paragraph("PROFESSIONAL SUMMARY")
    doc.add_paragraph("Dedicated software engineer with extensive experience in React and Node.js.")

    doc.add_paragraph("TECHNICAL SKILLS")
    doc.add_paragraph("Python, React, TypeScript, Node.js, PostgreSQL, Docker, Git, HTML, CSS")

    doc.add_paragraph("EDUCATION")
    doc.add_paragraph("B.Tech Computer Science")
    doc.add_paragraph("Aditya Engineering College")
    doc.add_paragraph("CGPA: 8.4/10")
    doc.add_paragraph("2020 - 2024")

    doc.add_paragraph("WORK EXPERIENCE")
    doc.add_paragraph("Alpha Soft | Full-Stack Engineer")
    doc.add_paragraph("Jun 2023 - Present")
    doc.add_paragraph("Developed interactive dashboards using React and TypeScript.")

    doc.add_paragraph("PROJECTS")
    doc.add_paragraph("Real-Time Analytics Dashboard")
    doc.add_paragraph("https://github.com/jordanlee/analytics")
    doc.add_paragraph("Built analytics visualization suite with React and PostgreSQL.")

    doc.add_paragraph("CERTIFICATIONS")
    doc.add_paragraph("Meta Front-End Developer Professional Certificate")
    doc.add_paragraph("Meta - 2023")

    stream = BytesIO()
    doc.save(stream)
    return stream.getvalue()


def create_resume_missing_sections() -> bytes:
    """Synthetic resume missing education and experience sections."""
    text = """Morgan Riley
morgan.riley@example.com | +1-555-0122
https://github.com/morganriley

TECHNICAL SKILLS
Python, SQL, Git, Linux, Docker

PROJECTS
Personal Portfolio Site
https://github.com/morganriley/portfolio
Created lightweight static site using HTML and CSS.
"""
    return text.encode("utf-8")


def create_resume_multi_skills() -> bytes:
    """Synthetic resume with dense multi-domain skills."""
    text = """Casey West
casey.west@example.com | +1-555-0133

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, Java, C++, Go, Rust, SQL, HTML, CSS
Frameworks: FastAPI, Django, Flask, React, Next.js, Node.js, Express, PyTorch, TensorFlow
Databases & Tools: PostgreSQL, MySQL, Redis, MongoDB, Docker, Kubernetes, Git, AWS, Linux, CI/CD
Domain: Machine Learning, Deep Learning, REST API, Agile, Problem Solving
"""
    return text.encode("utf-8")


def create_malformed_pdf() -> bytes:
    """Corrupted bytes pretending to be a PDF."""
    return b"%PDF-1.4\ncorrupted_data_not_valid_pdf_structure"


def create_malformed_docx() -> bytes:
    """Corrupted bytes with PK zip signature but corrupt zip archive."""
    return b"PK\x03\x04\x14\x00\x00\x00broken_corrupted_zip_archive_data"


def create_empty_document() -> bytes:
    """Zero-byte document."""
    return b""


def create_no_text_pdf() -> bytes:
    """Valid PDF with empty stream (simulating a blank or scanned page without OCR)."""
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 0 >>\nstream\nendstream\nendobj\n"
    )
    xref_pos = len(body)
    pdf = body + (
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000200 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode("ascii")
        + b"\n%%EOF\n"
    )
    return pdf


def create_oversized_resume(size_mb: int = 11) -> bytes:
    """Oversized file exceeding default 10MB limit."""
    prefix = b"%PDF-1.4\n"
    padding = b"A" * (size_mb * 1024 * 1024)
    return prefix + padding


def create_unsupported_file() -> bytes:
    """Disguised executable binary (Windows PE MZ header)."""
    return b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00fake_executable"
