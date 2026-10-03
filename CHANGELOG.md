# Changelog

All notable changes to CareerLens will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Phase 3: PostgreSQL database configuration and pgvector setup
- Phase 4: Core data models and Alembic migrations
- Phase 5: Authentication module (JWT, bcrypt)
- Phase 6: Opportunity and tracking data models
- Phase 7: React + Vite frontend scaffold
- Phase 8: Security and dev tooling configuration
- Phase 9: Testing foundation
- Phase 10: 30% milestone documentation and commit

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
