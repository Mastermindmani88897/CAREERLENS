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
   - Phase 21: Application tracking and status transition frontend ← **NEXT**
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
| **Phase 22+** | Subsequent Phases | **NOT STARTED** | Scheduled |

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
