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

Run all unit, integration, and security regression tests:
```powershell
cd backend
pytest
```

Run a specific test module:
```powershell
pytest tests/test_security_hardening.py
```

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
