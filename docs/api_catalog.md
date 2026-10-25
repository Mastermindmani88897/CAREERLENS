# CareerLens — REST API Catalog & Endpoint Reference (v1.1)

This catalog provides an exact, comprehensive specification of all 34 REST API endpoints registered in CareerLens, grounded in the application source code and OpenAPI 3.1 definitions.

---

## 1. Authentication & Security Overview

- **Base URL**: `/api/v1` (or direct `/health` for container probes).
- **Authentication Scheme**: HTTP Bearer JWT tokens in the `Authorization` header:
  ```http
  Authorization: Bearer <access_token>
  ```
- **Token Format**: HMAC-SHA256 (`HS256`) signed JWT with `sub` claim containing user UUID string and `exp` timestamp.
- **Common Error Codes**:
  - `400 Bad Request`: Schema validation error or missing prerequisite data.
  - `401 Unauthorized`: Missing, expired, or invalid JWT Bearer token.
  - `403 Forbidden`: Resource belongs to a different candidate (ownership check failure).
  - `404 Not Found`: Target entity ID does not exist.
  - `422 Unprocessable Content`: Business logic constraint violation (e.g., prohibited state machine transition, inactive opportunity application).
  - `500 Internal Server Error`: Unhandled server-side exception (masked in production).

---

## 2. API Endpoints by Domain

### 2.1. Health & Readiness (`/health`)

#### 1. Root Service Health
- **Endpoint**: `GET /health` (also aliased at `GET /api/v1/health`)
- **Authentication**: None (Public)
- **Purpose**: Container readiness and liveness probe.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "version": "0.5.0",
    "timestamp": "2026-10-25T14:00:00Z"
  }
  ```

#### 2. Database & pgvector Health
- **Endpoint**: `GET /health/db` (also aliased at `GET /api/v1/health/db`)
- **Authentication**: None (Public)
- **Purpose**: Verifies active PostgreSQL connection pool and pgvector extension availability.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "pgvector": "available",
    "vector_version": "0.8.0"
  }
  ```
- **Response `503 Service Unavailable`**: Database unreachable or vector extension missing.

---

### 2.2. Authentication (`/api/v1/auth`)

#### 3. User Registration
- **Endpoint**: `POST /api/v1/auth/register`
- **Authentication**: None (Public)
- **Purpose**: Creates a new user account with hashed password and returns an initial access token.
- **Request Body (`UserRegister`)**:
  ```json
  {
    "email": "candidate@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response `201 Created` (`TokenResponse`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "email": "candidate@example.com",
      "is_active": true,
      "created_at": "2026-10-25T14:00:00Z"
    }
  }
  ```
- **Errors**: `400 Bad Request` if email is already registered or password fails complexity criteria.

#### 4. User Login
- **Endpoint**: `POST /api/v1/auth/login`
- **Authentication**: None (Public)
- **Purpose**: Authenticates credentials and returns a signed JWT access token.
- **Request Body (`UserLogin`)**:
  ```json
  {
    "email": "candidate@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response `200 OK` (`TokenResponse`)**: Same schema as registration.
- **Errors**: `401 Unauthorized` for invalid email or password.

#### 5. Current User Profile
- **Endpoint**: `GET /api/v1/auth/me`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Returns the authenticated user's account details.
- **Response `200 OK` (`UserResponse`)**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "candidate@example.com",
    "is_active": true,
    "created_at": "2026-10-25T14:00:00Z"
  }
  ```

---

### 2.3. Resumes (`/api/v1/resumes`)

#### 6. Upload & Parse Resume
- **Endpoint**: `POST /api/v1/resumes`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Ingests, parses, and extracts structured entities from a PDF or DOCX resume document.
- **Request (Multipart Form Data)**:
  - `file`: Binary file upload (PDF / DOCX, $\le 10\text{ MB}$).
- **Response `201 Created` (`ResumeExtractionResponse`)**:
  ```json
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "candidate_profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "file_name": "jane_doe_resume.pdf",
    "parsed_data": {
      "contact_info": { "name": "Jane Doe", "email": "jane@example.com", "phone": "+1-555-0199" },
      "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "React"],
      "experiences": [
        {
          "company": "Tech Corp",
          "title": "Software Engineer",
          "start_date": "2022-01-01",
          "end_date": "2024-01-01",
          "is_current": false,
          "description": "Backend API development in Python and async microservices."
        }
      ],
      "educations": [
        {
          "institution": "State University",
          "degree": "Bachelor of Science in Computer Science",
          "education_level": "bachelor",
          "graduation_year": 2021
        }
      ]
    },
    "created_at": "2026-10-25T14:00:00Z"
  }
  ```
- **Errors**: `400 Bad Request` (unsupported file type, oversized document), `422 Unprocessable Content` (unparseable / empty text PDF).

