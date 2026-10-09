# Changelog

All notable changes to CareerLens will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Phase 19+: Hybrid matching engine, explainable AI, and subsequent roadmap phases

---

## [0.18.0] — 2026-10-09

### Added
- **Phase 18 — Recommendations Frontend (Semantic Opportunity Recommendations)**:
  - Created strongly-typed TypeScript recommendation interfaces in `frontend/src/types/recommendation.ts` strictly mirroring backend schemas (`SemanticOpportunityItem`, `RecommendationListResponse`, `RecommendationFilterParams`).
  - Implemented `frontend/src/services/recommendationService.ts` with native fetch, bearer token handling, query parameter serialization, and structured error handling (`RecommendationError`) for 400, 401, 404, and 500 status codes.
  - Implemented `frontend/src/components/recommendations/RecommendationCard.tsx` featuring structured metadata badges, compensation formatting, safe plain-text snippets (XSS-safe), and a neutral cosine similarity indicator (`Cosine: +0.84`) preserving the `[-1.0, 1.0]` range without artificial hiring probabilities or biased color thresholds.
  - Implemented `frontend/src/components/recommendations/RecommendationFilters.tsx` supporting backend-verified facets (`opportunity_type`, `work_mode`, `employment_type`, `location`) and filter reset actions.
  - Implemented `frontend/src/pages/RecommendationsPage.tsx` with dedicated, accessible UX states for loading skeletons, empty results, 404 candidate profile missing (CTA to `/profile`), 400 profile text insufficient (CTA to `/profile`), 401 unauthorized (CTA to `/login`), and 500 retryable error state.
  - Registered `/recommendations` route in `frontend/src/App.tsx` and added navigation link to `frontend/src/components/layout/Navbar.tsx`.
  - Added comprehensive test suite `frontend/src/test/Recommendations.test.tsx` (11 tests) and updated `App.test.tsx` (10 tests). Total frontend tests passing: 68/68.

---

## [0.17.0] — 2026-10-09

### Added
- **Phase 17 — Semantic Retrieval & Vector Search**:
  - Implemented authenticated semantic opportunity retrieval endpoint `GET /api/v1/recommendations/`.
  - pgvector cosine distance search against active opportunity embeddings in PostgreSQL.
  - Candidate profile vector alignment ordering in `[-1.0, 1.0]`.
  - Added 21 backend semantic retrieval tests in `backend/tests/test_semantic_retrieval.py`. Total backend tests passing: 225/225.

---

## [0.16.0] — 2026-10-08

### Added
- **Phase 16 — Local Embedding Foundation**:
  - Added `profile_embedding Vector(384)` and `embedding_updated_at DateTime(timezone=True)` to `CandidateProfile` via Alembic migration `e9f42a8b3c1d`.
  - Reused existing `Opportunity.job_embedding Vector(384)` and `Opportunity.embedding_updated_at` without redundant columns.
  - Implemented modular local embedding provider architecture under `app/services/embeddings/`:
    - `BaseEmbeddingProvider` interface with batch and single embedding generation methods.
    - `LocalSentenceTransformersProvider` wrapping `sentence-transformers/all-MiniLM-L6-v2` with thread-safe singleton lazy loading, forced CPU inference, input validation, and 384-dimensional output verification.
    - `CandidateTextNormalizer` and `OpportunityTextNormalizer` providing deterministic, whitespace-safe, normalized text representations strictly excluding sensitive data (passwords, emails, phone numbers, addresses, auth tokens, compensation).
    - `EmbeddingService` facade with non-blocking async execution via `asyncio.to_thread`, stale detection accounting for parent and child entities, safe failure handling, and batch operations.
  - Integrated embedding lifecycle hooks into:
    - `opportunity_ingest_service.py` (batch opportunity embedding post-commit)
    - `profile_service.py` (profile creation, update, and child skill/experience/education/project/certification mutations)
    - `profile_sync_service.py` (resume-to-profile sync post-commit)
  - Added CPU-only PyTorch and sentence-transformers dependencies without CUDA or GPU requirements.
  - Added 19 automated embedding tests in `tests/test_embeddings.py` covering provider initialization, dimension verification, normalization, determinism, lifecycle management, stale detection, safe failure handling, and privacy controls.
  - Verified 204 passing backend tests and 56 passing frontend tests with zero regressions.

