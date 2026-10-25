# CareerLens — Project Roadmap & Milestone Tracking

This document defines the official development roadmap and current milestone completion status for CareerLens (v1.1 Roadmap).

---

## 1. Milestone Overview

CareerLens development is organized into three major milestone horizons:

1. **30% Foundation Milestone (Phases 1–10)** — **COMPLETE**
   - Repository scaffolding, configuration, and environment hygiene
   - FastAPI backend core, async database infrastructure, and pgvector extension
   - Core relational data models (User, Candidate Profile, Opportunity, and Tracking models)
   - User authentication and JWT access token handling
   - Modern React + TypeScript + Vite frontend scaffold with application shell
   - Security hardening (headers, CORS, log redaction, error masking, secret scanning)
   - Reusable testing foundation (centralized pytest, test DB safety guard, deterministic factories, frontend test utilities)
   - Foundation milestone audit, quality gate verification, and checkpoint

2. **60% Core Intelligence Milestone (Phases 11–18)** — **COMPLETE**
   - Phase 11: Resume parsing and information extraction pipeline
   - Phase 12: Candidate profile API and resume synchronization
   - Phase 13: Candidate profile frontend
   - Phase 14: Opportunity ingestion and normalization foundation
   - Phase 15: Opportunity discovery and exploration
   - Phase 16: Local embedding foundation (`all-MiniLM-L6-v2`)
   - Phase 17: Semantic retrieval and vector search
   - Phase 18: Recommendations frontend (semantic opportunity recommendations)

3. **100% Production & Delivery Milestone (Phases 19–25)** — **COMPLETE**
   - Phase 19: Hybrid matching engine and eligibility evaluation backend — **COMPLETE**
   - Phase 20: Opportunity exploration and recommendation frontend — **COMPLETE**
   - Phase 21: Application tracking and status transition frontend — **COMPLETE**
   - Phase 22: End-to-end integration and user acceptance testing — **COMPLETE**
   - Phase 23: Performance optimization, caching, and database tuning — **COMPLETE**
   - Phase 24: Deployment configuration, Docker containerization, and CI/CD — **COMPLETE** *(CI pipeline verified with 100% passing tests on commit `9dbe0c9`)*
   - Phase 25: Final academic project defense documentation and handover — **COMPLETE**

4. **Horizon 4: Autonomous Sourcing & Form Automation Milestone (Phases 26–27)** — **SCHEDULED (MANDATORY)**
   - Phase 26: Multi-platform opportunity collection and resilient web scraping (jobs, internships, hackathons, coding contests) — **NEXT MANDATORY CORE REQUIREMENT**
   - Phase 27: Automated external application form filling and user-confirmed submission workflow — **MANDATORY CORE REQUIREMENT**

---

## 2. Phase Status Matrix