#### 7. List Uploaded Resumes
- **Endpoint**: `GET /api/v1/resumes`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Lists all resumes uploaded by the current authenticated candidate.
- **Response `200 OK`**: Array of `ResumeSummaryResponse` items.

#### 8. Retrieve Single Resume
- **Endpoint**: `GET /api/v1/resumes/{resume_id}`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Retrieves full structured JSON extraction payload for a specific resume.
- **Constraints**: Candidate ownership verified (`resume.candidate_profile_id == current_profile.id`).

---

### 2.4. Candidate Profiles (`/api/v1/profiles`)

#### 9. Create Candidate Profile
- **Endpoint**: `POST /api/v1/profiles`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Initializes candidate profile metadata for the authenticated user.
- **Request Body (`CandidateProfileCreate`)**:
  ```json
  {
    "full_name": "Jane Doe",
    "headline": "Full Stack Engineer | Python & React",
    "summary": "Experienced backend developer specializing in FastAPI and scalable PostgreSQL architectures.",
    "location": "San Francisco, CA",
    "open_to_relocation": true,
    "preferred_work_mode": "hybrid",
    "preferred_employment_type": "full_time"
  }
  ```
- **Response `201 Created` (`CandidateProfileResponse`)**

#### 10. Get Current Candidate Profile
- **Endpoint**: `GET /api/v1/profiles/me`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Retrieves the full profile tree for the authenticated user (including nested skills, educations, experiences, projects, and certifications).
- **Response `200 OK` (`CandidateProfileResponse`)**: Complete nested profile hierarchy.
- **Errors**: `404 Not Found` if candidate profile has not yet been initialized.

#### 11. Update Candidate Profile
- **Endpoint**: `PUT /api/v1/profiles/me`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Updates top-level candidate preferences, compensation expectations, or summary text.
- **Request Body (`CandidateProfileUpdate`)**

#### 12. Synchronize Profile from Resume
- **Endpoint**: `POST /api/v1/profiles/me/sync-from-resume/{resume_id}`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Reconciles structured extraction data from a parsed resume into the candidate profile.
- **Constraints**: Resumes must belong to the caller. Automatically deduplicates skills, experiences, and educations.

#### 13–15. Candidate Skills Sub-Resource
- `GET /api/v1/profiles/me/skills`: List all candidate skills.
- `POST /api/v1/profiles/me/skills`: Add skill (`skill_name`, optional `category`, optional `proficiency_level`).
- `DELETE /api/v1/profiles/me/skills/{skill_id}`: Remove skill.

#### 16–19. Candidate Experience Sub-Resource
- `GET /api/v1/profiles/me/experience`: List work experiences.
- `POST /api/v1/profiles/me/experience`: Add work experience (`company_name`, `job_title`, `start_date`, optional `end_date`, `is_current`, `work_mode`, `description`).
- `PUT /api/v1/profiles/me/experience/{experience_id}`: Update work experience.
- `DELETE /api/v1/profiles/me/experience/{experience_id}`: Remove work experience.

#### 20–23. Candidate Education Sub-Resource
- `GET /api/v1/profiles/me/education`: List education records.
- `POST /api/v1/profiles/me/education`: Add education (`institution`, `degree`, `field_of_study`, `education_level`, optional `graduation_year`).
- `PUT /api/v1/profiles/me/education/{education_id}`: Update education record.
- `DELETE /api/v1/profiles/me/education/{education_id}`: Remove education record.

#### 24–27. Candidate Projects Sub-Resource
- `GET /api/v1/profiles/me/projects`: List projects.
- `POST /api/v1/profiles/me/projects`: Add project (`title`, `description`, optional `repo_url`, optional `live_url`, `skills_used`).
- `PUT /api/v1/profiles/me/projects/{project_id}`: Update project record.
- `DELETE /api/v1/profiles/me/projects/{project_id}`: Remove project record.

#### 28–31. Candidate Certifications Sub-Resource
- `GET /api/v1/profiles/me/certifications`: List certifications.
- `POST /api/v1/profiles/me/certifications`: Add certification (`name`, `issuing_organization`, optional `issue_date`, optional `credential_url`).
- `PUT /api/v1/profiles/me/certifications/{certification_id}`: Update certification record.
- `DELETE /api/v1/profiles/me/certifications/{certification_id}`: Remove certification record.

---

### 2.5. Opportunities (`/api/v1/opportunities`)

