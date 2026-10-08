"""
Embeddings package initialization for Phase 16 Local Embedding Foundation.
Exports core interfaces, providers, normalizers, and service facade functions.
"""

from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.embedding_service import (
    embed_batch_async,
    embed_text_async,
    generate_candidate_profile_embedding,
    generate_opportunity_embedding,
    generate_opportunity_embeddings_batch,
    get_embedding_provider,
    is_candidate_embedding_stale,
    is_opportunity_embedding_stale,
    set_embedding_provider,
)
from app.services.embeddings.local_provider import LocalSentenceTransformersProvider
from app.services.embeddings.text_normalizer import (
    build_candidate_embedding_text,
    build_opportunity_embedding_text,
    normalize_whitespace,
)

__all__ = [
    "BaseEmbeddingProvider",
    "LocalSentenceTransformersProvider",
    "normalize_whitespace",
    "build_opportunity_embedding_text",
    "build_candidate_embedding_text",
    "get_embedding_provider",
    "set_embedding_provider",
    "embed_text_async",
    "embed_batch_async",
    "is_candidate_embedding_stale",
    "is_opportunity_embedding_stale",
    "generate_candidate_profile_embedding",
    "generate_opportunity_embedding",
    "generate_opportunity_embeddings_batch",
]