| Phase | Phase Name | Status | Verified Checkpoint / Commit |
|---|---|---|---|
| **Phase 1** | Repository Setup & Project Scaffold | **COMPLETE** | `98f050c` |
| **Phase 2** | Backend Scaffold & FastAPI | **COMPLETE** | `4ab753b` |
| **Phase 3** | PostgreSQL + pgvector Foundation | **COMPLETE** | `eb3c408` |
| **Phase 4** | Core Candidate Data Models | **COMPLETE** | `7d4988d` |
| **Phase 5** | Authentication Module | **COMPLETE** | `da41d09` |
| **Phase 6** | Opportunity & Tracking Models | **COMPLETE** | `250e3d4` |
| **Phase 7** | Frontend Scaffold | **COMPLETE** | `0501a09` |
| **Phase 8** | Security & Development Tooling Hardening | **COMPLETE** | `b7dc1b7` |
| **Phase 9** | Testing Foundation | **COMPLETE** | `8d46829` |
| **Phase 10** | 30% Foundation Milestone Verification & Checkpoint | **COMPLETE** | `7adc7d5` |
| **Phase 11** | Resume Parsing & Extraction Pipeline | **COMPLETE** | `79f8091` |
| **Phase 12** | Candidate Profile API & Resume Synchronization | **COMPLETE** | `0049241` |
| **Phase 13** | Candidate Profile Frontend | **COMPLETE** | `6713079` |
| **Phase 14** | Opportunity Ingestion & Normalization Foundation | **COMPLETE** | `3de7e5d` |
| **Phase 15** | Opportunity Discovery & Exploration | **COMPLETE** | `65ca3d0` |
| **Phase 16** | Local Embedding Foundation (`all-MiniLM-L6-v2`) | **COMPLETE** | `ca44193` |
| **Phase 17** | Semantic Retrieval & Vector Search | **COMPLETE** | `c02b070` |
| **Phase 18** | Recommendations Frontend (Semantic Opportunity Recommendations) | **COMPLETE** | `3e35141` |
| **Phase 19** | Hybrid Matching Engine & Eligibility Evaluation Backend | **COMPLETE** | `44ed185` |
| **Phase 20** | Opportunity Exploration & Recommendation Frontend | **COMPLETE** | `2bb8cc6` |
| **Phase 21** | Application Tracking & Status Transition Frontend | **COMPLETE** | `a058bfc` |
| **Phase 22** | End-to-End Integration & User Acceptance Testing | **COMPLETE** | `436165e` |
| **Phase 23** | Performance Optimization, Caching & Database Tuning | **COMPLETE** | `2c25293` |
| **Phase 24** | Deployment Configuration, Docker Containerization & CI/CD | **COMPLETE (CI Verified)** | `9dbe0c9` |
| **Phase 25** | Final Academic Project Defense Documentation & Handover | **COMPLETE** | Verified Artifacts |
| **Phase 26** | Multi-Platform Opportunity Collection & Resilient Web Scraping | **IN PROGRESS** *(Phase 26.1 Audit Complete)* | [`docs/phase_26_architecture_plan.md`](file:///e:/CAREERLENS/docs/phase_26_architecture_plan.md) |
| **Phase 27** | Automated External Application Form Filling & User Confirmation | **SCHEDULED** *(Mandatory)* | Post-Phase 26 |

---

## 3. Explicit Boundaries — 30% Foundation Milestone

The 30% Foundation Milestone represents the verified structural, relational, architectural, and security foundation. It does **not** implement feature-level business logic scheduled for later phases.

### Specifically Excluded Capabilities (Deferred to Phase 11+):
- **Resume Parsing & Extraction**: No PDF/DOCX parsing, no regex parser, no spaCy entity extraction.
- **AI/ML & Embeddings**: No `sentence-transformers` models loaded, no embedding generation pipelines.
- **Recommendation Engine**: No hybrid scoring algorithm, no vector similarity querying API endpoints.
- **Skill-Gap & Explainability**: No automated skill-gap analysis or natural language explanation generation.
- **Job Ingestion & Scraping**: No external job board APIs (Adzuna, RemoteOK) or web scrapers.
- **LLM Integrations**: No active API calls to Gemini or OpenAI.
- **Interview Preparation**: No dynamic LLM prompt generation or interview quiz synthesis.
- **Browser Automation / E2E**: No Playwright/Cypress end-to-end browser test suites.

---

## 4. Phase 24 Deployment Verification Audit & Core Requirements Status

### A. Deployment Verification & CI Failure Resolution
- **Implementation Complete (`15e7c04`)**:
  - `backend/Dockerfile`: Multi-stage build with non-root user (`careerlens`, UID 10001), offline pre-cached MiniLM embeddings, and container healthcheck.
  - `frontend/Dockerfile`: Multi-stage build with Node 20 build and Nginx 1.27 Alpine runtime with healthcheck.
  - `docker-compose.yml` & `compose.yaml`: Coordinated multi-container stack (`db`, `migration`, `backend`, `frontend`) with network isolation, healthcheck dependencies, and controlled one-off migration execution.
  - `frontend/nginx.conf`: Static SPA serving, reverse proxy for `/api/` and docs, security headers, and gzip compression.
  - Production security validation: Startup checks enforce `DEBUG=false`, `JWT_SECRET_KEY` length >= 32 characters, non-placeholder database credentials, and reject wildcard CORS origins.
- **CI Failure Diagnosis & Verified Fix**:
  - **Identified Failure**: In GitHub Actions workflow runs `40087898942` and `40167750975`, `backend-ci` failed at `Execute Pytest Suite` on `tests/test_database.py::test_careerlens_user_least_privilege` (`AssertionError: Least privilege violated: CREATEDB must be False`, `assert True is False`).
  - **Root Cause**: The standard `pgvector/pgvector:pg16` Docker service container initializes `POSTGRES_USER: careerlens_user` as the cluster's bootstrap superuser (`SUPERUSER`, `CREATEDB`). In PostgreSQL, a bootstrap user cannot revoke its own `SUPERUSER` attribute (`DETAIL: The bootstrap user must have the SUPERUSER attribute`).
  - **Resolution Applied**:
    1. Reconfigured `.github/workflows/ci.yml` `postgres` service container to use standard bootstrap user `postgres` (`POSTGRES_USER: postgres`).
    2. Updated initialization step to connect as `postgres`, initialize pgvector extension, and create an isolated application role `careerlens_user` with `NOCREATEDB NOSUPERUSER NOCREATEROLE`, transferring database and schema ownership to `careerlens_user`.
  - **Verified Result**: Remote GitHub Actions workflow run `40174988958` on commit `9dbe0c9` completed with **`success`** across all three jobs:
    - `Backend Lint, Security & Tests`: **SUCCESS** (All 348 pytest tests passing including least-privilege role assertions)
    - `Frontend Lint, Type-Check, Tests & Build`: **SUCCESS**
    - `Docker Build & Compose Config Validation`: **SUCCESS**
- **Runtime Deployment Verification (Host Limitation)**:
  - **Host Environment**: Docker engine is not available on the current Windows development host (`docker: command not found`). Runtime container boot and live Nginx proxy testing cannot be verified locally on the host; container builds and Compose validation are verified in CI.

### B. PostgreSQL Deployment Version Compatibility
- **Supported Deployment Target**: PostgreSQL 16 LTS via `pgvector/pgvector:pg16` in Docker Compose and CI configurations.
- **Development Host Version**: PostgreSQL 18.x locally.
- **Compatibility**: Verified schema definitions, pgvector vector operations, and Alembic migrations execute cleanly across both PostgreSQL 16 and 18 without syntax or dialect incompatibilities.

### C. In-Memory Caching & Single-Worker Deployment Assumption
- `backend/app/core/cache.py` implements an in-process, asynchronous LRU cache with monotonic TTL.
- **Single-Worker Requirement**: Cache state is local to each Python process. The deployment assumes a single Uvicorn worker per container. Multi-worker scaling or clustered replicas require migrating to a distributed cache store (Redis/KeyDB) to ensure instantaneous cross-worker cache invalidation.

### D. Automated External Application Form Filling Status
- **Core Requirement Explicit Status**: Automated external application form filling (e.g., browser extensions, automated ATS form DOM autofill, or external web submission bots) is **NOT IMPLEMENTED** in the current Phase 1–24 repository.
- **Implemented Scope**: The repository implements internal opportunity discovery, semantic recommendations, hybrid eligibility matching, and internal candidate application tracking lifecycle (saved -> applied -> interviewing -> offered -> rejected/withdrawn) with audit logging.
- **Mandatory Roadmap Scheduling**: Because automated external application form filling is a mandatory core requirement of CareerLens, it is formally scheduled as **Phase 27** in Horizon 4.

### E. Phase 25: Final Academic Project Defense Documentation & Handover — COMPLETE
- **Objective Achieved**: Consolidated the complete Phase 1–24 implementation into defense-ready architectural documentation, operational manuals, academic defense dossier, and transparent evaluation metrics reports.
- **Completed Artifacts**:
  1. [`docs/architecture.md`](file:///e:/CAREERLENS/docs/architecture.md): Complete system architecture specification covering data models, vector search, hybrid matching formula, security boundaries, and container topology.
  2. [`docs/api_catalog.md`](file:///e:/CAREERLENS/docs/api_catalog.md): Complete API catalog documenting all 34 REST endpoints, request/response schemas, error codes, and ownership constraints.
  3. [`docs/operations_handover.md`](file:///e:/CAREERLENS/docs/operations_handover.md): Operations and engineering handover manual detailing Windows/Docker setup, least-privilege PostgreSQL configuration, database backup/restore, and deployment troubleshooting.
  4. [`docs/academic_defense.md`](file:///e:/CAREERLENS/docs/academic_defense.md): Academic defense dossier including slide-by-slide defense presentation outline, demonstration script with recovery steps, and authoritative references.
  5. [`docs/evaluation_metrics.md`](file:///e:/CAREERLENS/docs/evaluation_metrics.md): Transparent evaluation metrics report distinguishing verified test counts (348 backend + 113 frontend) from unmeasured empirical IR metrics with a reproducible benchmark protocol.
- **Verification Gates**: 461 automated tests passing (348 backend + 113 frontend), clean Ruff and Bandit security scans, zero type errors.

### F. Mandatory Horizon 4 Core Requirements Architecture & Acceptance Criteria (Next Milestone)

#### Phase 26: Multi-Platform Opportunity Collection & Resilient Web Scraping
- **Core Requirement**: CareerLens must automatically aggregate opportunities across jobs, internships, hackathons, and coding contests from multiple heterogeneous platforms.
- **Sub-Phase Status**:
  - **Phase 26.1: Multi-Platform Audit & Architecture Plan — COMPLETE**: Documented in [`docs/phase_26_architecture_plan.md`](file:///e:/CAREERLENS/docs/phase_26_architecture_plan.md). Feasibility matrix across 12 platforms, robots.txt compliance, schema evolution design, and zero unapproved scraping.
  - **Phase 26.2: Database Migration & Ingestion Foundation — COMPLETE**:
    - Extended `OpportunityType` with `coding_contest`.
    - Extended `OpportunitySource` with platform sources: Remotive, Arbeitnow, Codeforces, Greenhouse, Lever, Adzuna, USAJOBS, Remote OK, Devpost.
    - Added event & synchronization fields to `opportunities`: `event_start_time`, `event_end_time`, `registration_deadline`, `duration_seconds`, `prize_summary`, `first_seen_at`, `last_seen_at`, `external_metadata` (JSONB).
    - Created `connector_sync_status` table for operational telemetry and recovery state without secrets.
    - Alembic migration `a2b3c4d5e6f7_add_multi_platform_and_contest_foundation.py` tested for forward upgrade, backward compatibility with existing records, and safe downgrade.
    - Total verified test suite: 471 tests passing (358 backend + 113 frontend), clean Ruff and Bandit scans.
  - **Phase 26.3: Wave 1 Connectors (Zero-Credential Public APIs) — SCHEDULED NEXT**: Remotive, Arbeitnow, Codeforces, and Greenhouse public job boards.
- **Architectural Specifications & Acceptance Criteria**:
  1. **Dual Ingestion Engine**:
     - Official APIs & Authorized Feeds: Connector modules for structured platforms using authenticated API keys/tokens managed securely via environment variables.
     - Permitted Web Scraping: Source-specific scrapers using BeautifulSoup/Playwright adhering to platform robots.txt, terms, and rate limits.
  2. **Multi-Category Coverage**: Connectors for employment (jobs/internships) and competitive learning (hackathons, competitive programming contests).
  3. **Robust Data Pipeline**: Schema normalization into standard `Opportunity` models, validation, deduplication via `(source, source_id)` and fuzzy title/company matching, expiration handling, cursor pagination, exponential backoff retries, and scheduled background refresh.
  4. **Source Transparency**: Explicit source attribution, connector-isolated test suites, and graceful degradation/reporting for credential-gated or rate-limited sources.

#### Phase 27: Automated External Application Form Filling & User-Confirmed Submission
- **Core Requirement**: CareerLens must assist candidates by automatically filling supported external job application forms using verified profile and resume data, subject to strict user review and explicit confirmation.
- **Architectural Specifications & Acceptance Criteria**:
  1. **Autofill Engine**: Browser extension or automated browser agent (Playwright) capable of detecting standard ATS form fields (Workday, Greenhouse, Lever, Taleo) and mapping candidate profile/resume data (contact, education, skills, experience, portfolio links).
  2. **User In-the-Loop Review**: Compulsory interactive preview modal displaying populated fields for candidate verification, modification, and explicit manual confirmation prior to form submission.
  3. **Verified Submission & Outcome Tracking**: Automated post-submission receipt detection, verification of submission success, and seamless status transition in the internal `applications` tracking system from `saved` to `applied` with audit timestamp and platform reference.