#### 32. List Opportunities (Search, Filter, Paginate)
- **Endpoint**: `GET /api/v1/opportunities/`
- **Authentication**: None (Public) / Optional User
- **Purpose**: Explores opportunities with multi-attribute filtering, keyword search, and pagination.
- **Query Parameters**:
  - `keyword` (str, optional): Search across title, company name, and description.
  - `work_mode` (`onsite` | `hybrid` | `remote` | `any`, optional).
  - `employment_type` (`full_time` | `part_time` | `contract` | `internship` | `any`, optional).
  - `location` (str, optional): Case-insensitive location filter.
  - `skills` (list[str], optional): Required skills filter.
  - `is_active` (bool, default `true`).
  - `page` (int, default `1`, min `1`).
  - `page_size` (int, default `20`, min `1`, max `100`).
  - `sort_by` (str, default `created_at`).
  - `sort_dir` (`asc` | `desc`, default `desc`).
- **Response `200 OK` (`OpportunityListResponse`)**:
  ```json
  {
    "items": [
      {
        "id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
        "title": "Senior Backend Engineer",
        "company_name": "CloudScale Inc",
        "location": "Remote",
        "work_mode": "remote",
        "employment_type": "full_time",
        "min_experience_years": 3,
        "required_education_level": "bachelor",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "is_active": true,
        "created_at": "2026-10-25T12:00:00Z"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
  ```

