# CareerLens — Academic Defense & Project Handover Dossier (v1.1)

## 1. Problem Statement & Motivation

Modern online hiring and career discovery platforms suffer from severe structural asymmetries that disadvantage both candidates and recruiters:

1. **Keyword-Obsessed Filtering (ATS Fallacy)**: Legacy Applicant Tracking Systems (ATS) rely on exact syntactic keyword matching. Qualified candidates who express competencies using valid synonyms or project descriptions are systematically filtered out.
2. **Opaque "Black-Box" Algorithmic Bias**: Commercial platforms utilize proprietary, opaque machine learning rankers that offer zero explainability. Candidates receive arbitrary rejection notifications without understanding qualification gaps.
3. **Fragmented Opportunity Landscapes**: Job opportunities, technical internships, hackathons, and coding contests are dispersed across disjointed platforms, requiring candidates to manually track applications across fragmented spreadsheets.
4. **Data Privacy & Telemetry Concerns**: Centralized hiring platforms harvest candidate resumes and personal identifiable information (PII) for monetization and third-party advertising.

**Motivation**: To develop an open-architecture, privacy-preserving career intelligence platform that combines **dense semantic vector retrieval** with **transparent multi-factor deterministic scoring**, providing candidates with explainable recommendations, actionable skill-gap diagnostics, and unified application tracking.

---

## 2. Project Objectives & Scope

### 2.1. Primary Engineering Objectives
1. **Local Privacy-First NLP Ingestion**: Extract structured entities (skills, experience intervals, academic credentials) from PDF and DOCX resumes locally without sending documents to third-party APIs.
2. **Dense Semantic Embedding & Vector Search**: Generate 384-dimensional dense vector embeddings using local transformer models (`all-MiniLM-L6-v2`) and perform sub-linear vector similarity search via PostgreSQL `pgvector` HNSW indexes.
3. **Deterministic & Explainable Hybrid Matching**: Combine semantic similarity (35%) with deterministic domain constraints (65%) across skill overlap, experience depth, academic hierarchy, location compatibility, work-mode preference, and employment-type alignment.
4. **Actionable Feedback & Skill Gap Analysis**: Provide candidates with transparent score breakdowns, matched vs. missing skills, and natural-language explanations.
5. **Audited Application Lifecycle Tracking**: Implement a deterministic application tracking state machine with immutable audit logging.

### 2.2. Scope Demarcation (Current vs. Future Roadmap)
- **Implemented Scope (Phases 1–25)**:
  - Complete backend REST API (FastAPI, SQLAlchemy 2.0 async, PostgreSQL, pgvector).
  - Complete frontend Single Page Application (React 19, TypeScript, Vite, Tailwind CSS v4).
  - Local resume extraction, normalization, and profile synchronization.
  - Opportunity batch ingestion, vector indexing, and hybrid matching engine.
  - Interactive application tracking and status transition state machine.
  - Multi-container Docker Compose deployment and verified CI/CD pipeline.
- **Mandatory Scheduled Scope (Horizon 4 — Phases 26–27)**:
  - **Phase 26**: Automated multi-platform scraping & authorized feed ingestion (jobs, internships, hackathons, coding contests).
  - **Phase 27**: Automated external ATS application form filling with mandatory user confirmation.

---

## 3. Existing Systems vs. Proposed System (CareerLens)

```
┌─────────────────────────────┬─────────────────────────────┬─────────────────────────────┐
│ Feature Dimension           │ Existing Commercial ATS     │ Proposed CareerLens System  │
├─────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Retrieval Mechanism         │ Lexical keyword search (BM25│ Dense semantic vector search│
│                             │ / Boolean keyword filters)  │ via pgvector HNSW indexing  │
├─────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Match Transparency         │ Opaque score or hidden rank │ Open 7-factor weighted score│
│                             │ with zero feedback          │ with full JSON breakdown    │
├─────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Skill Gap Diagnostics       │ None (binary accept/reject) │ Explicit matched vs missing │
│                             │                             │ required & preferred skills │
├─────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Overqualification Handling  │ Often silently rejected     │ Soft penalty only; never    │
│                             │                             │ independently disqualifies  │
├─────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Missing Data Policy         │ Often causes hard rejection │ Neutral score (0.50) with   │
│                             │                             │ explicit review warning     │
├─────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Data Privacy & Hosting      │ Hosted SaaS harvesting data │ Local execution, self-host- │
│                             │                             │ able, non-root Docker stack │
└─────────────────────────────┴─────────────────────────────┴─────────────────────────────┘
```

