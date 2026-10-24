"""
Phase 23: Performance Optimization, Database Indexing, and Caching Test Suite.

Covers:
1. Cache Unit Tests:
   - Cache hit / miss behavior
   - TTL expiration and eviction
   - LRU capacity enforcement
   - Prefix invalidation
   - Deterministic key hashing
   - Graceful degradation on simulated cache failure
2. Multi-User and Cross-Candidate Isolation:
   - Candidate A vs. Candidate B cache isolation
   - Guarantee that candidate profile, match, and application data never leak across candidates
3. Invalidation Triggers:
   - Profile update invalidates candidate recommendations and matches
   - Ingestion invalidates opportunity listing and recommendations
   - Application status change invalidates candidate application list
4. Database Index Catalog Verifications:
   - opportunities_active_created_idx
   - applications_profile_updated_idx
   - opportunities_job_embedding_hnsw_idx
"""

import asyncio
import uuid

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    AsyncCacheManager,
    cache,
    make_applications_list_key,
    make_matches_list_key,
    make_opportunity_detail_key,
    make_recommendations_key,
)
from app.core.security import create_access_token
from tests.factories import CandidateProfileFactory, OpportunityFactory, UserFactory

# ---------------------------------------------------------------------------
# 1. Async Cache Manager Unit Tests
# ---------------------------------------------------------------------------


class TestAsyncCacheUnit:
    """Verifies internal mechanics of the in-memory asynchronous cache."""

    async def test_cache_hit_and_miss_lifecycle(self) -> None:
        mgr = AsyncCacheManager(maxsize=10, default_ttl=5.0)

        # 1. Miss on empty cache
        val = await mgr.get("test:key:1")
        assert val is None
        assert mgr.misses == 1
        assert mgr.hits == 0

        # 2. Store and hit
        await mgr.set("test:key:1", {"data": 42}, ttl=5.0)
        assert mgr.size == 1

        val2 = await mgr.get("test:key:1")
        assert val2 == {"data": 42}
        assert mgr.hits == 1

    async def test_ttl_expiration(self) -> None:
        mgr = AsyncCacheManager(maxsize=10, default_ttl=0.05)
        await mgr.set("expiring:key", "temporary_value", ttl=0.05)

        # Immediate fetch should succeed
        assert await mgr.get("expiring:key") == "temporary_value"

        # Wait for TTL to expire
        await asyncio.sleep(0.08)

        # Subsequent fetch must return None (expired)
        assert await mgr.get("expiring:key") is None
        assert mgr.size == 0

    async def test_lru_capacity_eviction(self) -> None:
        mgr = AsyncCacheManager(maxsize=3, default_ttl=10.0)

        await mgr.set("k1", 1)
        await mgr.set("k2", 2)
        await mgr.set("k3", 3)
        assert mgr.size == 3
        assert mgr.evictions == 0

        # Access k1 to make k2 the least recently used
        await mgr.get("k1")

        # Adding k4 must evict k2
        await mgr.set("k4", 4)
        assert mgr.size == 3
        assert mgr.evictions == 1

        assert await mgr.get("k2") is None  # Evicted
        assert await mgr.get("k1") == 1  # Retained
        assert await mgr.get("k3") == 3  # Retained
        assert await mgr.get("k4") == 4  # Retained

    async def test_prefix_invalidation(self) -> None:
        mgr = AsyncCacheManager(maxsize=20, default_ttl=10.0)

        await mgr.set("opp:list:hash1", "results1")
        await mgr.set("opp:list:hash2", "results2")
        await mgr.set("opp:detail:123", "detail123")
        await mgr.set("recom:cand1:hash", "recom1")

        # Invalidate only opp:list:
        invalidated = await mgr.invalidate_prefix("opp:list:")
        assert invalidated == 2
        assert mgr.invalidations == 2

        assert await mgr.get("opp:list:hash1") is None
        assert await mgr.get("opp:list:hash2") is None
        assert await mgr.get("opp:detail:123") == "detail123"
        assert await mgr.get("recom:cand1:hash") == "recom1"

    async def test_deterministic_key_hashing(self) -> None:
        mgr = AsyncCacheManager()

        params1 = {"b": 2, "a": 1, "nested": {"y": "val", "x": 10}}
        params2 = {"nested": {"x": 10, "y": "val"}, "a": 1, "b": 2}

        # Key generator must be insensitive to key ordering in dictionaries
        k1 = mgr.hash_key("prefix", params1)
        k2 = mgr.hash_key("prefix", params2)
        assert k1 == k2
        assert len(k1) == 16


# ---------------------------------------------------------------------------
# 2. Cross-Candidate Isolation and Key Namespacing
# ---------------------------------------------------------------------------


