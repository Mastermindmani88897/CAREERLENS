# Changelog

All notable changes to CareerLens will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Phase 5: Authentication module (JWT, bcrypt)
- Phase 6: Opportunity and tracking data models
- Phase 7: React + Vite frontend scaffold
- Phase 8: Security and dev tooling configuration
- Phase 9: Testing foundation
- Phase 10: 30% milestone documentation and commit

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
