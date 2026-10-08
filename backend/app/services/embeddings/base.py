"""
Base embedding provider abstraction for Phase 16 Local Embedding Foundation.
Defines interface for computing dense vector representations.
"""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract base class for CareerLens embedding generation providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Expected output vector dimensionality."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier name of the underlying embedding model."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Generate a normalized dense vector embedding for a single text input.
        Must be synchronous and CPU-safe. Thread offloading handled by service facade.
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate normalized dense vector embeddings for a list of text inputs.
        Must preserve input ordering and handle empty lists gracefully.
        """
        pass
