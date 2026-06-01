from collections.abc import Sequence

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.query import QueryRoute, SourceCitation
from app.verification.confidence import confidence_label, normalize_score, score_confidence
from app.verification.verifier import verify_response


def source(
    snippet: str,
    score: float = 0.9,
    retrieval_mode: str = "semantic",
    source_type: QueryRoute = QueryRoute.SEMANTIC,
    chunk_id: str | None = "chunk-1",
) -> SourceCitation:
    """Build a source citation for verification tests."""
    return SourceCitation(
        title=f"{retrieval_mode.title()} evidence",
        score=score,
        source_type=source_type,
        snippet=snippet,
        source_id=chunk_id,
        chunk_id=chunk_id,
        document_id="document-1",
        retrieval_mode=retrieval_mode,
        metadata={"document_source_type": "text"},
    )


def test_no_sources_are_not_grounded_and_low_confidence() -> None:
    """Missing evidence produces an ungrounded, low-confidence verification result."""
    verification = verify_response("What changed?", "placeholder answer", [], 0.82)
    confidence = score_confidence([], 0.82, verification)

    assert not verification.grounded
    assert not verification.is_grounded
    assert verification.evidence_count == 0
    assert "no_sources" in verification.warnings
    assert verification.confidence == confidence.score
    assert confidence.label == "low"


def test_one_strong_source_is_grounded() -> None:
    """A strong single source is grounded but still notes the limited evidence count."""
    verification = verify_response(
        "How does retrieval work?",
        "placeholder answer",
        [source("Semantic retrieval uses vector distance for related meaning.", 0.95)],
        0.8,
    )

    assert verification.is_grounded
    assert verification.evidence_count == 1
    assert "single_source_evidence" in verification.warnings
    assert "weak_evidence" not in verification.warnings


def test_retrieval_mode_diversity_improves_confidence() -> None:
    """Mixed retriever evidence scores higher than same-mode evidence."""
    single_mode_sources = [
        source("Semantic context one.", 0.86, "semantic", QueryRoute.SEMANTIC, "sem-1"),
        source("Semantic context two.", 0.86, "semantic", QueryRoute.SEMANTIC, "sem-2"),
    ]
    mixed_mode_sources = [
        source("Semantic context one.", 0.86, "semantic", QueryRoute.SEMANTIC, "sem-1"),
        source("Keyword context two.", 0.86, "keyword", QueryRoute.BM25, "key-1"),
    ]

    single_verification = verify_response("Compare evidence", "answer", single_mode_sources, 0.8)
    mixed_verification = verify_response("Compare evidence", "answer", mixed_mode_sources, 0.8)
    single_confidence = score_confidence(single_mode_sources, 0.8, single_verification)
    mixed_confidence = score_confidence(mixed_mode_sources, 0.8, mixed_verification)

    assert single_verification.retrieval_modes == ["semantic"]
    assert mixed_verification.retrieval_modes == ["semantic", "keyword"]
    assert mixed_confidence.score > single_confidence.score


def test_duplicate_evidence_adds_warning_and_penalty() -> None:
    """Duplicate snippets are reported and reduce confidence."""
    unique_sources = [
        source("First independent evidence.", 0.82, "semantic", QueryRoute.SEMANTIC, "sem-1"),
        source("Second independent evidence.", 0.82, "keyword", QueryRoute.BM25, "key-1"),
    ]
    duplicate_sources = [
        source("Repeated evidence appears here.", 0.82, "semantic", QueryRoute.SEMANTIC, "sem-1"),
        source("Repeated evidence appears here.", 0.82, "keyword", QueryRoute.BM25, "key-1"),
    ]

    unique_verification = verify_response("Check evidence", "answer", unique_sources, 0.8)
    duplicate_verification = verify_response("Check evidence", "answer", duplicate_sources, 0.8)
    unique_confidence = score_confidence(unique_sources, 0.8, unique_verification)
    duplicate_confidence = score_confidence(duplicate_sources, 0.8, duplicate_verification)

    assert "duplicate_evidence" in duplicate_verification.warnings
    assert duplicate_confidence.score < unique_confidence.score


@pytest.mark.parametrize(
    ("snippets", "expected_note"),
    [
        (
            ["Usage increased during the demo.", "Usage decreased during the demo."],
            "increase versus decrease",
        ),
        (
            ["External export is allowed.", "External export is not allowed."],
            "whether the action is allowed",
        ),
        (
            ["The feature flag is true.", "The feature flag is false."],
            "true versus false",
        ),
        (
            ["The timeout is 5 seconds.", "The timeout is 10 seconds."],
            "numeric mismatch",
        ),
    ],
)
def test_conflict_detection_uses_simple_lexical_rules(
    snippets: list[str],
    expected_note: str,
) -> None:
    """Simple lexical contradictions are flagged without calling an LLM."""
    sources = [
        source(snippets[0], 0.8, "semantic", QueryRoute.SEMANTIC, "left"),
        source(snippets[1], 0.8, "keyword", QueryRoute.BM25, "right"),
    ]

    verification = verify_response("Check conflict", "answer", sources, 0.8)

    assert verification.has_conflicts
    assert any(expected_note in note for note in verification.conflict_notes)
    assert "conflicting_evidence" in verification.warnings


def test_score_normalization_and_confidence_labels_are_stable() -> None:
    """Confidence helpers clamp scores and assign deterministic labels."""
    assert normalize_score(-0.5) == 0.0
    assert normalize_score(0.55) == 0.55
    assert normalize_score(1.5) == 1.0
    assert confidence_label(0.2) == "low"
    assert confidence_label(0.55) == "medium"
    assert confidence_label(0.9) == "high"


async def test_query_response_includes_verification_and_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint returns the Task 9 verification and confidence fields."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one source without touching a database."""
        return [source("Semantic retrieval uses vector distance.", 0.91)]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Which retrieval approach finds related meaning?"},
        )

    payload = response.json()

    assert response.status_code == 200
    assert "verification" in payload
    assert "confidence" in payload
    assert payload["verification"]["is_grounded"] is True
    assert payload["verification"]["evidence_count"] == 1
    assert payload["confidence"]["label"] in {"low", "medium", "high"}
    assert 0.0 <= payload["confidence"]["score"] <= 1.0