---

## [0.15.0] — 2026-10-08

### Added
- **Phase 15 — Opportunity Discovery & Exploration**:
  - Implemented public active opportunity search and filtering backend in `app/services/opportunity_search_service.py` with multi-field keyword search (title, company, description, location, canonical skill names), opportunity type, work mode, employment type, location, experience range overlap, and sorting.
  - Created public discovery API endpoint `GET /api/v1/opportunities/discover` and detail endpoint `GET /api/v1/opportunities/public/{id}`.
  - Created React frontend discovery interface in `frontend/src/features/opportunities/` with search input, filters, sort controls, opportunity cards, detail view, and safe external link handling (`rel="noopener noreferrer"`).
  - Added 8 backend discovery tests in `tests/test_opportunity_discovery.py` and 5 frontend discovery tests in `frontend/src/features/opportunities/__tests__/`.
  - Verified 185 passing backend tests and 56 passing frontend tests.

---

## [0.14.0] — 2026-10-08

### Added
- **Phase 14 — Opportunity Ingestion & Normalization Foundation**:
  - Added PostgreSQL `opportunity_type_enum` with values `('job', 'internship', 'hackathon')` and column `opportunities.opportunity_type` via Alembic migration `d8e31a7f4b9c` with index `opportunities_type_idx`.
  - Updated SQLAlchemy ORM models (`Opportunity`, `OpportunitySkill`, `OpportunityType`).
  - Created strongly typed Pydantic v2 schemas in `app/schemas/opportunity.py` (`RawOpportunityRow`, `OpportunityCreate`, `OpportunityUpdate`, `OpportunityResponse`, `OpportunityDetailResponse`, `OpportunityListResponse`, `OpportunityIngestResult`).
  - Implemented deterministic text, URL, salary, date, and enum normalization service in `app/services/opportunity_normalizer.py`.
  - Implemented deterministic canonical skill normalization in `app/services/opportunity_skill_normalizer.py` reusing canonical catalog without ML/LLM models.
  - Implemented robust opportunity ingestion and deduplication service in `app/services/opportunity_ingest_service.py` supporting primary (`source + source_id`) and fallback deduplication.
  - Created opportunity REST API endpoints in `app/api/v1/endpoints/opportunities.py`:
    - `POST /api/v1/opportunities/ingest` (multi-format CSV or JSON batch ingestion, authenticated)
    - `GET /api/v1/opportunities/` (filtering by `opportunity_type`, `work_mode`, `employment_type`, with pagination)
    - `GET /api/v1/opportunities/{id}` (single opportunity detail with associated skills)
  - Created synthetic development dataset in `data/sample/opportunities_synthetic.csv` covering jobs, internships, hackathons, and edge cases.
  - Added 32 automated tests across `test_opportunity_normalizer.py`, `test_opportunity_deduplication.py`, `test_opportunity_ingestion.py`, and `test_opportunity_api.py`.
  - Verified 177 passing backend tests and 51 passing frontend tests with zero regressions.

---


## [0.9.0] — 2026-10-05

### Added
- **30% Foundation Milestone Completed & Verified** (Phases 1–10):
  - Completed comprehensive repository, backend, database, frontend, security, and testing foundation audits.
  - Published [`docs/roadmap.md`](docs/roadmap.md) defining the v1.1 roadmap, phase status matrix, and scope boundaries.
  - Published [`docs/architecture.md`](docs/architecture.md) detailing the Modular Monolith architecture across backend, PostgreSQL 18.6 + pgvector, React 19, security pipelines, and testing foundations.
  - Formally verified zero regressions across 94 backend tests (pytest) and 23 frontend tests (vitest).
  - Verified static security scans with zero vulnerabilities (Bandit, npm audit, secret scanner).
  - Verified clean database schema state across `careerlens_db` and `careerlens_test` at Alembic head revision `c7e23d4f5a6b` with 15 relational tables and native pgvector extension.
  - Confirmed strict boundary preservation: Phase 11 (Resume Parsing) and subsequent AI/ML features remain untouched and scheduled next.

