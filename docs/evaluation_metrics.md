# CareerLens — System Evaluation Metrics & Quality Report (v1.1)

This document provides a rigorous, transparent report of all verified system metrics, benchmark data, and quality gates across the CareerLens repository.

---

## 1. Automated Test Suite Metrics (Measured)

All automated tests have been executed on the repository codebase and independently verified in continuous integration.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Verified Test Metrics Summary                   │
├─────────────────────┬───────────┬──────────┬───────────┬───────────────┤
│ Test Harness        │ Files     │ Tests    │ Status    │ Duration      │
├─────────────────────┼───────────┼──────────┼───────────┼───────────────┤
│ Backend (Pytest)    │ 15 files  │ 348 tests│ PASSED    │ 114.70 seconds│
│ Frontend (Vitest)   │ 11 files  │ 113 tests│ PASSED    │ 43.86 seconds │
├─────────────────────┼───────────┼──────────┼───────────┼───────────────┤
│ Total Verification  │ 26 files  │ 461 tests│ 100% GREEN│ ~2m 39s       │
└─────────────────────┴───────────┴──────────┴───────────┴───────────────┘
```

### 1.1. Backend Test Suite Coverage Breakdown
- `tests/test_database.py`: 11 passed (database connection, session rollback isolation, pgvector math, least-privilege role assertions).
- `tests/test_auth_api.py`: 20 passed (registration, login, invalid passwords, duplicate emails, expired tokens, me endpoint).
- `tests/test_candidate_api.py`: 48 passed (candidate profile CRUD, sub-resource CRUD for skills, experiences, educations, projects, certifications, cross-user ownership isolation).
- `tests/test_resume_api.py`: 25 passed (PDF extraction, DOCX extraction, invalid file types, oversized file rejections, empty text handling, resume synchronization).
- `tests/test_opportunity_api.py`: 32 passed (opportunity ingestion, filtering, pagination, keyword search, vector embedding generation).
- `tests/test_recommendation_api.py`: 22 passed (vector nearest neighbor search, profile embedding fallback, distance sorting).
- `tests/test_matching_api.py`: 65 passed (7-factor hybrid scoring math, skill overlap logic, non-overlapping date interval merging, overqualification soft penalties, education hierarchy rules, work-mode conflicts, eligibility precedence, missing-evidence handling).
- `tests/test_application_api.py`: 52 passed (application creation, state machine transitions, prohibited transition rejection, duplicate application prevention, audit logging).
- `tests/test_e2e_integration.py`: 73 passed (complete multi-step candidate user journeys, lifecycle verification, security boundary audits).

### 1.2. Frontend Test Suite Coverage Breakdown
- `src/test/App.test.tsx`: 10 passed (application shell, route rendering, navigation, protected route boundaries).
- `src/test/Components.test.tsx`: 9 passed (foundational UI components, accessible button variants, form inputs).
- `src/test/Resume.test.tsx`: 11 passed (resume upload dropzone, file validation, parsing preview, sync confirmation).
- `src/test/Profile.test.tsx`: 16 passed (profile viewer, inline editing, sub-resource modal managers).
- `src/test/Opportunities.test.tsx`: 5 passed (filtering, pagination, keyword search, empty states).
- `src/test/Recommendations.test.tsx`: 11 passed (recommendation cards, similarity badges, error handling for missing profiles).
- `src/test/Matching.test.tsx`: 17 passed (match evaluation trigger, radar breakdowns, strength/gap accordions).
- `src/test/Applications.test.tsx`: 24 passed (stage columns, status transition modals, audit timeline history).
- `src/test/E2EIntegration.test.tsx`: 4 passed (multi-page user journey simulations).
- `src/test/Security.test.tsx`: 4 passed (token storage hygiene, XSS sanitization, authorization header propagation).
- `src/test/TestUtils.test.tsx`: 2 passed (isolated router rendering fixtures).

---

## 2. Static Code Analysis & Security Scans (Measured)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Static Security & Linting                       │
├─────────────────────┬───────────────────┬──────────────────────────────┤
│ Tool                │ Scope             │ Measured Result              │
├─────────────────────┼───────────────────┼──────────────────────────────┤
│ Ruff Linter         │ Backend & Scripts │ PASSED (0 issues)            │
│ Ruff Formatter      │ Backend & Scripts │ PASSED (115 files formatted) │
│ Bandit (AST SAST)   │ Backend & Alembic │ PASSED (10,488 lines, 0 vulns│
│ Oxlint              │ Frontend          │ PASSED (0 errors)            │
│ TypeScript (tsc)    │ Frontend          │ PASSED (0 type errors)       │
└─────────────────────┴───────────────────┴──────────────────────────────┘
```

---

## 3. Database Least-Privilege Verification (Measured)

Direct SQL query against PostgreSQL `pg_roles` for application role `careerlens_user`:
```sql
SELECT rolname, rolcanlogin, rolcreatedb, rolsuper, rolcreaterole 
FROM pg_roles 
WHERE rolname = 'careerlens_user';
```

