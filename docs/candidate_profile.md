# CareerLens — Phase 12 Candidate Profile API & Resume Synchronization

This document specifies the technical design, ownership model, merge heuristics, and REST API specification for the **Candidate Profile API and Resume-to-Profile Synchronization Pipeline**.

---

## 1. Overview & Architectural Boundary

The Candidate Profile represents the central, authoritative data store for a candidate's professional identity within CareerLens. It provides a structured, validated, and user-editable profile that harmonizes:

1. **Resume-Derived Information**: Extracted deterministically from uploaded resumes during Phase 11.
2. **User-Provided Information**: Explicitly entered, updated, and curated by the candidate.

> [!IMPORTANT]
> **Authoritative Boundary & User-Edit Preservation**
> The resume is **not** the authoritative profile. Profile changes made manually by the user remain the single source of truth.
> When synchronizing profile attributes from an uploaded resume, pre-existing user-entered values are strictly preserved and never overwritten.

---

## 2. Profile Ownership & Authorization Model

- **One-to-One User Relationship**: Each authenticated `User` account has exactly one corresponding `CandidateProfile` record (`CandidateProfile.user_id == User.id`, unique index).
- **Strict User Isolation**: All profile endpoints (`/api/v1/profiles/me`) resolve the authenticated subject directly from the validated JWT token (`get_current_active_user`).
- **Sub-Resource Ownership**: Sub-resources (skills, education records, experiences, projects, and certifications) are bound to the candidate's `profile_id`. Cross-user access (e.g. attempting to read, update, or delete another user's sub-resource) returns HTTP 404 or HTTP 403.
- **Resume Access Authorization**: Synchronizing a profile from a resume (`/api/v1/profiles/me/sync-from-resume/{resume_id}`) requires that the resume's owner matches the requesting user. Cross-user sync attempts are logged and rejected with HTTP 403 Forbidden.

---

## 3. Resume-to-Profile Synchronization & Merge Rules

Synchronization is controlled via `POST /api/v1/profiles/me/sync-from-resume/{resume_id}`.

### Deterministic Merge Heuristics:
1. **Core Profile Fields (`phone`, `linkedin_url`, `github_url`, `portfolio_url`, `summary`)**:
   - If the profile field is currently empty (`None` or empty string) and the parsed resume contains this field, it is populated.
   - If the profile field already contains a user-entered value, the existing value is preserved.
2. **Full Name**:
   - If the profile full name is empty or matches the initial default email handle, and the resume has an extracted name, it is updated.
   - User-customized names are preserved.
3. **Skills (`/me/skills`)**:
   - Additive merge: Skills present in the resume that do not yet exist on the profile (case-insensitive deduplication) are added with `source = "resume"`.
   - Existing manual skills (`source = "manual"`) are never removed.
4. **Education (`/me/education`)**:
   - Deduplicated on `(institution.lower(), degree.lower())`.
   - Only new, distinct educational credentials from the resume are added. Existing records are untouched.
5. **Work Experience (`/me/experience`)**:
   - Deduplicated on `(company.lower(), title.lower())`.
   - Distinct work experiences are merged with date ranges and skills used.
6. **Projects (`/me/projects`)**:
   - Deduplicated on `title.lower()`.
   - New projects are added with technologies and URLs.
7. **Certifications (`/me/certifications`)**:
   - Deduplicated on `name.lower()`.
   - New certifications are added with issuers and dates.
8. **Idempotency Guarantee**:
   - Calling the synchronization endpoint repeatedly with the same resume produces zero duplicate records (`skills_added = 0`, `educations_added = 0`, etc.).

---

## 4. API Endpoints

### Core Profile Operations
| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/api/v1/profiles` | Explicitly create a candidate profile | `201 Created` / `409 Conflict` |
| `GET` | `/api/v1/profiles/me` | Retrieve profile with all nested sub-resources | `200 OK` |
| `PUT` | `/api/v1/profiles/me` | Update candidate profile fields | `200 OK` |
| `POST` | `/api/v1/profiles/me/sync-from-resume/{resume_id}` | Synchronize profile attributes from parsed resume | `200 OK` / `400` / `403` / `404` |

### Sub-Resource Endpoints
| Resource | Endpoints | Supported Operations |
|---|---|---|
| **Skills** | `/api/v1/profiles/me/skills`<br>`/api/v1/profiles/me/skills/{skill_id}` | `GET` (list), `POST` (add, `201`), `DELETE` (`204`) |
| **Education** | `/api/v1/profiles/me/education`<br>`/api/v1/profiles/me/education/{education_id}` | `GET` (list), `POST` (add, `201`), `PUT` (update, `200`), `DELETE` (`204`) |
| **Experience** | `/api/v1/profiles/me/experience`<br>`/api/v1/profiles/me/experience/{experience_id}` | `GET` (list), `POST` (add, `201`), `PUT` (update, `200`), `DELETE` (`204`) |
| **Projects** | `/api/v1/profiles/me/projects`<br>`/api/v1/profiles/me/projects/{project_id}` | `GET` (list), `POST` (add, `201`), `PUT` (update, `200`), `DELETE` (`204`) |
| **Certifications** | `/api/v1/profiles/me/certifications`<br>`/api/v1/profiles/me/certifications/{certification_id}` | `GET` (list), `POST` (add, `201`), `PUT` (update, `200`), `DELETE` (`204`) |

---

## 5. Validation & Integrity Controls

- **Date Range Integrity**: `end_date` must not be earlier than `start_date` across education, experience, and project entities.
- **Experience Years**: Non-negative integer ranges (`0` to `70`).
- **String Length Limits**: Field length boundaries (e.g. 255 chars for names/institutions/companies, 50 chars for phone/grades) prevent denial-of-service payloads.
- **Enumeration Constraints**: Strict validation on `WorkMode`, `EmploymentType`, `SkillCategory`, `SkillProficiency`, `SkillSource`, and `EducationLevel`.

---

## 6. Testing Strategy

The test suite in `backend/tests/test_profile_api.py` includes 13 integration test modules covering:
- Authentication rejection (HTTP 401)
- Profile creation and 409 conflict handling
- Profile retrieval, default initialization, and updating
- Complete CRUD across Skills, Education, Experience, Projects, and Certifications
- Cross-user authorization isolation
- Validation error handling (HTTP 422)
- Resume-to-profile synchronization with user-edit preservation
- Synchronization idempotency and repeated execution
- Cross-user resume synchronization rejection (HTTP 403)
- Direct database persistence verification via SQLAlchemy async sessions
