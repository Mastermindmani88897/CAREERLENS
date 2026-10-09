# CareerLens — Semantic Retrieval Architecture

> Document Version: 1.0.0  
> Phase: Phase 17 — Semantic Retrieval & Vector Search  
> Status: Implemented & Verified  

---

## 1. Overview & Objectives

Phase 17 delivers personalized, high-performance semantic opportunity retrieval for authenticated candidates. It bridges candidate profiles and stored opportunity listings via dense vector similarity querying directly within PostgreSQL using pgvector.

### Core Pipeline Flow:
```
Authenticated Candidate (Bearer JWT)
       │
       ▼
Resolve CandidateProfile (user_id)
       │
       ▼
Verify Freshness & Content Sufficiency
       │
       ▼
SQLAlchemy pgvector Cosine Distance Query (`<=>`)
       │
       ▼
Active Eligible Opportunities Filtered & Ranked
       │
       ▼
Ranked Semantic Recommendations (`semantic_similarity` in [-1.0, 1.0])
```

---

## 2. API Contract

### Endpoint: `GET /api/v1/recommendations/`

* **Authentication:** Mandatory Bearer JWT via `get_current_active_user`.
* **Candidate Resolution:** Strictly scoped to `current_user.id`. No client-supplied candidate or user IDs are accepted.

### Query Parameters

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `page` | `int` | `1` | `ge=1` | Pagination page number |
| `page_size` | `int` | `20` | `ge=1, le=100` | Results per page (bounded top-K) |
| `opportunity_type` | `OpportunityType \| None` | `None` | `job, internship, hackathon` | Optional type filter |
| `work_mode` | `WorkMode \| None` | `None` | `remote, hybrid, onsite, any` | Optional work mode filter |
| `employment_type` | `EmploymentType \| None` | `None` | `fulltime, parttime, internship, contract, any` | Optional employment type filter |
| `location` | `str \| None` | `None` | `max_length=100` | Case-insensitive substring match |

### Response Schema

```python
class SemanticOpportunityItem(OpportunityResponse):
    semantic_similarity: float  # Range: [-1.0, 1.0]

class RecommendationListResponse(BaseModel):
    items: list[SemanticOpportunityItem]
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

## 3. Mathematical Formulation & Score Semantics

### 3.1 Cosine Distance & Raw Similarity
In PostgreSQL pgvector, the cosine distance between candidate vector $u$ and opportunity vector $v$ is computed via the native operator `<=>`:
$$D(u, v) = 1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$

Because all embeddings in CareerLens are unit-normalized ($L_2 = 1.0$) at generation time:
$$D(u, v) = 1 - (u \cdot v) \in [0, 2]$$

Raw cosine similarity is derived as:
$$S(u, v) = 1.0 - D(u, v) \in [-1.0, 1.0]$$

### 3.2 Score Semantics
* The `semantic_similarity` score represents pure dense vector semantic alignment in `[-1.0, 1.0]`.
* **No Artificial Clamping:** Scores are never artificially clamped to zero.
* **Important Distinction:** The similarity score is **not** a hiring probability, **not** an eligibility determination, and **not** a hybrid score.

---

## 4. Query Strategy & Deterministic Ordering

### 4.1 SQL Predicates
1. `Opportunity.is_active.is_(True)`: Inactive listings are strictly excluded.
2. `Opportunity.job_embedding.is_not(None)`: Listings without embeddings are excluded.
3. Optional narrowing filters (`opportunity_type`, `work_mode`, `employment_type`, `location`) apply as standard `WHERE` conditions without altering similarity scores.

### 4.2 Deterministic Tie-Breaking
To prevent non-deterministic pagination ordering across runs when distances are identical:
1. `distance ASC` (closest semantic match first)
2. `Opportunity.posted_date DESC NULLS LAST` (most recently posted)
3. `Opportunity.created_at DESC` (most recently ingested)
4. `Opportunity.id ASC` (deterministic primary key tie-breaker)

---

## 5. Candidate Embedding Lifecycle & Edge Case Handling

1. **Missing Candidate Profile:** Returns `HTTP 404 Not Found` with detail `"Candidate profile not found. Please create a profile before requesting recommendations."`.
2. **Insufficient Content:** Profiles with empty or whitespace-only normalized text return `HTTP 400 Bad Request` with detail `"Candidate profile has insufficient content for recommendations. Please add skills, experience, or headline to your profile."`.
3. **Missing or Stale Embeddings:** On-demand embedding generation is automatically triggered before query execution if the candidate has added or modified skills, experiences, or profile data.
4. **Preservation on Failure:** If on-demand regeneration fails but a prior valid vector exists, the service falls back to the prior vector and logs a warning. Previous vectors are never destroyed by failed regeneration attempts.

---

## 6. Privacy & Security Safeguards

1. **Vector Masking:** Raw vector arrays (`384` floats) and internal timestamps are strictly excluded from API responses.
2. **PII Isolation:** Text normalization excludes all names, emails, phones, addresses, and compensation.
3. **No Direct Vector Submission:** Clients cannot supply arbitrary vectors to query against.
4. **Log Hygiene:** Logs record only `user_id`, result count, and query duration; no raw profile or opportunity text is ever logged.

---

## 7. Performance & Index Decisions

* **Current Scale:** At benchmark/synthetic dataset volume (< 10,000 listings), exact sequential SIMD scan in pgvector executes in < 5ms with 100% recall.
* **Index Decision:** No vector index (HNSW/IVFFlat) is needed or created in Phase 17. An index migration is deferred until measured dataset scale exceeds 50,000 listings and latency justifies approximate search.