---

## 4. Architectural & Module Description

The system follows a clean **Modular Monolith** architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CareerLens Core Modules                         │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Module                   │ Core Functionality                          │
├──────────────────────────┼─────────────────────────────────────────────┤
│ app.core                 │ Configuration, security, JWT, caching       │
│ app.models               │ SQLAlchemy 2.0 ORM entities & pgvector types│
│ app.schemas              │ Pydantic v2 validation & serialization      │
│ app.services.resume      │ pdfplumber/docx text extraction & NLP parser│
│ app.services.embeddings  │ sentence-transformers MiniLM-L6-v2 pipeline │
│ app.services.matching    │ 7-factor scoring engine & eligibility rules │
│ app.services.application │ Lifecycle state machine & audit log service │
│ app.api.v1               │ 34 REST endpoints across 8 modular routers  │
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

## 5. Database Design & Entity Architecture

The relational schema consists of **15 tables** with strict referential integrity (`ON DELETE CASCADE`):

1. **`users`**: Identity credentials (UUID PK, unique email, bcrypt hashed password, active flag).
2. **`candidate_profiles`**: 1-to-1 relationship with `users`. Stores career summary, location, relocation preference, and work preferences.
3. **`skills`**: Child entity of `candidate_profiles`. Stores normalized skill names, categories, and proficiency levels.
4. **`experiences`**: Candidate work history intervals with date tracking and work modes.
5. **`educations`**: Candidate academic degrees, institutions, and standardized `EducationLevel` enums.
6. **`projects`**: Technical projects, repository links, and skill tags.
7. **`certifications`**: Professional credentials, issuers, and verification URLs.
8. **`resumes`**: Raw text, file metadata, and structured JSON extraction payloads.
9. **`opportunities`**: Job postings containing text attributes, required/preferred skill arrays, and native `VECTOR(384)` embedding column.
10. **`opportunity_skills`**: Structured relational skill requirements with `is_required` flags.
11. **`matches`**: Persisted evaluation records between candidate profiles and opportunities with composite unique constraint `(candidate_profile_id, opportunity_id)`.
12. **`applications`**: Application tracking records with unique constraint preventing duplicate submissions.
13. **`application_status_history`**: Immutable status change audit log.
14. **`interview_prep`**: Tailored interview prep notes and guidance.
15. **`alembic_version`**: DDL migration tracking.

---

## 6. Semantic Retrieval & Hybrid Recommendation Methodology

### 6.1. Dense Semantic Vector Retrieval
1. **Transformer Model**: `sentence-transformers/all-MiniLM-L6-v2`.
   - Embeds textual inputs into dense 384-dimensional Euclidean space.
   - High compute efficiency: runs entirely in local CPU inference with negligible latency.
2. **Vector Indexing (HNSW)**:
   - PostgreSQL `pgvector` extension creates a Hierarchical Navigable Small World graph over `opportunities.embedding`:
     ```sql
     CREATE INDEX idx_opportunities_embedding_hnsw 
     ON opportunities USING hnsw (embedding vector_cosine_ops) 
     WITH (m = 16, ef_construction = 64);
     ```
   - Enables fast approximate nearest neighbor (ANN) retrieval using the cosine distance operator `<=>`.

### 6.2. Hybrid Scoring Formulation
The overall candidate-opportunity match score is calculated across seven dimensions:

$$\text{Final Score} = \sum_{i=1}^{7} w_i \cdot S_i$$

Where weights $\sum w_i = 1.00$:
- $w_{\text{semantic}} = 0.35$: Normalized cosine similarity $\max(0.0, \cos(\theta))$.
- $w_{\text{skill}} = 0.25$: Required skills ratio ($70\%$) + Preferred skills ratio ($30\%$).
- $w_{\text{experience}} = 0.15$: Non-overlapping work experience years evaluated against min/max thresholds. Overqualification penalty: $\max(0.60, 1.0 - 0.05 \cdot (\text{years} - \text{max}))$.
- $w_{\text{education}} = 0.10$: Ordered attainment ladder ($\text{NONE} < \text{DIPLOMA} < \text{BACHELOR} < \text{MASTER} < \text{PHD}$).
- $w_{\text{location}} = 0.05$: Location match, remote tolerance, and relocation preference ($0.70$).
- $w_{\text{work\_mode}} = 0.05$: Remote, hybrid, and onsite compatibility.
- $w_{\text{employment\_type}} = 0.05$: Full-time, part-time, contract, or internship alignment.

