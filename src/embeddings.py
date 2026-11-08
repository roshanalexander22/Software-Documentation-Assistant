"""
Embeddings generation module.
Wraps sentence-transformers with caching, normalization, and graceful fallback.
"""

from typing import Iterable
import numpy as np


class EmbeddingService:
    """
    Generates normalized dense vector embeddings for documents and queries.
    Uses SentenceTransformers model (e.g., all-MiniLM-L6-v2) by default,
    with an adaptive deterministic dense fallback for zero-network testing.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        self._model = None
        self._is_fallback = False

    def _load_model(self):
        """Lazy loader for the SentenceTransformers model."""
        if self._model is not None or self._is_fallback:
            return

        try:
            from sentence_transformers import SentenceTransformer
            print(f"[INFO] Loading embedding model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            print("[INFO] Embedding model loaded successfully.")
        except Exception as e:
            print(f"[WARN] Failed to load SentenceTransformer ({e}). Falling back to deterministic dense vectorizer.")
            self._is_fallback = True

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Embeds a list of texts into a 2D float32 numpy array [N, dim]."""
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        self._load_model()

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embeddings.astype(np.float32)

        # Deterministic dense fallback
        return self._deterministic_fallback_embed(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """Embeds a single query into a 1D float32 numpy array [dim]."""
        return self.embed_texts([query])[0]

    def _deterministic_fallback_embed(self, texts: list[str]) -> np.ndarray:
        """
        Lightweight, deterministic hashed token dense embedding fallback.
        Ensures unit tests and offline execution never hang or crash without weights.
        """
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = text.lower().split()
            if not words:
                vectors[i, 0] = 1.0
                continue
            for word in words:
                # Murmur-like hash bucket distribution
                h = abs(hash(word))
                dim_idx = h % self.dim
                sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
                vectors[i, dim_idx] += sign
            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] /= norm
            else:
                vectors[i, 0] = 1.0
        return vectors

