import math

import pytest

from app.embeddings.provider import (
    DEFAULT_EMBEDDING_DIMENSION,
    LocalHashEmbeddingProvider,
)


async def test_local_embedding_provider_is_deterministic() -> None:
    """Local hash embeddings are stable for the same input text."""
    provider = LocalHashEmbeddingProvider(dimension=32)

    first = await provider.embed_query("Semantic search finds related meaning")
    second = await provider.embed_query("Semantic search finds related meaning")

    assert first == second
    assert any(value != 0.0 for value in first)


async def test_local_embedding_provider_uses_configured_dimension() -> None:
    """Local hash embeddings respect the configured output dimension."""
    provider = LocalHashEmbeddingProvider(dimension=24)

    embedding = await provider.embed_document("ContextEngine stores vectors in pgvector")

    assert len(embedding) == 24


async def test_default_embedding_dimension_matches_pgvector_schema() -> None:
    """The default local embedding dimension matches chunks.embedding."""
    provider = LocalHashEmbeddingProvider()

    embedding = await provider.embed_query("default dimension")

    assert provider.dimension == DEFAULT_EMBEDDING_DIMENSION
    assert len(embedding) == DEFAULT_EMBEDDING_DIMENSION


async def test_empty_embedding_text_returns_zero_vector() -> None:
    """Empty text returns a stable zero vector."""
    provider = LocalHashEmbeddingProvider(dimension=12)

    assert await provider.embed_query("   ") == [0.0] * 12


async def test_non_empty_embedding_is_unit_normalized() -> None:
    """Non-empty local embeddings are normalized for cosine distance."""
    provider = LocalHashEmbeddingProvider(dimension=32)

    embedding = await provider.embed_query("semantic meaning")
    norm = math.sqrt(sum(value * value for value in embedding))

    assert norm == pytest.approx(1.0)