### 6.3. Deterministic Eligibility Precedence Rules
- **REVIEW_REQUIRED** is triggered if any of the following conditions occur:
  1. Candidate total experience $< 30\%$ of required minimum.
  2. Zero required skills matched when required skills are specified.
  3. Education is 2+ levels below target requirement or missing evidence for a degree-required role.
  4. Explicit work-mode conflict (onsite role for remote candidate without relocation).
  5. Explicit employment type mismatch.
  6. Final composite score $< 0.30$.
- **PARTIAL**: Applied when soft mismatches exist and final score is in $[0.30, 0.50)$.
- **ELIGIBLE**: Applied when all constraints are satisfied and final score $\ge 0.50$.

---

## 7. Testing Methodology & Verification Results

The CareerLens test harness uses automated unit, isolation, and integration suites:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Verified Test Metrics                           │
├─────────────────────┬──────────────┬──────────────┬────────────────────┤
│ Test Suite          │ Test Count   │ Status       │ Duration           │
├─────────────────────┼──────────────┼──────────────┼────────────────────┤
│ Backend Unit & Int. │ 348 tests    │ 100% Passed  │ ~1m 55s            │
│ Frontend Component  │ 113 tests    │ 100% Passed  │ ~44s               │
├─────────────────────┼──────────────┼──────────────┼────────────────────┤
│ Total Verification  │ 461 tests    │ 100% Passed  │ ~2m 39s            │
└─────────────────────┴──────────────┴──────────────┴────────────────────┘
```

- **Static Analysis**: Ruff lint (`0 issues`), Ruff formatting (`115 files formatted`), Bandit security scan (`10,488 lines, 0 vulnerabilities`).
- **Database Security**: Role least-privilege test (`test_careerlens_user_least_privilege`) validates that `rolcanlogin=True` and `rolcreatedb=False`, `rolsuper=False`, `rolcreaterole=False`.
- **Continuous Integration**: GitHub Actions CI pipeline passes all 3 jobs on commit `dd5ff93`:
  - `Backend Lint, Security & Tests`: SUCCESS
  - `Frontend Lint, Type-Check, Tests & Build`: SUCCESS
  - `Docker Build & Compose Config Validation`: SUCCESS

---

## 8. Live Demonstration Script

### Act 1: Authentication & Local Resume Extraction (3 Minutes)
1. **Action**: Open `http://localhost:5173/register` and register a new candidate account.
2. **Action**: Navigate to `/resume` and upload a technical sample resume (`sample_resume.pdf`).
3. **Observation**: Notice instant text extraction via `pdfplumber` without sending files to external third-party services. The UI displays parsed technical skills, employment dates, and academic degrees.
4. **Action**: Click "Sync with Candidate Profile".
5. **Observation**: Navigate to `/profile`. Extracted skills and experiences appear populated in the profile editor.

### Act 2: Opportunity Exploration & Semantic Recommendations (3 Minutes)
1. **Action**: Navigate to `/opportunities`.
2. **Observation**: Filter opportunities by `Work Mode: Remote` and `Type: Full-Time`. Notice sub-10ms query execution powered by PostgreSQL indexes.
3. **Action**: Navigate to `/recommendations`.
4. **Observation**: The system displays semantically recommended opportunities ordered by vector similarity between the candidate's profile summary and opportunity embeddings.

### Act 3: Transparent Hybrid Match Evaluation & Explainability (3 Minutes)
1. **Action**: Select a recommended opportunity and click "Evaluate Hybrid Match".
2. **Observation**: The UI renders a radar/breakdown card displaying the composite score (e.g., `88%`), individual factor weights, matched vs. missing required skills, and clear natural-language explanation sentences.
3. **Action**: Select an opportunity with an intentional experience shortfall (e.g., requires 5 years, candidate has 1 year).
4. **Observation**: The engine marks the match as `REVIEW_REQUIRED` with an explicit diagnostic warning: `"Severe experience shortfall: 1.0 years vs 5.0 years required"`.

### Act 4: Audited Application Tracking (2 Minutes)
1. **Action**: Click "Apply / Save" on an eligible opportunity.
2. **Observation**: Navigate to `/applications`. The application appears in the `APPLIED` column.
3. **Action**: Click "Update Status" and advance the application to `INTERVIEW`. Enter audit notes: `"Technical screen passed."`
4. **Observation**: Open application details. The status history log records the transition timestamp, previous status (`applied`), new status (`interview`), and candidate notes.

