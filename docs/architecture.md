# CareerLens — System Architecture (30% Foundation Milestone)

This document provides an accurate, evidence-backed description of the current architecture of CareerLens as established at the completion of the 30% Foundation Milestone.

---

## 1. Architectural Pattern: Modular Monolith

CareerLens is architected as a **Modular Monolith** designed for high cohesion, strict separation of concerns, and clear internal boundaries:

```
[ Client / Browser ]
        │
        ▼ (HTTP / JSON + Bearer JWT)
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Core                     │
│                                                             │
│  ┌───────────────────────┐       ┌───────────────────────┐  │
│  │ Security Middleware   │       │  Centralized Config   │  │
│  │ - Security Headers    │       │  - Pydantic Settings  │  │
│  │ - CORS Restrictions   │       │  - Env Separation     │  │
│  │ - Error Masking       │       │  - Test DB Routing    │  │
│  │ - Log Redaction       │       └───────────────────────┘  │
│  └───────────┬───────────┘                                  │
│              ▼                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   API v1 Routers                      │  │
│  │   /health        /auth/register    /auth/login        │  │
│  │   /health/db     /auth/me                             │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                Services & Dependencies                │  │
│  │   - AuthService (bcrypt hashing, JWT issuing)         │  │
│  │   - Dependency Injection (get_current_user, get_db)   │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │             SQLAlchemy 2.x ORM Domain                 │  │
│  │   - User & Candidate Profile Sub-Entities             │  │
│  │   - Opportunity & Tracking Sub-Entities               │  │
│  │   - pgvector Vector(384) Integration                  │  │
│  └───────────────────────┬───────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           ▼ (AsyncPG Driver)
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL 18.6 DB                       │
│  - pgvector 0.8.6 Extension                                 │
│  - 15 Relational Tables with ON DELETE CASCADE              │
│  - Multi-Column Indexes & Partial Constraints               │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack Breakdown

| Subsystem | Active Technology | Role & Status |
|---|---|---|
| **Runtime** | Python 3.12.4 | Backend runtime environment |
| **API Framework** | FastAPI + Uvicorn | Async ASGI web framework and routing |
| **ORM / Data Access** | SQLAlchemy 2.0 (asyncio) + AsyncPG | Async database operations, connection pooling |
| **Database Migrations** | Alembic | Version-controlled DDL migrations (`c7e23d4f5a6b`) |
| **Relational Database** | PostgreSQL 18.6 | Primary ACID transactional storage |
| **Vector Extension** | pgvector 0.8.6 | Native vector storage (`VECTOR(384)`) |
| **Frontend Framework** | React 19 + TypeScript | Declarative client-side user interface |
| **Build & Dev Tooling** | Vite | Lightning-fast ESM bundler and HMR server |
| **Frontend Styling** | Tailwind CSS v4 | Utility-first CSS styling engine |
| **Backend Testing** | Pytest + pytest-asyncio | Unit, isolation, factory, and integration test suite |
| **Frontend Testing** | Vitest + Testing Library | Component, router, and client security test suite |
| **Code Linters** | Ruff (backend) + Oxlint (frontend) | Static code analysis and style conformance |
| **Security Scanning** | Bandit + npm audit + Quality Gate | Static AST security analysis and secret checking |

---

## 3. Database Layer Foundation

The database architecture consists of two isolated PostgreSQL instances:
- **`careerlens_db`**: Application development database
- **`careerlens_test`**: Isolated testing database automatically targeted during test runs

### Relational Schema (15 Tables):
1. `users`: Authentication identities (email, hashed password, active status)
2. `candidate_profiles`: Candidate preferences, compensation, and profile metadata
3. `resumes`: Resume document storage and structured extraction payloads
4. `skills`: Candidate skills with taxonomy categories and proficiency ratings
5. `educations`: Academic degree, institution, and field of study history
6. `experiences`: Professional employment history and work mode records
7. `projects`: Academic and personal software engineering projects
8. `certifications`: Professional licenses and credentials
9. `opportunities`: Job postings with compensation, requirements, and `VECTOR(384)` embedding column
10. `opportunity_skills`: Normalized skill requirements with `is_required` flags
11. `matches`: Candidate-to-opportunity scoring records with JSON breakdowns
12. `applications`: Application lifecycle tracking state machine
13. `application_status_history`: Immutable status transition audit log
14. `interview_prep`: Structured interview preparation packages
15. `alembic_version`: Migration version pointer

---

## 4. Security Architecture Baseline

1. **Secret Isolation**:
   - Zero credentials or tokens tracked in version control.
   - Dynamic environment loading via Pydantic `Settings`.
   - Automated secret scanners running at quality gates.
2. **Defensive Headers & CORS**:
   - Standard security headers automatically injected on all HTTP responses.
   - Strict origin whitelisting with wildcard `*` rejected in production.
3. **Log Sanitization & Error Masking**:
   - `SensitiveDataFilter` strips passwords, bearer tokens, and connection strings from logs.
   - Unhandled exceptions are masked server-side to generic HTTP 500 responses.

---

## 5. Testing Foundation Architecture

- **Safety Guard**: `enforce_test_database_safety` autouse fixture aborts if non-test DB is targeted.
- **Transaction Isolation**: `db_session` fixture uses nested rollbacks to eliminate test crosstalk.
- **Deterministic Factories**: Typed `BaseFactory[T]` builders for all 14 entities.
- **Frontend Utilities**: `renderWithRouter` for isolated page and component testing.
