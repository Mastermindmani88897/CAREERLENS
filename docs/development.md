# CareerLens — Development & Tooling Guide

This document defines standardized commands for local development, linting, testing, and quality verification across the CareerLens backend and frontend.

---

## 1. Unified Quality Gate

Run all backend and frontend quality checks, secret leak scans, linters, and test suites in a single command:

```powershell
python scripts/check_quality.py
```

---

## 2. Backend Development (Python 3.12)

### Virtual Environment Activation

**Windows (PowerShell):**
```powershell
.\backend\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
source backend/.venv/bin/activate
```

### Running Backend Tests (Pytest)

Run all unit, integration, factory, and security regression tests:
```powershell
cd backend
pytest
```

Run with verbose test execution details:
```powershell
pytest -v
```

Run a specific test category or module:
```powershell
pytest tests/test_factories.py -v
pytest tests/test_isolation.py -v
pytest tests/test_integration_foundation.py -v
pytest tests/test_security_hardening.py -v
```

### Testing Foundation & Safety Architecture

1. **Test Database Safety Guard**:
   - Automated tests run strictly against `careerlens_test`.
   - `conftest.py` contains an autouse safety fixture (`enforce_test_database_safety`) that aborts execution if `careerlens_db` or a non-test database URL is configured.
   - `settings.effective_database_url` switches dynamically to `TEST_DATABASE_URL` when `ENVIRONMENT == "test"`.

2. **Database Isolation & Session Rollback**:
   - `db_session` fixture uses a dedicated async session wrapped in nested transaction rollbacks to prevent state leakage between tests.
   - Test data created during tests is rolled back automatically unless committed.

3. **Deterministic Test Data Factories (`backend/tests/factories`)**:
   - Built with generic typed `BaseFactory[T]` supporting in-memory `.build(**overrides)` and persistent `await .create(db_session, **overrides)`.
   - Available factories covering all 14 core & tracking models:
     - `UserFactory`
     - `CandidateProfileFactory`, `ResumeFactory`, `SkillFactory`, `EducationFactory`, `ExperienceFactory`, `ProjectFactory`, `CertificationFactory`
     - `OpportunityFactory`, `OpportunitySkillFactory`
     - `MatchFactory`, `ApplicationFactory`, `ApplicationStatusHistoryFactory`, `InterviewPrepFactory`

4. **Authentication Test Helpers (`backend/tests/helpers/auth.py`)**:
   - `create_test_user(db_session, ...)`: Creates persistent test user with hashed password.
   - `create_auth_token(user, ...)`: Generates valid JWT bearer token.
   - `get_auth_headers(token)`: Formats standard `{"Authorization": f"Bearer {token}"}` dictionary.
   - `login_test_user(client, email, password)`: Exercises the real `/api/v1/auth/login` endpoint.
   - Reusable fixtures: `authenticated_user`, `auth_headers`, `authenticated_client`.

5. **Async Integration Client**:
   - `async_client`: `httpx.AsyncClient` configured with ASGI transport over FastAPI `app`.

### Code Formatting & Linting (Ruff)

Check linting rules:
```powershell
cd backend
ruff check .
```

Check code formatting:
```powershell
cd backend
ruff format --check .
```

Apply automatic formatting:
```powershell
cd backend
ruff format .
```

### Static Security Analysis (Bandit)

Scan backend source and migrations for security vulnerabilities (medium/high severity threshold):
```powershell
cd backend
bandit -r app alembic scripts -ll
```

### FastAPI Development Server

Start the local API development server with auto-reload:
```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Base URL: `http://localhost:8000/api/v1`
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/api/v1/health`

---

## 3. Frontend Development (React + Vite + TypeScript)

### Dependency Installation

```powershell
cd frontend
npm install
```

### Development Server

Start Vite local development server:
```powershell
cd frontend
npm run dev
```
Accessible at: `http://localhost:5173`

### Production Bundle Build

Compile TypeScript and build the production bundle:
```powershell
cd frontend
npm run build
```

### Code Linting (Oxlint)

Run fast Rust-based linter across TypeScript and React components:
```powershell
cd frontend
npm run lint
```

### TypeScript Type-Checking

Validate TypeScript types without emitting bundle:
```powershell
cd frontend
npm run type-check
```

### Automated Testing (Vitest)

Execute Vitest component, routing, and security tests:
```powershell
cd frontend
npm test
```

### Shared Frontend Test Utilities (`frontend/src/test/test-utils.tsx`)

- `renderWithRouter(ui, { initialEntries = ['/'], routerOptions = {} })`: Wraps components and pages in a configured `MemoryRouter` for isolated routing and link navigation testing.
- `createMockFrontendUser(overrides)`: Deterministic user factory for frontend components.
- Direct re-exports of Testing Library utilities (`screen`, `waitFor`, `act`, `fireEvent`, `within`, `cleanup`, `userEvent`).

### Dependency Security Audit (npm audit)

Inspect frontend package tree for known security vulnerabilities:
```powershell
cd frontend
npm audit
```

---

## 4. Pre-Commit Configuration (Optional)

A lightweight `.pre-commit-config.yaml` is provided in the repository root. To enable automatic git pre-commit checks:

```powershell
pip install pre-commit
pre-commit install
```
