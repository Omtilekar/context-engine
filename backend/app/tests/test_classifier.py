"""Tests for the GPT-4o-mini LLM query classifier and its heuristic fallback."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.retrieval.router import RetrievalRouter, _classify_with_llm
from app.schemas.query import QueryRequest, QueryRoute, RouteDecision

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_openai_response(
    route: str,
    confidence: float = 0.9,
    reasoning: str = "test",
    entities: list[str] | None = None,
) -> MagicMock:
    """Build a mock OpenAI chat-completion response for the classifier."""
    content = json.dumps(
        {
            "route": route,
            "confidence": confidence,
            "reasoning": reasoning,
            "entities": entities or [],
        }
    )
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_mock_client(response: MagicMock) -> MagicMock:
    """Wrap a response mock inside a minimal AsyncOpenAI client mock."""
    mock_completions = MagicMock()
    mock_completions.create = AsyncMock(return_value=response)
    mock_chat = MagicMock()
    mock_chat.completions = mock_completions
    mock_client = MagicMock()
    mock_client.chat = mock_chat
    return mock_client


# ---------------------------------------------------------------------------
# _classify_with_llm â€” unit tests
# ---------------------------------------------------------------------------


async def test_classify_with_llm_returns_none_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None immediately when OPENAI_API_KEY is not configured."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY=None),
    )
    result = await _classify_with_llm("What is ContextEngine?")
    assert result is None


async def test_classify_with_llm_returns_none_when_classifier_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when LLM_CLASSIFIER_ENABLED is False even with an API key."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test", LLM_CLASSIFIER_ENABLED=False),
    )
    result = await _classify_with_llm("What is ContextEngine?")
    assert result is None


@pytest.mark.parametrize(
    "route",
    ["wiki", "semantic", "bm25", "sql", "graph", "hybrid"],
)
async def test_classify_with_llm_returns_route_decision_for_all_six_routes(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM classifier returns a RouteDecision with the correct route for each of the 6 routes."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response(route, confidence=0.88)
    mock_client = _make_mock_client(mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("test query")

    assert result is not None
    assert isinstance(result, RouteDecision)
    assert result.route == QueryRoute(route)
    assert result.confidence == pytest.approx(0.88)


async def test_classify_with_llm_returns_none_on_openai_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when the OpenAI API call raises any exception."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_completions = MagicMock()
    mock_completions.create = AsyncMock(side_effect=RuntimeError("API error"))
    mock_chat = MagicMock()
    mock_chat.completions = mock_completions
    mock_client = MagicMock()
    mock_client.chat = mock_chat

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("test query")

    assert result is None


async def test_classify_with_llm_returns_none_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when the LLM response is not valid JSON."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_message = MagicMock()
    mock_message.content = "This is not JSON at all"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = _make_mock_client(mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("test query")

    assert result is None


async def test_classify_with_llm_returns_none_on_unknown_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when the LLM returns an unrecognised route value."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response("totally_unknown_route")
    mock_client = _make_mock_client(mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("test query")

    assert result is None


async def test_classify_with_llm_populates_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entities extracted by the LLM are included in the RouteDecision."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response(
        "graph",
        reasoning="Relationship query about known entities.",
        entities=["ContextEngine", "PostgreSQL"],
    )
    mock_client = _make_mock_client(mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("How is ContextEngine related to PostgreSQL?")

    assert result is not None
    assert result.entities == ["ContextEngine", "PostgreSQL"]


async def test_classify_with_llm_clamps_high_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confidence values above 1.0 are clamped to 1.0."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response("wiki", confidence=1.5)
    mock_client = _make_mock_client(mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("What is ContextEngine?")

    assert result is not None
    assert result.confidence == pytest.approx(1.0)


async def test_classify_with_llm_clamps_negative_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confidence values below 0.0 are clamped to 0.0."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response("sql", confidence=-0.5)
    mock_client = _make_mock_client(mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        result = await _classify_with_llm("How many records?")

    assert result is not None
    assert result.confidence == pytest.approx(0.0)


async def test_classify_with_llm_uses_gpt4o_mini_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The classifier always uses the gpt-4o-mini model, not gpt-4o."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response("semantic")
    mock_completions = MagicMock()
    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat = MagicMock()
    mock_chat.completions = mock_completions
    mock_client = MagicMock()
    mock_client.chat = mock_chat

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        await _classify_with_llm("What are the risks?")

    call_kwargs = mock_completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4o-mini"


async def test_classify_with_llm_sends_json_response_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The classifier requests JSON response format from the API."""
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.retrieval.router.get_settings",
        lambda: Settings(OPENAI_API_KEY="sk-test"),
    )
    mock_response = _mock_openai_response("bm25")
    mock_completions = MagicMock()
    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat = MagicMock()
    mock_chat.completions = mock_completions
    mock_client = MagicMock()
    mock_client.chat = mock_chat

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        await _classify_with_llm("Find keyword pgvector")

    call_kwargs = mock_completions.create.call_args
    assert call_kwargs.kwargs["response_format"]["type"] == "json_object"


