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

2. **60% Core Intelligence Milestone (Phases 11–18)** — **NOT STARTED**
   - Phase 11: Resume parsing and information extraction pipeline
   - Phase 12: Skill taxonomy normalization and extraction
   - Phase 13: Local vector embedding pipeline (`all-MiniLM-L6-v2`) and pgvector index optimization
   - Phase 14: Job ingestion pipelines (APIs and synthetic benchmarks)
   - Phase 15: Hybrid matching engine (semantic vector similarity + deterministic eligibility)
   - Phase 16: Explainable AI recommendation engine and skill-gap analyzer
   - Phase 17: Application tracking API workflows
   - Phase 18: AI-assisted interview preparation generator

3. **100% Production & Delivery Milestone (Phases 19–25)** — **NOT STARTED**
   - Phase 19: Candidate profile and resume management frontend
   - Phase 20: Opportunity exploration and recommendation frontend
   - Phase 21: Application tracking and status transition frontend
   - Phase 22: End-to-end integration and user acceptance testing
   - Phase 23: Performance optimization, caching, and database tuning
   - Phase 24: Deployment configuration, Docker containerization, and CI/CD
   - Phase 25: Final academic project defense documentation and handover

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
| **Phase 10** | 30% Foundation Milestone Verification & Checkpoint | **COMPLETE** | Pending commit |
| **Phase 11** | Resume Parsing & Extraction Pipeline | **NOT STARTED** | Scheduled Next |
| **Phase 12+** | Subsequent Core Intelligence Phases | **NOT STARTED** | Awaiting authorization |

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
