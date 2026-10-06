# CareerLens

**Intelligent Job Recommendation and Career Intelligence System**

> Final-Year B.Tech Computer Science Engineering Project

---

## Overview

CareerLens is an intelligent job recommendation system that helps candidates:

- Discover relevant job opportunities through semantic AI matching
- Understand **why** each opportunity is relevant (Explainable AI)
- Identify skill gaps between their profile and each opportunity
- Track their job applications through the full lifecycle
- Prepare for interviews with AI-assisted preparation materials

The system uses a **hybrid matching engine** combining semantic vector similarity with deterministic eligibility evaluation. Every recommendation is evidence-backed and fully traceable to the candidate's actual profile and the job's actual requirements.

---

## Project Status

> 🏆 **Phases 1–12 Completed**
>
> All foundational infrastructure, data models, authentication, frontend scaffold, security hardening, testing foundations, resume extraction pipeline, and candidate profile API with resume synchronization are verified and complete.
> Scheduled Next: **Phase 13 — Candidate Profile Frontend** (NOT started).

---

## Phase Status Summary

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Repository Setup & Project Scaffold | ✅ **COMPLETE** |
| **Phase 2** | Backend Scaffold & FastAPI Health Core | ✅ **COMPLETE** |
| **Phase 3** | PostgreSQL 18.6 + pgvector 0.8.6 Foundation | ✅ **COMPLETE** |
| **Phase 4** | Core Candidate & Identity Data Models | ✅ **COMPLETE** |
| **Phase 5** | Authentication Module & JWT Infrastructure | ✅ **COMPLETE** |
| **Phase 6** | Opportunity & Application Tracking Models | ✅ **COMPLETE** |
| **Phase 7** | React 19 + TypeScript + Vite Frontend Scaffold | ✅ **COMPLETE** |
| **Phase 8** | Security & Tooling Hardening (Bandit, Oxlint) | ✅ **COMPLETE** |
| **Phase 9** | Testing Foundation (Fixtures, Factories, Safety) | ✅ **COMPLETE** |
| **Phase 10** | 30% Foundation Milestone Verification & Checkpoint | ✅ **COMPLETE** |
| **Phase 11** | Resume Parsing & Extraction Pipeline | ✅ **COMPLETE** |
| **Phase 12** | Candidate Profile API & Resume Synchronization | ✅ **COMPLETE** |
| **Phase 13** | Candidate Profile Frontend | ⏳ **SCHEDULED NEXT** |

---

## Current Architecture & Scope Boundaries

CareerLens is implemented as a **Modular Monolith** (see [`docs/architecture.md`](docs/architecture.md) and [`docs/roadmap.md`](docs/roadmap.md)):

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (asyncio), Alembic (`c7e23d4f5a6b`)
- **Database**: PostgreSQL 18.6 with pgvector 0.8.6 (`careerlens_db`, `careerlens_test`)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide React
- **Testing**: Pytest (94 tests), Vitest (23 tests), Testing Library, deterministic factories
- **Security**: Ruff, Bandit, Oxlint, npm audit, response headers, log redaction, error masking

> [!NOTE]
> **Foundation Boundary Notice**: The current milestone covers structural foundation only. Resume parsing, vector embedding pipelines, hybrid recommendation engines, job scrapers, and external LLM APIs belong to subsequent phases (Phases 11+) and are not yet implemented.

### Prerequisites

- Python 3.12
- Node.js v22+
- PostgreSQL 18.6 (with pgvector extension)
- Git

### Quick Quality Verification

Run the full security, linting, and testing gate across backend and frontend:

```powershell
python scripts/check_quality.py
```

For detailed individual commands, see [`docs/development.md`](docs/development.md).

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```bash
copy .env.example .env
```

> ⚠️ **Never commit `.env` to version control.** It is listed in `.gitignore`.

See `.env.example` for all required and optional variables.

---

## Documentation

| Document | Description |
|---|---|
| `docs/architecture.md` | System architecture and module design |
| `docs/database.md` | Entity-relationship design and migration guide |
| `docs/api.md` | API endpoint reference |
| `docs/development.md` | Local development setup guide |
| `docs/security_checklist.md` | Pre-commit and pre-push security checklist |
| `docs/resume_pipeline.md` | Phase 11 Resume ingestion & deterministic extraction pipeline |
| `docs/candidate_profile.md` | Phase 12 Candidate Profile API & resume synchronization specification |

---

## License

MIT License — see `LICENSE` for details.

---

*CareerLens — Final-Year B.Tech CSE Project*