# ---------------------------------------------------------------------------
# RetrievalRouter.route() integration with LLM
# ---------------------------------------------------------------------------


async def test_router_uses_llm_decision_when_classifier_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Router returns the LLM decision when _classify_with_llm returns a RouteDecision."""
    llm_result = RouteDecision(
        route=QueryRoute.GRAPH,
        confidence=0.93,
        reasoning="LLM detected a graph query.",
        entities=["ContextEngine", "PostgreSQL"],
    )

    async def mock_classify(query: str) -> RouteDecision | None:
        return llm_result

    monkeypatch.setattr("app.retrieval.router._classify_with_llm", mock_classify)

    router = RetrievalRouter()
    decision = await router.route(QueryRequest(query="any query"))

    assert decision.route == QueryRoute.GRAPH
    assert decision.confidence == pytest.approx(0.93)
    assert decision.entities == ["ContextEngine", "PostgreSQL"]
    assert decision.reasoning == "LLM detected a graph query."


async def test_router_falls_back_to_heuristic_when_classifier_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Router uses heuristic classification when _classify_with_llm returns None."""

    async def mock_classify(query: str) -> RouteDecision | None:
        return None

    monkeypatch.setattr("app.retrieval.router._classify_with_llm", mock_classify)

    router = RetrievalRouter()
    decision = await router.route(QueryRequest(query="How many records in total?"))

    assert decision.route == QueryRoute.SQL


async def test_router_heuristic_fallback_covers_all_six_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Heuristic fallback can produce all six route types."""

    async def mock_classify(query: str) -> RouteDecision | None:
        return None

    monkeypatch.setattr("app.retrieval.router._classify_with_llm", mock_classify)

    router = RetrievalRouter()
    cases: list[tuple[str, QueryRoute]] = [
        ("What is ContextEngine?", QueryRoute.WIKI),
        ("How many records were created in Q3?", QueryRoute.SQL),
        ('Find exact phrase "context-engine"', QueryRoute.BM25),
        ("How is Alice connected to Bob?", QueryRoute.GRAPH),
        ("Define vectorless RAG in the documentation", QueryRoute.WIKI),
        ("Compare exact GDPR mentions and total incident counts", QueryRoute.HYBRID),
        ("Which requirements create the largest operational risk?", QueryRoute.SEMANTIC),
    ]
    for query_text, expected_route in cases:
        decision = await router.route(QueryRequest(query=query_text))
        assert decision.route == expected_route, (
            f"Expected {expected_route} for '{query_text}', got {decision.route}"
        )


async def test_router_llm_decision_entities_propagate_to_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entities returned by the LLM are preserved on the RouteDecision."""
    llm_result = RouteDecision(
        route=QueryRoute.WIKI,
        confidence=0.96,
        reasoning="Documentation lookup.",
        entities=["pgvector", "PostgreSQL"],
    )

    async def mock_classify(query: str) -> RouteDecision | None:
        return llm_result

    monkeypatch.setattr("app.retrieval.router._classify_with_llm", mock_classify)

    router = RetrievalRouter()
    decision = await router.route(QueryRequest(query="Explain pgvector"))

    assert decision.entities == ["pgvector", "PostgreSQL"]