---

## [0.8.0] — 2026-10-05

### Added
- **Centralized Test Configuration & Database Safety** (`backend/tests/conftest.py`, `backend/app/core/config.py`):
  - `enforce_test_database_safety` autouse fixture strictly preventing test runs against production or development database (`careerlens_db`); forces immediate abortion if non-test DB is targeted.
  - `settings.effective_database_url` dynamically switches to `TEST_DATABASE_URL` (`careerlens_test`) during `ENVIRONMENT == "test"`.
  - Transaction-level test isolation via `db_session` fixture with automatic nested rollbacks.
  - Async ASGI test client fixture (`async_client`) using `httpx.AsyncClient`.
  - Authenticated test fixtures: `authenticated_user`, `auth_headers`, `authenticated_client`, `sample_candidate_profile`, `sample_opportunity`.
- **Deterministic Test Data Factories** (`backend/tests/factories/`):
  - Generic typed `BaseFactory[T]` supporting in-memory `.build(**overrides)` and persistent async `.create(db_session, **overrides)`.
  - Factories for all 14 core, candidate, opportunity, and tracking entities:
    - `UserFactory` (`backend/tests/factories/user_factory.py`)
    - `CandidateProfileFactory`, `ResumeFactory`, `SkillFactory`, `EducationFactory`, `ExperienceFactory`, `ProjectFactory`, `CertificationFactory` (`backend/tests/factories/candidate_factory.py`)
    - `OpportunityFactory`, `OpportunitySkillFactory` (`backend/tests/factories/opportunity_factory.py`)
    - `MatchFactory`, `ApplicationFactory`, `ApplicationStatusHistoryFactory`, `InterviewPrepFactory` (`backend/tests/factories/tracking_factory.py`)
- **Authentication Test Helpers** (`backend/tests/helpers/auth.py`):
  - `create_test_user`, `create_auth_token`, `get_auth_headers`, `create_authenticated_headers`, `login_test_user` for testing real authentication flows.
- **Backend Testing Foundation Test Suites**:
  - `backend/tests/test_factories.py` (7 tests): Validates in-memory build and database persistence across all 14 factories.
  - `backend/tests/test_isolation.py` (3 tests): Validates database safety abort mechanism, test environment URL routing, and session rollback isolation.
  - `backend/tests/test_integration_foundation.py` (5 tests): Validates async client, authenticated client fixture, login flow helper, and sample model fixtures.
- **Frontend Test Foundation** (`frontend/src/test/`):
  - `frontend/src/test/test-utils.tsx`: Shared test utilities providing `renderWithRouter` (wrapping components in configured `MemoryRouter`), `createMockFrontendUser` mock factory, and re-exported Testing Library utilities.
  - `frontend/src/test/TestUtils.test.tsx` (2 tests): Verifies router-isolated component rendering and mock data defaults.
- **Documentation**:
  - Updated `docs/development.md` with backend testing foundation, test database safety guard, factory usage, authentication test helpers, and frontend test utilities.

### Security
- Verified zero credentials or real user data in test fixtures and factories.
- Hardened database safety guard preventing accidental data pollution or destructive operations on development or production databases.

---

## [0.7.0] — 2026-10-05

### Added
- **Unified Quality Gate Script** (`scripts/check_quality.py`):
  - Standardized runner for secret scans, Ruff lint & format checks, Bandit static analysis, backend pytest suite, frontend Oxlint, TypeScript type-check, Vitest, and production Vite build.
