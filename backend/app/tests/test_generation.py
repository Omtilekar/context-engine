from collections.abc import Sequence
from types import SimpleNamespace
from typing import Literal

import pytest
from httpx import ASGITransport, AsyncClient

from app.generation.generator import (
    build_disabled_answer,
    extract_used_citations,
    generate_answer,
)
from app.generation.provider import (
    DisabledAnswerProvider,
    GroundedPrompt,
    OpenAIAnswerProvider,
    ProviderCompletion,
)
from app.main import app
from app.schemas.query import (
    ConfidenceResult,
    QueryRoute,
    SourceCitation,
    VerificationResult,
)


class StaticAnswerProvider:
    """Answer provider test double that returns a fixed response."""

    async def generate(
        self,
        prompt: GroundedPrompt,
        fallback_answer: str,
    ) -> ProviderCompletion:
        """Return a deterministic provider completion."""
        return ProviderCompletion(
            text="The retrieved source says semantic search uses vector distance [1].",
            provider="openai",
            model="gpt-4o",
            tokens_used=17,
        )


def source(
    snippet: str,
    score: float = 0.86,
    retrieval_mode: str = "semantic",
    source_type: QueryRoute = QueryRoute.SEMANTIC,
    chunk_id: str = "chunk-1",
) -> SourceCitation:
    """Build one source citation for generation tests."""
    return SourceCitation(
        title=f"{retrieval_mode.title()} Demo",
        score=score,
        source_type=source_type,
        snippet=snippet,
        source_id=chunk_id,
        chunk_id=chunk_id,
        document_id="document-1",
        retrieval_mode=retrieval_mode,
        metadata={"document_source_type": "text"},
    )


def verification(
    has_conflicts: bool = False,
    warnings: list[str] | None = None,
) -> VerificationResult:
    """Build a verification result for generation tests."""
    conflict_notes = (
        ["Sources disagree on increase versus decrease direction."] if has_conflicts else []
    )
    return VerificationResult(
        grounded=True,
        is_grounded=True,
        has_conflicts=has_conflicts,
        warnings=warnings or [],
        evidence_count=2,
        retrieval_modes=["semantic", "keyword"],
        conflict_notes=conflict_notes,
        conflicts=conflict_notes,
        confidence=0.74,
    )


def confidence(
    label: Literal["low", "medium", "high"] = "high",
    score: float = 0.82,
) -> ConfidenceResult:
    """Build a confidence result for generation tests."""
    return ConfidenceResult(
        score=score,
        label=label,
        reasons=["route_confidence=0.82", "average_source_score=0.86"],
        explanation="route_confidence=0.82; average_source_score=0.86",
    )


async def test_disabled_provider_returns_deterministic_answer_with_citations() -> None:
    """Disabled provider returns a local answer and citations without external calls."""
    sources = [
        source("Semantic search uses vector distance for related meaning.", chunk_id="sem-1"),
        source("Keyword retrieval uses exact lexical matching.", 0.8, "keyword", QueryRoute.BM25),
    ]

    result = await generate_answer(
        query="How does retrieval work?",
        sources=sources,
        verification=verification(),
        confidence=confidence(),
        provider=DisabledAnswerProvider(),
    )

    assert result.answer.startswith("Based on 2 retrieved sources")
    assert len(result.citations) == 2
    assert result.metadata.provider == "disabled"
    assert result.metadata.fallback_reason == "llm_provider_disabled"


async def test_openai_provider_missing_api_key_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI mode gracefully falls back when no API key is configured."""
    fake_settings = SimpleNamespace(openai_api_key=None, openai_model="gpt-4o")
    monkeypatch.setattr("app.generation.provider.get_settings", lambda: fake_settings)

    completion = await OpenAIAnswerProvider().generate(
        GroundedPrompt(system="system", user="user"),
        fallback_answer="fallback answer [1]",
    )

    assert completion.text == "fallback answer [1]"
    assert completion.provider == "disabled"
    assert completion.fallback_reason == "missing_openai_api_key"


def test_extract_used_citations_only_returns_retrieved_sources() -> None:
    """Citation extraction ignores duplicates and out-of-range citation indexes."""
    sources = [
        source("first", retrieval_mode="semantic", chunk_id="one"),
        source("second", retrieval_mode="keyword", source_type=QueryRoute.BM25, chunk_id="two"),
    ]

    citations = extract_used_citations("Facts from [1], [2], [99], and again [1].", sources)

    assert [citation.title for citation in citations] == ["Semantic Demo", "Keyword Demo"]
    assert [citation.retrieval_mode for citation in citations] == ["semantic", "keyword"]


def test_disabled_answer_mentions_low_confidence() -> None:
    """Disabled answer text surfaces low confidence evidence."""
    answer = build_disabled_answer(
        "What is the answer?",
        [source("Only weak evidence is available.")],
        verification(warnings=["weak_evidence"]),
        confidence(label="low", score=0.28),
    )

    assert "low confidence" in answer
    assert "[1]" in answer


def test_disabled_answer_mentions_conflicts() -> None:
    """Disabled answer text surfaces conflict notes."""
    answer = build_disabled_answer(
        "Did usage increase?",
        [
            source("Usage increased during the demo.", chunk_id="one"),
            source("Usage decreased during the demo.", chunk_id="two"),
        ],
        verification(has_conflicts=True),
        confidence(label="medium", score=0.58),
    )

    assert "possible conflicts" in answer
    assert "increase versus decrease" in answer


async def test_generator_output_schema_from_mocked_provider() -> None:
    """Generator returns the expected schema from a mocked provider completion."""
    result = await generate_answer(
        query="How does semantic search work?",
        sources=[source("Semantic search uses vector distance.")],
        verification=verification(),
        confidence=confidence(),
        provider=StaticAnswerProvider(),
    )

    assert result.answer.startswith("The retrieved source says")
    assert result.citations[0].title == "Semantic Demo"
    assert result.metadata.provider == "openai"
    assert result.metadata.model == "gpt-4o"
    assert result.metadata.tokens_used == 17


async def test_query_endpoint_includes_answer_and_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint includes generated answer text and citation metadata."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one source without touching a database."""
        return [source("Semantic search uses vector distance.", chunk_id="semantic-1")]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)
    monkeypatch.setattr(
        "app.generation.generator.get_generation_provider",
        lambda: DisabledAnswerProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "How does semantic search find related meaning?"},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["answer"].startswith("Based on 1 retrieved source")
    assert payload["citations"] == [
        {"title": "Semantic Demo", "retrieval_mode": "semantic", "score": 0.86}
    ]
    assert payload["generation_metadata"]["provider"] == "disabled"
