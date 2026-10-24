"""Embedding provider abstractions and deterministic local embeddings for D3 Story Lab.

ENFORCES:
1. Zero required paid or cloud APIs: Works out of the box with deterministic local embeddings.
2. Abstract EmbeddingProvider interface allowing drop-in upgrades without changing business logic.
3. Stable indexing version and model identifier tracking to detect incompatible vector caches.
4. Safe fallback: If semantic embeddings are disabled or unavailable, system operates cleanly via lexical retrieval.
"""

from __future__ import annotations
import math
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class EmbeddingProvider(ABC):
    """Abstract protocol for text embedding generation."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Identifier of the embedding model."""
        pass

    @property
    @abstractmethod
    def index_version(self) -> str:
        """Version of the vector indexing format."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is functional in the current runtime environment."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate normalized embedding vector for a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embedding vectors for multiple strings."""
        pass

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two unit vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class LocalFeatureEmbeddingProvider(EmbeddingProvider):
    """Deterministic, zero-dependency local embedding provider based on character/word n-gram hashing.

    Produces a stable 128-dimensional unit vector that captures morphological and lexical semantic proximity
    without requiring third-party weights or cloud network requests.
    """

    def __init__(self, dimensions: int = 128, version: str = "v1-local-hash"):
        self._dims = dimensions
        self._version = version

    @property
    def model_id(self) -> str:
        return f"d3-local-feature-{self._dims}d"

    @property
    def index_version(self) -> str:
        return self._version

    @property
    def is_available(self) -> bool:
        return True

    def embed_text(self, text: str) -> List[float]:
        """Map text to a deterministic 128-dimensional normalized vector."""
        if not text or not text.strip():
            return [0.0] * self._dims

        clean = text.lower().strip()
        vec = [0.0] * self._dims

        # 1. Word token hashing
        words = clean.split()
        for w in words:
            if len(w) > 2:
                # Primary word bucket
                h = int(hashlib.sha256(w.encode("utf-8")).hexdigest(), 16)
                idx = h % self._dims
                sign = 1.0 if (h // self._dims) % 2 == 0 else -1.0
                vec[idx] += 1.5 * sign

        # 2. Character trigram hashing for fuzzy morphological overlap
        for i in range(max(0, len(clean) - 2)):
            trigram = clean[i : i + 3]
            h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dims
            sign = 1.0 if (h // self._dims) % 2 == 0 else -1.0
            vec[idx] += 0.5 * sign

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            return [round(v / norm, 6) for v in vec]
        return [0.0] * self._dims

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation."""
        return [self.embed_text(t) for t in texts]