- **Centralized Logging Security & Redaction Foundation** (`backend/app/core/logging.py`):
  - `SensitiveDataFilter`: Intercepts log records to redact plaintext user passwords, Bearer tokens, Basic credentials, database connection URIs with embedded passwords, and authorization headers.
  - `setup_logging` and `get_logger`: Centralized application logging initialization under the `careerlens` namespace.
- **Security Response Headers Middleware** (`backend/app/main.py`):
  - Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and production `Strict-Transport-Security`.
- **Unhandled Server Exception Masking** (`backend/app/main.py`):
  - Catches unhandled exceptions, logs sanitized error details server-side, and emits generic `{"detail": "Internal server error"}` with HTTP 500 without leaking stack traces or internal filesystem paths.
- **Production Configuration Safeguards** (`backend/app/core/config.py`):
  - Enforces `DEBUG=False`, strong JWT secret (>= 32 chars), non-placeholder `DATABASE_URL`, and rejection of wildcard CORS origin in production environments.
  - Automatically parses comma-separated origin strings from `ALLOWED_ORIGINS` and strips trailing slashes.
- **Security-Focused Test Suites**:
  - `backend/tests/test_security_hardening.py` (15 tests): Validates security headers, CORS baseline, logging redaction, unhandled error masking, production settings validation, and `.env.example` placeholder hygiene.
  - `frontend/src/test/Security.test.tsx` (4 tests): Validates exclusion of server-only secrets from client bundle, password input obfuscation (`type="password"`), absence of `dangerouslySetInnerHTML`, and default token isolation.
- **Pre-Commit Configuration** (`.pre-commit-config.yaml`):
  - Lightweight git pre-commit configuration with file hygiene, private key detection, and Ruff formatting.
- **Standardized Documentation**:
  - `docs/development.md`: Comprehensive guide to backend, frontend, and quality gate commands.
  - `docs/security_checklist.md`: Security policies for secret management, CORS baseline, security headers, logging, and error handling.

### Changed
- Hardened CORS configuration to explicit HTTP methods and allowed headers.
- Enhanced database health check error handling in `backend/app/api/v1/endpoints/health.py` to avoid leaking database internals.
- Strengthened `.gitignore` rules across root and frontend for certificates (`*.pem`, `*.key`), database dumps, and environment variants.

---

## [0.6.0] — 2026-10-04

### Added
- React 19 + TypeScript + Vite modern frontend scaffold (`frontend/`):
  - Application shell and responsive navigation bar with CareerLens branding
  - Responsive landing page with Hero section, value propositions, and Call-to-Action routing
  - Authentication views (`LoginPage`, `RegisterPage`) with password policy indicators
  - Dashboard overview with match metric placeholders and application tracking cards
  - Dedicated 404 Not Found error page
- Core UI component library (`frontend/src/components/ui/`): Button, Card, Badge, Input, LoadingState
- Comprehensive frontend test suite using Vitest and React Testing Library (17 tests)
- Oxlint linting, TypeScript type-check, and Vite production bundle build verification

---

## [0.5.0] — 2026-10-04

### Added
- Opportunity & Tracking ORM entities according to approved v1.1 ER design (`backend/app/models/`):
  - `Opportunity`: Job listing entity with compensation, work mode, employment type, location, required/preferred skill arrays, and vector column `job_embedding (VECTOR(384))`
  - `OpportunitySkill`: Normalized skill mappings for opportunities with `is_required` flag and unique constraint `(opportunity_id, skill_name)`
  - `Match`: Match scoring entity linking `CandidateProfile` and `Opportunity` with semantic/deterministic/final scores, JSONB breakdowns, and unique pair constraint
  - `Application`: Job application tracking record with `ApplicationStatus` enum, applied date, and unique candidate/opportunity constraint
  - `ApplicationStatusHistory`: Immutable audit trail for application status transitions
  - `InterviewPrep`: Tailored interview preparation content with structured JSONB and unique candidate/opportunity constraint
