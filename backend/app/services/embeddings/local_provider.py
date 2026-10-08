"""
Local SentenceTransformers embedding provider for Phase 16.
Implements BaseEmbeddingProvider using sentence-transformers/all-MiniLM-L6-v2 on CPU.
"""

import os
import threading
from typing import Any

from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.services.embeddings.base import BaseEmbeddingProvider

# Suppress Hugging Face symlink warning on Windows platforms
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class LocalSentenceTransformersProvider(BaseEmbeddingProvider):
    """
    Local CPU-based embedding provider using SentenceTransformers.
    Employs lazy thread-safe singleton model loading to prevent redundant memory overhead.
    """

    _model: SentenceTransformer | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        model_name: str | None = None,
        dimension: int | None = None,
    ) -> None:
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._dimension = dimension or settings.EMBEDDING_DIMENSION

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @classmethod
    def reset_model(cls) -> None:
        """Reset the singleton model instance (primarily used for test isolation)."""
        with cls._lock:
            cls._model = None

    @classmethod
    def set_model(cls, model: Any) -> None:
        """Inject a model instance (primarily used for unit testing)."""
        with cls._lock:
            cls._model = model

    def _get_model(self) -> SentenceTransformer:
        """Lazy thread-safe singleton loading of the SentenceTransformer model on CPU."""
        if LocalSentenceTransformersProvider._model is None:
            with LocalSentenceTransformersProvider._lock:
                if LocalSentenceTransformersProvider._model is None:
                    LocalSentenceTransformersProvider._model = SentenceTransformer(
                        self._model_name,
                        device="cpu",
                    )
        return LocalSentenceTransformersProvider._model

    def embed_text(self, text: str) -> list[float]:
        """
        Generate a normalized 384-dimensional vector embedding for a single text.
        Handles empty/whitespace input safely by returning a zero-vector.
        """
        if not isinstance(text, str):
            raise TypeError(f"Input text must be a string, got {type(text).__name__}")

        cleaned = text.strip()
        if not cleaned:
            return [0.0] * self._dimension

        model = self._get_model()
        vec = model.encode(
            cleaned,
            normalize_embeddings=True,
            device="cpu",
            show_progress_bar=False,
        )
        vec_list = [float(x) for x in vec]
        if len(vec_list) != self._dimension:
            raise ValueError(
                f"Embedding output dimension mismatch: expected {self._dimension}, "
                f"got {len(vec_list)}"
            )
        return vec_list

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate normalized embeddings for a batch of texts.
        Preserves original ordering and processes non-empty texts in batches on CPU.
        """
        if not isinstance(texts, list):
            raise TypeError(f"Input texts must be a list, got {type(texts).__name__}")

        if not texts:
            return []

        for idx, item in enumerate(texts):
            if not isinstance(item, str):
                raise TypeError(
                    f"Input text at index {idx} must be a string, got {type(item).__name__}"
                )

        results: list[list[float]] = [[0.0] * self._dimension for _ in range(len(texts))]
        non_empty_indices: list[int] = []
        non_empty_texts: list[str] = []

        for idx, t in enumerate(texts):
            cleaned = t.strip()
            if cleaned:
                non_empty_indices.append(idx)
                non_empty_texts.append(cleaned)

        if non_empty_texts:
            model = self._get_model()
            vecs = model.encode(
                non_empty_texts,
                normalize_embeddings=True,
                device="cpu",
                batch_size=32,
                show_progress_bar=False,
            )
            for i, original_idx in enumerate(non_empty_indices):
                v_list = [float(x) for x in vecs[i]]
                if len(v_list) != self._dimension:
                    raise ValueError(
                        f"Embedding output dimension mismatch: expected {self._dimension}, "
                        f"got {len(v_list)}"
                    )
                results[original_idx] = v_list

        return results
