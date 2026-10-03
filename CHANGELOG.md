# Changelog

All notable changes to CareerLens will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Phase 2: Python virtual environment and FastAPI backend scaffold
- Phase 3: PostgreSQL database configuration and pgvector setup
- Phase 4: Core data models and Alembic migrations
- Phase 5: Authentication module (JWT, bcrypt)
- Phase 6: Opportunity and tracking data models
- Phase 7: React + Vite frontend scaffold
- Phase 8: Security and dev tooling configuration
- Phase 9: Testing foundation
- Phase 10: 30% milestone documentation and commit

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
