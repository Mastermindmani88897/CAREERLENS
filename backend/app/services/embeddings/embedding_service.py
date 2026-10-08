"""
Embedding Service facade for Phase 16 Local Embedding Foundation.
Orchestrates text normalization, thread-offloaded embedding inference,
lifecycle management, stale detection, and resilient persistence.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.candidate import CandidateProfile
from app.models.opportunity import Opportunity
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local_provider import LocalSentenceTransformersProvider
from app.services.embeddings.text_normalizer import (
    build_candidate_embedding_text,
    build_opportunity_embedding_text,
)

if TYPE_CHECKING:
    from app.models.candidate import (
        Certification,
        Education,
        Experience,
        Project,
        Skill,
    )
    from app.models.opportunity import OpportunitySkill

logger = logging.getLogger(__name__)

# Global singleton provider instance
_provider_instance: BaseEmbeddingProvider | None = None


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Retrieve or initialize the active embedding provider based on configuration."""
    global _provider_instance
    if _provider_instance is None:
        if settings.EMBEDDING_PROVIDER == "local":
            _provider_instance = LocalSentenceTransformersProvider(
                model_name=settings.EMBEDDING_MODEL,
                dimension=settings.EMBEDDING_DIMENSION,
            )
        else:
            # Fallback to local provider if unspecified
            _provider_instance = LocalSentenceTransformersProvider(
                model_name=settings.EMBEDDING_MODEL,
                dimension=settings.EMBEDDING_DIMENSION,
            )
    return _provider_instance


def set_embedding_provider(provider: BaseEmbeddingProvider | None) -> None:
    """Explicitly inject embedding provider (used for test isolation)."""
    global _provider_instance
    _provider_instance = provider


async def embed_text_async(text: str) -> list[float]:
    """Offload synchronous embedding inference to worker thread to avoid blocking event loop."""
    provider = get_embedding_provider()
    return await asyncio.to_thread(provider.embed_text, text)


async def embed_batch_async(texts: list[str]) -> list[list[float]]:
    """Offload synchronous batch embedding inference to worker thread."""
    provider = get_embedding_provider()
    return await asyncio.to_thread(provider.embed_batch, texts)


def is_candidate_embedding_stale(
    profile: CandidateProfile,
    skills: list[Skill] | None = None,
    educations: list[Education] | None = None,
    experiences: list[Experience] | None = None,
    projects: list[Project] | None = None,
    certifications: list[Certification] | None = None,
) -> bool:
    """
    Evaluate whether a candidate profile's embedding is stale.
    An embedding is stale if:
    1. profile_embedding is None.
    2. embedding_updated_at is None.
    3. profile.updated_at is more recent than embedding_updated_at.
    4. Any child record was created/modified after embedding_updated_at.
    """
    if profile.profile_embedding is None or profile.embedding_updated_at is None:
        return True

    emb_time = profile.embedding_updated_at

    # Ensure profile.updated_at comparison is timezone-aware
    if profile.updated_at:
        p_up = profile.updated_at
        if p_up.tzinfo is None and emb_time.tzinfo is not None:
            p_up = p_up.replace(tzinfo=UTC)
        elif p_up.tzinfo is not None and emb_time.tzinfo is None:
            emb_time = emb_time.replace(tzinfo=UTC)
        if p_up > emb_time:
            return True

    # Check child records safely without triggering async lazy loading
    children = []
    if skills is not None:
        children.extend(skills)
    elif "skills" in profile.__dict__ and profile.skills:
        children.extend(profile.skills)

    if educations is not None:
        children.extend(educations)
    elif "educations" in profile.__dict__ and profile.educations:
        children.extend(profile.educations)

    if experiences is not None:
        children.extend(experiences)
    elif "experiences" in profile.__dict__ and profile.experiences:
        children.extend(profile.experiences)

    if projects is not None:
        children.extend(projects)
    elif "projects" in profile.__dict__ and profile.projects:
        children.extend(profile.projects)

    if certifications is not None:
        children.extend(certifications)
    elif "certifications" in profile.__dict__ and profile.certifications:
        children.extend(profile.certifications)

    for item in children:
        child_time = getattr(item, "updated_at", None) or getattr(item, "created_at", None)
        if child_time:
            if child_time.tzinfo is None and emb_time.tzinfo is not None:
                child_time = child_time.replace(tzinfo=UTC)
            elif child_time.tzinfo is not None and emb_time.tzinfo is None:
                emb_time = emb_time.replace(tzinfo=UTC)
            if child_time > emb_time:
                return True

    return False


def is_opportunity_embedding_stale(
    opportunity: Opportunity,
    skills: list[OpportunitySkill] | None = None,
) -> bool:
    """
    Evaluate whether an opportunity's embedding is stale.
    An embedding is stale if:
    1. job_embedding is None.
    2. embedding_updated_at is None.
    3. opportunity.updated_at is more recent than embedding_updated_at.
    """
    if opportunity.job_embedding is None or opportunity.embedding_updated_at is None:
        return True

    emb_time = opportunity.embedding_updated_at
    if opportunity.updated_at:
        o_up = opportunity.updated_at
        if o_up.tzinfo is None and emb_time.tzinfo is not None:
            o_up = o_up.replace(tzinfo=UTC)
        elif o_up.tzinfo is not None and emb_time.tzinfo is None:
            emb_time = emb_time.replace(tzinfo=UTC)
        if o_up > emb_time:
            return True

    return False


