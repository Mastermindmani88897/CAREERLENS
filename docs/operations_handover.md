# CareerLens — Operations & Engineering Handover Manual (v1.1)

This manual provides authoritative, repository-grounded operational guidance for deploying, maintaining, debugging, and developing CareerLens across local Windows development environments and production Docker deployments.

---

## 1. System Requirements & Prerequisites

### 1.1. Host Development Environment (Windows 10/11)
- **Python**: Version 3.12.x (verified on Python 3.12.4 64-bit).
- **Node.js**: Version 20.x or 22.x LTS with `npm` 10+.
- **PostgreSQL**: PostgreSQL 16.x LTS or 18.x with `pgvector` extension installed (`vector.dll` / `vector.control`).
- **PowerShell**: Version 5.1+ or PowerShell 7.x.
- **Git**: Git 2.40+.

### 1.2. Production Deployment Environment (Docker)
- **Docker Engine**: Version 24.0+ with Docker Compose v2 (`compose.yaml`).
- **Linux Kernel**: 5.10+ (Ubuntu 22.04 LTS recommended).
- **Memory**: Minimum 4 GB RAM (8 GB recommended for local MiniLM embedding model execution).
- **Storage**: Minimum 10 GB free disk space (for PostgreSQL data volume and pre-cached PyTorch models).

---

## 2. Environment Variables & Secret Configuration

CareerLens strictly enforces secret isolation. Configuration is managed via `.env` files loaded dynamically by Pydantic `Settings`.

> [!CAUTION]
> Never commit actual passwords, API keys, or JWT secret keys to version control. The templates below contain placeholders only.

### 2.1. Backend Configuration (`backend/.env`)

```ini
# --- Application Environment ---
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# --- Database & pgvector Connection ---
# Local development format: postgresql+asyncpg://<db_user>:<password>@<host>:<port>/<database>
DATABASE_URL=postgresql+asyncpg://careerlens_user:YOUR_LOCAL_DB_PASSWORD@localhost:5432/careerlens_db
TEST_DATABASE_URL=postgresql+asyncpg://careerlens_user:YOUR_LOCAL_DB_PASSWORD@localhost:5432/careerlens_test

# --- Authentication & Cryptography ---
# Generate a cryptographically secure 64-character secret: python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET_KEY=YOUR_CRYPTOGRAPHICALLY_SECURE_JWT_SECRET_KEY_MIN_32_CHARS
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# --- CORS Origin Whitelist ---
# Comma-separated list of allowed origins. Wildcards (*) are strictly rejected in production.
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173

# --- Storage & Model Providers ---
RESUME_UPLOAD_DIR=data/uploads/resumes
EMBEDDING_PROVIDER=local
LLM_PROVIDER=none
GEMINI_API_KEY=
OPENAI_API_KEY=
```

### 2.2. Production Docker Compose Configuration (`.env`)

```ini
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO

# PostgreSQL Configuration
POSTGRES_USER=careerlens_user
POSTGRES_PASSWORD=YOUR_STRONG_POSTGRES_PASSWORD_HERE
POSTGRES_DB=careerlens_db
POSTGRES_PORT=5432
POSTGRES_BIND_IP=127.0.0.1

# JWT & Security
JWT_SECRET_KEY=YOUR_PRODUCTION_JWT_SECRET_KEY_MINIMUM_32_CHARACTERS_LONG
CORS_ORIGINS=http://localhost,http://127.0.0.1,https://yourdomain.com

# Service Ports
BACKEND_PORT=8000
BACKEND_BIND_IP=127.0.0.1
FRONTEND_PORT=80
```

---

## 3. Local Development Setup (Step-by-Step)

### Step 3.1: Repository Clone & Structure
```powershell
git clone https://github.com/Mastermindmani88897/CAREERLENS.git E:\CAREERLENS
cd E:\CAREERLENS
```

### Step 3.2: Backend Virtual Environment & Dependencies
```powershell
cd E:\CAREERLENS\backend
# Create isolated Python 3.12 virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.3: PostgreSQL Database & Least-Privilege Role Setup
The project provides an automated, idempotent setup script (`scripts/setup_db.py`) that initializes the development and test databases, creates the least-privilege `careerlens_user` application role, enables `pgvector`, and generates `.env` with a secure randomized password:

```powershell
cd E:\CAREERLENS
# Set administrative password for bootstrap superuser 'postgres'
$env:PGPASSWORD="YOUR_POSTGRES_SUPERUSER_PASSWORD"

# Execute idempotent database setup
& "E:\CAREERLENS\backend\.venv\Scripts\python.exe" scripts/setup_db.py
```

#### Manual SQL Initialization (Alternative):
If performing setup manually via `psql`:
```sql
-- 1. Create application databases
CREATE DATABASE careerlens_db;
CREATE DATABASE careerlens_test;

-- 2. Create least-privilege application role (NOCREATEDB, NOSUPERUSER, NOCREATEROLE)
CREATE ROLE careerlens_user WITH LOGIN PASSWORD 'YOUR_STRONG_PASSWORD' NOCREATEDB NOSUPERUSER NOCREATEROLE;