#### 33. Retrieve Opportunity Detail
- **Endpoint**: `GET /api/v1/opportunities/{id}`
- **Authentication**: None (Public)
- **Purpose**: Retrieves full opportunity details including structured skill requirements.
- **Response `200 OK` (`OpportunityDetailResponse`)`

#### 34. Ingest Opportunities (Batch CSV / JSON)
- **Endpoint**: `POST /api/v1/opportunities/ingest`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Batch ingests opportunities from JSON payload or CSV multipart file. Automatically extracts skills, normalizes attributes, and computes pgvector embeddings via `all-MiniLM-L6-v2`.
- **Response `200 OK`**:
  ```json
  {
    "total_received": 15,
    "successfully_ingested": 14,
    "duplicates_skipped": 1,
    "errors": []
  }
  ```

---

### 2.6. Semantic Recommendations (`/api/v1/recommendations`)

#### 35. Get Candidate Opportunity Recommendations
- **Endpoint**: `GET /api/v1/recommendations/`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Retrieves semantically ranked opportunities using pgvector approximate nearest neighbor cosine similarity against the candidate's profile summary embedding.
- **Query Parameters**:
  - `limit` (int, default `10`, min `1`, max `50`).
  - `work_mode` (optional filter).
  - `employment_type` (optional filter).
  - `location` (optional filter).
- **Response `200 OK`**: Array of opportunities annotated with `semantic_similarity` score [0.0, 1.0].
- **Errors**:
  - `400 Bad Request`: Candidate profile has empty headline/summary/skills (insufficient text to generate embedding).
  - `404 Not Found`: Candidate profile not found.

---

### 2.7. Hybrid Matching Engine (`/api/v1/matches`)

#### 36. Trigger Single Opportunity Match Evaluation
- **Endpoint**: `POST /api/v1/matches/`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Evaluates candidate against a single opportunity using the 7-factor hybrid matching engine and persists the result idempotently.
- **Request Body (`MatchCreateRequest`)**:
  ```json
  {
    "opportunity_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab"
  }
  ```
- **Response `200 OK` (`MatchResponse`)**:
  ```json
  {
    "id": "98765432-abcd-ef01-2345-6789abcdef01",
    "candidate_profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "opportunity_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
    "semantic_score": 0.8421,
    "deterministic_score": 0.9125,
    "final_score": 0.8879,
    "eligibility_status": "eligible",
    "eligibility_warnings": null,
    "score_breakdown": {
      "weights": {
        "semantic_similarity": 0.35,
        "skill_overlap": 0.25,
        "experience": 0.15,
        "education": 0.10,
        "location": 0.05,
        "work_mode": 0.05,
        "employment_type": 0.05
      },
      "skill_overlap": { "score": 0.95, "matched_required": ["Python", "FastAPI"], "missing_required": [] },
      "experience": { "score": 1.0, "candidate_total_years": 4.5, "required_min_years": 3.0 },
      "education": { "score": 1.0, "required_level": "bachelor", "candidate_highest_level": "bachelor" },
      "location": { "score": 1.0, "open_to_relocation": true },
      "work_mode": { "score": 1.0, "opportunity_work_mode": "remote", "candidate_preferred_work_mode": "remote" },
      "employment_type": { "score": 1.0, "is_match": true }
    },
    "explanation": {
      "strengths": [
        "Strong skill alignment: matched 3/3 required skills (FastAPI, PostgreSQL, Python)",
        "Experience requirement fully satisfied: candidate possesses 4.5 years (minimum required: 3.0 years)",
        "Education level matches or exceeds target requirement (bachelor)"
      ],
      "gaps": []
    },
    "skill_gap": {
      "matched_required_skills": ["fastapi", "postgresql", "python"],
      "missing_required_skills": [],
      "matched_preferred_skills": ["docker"],
      "missing_preferred_skills": ["kubernetes"]
    },
    "computed_at": "2026-10-25T14:00:00Z"
  }
  ```

#### 37. Evaluate Matches Across Multiple Opportunities (Batch / Discovery)
- **Endpoint**: `POST /api/v1/matches/evaluate`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Evaluates candidate matches against a list of `opportunity_ids` or automatically discovers top matches across active opportunities.
- **Request Body (`MatchEvaluationRequest`)**:
  ```json
  {
    "opportunity_ids": ["c1d2e3f4-5678-90ab-cdef-1234567890ab"],
    "limit": 10
  }
  ```

#### 38. List Persisted Matches for Candidate
- **Endpoint**: `GET /api/v1/matches/`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Retrieves candidate's previously evaluated matches with sorting by `final_score DESC` and filtering by `eligibility_status`.
- **Query Parameters**:
  - `status` (`eligible` | `partial` | `review_required`, optional).
  - `min_score` (float, optional).
  - `page` (int, default `1`).
  - `page_size` (int, default `20`).

#### 39. Retrieve Single Match by Opportunity or Match ID
- **Endpoint**: `GET /api/v1/matches/{identifier}`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Retrieves an existing match evaluation by `opportunity_id` or `match_id`.

---

### 2.8. Application Tracking (`/api/v1/applications`)

#### 40. Create or Save Application
- **Endpoint**: `POST /api/v1/applications/`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Records a new application in `saved` or `applied` status for the candidate.
- **Request Body (`ApplicationCreate`)**:
  ```json
  {
    "opportunity_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
    "status": "applied",
    "notes": "Submitted via internal career portal."
  }
  ```
- **Response `201 Created` (`ApplicationResponse`)**:
  ```json
  {
    "id": "78901234-abcd-ef01-2345-6789abcdef01",
    "candidate_profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "opportunity_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
    "status": "applied",
    "notes": "Submitted via internal career portal.",
    "applied_at": "2026-10-25T14:00:00Z",
    "created_at": "2026-10-25T14:00:00Z",
    "updated_at": "2026-10-25T14:00:00Z",
    "permitted_next_statuses": ["oa", "interview", "offer", "rejected", "withdrawn"]
  }
  ```
- **Errors**: `404 Not Found` (opportunity missing), `422 Unprocessable Content` (opportunity inactive, or duplicate application already exists).

#### 41. List Tracked Applications
- **Endpoint**: `GET /api/v1/applications/`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Lists tracked applications with stage filtering, keyword search, and pagination.
- **Query Parameters**:
  - `status` (`saved` | `applied` | `oa` | `interview` | `offer` | `rejected` | `withdrawn`, optional).
  - `search` (str, optional): Filter by title or company name.
  - `page` (int, default `1`).
  - `page_size` (int, default `20`).

#### 42. Get Single Application Detail with Audit History
- **Endpoint**: `GET /api/v1/applications/{application_id}`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Retrieves full application details including status transition history timeline.
- **Response `200 OK` (`ApplicationDetailResponse`)**: Includes `status_history` array containing `from_status`, `to_status`, `changed_at`, and `notes`.

#### 43. Update Application Status (Transition Lifecycle)
- **Endpoint**: `PATCH /api/v1/applications/{application_id}/status`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Transitions application to a new lifecycle stage, validates transition against state machine rules, and logs audit trail.
- **Request Body (`ApplicationStatusUpdate`)**:
  ```json
  {
    "status": "interview",
    "notes": "Passed technical assessment. Round 1 scheduled for next Tuesday."
  }
  ```
- **Response `200 OK` (`ApplicationResponse`)**
- **Errors**: `422 Unprocessable Content` if target status transition is prohibited by state machine or application is already in a terminal state (`rejected`, `withdrawn`).

#### 44. Delete Application
- **Endpoint**: `DELETE /api/v1/applications/{application_id}`
- **Authentication**: Required (`Bearer <token>`)
- **Purpose**: Deletes application record and associated audit history.

#### 45. Get Permitted Transition Matrix
- **Endpoint**: `GET /api/v1/applications/transitions`
- **Authentication**: None (Public) / Optional User
- **Purpose**: Returns the static state machine transition mapping for client-side validation and workflow rendering.
- **Response `200 OK`**:
  ```json
  {
    "saved": ["applied", "withdrawn"],
    "applied": ["oa", "interview", "offer", "rejected", "withdrawn"],
    "oa": ["interview", "offer", "rejected", "withdrawn"],
    "interview": ["interview", "offer", "rejected", "withdrawn"],
    "offer": ["rejected", "withdrawn"],
    "rejected": [],
    "withdrawn": []
  }
  ```