async def generate_candidate_profile_embedding(
    db: AsyncSession,
    profile_id: uuid.UUID,
    commit: bool = True,
) -> list[float] | None:
    """
    Generate and persist a 384-dimensional vector embedding for a CandidateProfile.
    Safely catches any model or persistence errors without breaking parent operations.
    Excludes all PII and sensitive data.
    """
    try:
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.id == profile_id)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.educations),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.projects),
                selectinload(CandidateProfile.certifications),
            )
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile is None:
            logger.warning(
                "Cannot generate candidate embedding: profile not found",
                extra={"entity_type": "candidate_profile", "entity_id": str(profile_id)},
            )
            return None

        text = build_candidate_embedding_text(profile)
        vector = await embed_text_async(text)

        now_utc = datetime.now(UTC)
        profile.profile_embedding = vector
        profile.embedding_updated_at = now_utc

        if commit:
            await db.commit()
            await db.refresh(profile)

        logger.info(
            "Candidate profile embedding generated successfully",
            extra={
                "entity_type": "candidate_profile",
                "entity_id": str(profile_id),
                "operation": "generate_embedding",
                "dimension": len(vector),
            },
        )
        return vector

    except Exception as exc:
        logger.error(
            "Failed to generate candidate profile embedding: %s",
            type(exc).__name__,
            extra={
                "entity_type": "candidate_profile",
                "entity_id": str(profile_id),
                "operation": "generate_embedding",
                "error_category": type(exc).__name__,
            },
        )
        return None


async def generate_opportunity_embedding(
    db: AsyncSession,
    opportunity_id: uuid.UUID,
    commit: bool = True,
) -> list[float] | None:
    """
    Generate and persist a 384-dimensional vector embedding for an Opportunity.
    Safely catches any errors to ensure core opportunity storage remains unaffected.
    """
    try:
        stmt = (
            select(Opportunity)
            .where(Opportunity.id == opportunity_id)
            .options(selectinload(Opportunity.skills))
        )
        res = await db.execute(stmt)
        opp = res.scalar_one_or_none()
        if opp is None:
            logger.warning(
                "Cannot generate opportunity embedding: opportunity not found",
                extra={"entity_type": "opportunity", "entity_id": str(opportunity_id)},
            )
            return None

        text = build_opportunity_embedding_text(opp, opp.skills)
        vector = await embed_text_async(text)

        now_utc = datetime.now(UTC)
        opp.job_embedding = vector
        opp.embedding_updated_at = now_utc

        if commit:
            await db.commit()
            await db.refresh(opp)

        logger.info(
            "Opportunity embedding generated successfully",
            extra={
                "entity_type": "opportunity",
                "entity_id": str(opportunity_id),
                "operation": "generate_embedding",
                "dimension": len(vector),
            },
        )
        return vector

    except Exception as exc:
        logger.error(
            "Failed to generate opportunity embedding: %s",
            type(exc).__name__,
            extra={
                "entity_type": "opportunity",
                "entity_id": str(opportunity_id),
                "operation": "generate_embedding",
                "error_category": type(exc).__name__,
            },
        )
        return None


async def generate_opportunity_embeddings_batch(
    db: AsyncSession,
    opportunity_ids: list[uuid.UUID],
    commit: bool = True,
) -> int:
    """
    Batch generate and persist embeddings for multiple opportunities.
    Returns the count of successfully embedded opportunities.
    """
    if not opportunity_ids:
        return 0

    try:
        stmt = (
            select(Opportunity)
            .where(Opportunity.id.in_(opportunity_ids))
            .options(selectinload(Opportunity.skills))
        )
        res = await db.execute(stmt)
        opportunities = list(res.scalars().all())

        if not opportunities:
            return 0

        texts = [build_opportunity_embedding_text(opp, opp.skills) for opp in opportunities]
        vectors = await embed_batch_async(texts)

        now_utc = datetime.now(UTC)
        for opp, vec in zip(opportunities, vectors, strict=False):
            opp.job_embedding = vec
            opp.embedding_updated_at = now_utc

        if commit:
            await db.commit()

        logger.info(
            "Batch opportunity embeddings generated successfully",
            extra={
                "entity_type": "opportunity",
                "operation": "generate_embeddings_batch",
                "count": len(opportunities),
            },
        )
        return len(opportunities)

    except Exception as exc:
        logger.error(
            "Failed to batch generate opportunity embeddings: %s",
            type(exc).__name__,
            extra={
                "entity_type": "opportunity",
                "operation": "generate_embeddings_batch",
                "error_category": type(exc).__name__,
            },
        )
        return 0
