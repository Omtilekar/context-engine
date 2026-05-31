import hashlib
import math
import re
from typing import Protocol

from app.core.config import get_settings

DEFAULT_EMBEDDING_DIMENSION = 1536
TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


class EmbeddingProvider(Protocol):
    """Interface for query and document embedding providers."""

    dimension: int

    async def embed_query(self, text: str) -> list[float]:
        """Embed a user query."""
        ...

    async def embed_document(self, text: str) -> list[float]:
        """Embed source document text."""
        ...


class LocalHashEmbeddingProvider:
    """Deterministic local embedding provider for development and tests.

    This provider is not a semantic model. It hashes normalized tokens into a fixed-length
    vector so local pgvector retrieval can be exercised without OpenAI calls or secrets.
    """

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> None:
        """Create a local hash embedding provider.

        Args:
            dimension: Output vector dimension. The production schema expects 1536.
        """
        if dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        self.dimension = dimension

    async def embed_query(self, text: str) -> list[float]:
        """Embed a user query using deterministic token hashing."""
        return self._embed(text)

    async def embed_document(self, text: str) -> list[float]:
        """Embed source document text using deterministic token hashing."""
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        """Hash tokens into a normalized vector."""
        vector = [0.0] * self.dimension
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], byteorder="big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (len(token) % 7) / 10.0
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 8) for value in vector]


class OpenAIEmbeddingProviderPlaceholder:
    """Placeholder for future text-embedding-3-small integration."""

    dimension = DEFAULT_EMBEDDING_DIMENSION

    async def embed_query(self, text: str) -> list[float]:
        """Raise until OpenAI embedding integration is implemented."""
        raise NotImplementedError("OpenAI embeddings will be implemented in a later Phase 3 task")

    async def embed_document(self, text: str) -> list[float]:
        """Raise until OpenAI embedding integration is implemented."""
        raise NotImplementedError("OpenAI embeddings will be implemented in a later Phase 3 task")


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider.

    The project currently defaults to local deterministic embeddings so unit tests and local
    Docker Compose smoke tests do not require network calls or secrets.
    """
    settings = get_settings()
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProviderPlaceholder()
    return LocalHashEmbeddingProvider(dimension=settings.embedding_dimension)