---

## 9. Academic Defense Slide-by-Slide Presentation Outline

- **Slide 1: Title & Author Information**
  - Project: *CareerLens: An Explainable, Privacy-Preserving Career Navigation and Semantic Matching Platform*.
  - Author, Institution, Date, and Academic Advisor.
- **Slide 2: The Problem: Structural Failures in Modern Hiring**
  - Syntactic keyword filtering discarding qualified talent.
  - Black-box algorithms offering no actionable candidate feedback.
  - Candidate privacy vulnerabilities and data monetization.
- **Slide 3: Proposed Solution: The CareerLens Architecture**
  - High-level modular monolith diagram (React 19 + FastAPI + pgvector).
  - Open, deterministic multi-factor scoring paired with dense vector search.
- **Slide 4: Local Information Extraction Pipeline**
  - PDF/DOCX structural parsing without cloud dependencies.
  - Taxonomy-driven skill normalization and date interval reconciliation.
- **Slide 5: Semantic Retrieval via pgvector & HNSW**
  - Dense text representations via `all-MiniLM-L6-v2` (384 dimensions).
  - Fast approximate nearest neighbor search using native cosine distance (`<=>`).
- **Slide 6: The 7-Factor Hybrid Matching Formulation**
  - Mathematical breakdown of scoring weights ($35\%$ semantic, $65\%$ deterministic).
  - Multi-tier skill overlap (required vs preferred) and non-overlapping experience calculation.
- **Slide 7: Transparent Explainability & Precedence Rules**
  - Diagnostic classifications: `ELIGIBLE`, `PARTIAL`, `REVIEW_REQUIRED`.
  - Missing-information policy: neutral baseline ($0.50$), no silent disqualification.
- **Slide 8: Audited Application Tracking State Machine**
  - Finite state machine diagram (Saved -> Applied -> OA/Interview -> Offer -> Terminal).
  - Immutable audit history and duplicate submission prevention.
- **Slide 9: Security Architecture & Least-Privilege Role Hardening**
  - JWT Bearer authentication, bcrypt hashing, and candidate ownership verification.
  - Resolving the PostgreSQL bootstrap role security issue (`NOCREATEDB`, `NOSUPERUSER`).
- **Slide 10: Quantitative Verification & Quality Gates**
  - 461 automated tests passing ($348$ backend + $113$ frontend).
  - 100% clean Bandit security scan, Ruff linting, and green GitHub Actions CI.
- **Slide 11: Limitations & Future Work (Horizon 4 Roadmap)**
  - Single-worker cache constraint (in-process LRU vs future Redis migration).
  - Scheduled Phase 26: Multi-platform automated opportunity scraping.
  - Scheduled Phase 27: Automated external ATS application form filling with user confirmation.
- **Slide 12: Conclusion & Summary of Contributions**
  - Summary of research and engineering achievements.
  - Q&A session.

---

## 10. Honest Academic Limitations & Future Work

1. **In-Process Cache Concurrency Limitation**:
   - The current `AsyncCacheManager` uses an in-memory `OrderedDict`. This assumes a single Uvicorn worker per container. Multi-worker scaling requires migrating to an external distributed cache (Redis).
2. **Deterministic Parsing vs Complex Formatting**:
   - Multi-column, graphically designed resumes (e.g., Canva templates) occasionally yield non-linear text streams. Future work will integrate layout-aware vision-language document parsers.
3. **Mandatory Future Phases**:
   - Web scraping across external job boards is scheduled for **Phase 26**.
   - Automated external ATS form filling is scheduled for **Phase 27**.

---

## 11. Authoritative References Actually Consulted

1. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. Proceedings of EMNLP-IJCNLP 2019. (Foundation for `all-MiniLM-L6-v2`).
2. Malkov, Y. A., & Yashunin, D. A. (2018). *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE Transactions on Pattern Analysis and Machine Intelligence. (Foundation for `pgvector` HNSW index).
3. PostgreSQL Global Development Group. (2024). *PostgreSQL 16 Documentation: Chapter 22 (Database Roles and Privileges) & System Catalogs (pg_roles)*.
4. FastAPI Documentation. (2024). *Dependency Injection & Security Bearer Token Handlers*. Sebastián Ramírez.
5. Pydantic v2 Documentation. (2024). *Settings Management and Runtime Data Validation*. Samuel Colvin.