-- 3. Grant database ownership to allow Alembic migrations without cluster admin rights
ALTER DATABASE careerlens_db OWNER TO careerlens_user;
ALTER DATABASE careerlens_test OWNER TO careerlens_user;

-- 4. Enable pgvector extension in both databases
\c careerlens_db
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO careerlens_user;

\c careerlens_test
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO careerlens_user;
```

### Step 3.4: Apply Alembic Migrations
```powershell
cd E:\CAREERLENS\backend
alembic upgrade head
```

### Step 3.5: Frontend Node Setup
```powershell
cd E:\CAREERLENS\frontend
npm ci
```

---

## 4. Starting the Application

### 4.1. Starting the Backend Development Server
```powershell
cd E:\CAREERLENS\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc UI: `http://127.0.0.1:8000/redoc`
- Direct Health Check: `http://127.0.0.1:8000/health`

### 4.2. Starting the Frontend Development Server
```powershell
cd E:\CAREERLENS\frontend
npm run dev
```
- Local SPA: `http://localhost:5173`

---

## 5. Quality Assurance & Testing Suite

Execute all quality gates locally before committing code:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Quality Gate Command Reference                    │
├─────────────────────┬──────────────────────────────────────────────────┤
│ Task                │ Command                                          │
├─────────────────────┼──────────────────────────────────────────────────┤
│ Backend Unit Tests  │ pytest -q                                        │
│ Database Tests      │ pytest -q tests/test_database.py                 │
│ Least-Privilege Test│ pytest -q tests/test_database.py::test_..._priv  │
│ Backend Lint        │ ruff check .                                     │
│ Backend Format Check│ ruff format --check .                            │
│ Bandit Security Scan│ bandit -r app alembic -ll                        │
│ Frontend Tests      │ npm test -- --run                                │
│ Frontend Lint       │ npm run lint                                     │
│ Frontend Type-Check │ npm run type-check                               │
│ Frontend Prod Build │ npm run build                                    │
└─────────────────────┴──────────────────────────────────────────────────┘
```

---

## 6. Production Docker Deployment

### 6.1. Build & Start Multi-Container Stack
```bash
# Validate compose configuration
docker compose config

# Build container images and start services in detached mode
docker compose up -d --build
```

### 6.2. Verify Container Health
```bash
docker compose ps
```
Expected output:
- `careerlens-db`: `Up (healthy)`
- `careerlens-migration`: `Exited (0)` (one-off migration execution)
- `careerlens-backend`: `Up (healthy)`
- `careerlens-frontend`: `Up (healthy)`

### 6.3. Container Shutdown
```bash
# Graceful stop
docker compose down

# Stop and purge volumes (Caution: removes database data)
docker compose down -v
```

---

## 7. Database Administration & Backup/Restore

### 7.1. Database Backup
```bash
# Export compressed binary dump of careerlens_db
docker exec -t careerlens-db pg_dump -U careerlens_user -F c -b -v -f /tmp/careerlens_db.dump careerlens_db
docker cp careerlens-db:/tmp/careerlens_db.dump ./backup_careerlens_$(date +%Y%m%d_%H%M%S).dump
```

### 7.2. Database Restore
```bash
# Restore from dump
docker cp ./backup_careerlens_20261025.dump careerlens-db:/tmp/restore.dump
docker exec -i careerlens-db pg_restore -U careerlens_user -d careerlens_db -v /tmp/restore.dump
```

---

## 8. Common Troubleshooting Procedures

### Issue 1: Database Least-Privilege Assertion Failure
- **Symptom**: `assert row["rolcreatedb"] is False` fails (`assert True is False`).
- **Cause**: Application user was created as the cluster's bootstrap superuser (`POSTGRES_USER`). In PostgreSQL, bootstrap users cannot be stripped of `SUPERUSER` or `CREATEDB`.
- **Resolution**:
  1. Initialize container with `POSTGRES_USER: postgres`.
  2. Create `careerlens_user` as a secondary role:
     ```sql
     CREATE ROLE careerlens_user WITH LOGIN NOCREATEDB NOSUPERUSER NOCREATEROLE;
     ALTER DATABASE careerlens_db OWNER TO careerlens_user;
     ```

### Issue 2: pgvector Extension Missing or Unregistered
- **Symptom**: `type "vector" does not exist` or `health/db` reports `vector unavailable`.
- **Cause**: Database created without pgvector extension loaded.
- **Resolution**:
  Connect as superuser `postgres` and run:
  ```sql
  \c careerlens_db
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

### Issue 3: Inactive Opportunity Application Rejection (HTTP 422)
- **Symptom**: Submitting an application returns `422 Unprocessable Content: Opportunity is inactive and cannot be applied to.`
- **Cause**: The application service strictly enforces that candidates cannot submit applications to inactive opportunities (`is_active=False`).
- **Resolution**: Target an active opportunity or update the opportunity's `is_active` status to `true`.

### Issue 4: Single-Worker Cache Invalidation Limitation
- **Symptom**: Changes made in one backend worker process are not immediately reflected in responses served by another worker.
- **Cause**: `AsyncCacheManager` is an in-process, asynchronous LRU memory cache local to each Python process.
- **Resolution**: Run a single Uvicorn worker per container (default). For horizontal multi-worker scaling, deploy Redis or KeyDB as an external distributed cache.