- Native PostgreSQL ENUM definitions: `opportunity_source_enum`, `eligibility_status_enum`, `application_status_enum`
- Relational and partial indexes: `opportunities_source_dedup_idx` (partial unique where source_id IS NOT NULL), `opportunities_active_idx`, `opportunities_employment_type_idx`, `opportunities_work_mode_idx`, `opp_skills_opp_id_idx`, `opp_skills_name_idx`, `matches_profile_score_idx`, `applications_profile_status_idx`, and `status_history_app_id_idx`
- Alembic database migrations:
  - Migration 0003 (`b4f81c9a1d2e`): Creates `opportunities`, `opportunity_skills`, `opportunity_source_enum`, and relational indexes
  - Migration 0004 (`c7e23d4f5a6b`): Creates `matches`, `applications`, `application_status_history`, `interview_prep`, `eligibility_status_enum`, and `application_status_enum`
- Applied both migrations cleanly to `careerlens_db` and `careerlens_test` with verified downgrade/re-upgrade rollback cycle
- Comprehensive automated test suite in `backend/tests/test_opportunity_models.py` (13 tests) validating model inheritance, metadata integrity, primary/foreign keys, unique constraints, enum definitions, CRUD operations, cascade deletion lifecycles, and partial index deduplication

### Security
- Verified strict cascade deletions (`ON DELETE CASCADE`) preventing orphaned sub-entities across all relational links
- Verified no credentials, tokens, or production database connection strings committed
- Static security analysis via Bandit passing with zero issues across application code, migration scripts, and test suites

---


## [0.4.0] — 2026-10-04

### Added
- Core authentication module (`backend/app/api/v1/endpoints/auth.py`):
  - `POST /api/v1/auth/register`: Safe user registration with input validation, duplicate email conflict handling (HTTP 409), password hashing via bcrypt, and safe profile response.
  - `POST /api/v1/auth/login`: User login validating credentials against stored bcrypt hash, issuing signed Bearer JWT access tokens (HTTP 200).
  - `GET /api/v1/auth/me`: Protected current-user identity endpoint validating Bearer JWT and returning safe user profile.
- Security and cryptographic utilities (`backend/app/core/security.py`):
  - Bcrypt password hashing (`hash_password`, `verify_password`) with per-user salt generation.
  - Password policy validation enforcing minimum 8 characters, maximum 72 bytes (preventing silent bcrypt truncation), and non-blank input.
  - JWT token generation (`create_access_token`) and validation (`decode_access_token`) with standard claims (`sub`, `exp`, `iat`, `type="access"`).
- Dependency injection (`backend/app/api/deps.py`):
  - `get_current_user` and `get_current_active_user` FastAPI dependencies validating Bearer JWT, checking expiration/claims, and retrieving active User from database.
- Pydantic schemas (`backend/app/schemas/auth.py`):
  - `UserRegisterRequest`, `UserLoginRequest`, `Token`, `UserResponse` with strict exclusion of sensitive fields (`hashed_password`).
- Authentication test suite (`backend/tests/test_auth.py`):
  - 25 dedicated test cases covering password policy, hashing, JWT lifecycle, expiration, signature verification, duplicate registration, credential validation, protected endpoints, and OpenAPI schema compliance.

### Security
- Password hashes generated exclusively with bcrypt and random salt; plaintext passwords never logged or stored.
- Sensitive fields (`hashed_password`) strictly excluded from all API response schemas.
- JWT secret key loaded dynamically from environment (`JWT_SECRET_KEY`); no hardcoded cryptographic secrets.
- Constant error responses on invalid credentials preventing email enumeration.
- Automated security scan via Bandit passing with zero issues across application code and dependencies.

---


## [0.3.0] — 2026-10-04

### Added
- Core candidate and identity ORM entities according to approved v1.1 ER design (`backend/app/models/`):
  - `User`: Identity entity with email uniqueness, password hash, and active/admin flags
  - `CandidateProfile`: Central candidate profile with work/employment preferences, location, compensation, and social links
  - `Resume`: Resume metadata, raw text extraction, and structured JSONB payload
  - `Skill`: Normalized candidate skills with category, proficiency level, and composite unique constraint `(candidate_profile_id, skill_name)`
  - `Education`: Education history with degree, institution, field of study, and education level enum
  - `Experience`: Professional experience with employment type, work mode, and PostgreSQL string array `skills_used`
  - `Project`: Personal/academic projects with live URL, repo link, and PostgreSQL string array `technologies`
  - `Certification`: Professional certifications with issuing organization, validity dates, and verification links
