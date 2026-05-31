import pytest
from pydantic import ValidationError

from app.retrieval.router import RetrievalRouter
from app.schemas.query import QueryRequest, QueryRoute


async def route_query(query: str) -> QueryRoute:
    """Route a query through the current heuristic router."""
    router = RetrievalRouter()
    decision = await router.route(QueryRequest(query=query))
    return decision.route


@pytest.mark.parametrize(
    ("query", "expected_route"),
    [
        (
            "Which requirements create the largest operational risk?",
            QueryRoute.SEMANTIC,
        ),
        (
            'Find exact phrase "context-engine-prod-rds"',
            QueryRoute.BM25,
        ),
        (
            "How many records were created in Q3?",
            QueryRoute.SQL,
        ),
        (
            "How is Alice connected to Bob?",
            QueryRoute.GRAPH,
        ),
        (
            "Define vectorless RAG in the documentation",
            QueryRoute.WIKI,
        ),
        (
            "Compare exact GDPR mentions and total incident counts across departments",
            QueryRoute.HYBRID,
        ),
    ],
)
async def test_router_selects_expected_route(query: str, expected_route: QueryRoute) -> None:
    """Heuristic router selects the expected retrieval route for representative queries."""
    assert await route_query(query) == expected_route


def test_query_request_rejects_empty_or_whitespace_query() -> None:
    """Empty and whitespace-only queries fail before routing."""
    with pytest.raises(ValidationError):
        QueryRequest(query="")

    with pytest.raises(ValidationError):
        QueryRequest(query="   ")


async def test_route_decision_metadata_shape_is_stable() -> None:
    """Route decisions expose the classifier-compatible metadata shape."""
    router = RetrievalRouter()
    decision = await router.route(QueryRequest(query="Which design risks matter most?"))
    payload = decision.model_dump()

    assert set(payload) == {"route", "confidence", "reasoning", "entities"}
    assert isinstance(decision.route, QueryRoute)
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.reasoning
    assert isinstance(decision.entities, list)
