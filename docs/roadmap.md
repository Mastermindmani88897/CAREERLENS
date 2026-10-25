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

3. **100% Production & Delivery Milestone (Phases 19–25)** — **IN PROGRESS**
   - Phase 19: Hybrid matching engine and eligibility evaluation backend — **COMPLETE**
   - Phase 20: Opportunity exploration and recommendation frontend — **COMPLETE**
   - Phase 21: Application tracking and status transition frontend — **COMPLETE**
   - Phase 22: End-to-end integration and user acceptance testing — **COMPLETE**
   - Phase 23: Performance optimization, caching, and database tuning — **COMPLETE**
   - Phase 24: Deployment configuration, Docker containerization, and CI/CD — **IMPLEMENTATION COMPLETE** *(Runtime deployment verification pending host Docker availability / CI test resolution)*
   - Phase 25: Final academic project defense documentation and handover ← **NEXT**

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
| **Phase 24** | Deployment Configuration, Docker Containerization & CI/CD | **IMPLEMENTATION COMPLETE** *(Runtime Verification Pending)* | `15e7c04` |
| **Phase 25** | Final Academic Project Defense Documentation & Handover | **NEXT** | Scheduled |

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

### A. Deployment Verification vs. Implementation Status
- **Implementation Complete (`15e7c04`)**:
  - `backend/Dockerfile`: Multi-stage build with non-root user (`careerlens`, UID 10001), offline pre-cached MiniLM embeddings, and container healthcheck.
  - `frontend/Dockerfile`: Multi-stage build with Node 20 build and Nginx 1.27 Alpine runtime with healthcheck.
  - `docker-compose.yml` & `compose.yaml`: Coordinated multi-container stack (`db`, `migration`, `backend`, `frontend`) with network isolation, healthcheck dependencies, and controlled one-off migration execution.
  - `frontend/nginx.conf`: Static SPA serving, reverse proxy for `/api/` and docs, security headers, and gzip compression.
  - Production security validation: Startup checks enforce `DEBUG=false`, `JWT_SECRET_KEY` length >= 32 characters, non-placeholder database credentials, and reject wildcard CORS origins.
- **Runtime Deployment Verification (Limitation Unresolved)**:
  - **Host Environment**: Docker engine is not available on the current Windows development host (`docker: command not found`). Runtime container boot, pgvector initialization in container, and live Nginx proxy testing cannot be verified locally.
  - **Remote CI Pipeline**: GitHub Actions workflow run `40087898942` on commit `da7a024` executed:
    - `Frontend Lint, Type-Check, Tests & Build`: **SUCCESS**
    - `Docker Build & Compose Config Validation`: **SUCCESS**
    - `Backend Lint, Security & Tests`: **FAILURE** (step `Execute Pytest Suite` failed in CI container environment, despite all 348 pytest tests passing locally on the host).

### B. PostgreSQL Deployment Version Compatibility
- **Supported Deployment Target**: PostgreSQL 16 LTS via `pgvector/pgvector:pg16` in Docker Compose and CI configurations.
- **Development Host Version**: PostgreSQL 18.x locally.
- **Compatibility**: Verified schema definitions, pgvector vector operations, and Alembic migrations execute cleanly across both PostgreSQL 16 and 18 without syntax or dialect incompatibilities.

### C. In-Memory Caching & Single-Worker Deployment Assumption
- `backend/app/core/cache.py` implements an in-process, asynchronous LRU cache with monotonic TTL.
- **Single-Worker Requirement**: Cache state is local to each Python process. The deployment assumes a single Uvicorn worker per container. Multi-worker scaling or clustered replicas require migrating to a distributed cache store (Redis/KeyDB) to ensure instantaneous cross-worker cache invalidation.

### D. Automated External Application Form Filling Status
- **Core Requirement Explicit Status**: Automated external application form filling (e.g., browser extensions, automated ATS form DOM autofill, or external web submission bots) is **NOT IMPLEMENTED** in this repository.
- **Implemented Scope**: The repository implements internal opportunity discovery, semantic recommendations, hybrid eligibility matching, and internal candidate application tracking lifecycle (saved -> applied -> interviewing -> offered -> rejected/withdrawn) with audit logging. External autofill automation remains an unfulfilled requirement and is not verified.

