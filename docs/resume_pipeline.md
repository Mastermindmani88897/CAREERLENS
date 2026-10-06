# CareerLens — Phase 11 Resume Parsing & Extraction Pipeline

This document specifies the technical design, security controls, and operational architecture of the **Phase 11 Resume Ingestion and Deterministic Extraction Pipeline**.

---

## 1. Overview & Architectural Boundary

The Phase 11 pipeline ingests candidate resumes, validates file integrity and security boundaries, normalizes raw text, segments document sections, and deterministically extracts structured candidate attributes (contact information, skills, education, experience, projects, and certifications).

> [!IMPORTANT]
> **Deterministic Heuristic Boundary**
> Phase 11 uses deterministic extraction and structured heuristics.
> Semantic matching and recommendation intelligence are implemented
> in later phases.
> No external LLM or proprietary AI API keys are required for this phase. The pipeline runs completely deterministically and locally (`LLM_PROVIDER=none`).

---

## 2. Ingestion & Format Support

| Format | Extensions | Engine / Parser Library | Extraction Mechanism |
|---|---|---|---|
| **Portable Document Format** | `.pdf` | `pypdf>=5.0.0` | Digital text layer extraction across all document pages |
| **Microsoft Word Document** | `.docx` | `python-docx>=1.1.0` | Paragraph and table cell traversal |
| **Plain Text** | `.txt` | Native Python | UTF-8 decode with Latin-1 fallback |

### File Constraints
- **Maximum File Size**: 10 MB (`MAX_RESUME_SIZE_MB=10`)
- **Supported File Types**: PDF (`application/pdf`), DOCX (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`), TXT (`text/plain`)
- **Magic Byte Validation**:
  - PDF: Enforces `%PDF-` header signature
  - DOCX: Enforces zip package magic signature (`PK\x03\x04`)

---

## 3. Upload Security Controls

1. **Path Traversal Prevention**: Filenames are sanitized, stripped of directory separators (`/`, `\`), null bytes, and traversal patterns (`..`).
2. **UUID Storage Isolation**: Physical upload files are saved with prefixed UUID filenames (`<uuid>_<sanitized_filename>`) within the configured upload directory (`./data/uploads/resumes`).
3. **Executable Rejection**: Executable files (`.exe`, `.sh`, `.bat`, `.cmd`, `.dll`, `.msi`) and suspicious script MIME types are rejected immediately with HTTP 400.
4. **Encryption / Password Handling**: Password-protected or encrypted PDF documents are detected and rejected with a clear, safe client error (`PasswordProtectedFileError`), preventing denial-of-service hanging.
5. **Redacted Logging**: Log messages redact personally identifiable information (PII) including email addresses, phone numbers, and authentication tokens.
6. **Owner-Only Access**: Resumes are linked to the authenticated candidate profile (`candidate_profile_id`). Cross-user retrieval returns HTTP 404/403.

---

## 4. Extraction Architecture & Processing Flow

```
+-------------------------------------------------------------+
|                      Resume Ingestion                       |
|   POST /api/v1/resumes/upload (Multipart Form / Auth)       |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                      Security Validation                    |
|   - Extension & MIME verification                           |
|   - Magic byte header checks                                |
|   - Size limit enforcement (< 10 MB)                        |
|   - Path traversal prevention & safe filename generation    |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                      Raw Text Extraction                    |
|   - PDF: pypdf page extraction                              |
|   - DOCX: python-docx paragraph/table extraction            |
|   - TXT: UTF-8 / Latin-1 decoding fallback                  |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                     Text Normalization                      |
|   - Unicode normalization (NFKC)                            |
|   - Carriage return & newline harmonization                 |
|   - Multiple space / tab collapse                           |
|   - Safe character preservation                             |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                Deterministic Section Detection              |
|   Regex & keyword segmentation into standard sections:      |
|   [contact, summary, skills, education, experience,        |
|    projects, certifications, achievements, publications]    |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                Structured Entity Extraction                 |
|   - Contact: Email regex, phone formats, LinkedIn/GitHub    |
|   - Skills: Conservative taxonomy keyword matching          |
|   - Education: Institution/degree regex, graduation years   |
|   - Experience: Role titles, company markers, date ranges   |
|   - Projects: Project headers, tech stack tags, URLs        |
|   - Certifications: Issuer patterns, credential links       |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                  Database & Response Storage                |
|   - Record stored in `resumes` table                        |
|   - `raw_text` preserved for auditing                       |
|   - `parsed_json` structured payload stored                 |
|   - Status updated to `parsed` (or `failed`)                |
+-------------------------------------------------------------+
```

---

## 5. API Endpoints

### 1. Upload & Parse Resume
- **Endpoint**: `POST /api/v1/resumes/upload`
- **Authentication**: Required (`Bearer <JWT>`)
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (binary document)
- **Response**: `ResumeResponse` (HTTP 201)
  ```json
  {
    "id": "e9c1d1a8-...",
    "candidate_profile_id": "b3f0...",
    "filename": "candidate_resume.pdf",
    "file_type": "pdf",
    "file_size_bytes": 10240,
    "status": "parsed",
    "parsed_data": {
      "contact": { "full_name": "Jordan Lee", "email": "jordan@example.com" },
      "skills": [{ "skill": "Python", "category": "backend" }],
      "education": [...],
      "experience": [...],
      "projects": [...]
    },
    "created_at": "2026-10-06T12:00:00Z"
  }
  ```

### 2. Retrieve Resume by ID
- **Endpoint**: `GET /api/v1/resumes/{resume_id}`
- **Authentication**: Required (`Bearer <JWT>`)
- **Response**: `ResumeDetailResponse` (HTTP 200)

### 3. List Resumes for Current Candidate
- **Endpoint**: `GET /api/v1/resumes/`
- **Authentication**: Required (`Bearer <JWT>`)
- **Response**: `ResumeListResponse` (HTTP 200)

---

## 6. Parsing Limitations & Boundaries

1. **OCR Limitation**: Scanned-image PDFs that contain only raster images without an embedded text layer cannot be parsed in Phase 11. When scanned PDFs are detected, the system safely raises a user-friendly error (`NoExtractableTextError`) explaining that OCR is not supported.
2. **Deterministic Extraction**: Extraction uses structured regex and keyword heuristics. It does not perform generative inference, hallucination, or probabilistic guessing.
3. **Complex Multi-Column Layouts**: Heavily stylized graphic resumes (e.g. multi-column infographics) will have text extracted in stream order, which may interleave adjacent column lines.

---

## 7. Testing Strategy

The Phase 11 implementation includes:
- **Synthetic Test Fixtures**: `backend/tests/helpers/synthetic_resumes.py` provides generated in-memory PDF, DOCX, and TXT resumes without relying on third-party test files or real user data.
- **Validation Tests**: `backend/tests/test_resume_validation.py` tests extension checks, magic bytes, oversized files, path traversal attacks, and executable rejection.
- **Extractor Tests**: `backend/tests/test_resume_extractors.py` tests PDF/DOCX/TXT text extraction, section splitting, and sub-entity extraction.
- **API Tests**: `backend/tests/test_resume_api.py` tests upload endpoints, status codes (201, 400, 401, 413, 422), and candidate profile ownership isolation.
- **Frontend Tests**: `frontend/src/test/Resume.test.tsx` tests dropzone rendering, client-side format/size validation, loading indicators, success cards, extraction previews, missing field fallbacks, and error retry paths.