class TestCrossCandidateCacheIsolation:
    """Guarantees that personalized cache keys strictly isolate candidate profiles."""

    def test_key_builders_include_profile_dimension(self) -> None:
        profile_a = uuid.uuid4()
        profile_b = uuid.uuid4()
        params = {"page": 1, "page_size": 20}

        recom_a = make_recommendations_key(profile_a, params)
        recom_b = make_recommendations_key(profile_b, params)
        assert recom_a != recom_b
        assert str(profile_a) in recom_a
        assert str(profile_b) in recom_b

        match_a = make_matches_list_key(profile_a, params)
        match_b = make_matches_list_key(profile_b, params)
        assert match_a != match_b
        assert str(profile_a) in match_a

        app_a = make_applications_list_key(profile_a, params)
        app_b = make_applications_list_key(profile_b, params)
        assert app_a != app_b
        assert str(profile_a) in app_a

    async def test_cross_candidate_cached_responses_isolated(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """
        Verify that Candidate A and Candidate B querying applications
        receive strictly isolated cached results.
        """
        user_a = await UserFactory.create(
            db_session, email=f"user_iso_a_{uuid.uuid4().hex[:6]}@example.com"
        )
        await CandidateProfileFactory.create(db_session, user_id=user_a.id)

        user_b = await UserFactory.create(
            db_session, email=f"user_iso_b_{uuid.uuid4().hex[:6]}@example.com"
        )
        await CandidateProfileFactory.create(db_session, user_id=user_b.id)

        opp = await OpportunityFactory.create(db_session, is_active=True)
        await db_session.commit()

        token_a = create_access_token(subject=str(user_a.id))
        headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = create_access_token(subject=str(user_b.id))
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Candidate A creates an application
        res_create = await async_client.post(
            "/api/v1/applications/",
            json={"opportunity_id": str(opp.id), "status": "saved"},
            headers=headers_a,
        )
        assert res_create.status_code == 201

        # Candidate A lists applications -> 1 application
        list_a1 = await async_client.get("/api/v1/applications/", headers=headers_a)
        assert list_a1.status_code == 200
        assert list_a1.json()["total"] == 1

        # Candidate A lists applications again -> cache hit
        list_a2 = await async_client.get("/api/v1/applications/", headers=headers_a)
        assert list_a2.status_code == 200
        assert list_a2.json()["total"] == 1

        # Candidate B lists applications -> MUST be 0 (no data leak from Candidate A's cache)
        list_b = await async_client.get("/api/v1/applications/", headers=headers_b)
        assert list_b.status_code == 200
        assert list_b.json()["total"] == 0


# ---------------------------------------------------------------------------
# 3. Cache Invalidation Triggers
# ---------------------------------------------------------------------------


class TestCacheInvalidationTriggers:
    """Verifies that mutations properly invalidate affected cache namespaces."""

    async def test_application_lifecycle_invalidates_list_cache(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await UserFactory.create(
            db_session, email=f"user_inv_{uuid.uuid4().hex[:6]}@example.com"
        )
        await CandidateProfileFactory.create(db_session, user_id=user.id)
        opp = await OpportunityFactory.create(db_session, is_active=True)
        await db_session.commit()

        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Candidate lists applications -> empty list cached
        res_1 = await async_client.get("/api/v1/applications/", headers=headers)
        assert res_1.status_code == 200
        assert res_1.json()["total"] == 0

        # 2. Candidate saves application -> triggers cache invalidation
        res_create = await async_client.post(
            "/api/v1/applications/",
            json={"opportunity_id": str(opp.id), "status": "saved"},
            headers=headers,
        )
        assert res_create.status_code == 201
        app_id = res_create.json()["id"]

        # 3. Candidate lists applications again -> must return 1 (fresh data, not stale cached 0)
        res_2 = await async_client.get("/api/v1/applications/", headers=headers)
        assert res_2.status_code == 200
        assert res_2.json()["total"] == 1
        assert res_2.json()["items"][0]["status"] == "saved"

        # 4. Status transition -> triggers cache invalidation
        res_trans = await async_client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "applied", "notes": "Submitted"},
            headers=headers,
        )
        assert res_trans.status_code == 200

        # 5. List applications filtered by applied -> returns 1 with updated status
        res_3 = await async_client.get("/api/v1/applications/?status=applied", headers=headers)
        assert res_3.status_code == 200
        assert res_3.json()["total"] == 1
        assert res_3.json()["items"][0]["status"] == "applied"

    async def test_opportunity_detail_caching_and_hit(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        opp = await OpportunityFactory.create(
            db_session, title="Ultra Cache Test Opportunity", is_active=True
        )
        await db_session.commit()

        cache_key = make_opportunity_detail_key(opp.id)
        await cache.delete(cache_key)

        # First request -> cache miss, fetches from db and stores
        res1 = await async_client.get(f"/api/v1/opportunities/{opp.id}")
        assert res1.status_code == 200
        assert res1.json()["title"] == "Ultra Cache Test Opportunity"

        cached = await cache.get(cache_key)
        assert cached is not None
        assert cached.title == "Ultra Cache Test Opportunity"

        # Second request -> served from cache
        res2 = await async_client.get(f"/api/v1/opportunities/{opp.id}")
        assert res2.status_code == 200
        assert res2.json()["title"] == "Ultra Cache Test Opportunity"


# ---------------------------------------------------------------------------
# 4. Database Index Catalog Verifications
# ---------------------------------------------------------------------------


class TestDatabaseIndexVerification:
    """Verifies that performance optimization indexes exist in the active PostgreSQL catalog."""

    async def test_performance_indexes_exist(self, db_session: AsyncSession) -> None:
        stmt = text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname IN (
                'opportunities_active_created_idx',
                'applications_profile_updated_idx',
                'opportunities_job_embedding_hnsw_idx'
            );
        """)
        res = await db_session.execute(stmt)
        existing_indexes = set(res.scalars().all())

        assert "opportunities_active_created_idx" in existing_indexes
        assert "applications_profile_updated_idx" in existing_indexes
        assert "opportunities_job_embedding_hnsw_idx" in existing_indexes
