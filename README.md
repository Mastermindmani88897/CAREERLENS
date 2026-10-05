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

> 🔒 **Phase 8 Completed** — Security & Development Tooling Hardened

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Ruff, Bandit, Pytest |
| Database | PostgreSQL 18.6, pgvector |
| AI / ML | sentence-transformers (`all-MiniLM-L6-v2`), pgvector HNSW |
| LLM | Configurable (Gemini / OpenAI / None — fallback templates) |
| Frontend | React 19, Vite, Tailwind CSS v4, Lucide React, Oxlint, Vitest |

---

## Repository Structure

```
CAREERLENS/
├── backend/          # FastAPI application, models, security core
├── frontend/         # React application, UI components, tests
├── data/
│   ├── sample/       # Development synthetic dataset (not production data)
│   └── uploads/      # Resume file uploads (gitignored)
├── docs/             # Architecture, development, and security documentation
├── tests/            # Project-level test utilities
├── scripts/          # CLI scripts (quality check, db setup, etc.)
├── .env.example      # Environment variable template (placeholders only)
└── README.md
```

---

## Setup & Development

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

---

## License

MIT License — see `LICENSE` for details.

---

*CareerLens — Final-Year B.Tech CSE Project*