- PostgreSQL native ENUM definitions: `work_mode_enum`, `employment_type_enum`, `skill_category_enum`, `skill_proficiency_enum`, `skill_source_enum`, `education_level_enum`
- Alembic revision `0a859f9b9f2c` (`create_core_candidate_models`) generated and applied to `careerlens_db` and `careerlens_test`
- Automated test suite in `backend/tests/test_models.py` verifying model inheritance, metadata integrity, primary/foreign keys, unique constraints, relationship persistence, cascade deletion lifecycle, and constraint violation guards

### Security
- Zero credentials, secrets, or tokens committed in migration scripts, models, or configurations
- Proper ON DELETE CASCADE foreign key constraints preventing orphaned candidate sub-entity records
- Static security analysis via Bandit passing with zero issues across application code, migration scripts, and utilities

---

## [0.2.0] — 2026-10-04

### Added
- PostgreSQL database configuration with `pgvector` v0.8.6 extension integration
- Dedicated application database (`careerlens_db`) and test database (`careerlens_test`) initialized
- Asynchronous database stack dependencies: `sqlalchemy[asyncio]`, `asyncpg`, `pgvector`, `greenlet`, and `alembic`
- Database layer (`backend/app/db/`): DeclarativeBase model foundation, async engine with connection pooling and `NullPool` test support, and `get_db` async session generator
- Alembic database migration infrastructure (`backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/`) configured with dynamic settings-based URL loading
- Database and pgvector health check endpoint `GET /api/v1/health/db` (with `/health/db` root alias)
- Database setup and credential orchestration script (`scripts/setup_db.py`)
- Automated test suite validating database async connection, session lifecycle, vector similarity distance metrics (L2, cosine), role least-privilege, Alembic configuration, and DB health endpoints (`backend/tests/test_database.py`)

### Security
- Zero credentials or passwords hardcoded in source code, scripts, or commit history
- Application database user `careerlens_user` hardened to least-privilege attributes (NOCREATEDB, NOSUPERUSER)
- Local secrets isolated exclusively within gitignored `.env`
- Static security analysis via Bandit passing with zero issues across application code and scripts

---

## [0.1.0] — 2026-10-03

### Added
- Python 3.12 virtual environment configuration
- Minimal backend dependency definitions (`backend/requirements.txt` and `backend/requirements-dev.txt`)
- FastAPI application entry point (`backend/app/main.py`)
- Application settings and configuration loader (`backend/app/core/config.py`)
- Modular API v1 router structure (`backend/app/api/v1/api.py`)
- Health check endpoint (`backend/app/api/v1/endpoints/health.py`) with `GET /api/v1/health` and `GET /health`
- Tool configurations for pytest and ruff (`backend/pyproject.toml`)
- Automated test suite verifying health endpoints, OpenAPI schema, and auth-less access (`backend/tests/`)

### Security
- Verified zero credentials, secrets, or real API keys in source code
- Automated AST security scan via Bandit passing with zero issues
- Confirmed health check operates completely isolated with no database or external service dependencies

---

## [0.0.1] — 2026-10-03

### Added
- Project repository initialized on GitHub
- Directory scaffold: `backend/`, `frontend/`, `data/sample/`, `data/uploads/`, `docs/`, `tests/`, `scripts/`
- `.gitignore` covering Python, Node, environment files, uploads, ML models, OS and editor artifacts
- `README.md` with project overview, technology stack, and structure
- `.env.example` with all environment variable placeholders (no real values)
- `CHANGELOG.md` initialized

### Security
- `.env` confirmed absent and covered by `.gitignore` before first commit
- No secrets, credentials, or API keys in any committed file
