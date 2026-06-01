from pathlib import Path

from app.retrieval.router import RetrievalRouter
from app.schemas.document import SourceType
from app.schemas.query import QueryRequest, QueryRoute
from app.scripts.demo_local import (
    DEMO_DATA_DIR,
    SAMPLE_QUERIES,
    demo_data_files,
    ingest_demo_documents,
    load_demo_documents,
    run_demo,
    run_demo_queries,
    seed_demo_knowledge,
)


def test_demo_data_files_exist_and_cover_portfolio_topics() -> None:
    """The portfolio dataset contains small text files for the local demo."""
    files = demo_data_files()
    names = {path.name for path in files}

    assert DEMO_DATA_DIR == Path(__file__).resolve().parents[3] / "demo" / "data"
    assert 5 <= len(files) <= 8
    assert names == {
        "aws_deployment_cost_controls.txt",
        "bm25_keyword_retrieval.txt",
        "graph_rag_relationships.txt",
        "hybrid_rag_overview.txt",
        "pgvector_semantic_search.txt",
        "portfolio_demo_script.txt",
        "verification_confidence.txt",
    }
    assert all(path.read_text(encoding="utf-8").strip() for path in files)


def test_demo_script_functions_are_importable() -> None:
    """Importing the demo script should not touch a live database."""
    assert callable(seed_demo_knowledge)
    assert callable(ingest_demo_documents)
    assert callable(run_demo_queries)
    assert callable(run_demo)


def test_load_demo_documents_returns_text_ingest_requests() -> None:
    """Demo data is converted into text ingestion requests with metadata."""
    documents = load_demo_documents()

    assert len(documents) == len(demo_data_files())
    assert all(document.source_type == SourceType.TEXT for document in documents)
    assert all(document.content for document in documents)
    assert all(document.filename and document.filename.endswith(".txt") for document in documents)
    assert all(document.metadata["demo"] == "portfolio" for document in documents)
    assert all("topic" in document.metadata for document in documents)


def test_sample_query_list_covers_all_routes() -> None:
    """The local demo has one sample query for every public retrieval route."""
    assert {demo_query.route for demo_query in SAMPLE_QUERIES} == {
        QueryRoute.WIKI,
        QueryRoute.SEMANTIC,
        QueryRoute.BM25,
        QueryRoute.SQL,
        QueryRoute.GRAPH,
        QueryRoute.HYBRID,
    }


async def test_sample_queries_route_as_declared() -> None:
    """Route-coverage demo questions match the heuristic router."""
    router = RetrievalRouter()

    for demo_query in SAMPLE_QUERIES:
        decision = await router.route(QueryRequest(query=demo_query.question))
        assert decision.route == demo_query.route