**Measured Attributes:**
- `rolname`: `careerlens_user`
- `rolcanlogin`: `TRUE` (Permitted application connection)
- `rolcreatedb`: `FALSE` (Least privilege enforced)
- `rolsuper`: `FALSE` (Least privilege enforced)
- `rolcreaterole`: `FALSE` (Least privilege enforced)

---

## 4. Semantic Retrieval Quality Metrics (Status: Honest Disclosure)

> [!NOTE]
> **Status: Not Yet Formally Benchmarked on Standard IR Datasets.**
> Semantic vector similarity in CareerLens is powered by the pre-trained `sentence-transformers/all-MiniLM-L6-v2` transformer model (which exhibits an established average performance of 68.06 on the Massive Text Embedding Benchmark - MTEB).
> In the CareerLens test environment, retrieval behavior is validated for functional correctness and cosine ranking monotonicity across synthetic test fixtures. However, quantitative information retrieval metrics (Recall@K, Precision@K, Mean Reciprocal Rank - MRR, and NDCG@K) have not yet been evaluated on an annotated, real-world candidate-job relevance corpus.

### Reproducible Evaluation Procedure for Future Benchmarking:
To measure empirical retrieval quality on real-world datasets:
1. **Corpus Preparation**: Assemble a dataset of $N \ge 1,000$ labeled job descriptions and $M \ge 200$ annotated candidate resumes with binary or graded relevance judgments $r \in \{0, 1, 2, 3\}$.
2. **Embedding Ingestion**: Ingest the labeled job corpus through `/api/v1/opportunities/ingest` to populate pgvector embeddings.
3. **Retrieval Execution**: For each candidate profile, query `/api/v1/recommendations/?limit=20` and record the retrieved opportunity IDs.
4. **Metric Calculation**:
   $$\text{Recall@K} = \frac{|\text{Relevant Retrieved in Top } K|}{|\text{Total Relevant}|}$$
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
   $$\text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$

---

## 5. Performance Measurements & Runtime Environment (Measured)

### 5.1. Measured Test Execution Times
- **Host Test Environment**: Windows 11 host, AMD/Intel x86_64, Python 3.12.4, PostgreSQL 18.x locally, NVMe SSD.
- **Backend Full Suite Duration**: $114.70\text{ seconds}$ across $348$ asynchronous tests (averaging $\sim 330\text{ ms}$ per test including database setup, session transactions, and mock embedding inferences).
- **Frontend Full Suite Duration**: $43.86\text{ seconds}$ across $113$ React component and router tests.
- **Vector Cosine Distance Test**: Direct vector cosine math query (`'[1,2,3]'::vector <-> '[3,2,1]'::vector`) executes in $< 1\text{ ms}$.

### 5.2. In-Memory Cache Performance Metrics
The `AsyncCacheManager` collects internal runtime telemetry accessible via properties:
- `cache.hits`: Cumulative number of successful cache retrievals.
- `cache.misses`: Cumulative number of cache misses requiring database evaluation.
- `cache.evictions`: Number of LRU items evicted upon reaching the 5,000-entry capacity limit.
- `cache.invalidations`: Number of items purged via tag/prefix invalidation.
- During high-throughput simulated queries, cached opportunity and match detail retrievals return in $< 0.1\text{ ms}$ in-process without database round-trips.

---

## 6. Continuous Integration vs. Host Runtime Verification

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Deployment Verification Matrix                  │
├──────────────────────────┬──────────────┬──────────────────────────────┤
│ Dimension                │ CI Pipeline  │ Host Local Environment       │
├──────────────────────────┼──────────────┼──────────────────────────────┤
│ PostgreSQL + pgvector    │ VERIFIED (16)│ VERIFIED (18.x locally)      │
│ Database Migrations      │ VERIFIED     │ VERIFIED                     │
│ Backend Quality Gates    │ VERIFIED     │ VERIFIED                     │
│ Frontend Quality Gates   │ VERIFIED     │ VERIFIED                     │
│ Docker Container Build   │ VERIFIED     │ NOT RUN (No local Docker)    │
│ Compose Config Validate  │ VERIFIED     │ NOT RUN (No local Docker)    │
│ Live Nginx Reverse Proxy │ VERIFIED     │ NOT RUN (No local Docker)    │
└──────────────────────────┴──────────────┴──────────────────────────────┘
```

- **GitHub Actions Verification**:
  - Run ID: `40176459857` on commit `dd5ff93`.
  - Result: **SUCCESS across all 3 jobs** (`Backend Lint, Security & Tests`, `Frontend Lint, Type-Check, Tests & Build`, and `Docker Build & Compose Config Validation`).
- **Host Limitation Note**:
  - The Windows host machine does not have the Docker daemon installed (`docker: command not found`). Local host container runtime booting is not possible on this specific host. Full multi-container Docker images and Compose configurations are verified and built in the GitHub Actions Linux runner environment.
