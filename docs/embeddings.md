# CareerLens — Local Embedding Foundation Architecture

> Document Version: 1.0.0  
> Phase: Phase 16 — Local Embedding Foundation  
> Status: Implemented & Verified  

---

## 1. Overview & Objectives

The Local Embedding Foundation establishes offline, privacy-preserving, high-performance semantic vector generation for CareerLens. It provides 384-dimensional dense vector embeddings for:

1. **Candidate Profiles**: Representing professional capabilities, skills, education, and experience.
2. **Opportunities**: Representing job, internship, and hackathon requirements and context.

The entire pipeline runs locally on **CPU** using PyTorch and HuggingFace Sentence Transformers. No external LLM or embedding API keys are required.

---

## 2. Configuration & Model Specifications

| Parameter | Value | Description |
|---|---|---|
| **Provider** | `local` | Local CPU inference via `sentence-transformers` |
| **Model** | `sentence-transformers/all-MiniLM-L6-v2` | Fast, lightweight 6-layer MiniLM model |
| **Vector Dimension** | `384` | Native embedding dimension (`Vector(384)`) |
| **Device** | `cpu` | Forced CPU execution (no CUDA or GPU dependencies) |
| **Storage** | PostgreSQL 18.6 + pgvector 0.8.6 | Stored in native `vector(384)` columns |

Configured in `backend/app/core/config.py`:
- `EMBEDDING_PROVIDER`: `"local"`
- `EMBEDDING_MODEL`: `"sentence-transformers/all-MiniLM-L6-v2"`
- `EMBEDDING_DIMENSION`: `384`

---

## 3. Database Schema

### 3.1 Candidate Profile (`candidate_profiles`)
- **`profile_embedding`**: `Vector(384)` (nullable)
- **`embedding_updated_at`**: `DateTime(timezone=True)` (nullable)
- Added via Alembic migration `e9f42a8b3c1d` (revision parent: `d8e31a7f4b9c`).

### 3.2 Opportunity (`opportunities`)
- **`job_embedding`**: `Vector(384)` (nullable, preexisting in Phase 3/6)
- **`embedding_updated_at`**: `DateTime(timezone=True)` (nullable)
- Reused existing pgvector columns; no redundant columns created.

---

## 4. Modular Service Architecture

```
backend/app/services/embeddings/
├── __init__.py               # Public interface exports
├── base.py                   # BaseEmbeddingProvider abstract interface
├── local_provider.py         # LocalSentenceTransformersProvider (singleton, lazy load, CPU)
├── text_normalizer.py        # CandidateTextNormalizer & OpportunityTextNormalizer
└── embedding_service.py      # EmbeddingService facade (lifecycle, stale check, async offload)
```

### 4.1 Lazy Singleton Provider (`LocalSentenceTransformersProvider`)
- Model weights are **not** loaded at application boot or module import time.
- The `SentenceTransformer` instance is instantiated lazily upon first embedding request.
- Thread-safe double-checked locking ensures exactly one model instance exists in memory across worker threads.
- Explicitly enforces `device="cpu"` and validates output dimensions.

### 4.2 Non-Blocking Async Inference
- Model inference (`model.encode`) is CPU-bound and synchronous.
- The service wraps inference with `asyncio.to_thread` to ensure FastAPI event loops remain responsive during embedding generation.

---

## 5. Deterministic Text Normalization

Raw database objects are never passed directly to the model. Text builders extract only semantically relevant professional data and format them deterministically.

### 5.1 Candidate Profile Representation
Fields included:
- **Title**: Current professional title or headline
- **Summary**: Professional summary text
- **Skills**: Canonical skill names (e.g. `Python, FastAPI, PostgreSQL`)
- **Experience**: Role, company, description, and key responsibilities
- **Education**: Degree, field of study, and institution
- **Projects**: Project title and description
- **Certifications**: Certification name and issuing organization

### 5.2 Opportunity Representation
Fields included:
- **Title**: Opportunity title
- **Company**: Company name
- **Opportunity Type**: `job`, `internship`, or `hackathon`
- **Employment Type & Work Mode**: e.g., `full_time`, `remote`
- **Location**: Cleaned location string
- **Required & Preferred Skills**: Canonical skill names
- **Experience & Education Requirements**: Min/max experience and degree
- **Description**: Truncated and normalized description (max 1000 characters)

### 5.3 Privacy & Security Protections
The following fields are **strictly prohibited** from embedding text construction:
- Passwords or password hashes
- Authentication tokens, session IDs, API keys
- Email addresses and phone numbers
- Home street addresses and personal identifiers
- Compensation / salary information (to prevent socioeconomic bias in embeddings)

---

## 6. Lifecycle Management & Stale Detection

### 6.1 Stale Logic
An embedding is considered **stale** and requires regeneration if:
1. The embedding vector is `NULL`.
2. `embedding_updated_at` is `NULL`.
3. The parent record has been modified after `embedding_updated_at` (`updated_at > embedding_updated_at`).
4. Any related child records (for candidate: skills, experiences, educations, projects, certifications) have an `updated_at > embedding_updated_at`.

### 6.2 Lifecycle Integration Triggers
- **Candidate Profile**:
  - `POST /api/v1/candidates/profile` (creation)
  - `PUT /api/v1/candidates/profile` (update)
  - Child mutations: adding, editing, or deleting skills, experiences, educations, projects, certifications
  - Resume synchronization (`POST /api/v1/candidates/profile/sync-from-resume`)
- **Opportunity**:
  - Ingestion via `OpportunityIngestService`: batch embedding generated post-commit for new/updated opportunities.

---

## 7. Safe Failure Handling & Privacy Controls

- **Non-Destructive Failures**: Model failure or inference errors never fail the core profile or opportunity transaction. If embedding generation fails, the primary record is safely committed, an error is logged with safe metadata, and the embedding remains `NULL`/stale for subsequent regeneration.
- **Log Hygiene**: Log records contain only safe metadata (`candidate_id`, `opportunity_id`, model name, error class). Under no circumstances are raw profile text, resume text, opportunity descriptions, or vector floats logged.
- **API Isolation**: Embedding vectors are **never** returned in public or authenticated API response schemas (`CandidateProfileResponse`, `OpportunityResponse`, `OpportunityDetailResponse`).
- **No Arbitrary Public Endpoint**: There is no `POST /embeddings` endpoint for public or arbitrary user text inference. Embedding generation is strictly an internal service capability.

---

## 8. Verification & Quality Gates

- **Unit & Integration Tests**: 19 tests in `backend/tests/test_embeddings.py` validating singleton loading, 384-dimension output, determinism, candidate/opportunity lifecycle, stale detection, safe failure handling, and security guarantees.
- **Backend Test Suite**: 204 passed tests (185 baseline + 19 Phase 16).
- **Frontend Test Suite**: 56 passed tests with zero regressions.
- **Security Scans**: 0 Bandit issues, 0 secret scan findings, 0 Oxlint issues, 0 npm audit vulnerabilities.
