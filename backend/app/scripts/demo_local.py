import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from textwrap import shorten

from app.db.connection import close_database_connections
from app.ingestion.pipeline import IngestionPipeline
from app.main import query
from app.schemas.document import DocumentIngestRequest, IngestResponse, SourceType
from app.schemas.query import QueryRequest, QueryResponse, QueryRoute
from app.scripts.seed_local import (
    seed_graph_relations,
    seed_product_catalog,
    seed_wiki_pages,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def default_demo_data_dir() -> Path:
    """Resolve demo data for both host virtualenv and Docker Compose runs."""
    repo_data_dir = REPO_ROOT / "demo" / "data"
    if repo_data_dir.exists():
        return repo_data_dir
    return Path("/demo/data")


DEMO_DATA_DIR = default_demo_data_dir()


@dataclass(frozen=True, slots=True)
class DemoQuestion:
    """One portfolio demo query and its expected route."""

    route: QueryRoute
    question: str
    description: str


SAMPLE_QUERIES: tuple[DemoQuestion, ...] = (
    DemoQuestion(
        route=QueryRoute.WIKI,
        question="What is ContextEngine?",
        description="Wiki memory definition route",
    ),
    DemoQuestion(
        route=QueryRoute.SEMANTIC,
        question="Which retrieval approach finds similar meaning in stored chunks?",
        description="pgvector semantic route",
    ),
    DemoQuestion(
        route=QueryRoute.BM25,
        question="Find exact keyword FlashRank",
        description="BM25 keyword route",
    ),
    DemoQuestion(
        route=QueryRoute.SQL,
        question="How many software products cost more than 100?",
        description="Structured SQL route; requires OPENAI_API_KEY for SQL rows",
    ),
    DemoQuestion(
        route=QueryRoute.GRAPH,
        question="Which entities are linked to ContextEngine?",
        description="PostgreSQL entity_relations graph route",
    ),
    DemoQuestion(
        route=QueryRoute.HYBRID,
        question="Compare exact keyword search and semantic search for ContextEngine",
        description="Hybrid semantic plus keyword route",
    ),
)


def demo_data_files(data_dir: Path = DEMO_DATA_DIR) -> list[Path]:
    """Return sorted demo text documents."""
    return sorted(data_dir.glob("*.txt"))


def title_from_path(path: Path) -> str:
    """Build a readable document title from a demo filename."""
    return path.stem.replace("_", " ").title()


def load_demo_documents(data_dir: Path = DEMO_DATA_DIR) -> list[DocumentIngestRequest]:
    """Load local demo text files as ingestion requests."""
    documents: list[DocumentIngestRequest] = []
    for path in demo_data_files(data_dir):
        documents.append(
            DocumentIngestRequest(
                source_type=SourceType.TEXT,
                title=title_from_path(path),
                filename=path.name,
                content=path.read_text(encoding="utf-8"),
                metadata={
                    "demo": "portfolio",
                    "filename": path.name,
                    "topic": path.stem.replace("_", "-"),
                },
            )
        )
    return documents


async def seed_demo_knowledge() -> None:
    """Seed local-only SQL, graph, and wiki data used by the portfolio demo."""
    await seed_product_catalog()
    await seed_graph_relations()
    await seed_wiki_pages()


async def ingest_demo_documents(
    documents: Sequence[DocumentIngestRequest] | None = None,
) -> list[IngestResponse]:
    """Ingest demo documents through the real ingestion pipeline."""
    pipeline = IngestionPipeline()
    demo_documents = list(documents) if documents is not None else load_demo_documents()
    responses: list[IngestResponse] = []
    for document in demo_documents:
        responses.append(await pipeline.ingest(document))
    return responses


async def run_demo_queries(
    questions: Sequence[DemoQuestion] = SAMPLE_QUERIES,
) -> list[QueryResponse]:
    """Run the sample route-coverage queries through the real query pipeline."""
    responses: list[QueryResponse] = []
    for demo_question in questions:
        responses.append(await query(QueryRequest(query=demo_question.question, top_k=5)))
    return responses


def format_demo_result(question: DemoQuestion, response: QueryResponse) -> str:
    """Render one query response for readable terminal output."""
    citations = [
        f"  - {citation.title} ({citation.retrieval_mode}, {citation.score:.2f})"
        for citation in response.citations
    ] or ["  - none"]
    audit_ids = []
    if response.query_log_id is not None:
        audit_ids.append(f"query_log_id={response.query_log_id}")
    if response.retrieval_run_id is not None:
        audit_ids.append(f"retrieval_run_id={response.retrieval_run_id}")
    audit_line = ", ".join(audit_ids) if audit_ids else "audit persistence skipped"

    return "\n".join(
        [
            "",
            f"Question: {question.question}",
            f"Expected route: {question.route.value} | Selected route: "
            f"{response.route_decision.route.value} "
            f"({response.route_decision.confidence:.2f})",
            f"Confidence: {response.confidence.label} ({response.confidence.score:.2f})",
            f"Sources: {len(response.sources)} | Citations: {len(response.citations)}",
            f"Audit: {audit_line}",
            f"Answer: {shorten(response.answer, width=420, placeholder='...')}",
            "Citations:",
            *citations,
        ]
    )


async def run_demo() -> list[QueryResponse]:
    """Run the complete local portfolio demo."""
    documents = load_demo_documents()
    print("ContextEngine local portfolio demo")
    print(f"Demo documents: {len(documents)} from {DEMO_DATA_DIR}")

    print("\nSeeding wiki, graph, and local SQL demo data...")
    await seed_demo_knowledge()

    print("\nIngesting demo documents...")
    ingest_responses = await ingest_demo_documents(documents)
    completed = sum(response.status == "completed" for response in ingest_responses)
    chunks = sum(response.chunk_count for response in ingest_responses)
    print(f"Ingested {completed}/{len(ingest_responses)} documents with {chunks} chunks.")

    print("\nRunning route coverage queries...")
    query_responses: list[QueryResponse] = []
    for demo_question in SAMPLE_QUERIES:
        response = await query(QueryRequest(query=demo_question.question, top_k=5))
        query_responses.append(response)
        print(format_demo_result(demo_question, response))

    return query_responses


async def main() -> None:
    """Run the local demo and close database resources."""
    try:
        await run_demo()
    finally:
        await close_database_connections()


if __name__ == "__main__":
    asyncio.run(main())
