import asyncio
import json

from openai.types.chat.completion_create_params import ResponseFormat as OpenAIResponseFormat

from app.core.config import get_settings
from app.core.logging import get_logger
from app.embeddings.provider import get_embedding_provider
from app.retrieval.graph import retrieve_graph
from app.retrieval.keyword import retrieve_keyword
from app.retrieval.merger import merge_sources
from app.retrieval.reranker import rerank_sources
from app.retrieval.semantic import retrieve_semantic
from app.retrieval.sql import retrieve_sql
from app.retrieval.wiki import retrieve_wiki
from app.schemas.query import QueryRequest, QueryRoute, RouteDecision, SourceCitation

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Few-shot examples — 10 per route, built once at module load
# (query, route, confidence, reasoning, entities)
# ---------------------------------------------------------------------------

_FEW_SHOT_EXAMPLES: list[tuple[str, str, float, str, list[str]]] = [
    # wiki
    (
        "What is ContextEngine?",
        "wiki",
        0.97,
        "Requests a definition of a known system.",
        ["ContextEngine"],
    ),
    (
        "Explain pgvector",
        "wiki",
        0.95,
        "Asks for an explanation of a known technology.",
        ["pgvector"],
    ),
    ("Define Hybrid RAG", "wiki", 0.95, "Requests a definition of a technique.", ["Hybrid RAG"]),
    (
        "Documentation for PostgreSQL full-text search",
        "wiki",
        0.93,
        "Requests reference documentation.",
        ["PostgreSQL"],
    ),
    (
        "Overview of FlashRank reranking",
        "wiki",
        0.92,
        "Asks for an overview of a component.",
        ["FlashRank"],
    ),
    (
        "What are wiki pages in ContextEngine?",
        "wiki",
        0.90,
        "Asks for a definition of a component.",
        ["wiki pages", "ContextEngine"],
    ),
    (
        "Guide to entity relation tables",
        "wiki",
        0.88,
        "Requests a usage guide for a component.",
        ["entity relation tables"],
    ),
    (
        "Tutorial for semantic search",
        "wiki",
        0.88,
        "Requests a tutorial for a feature.",
        ["semantic search"],
    ),
    (
        "How does BM25 work?",
        "wiki",
        0.87,
        "Asks for an explanation of a known algorithm.",
        ["BM25"],
    ),
    (
        "What is a vector database?",
        "wiki",
        0.86,
        "Requests a definition of a concept.",
        ["vector database"],
    ),
    # semantic
    (
        "Which retrieval approach finds similar meaning?",
        "semantic",
        0.90,
        "Asks a conceptual question about retrieval.",
        [],
    ),
    (
        "What are the main risks in RAG systems?",
        "semantic",
        0.88,
        "Open-ended question about risks.",
        ["RAG"],
    ),
    (
        "How does context compression improve answers?",
        "semantic",
        0.87,
        "Asks conceptually about a technique.",
        ["context compression"],
    ),
    (
        "What techniques improve retrieval quality?",
        "semantic",
        0.86,
        "Conceptual question about improvement approaches.",
        [],
    ),
    (
        "Why would you use hybrid retrieval?",
        "semantic",
        0.85,
        "Asks for reasoning about a design choice.",
        ["hybrid retrieval"],
    ),
    (
        "How should I handle conflicting sources?",
        "semantic",
        0.85,
        "Conceptual question about source conflicts.",
        [],
    ),
    (
        "What makes a good confidence score?",
        "semantic",
        0.84,
        "Asks for conceptual criteria.",
        ["confidence score"],
    ),
    (
        "Which approach best handles ambiguous queries?",
        "semantic",
        0.84,
        "Asks about handling ambiguity.",
        [],
    ),
    (
        "How does source grounding work?",
        "semantic",
        0.83,
        "Asks for understanding of a verification step.",
        ["source grounding"],
    ),
    (
        "What factors affect retrieval relevance?",
        "semantic",
        0.82,
        "Open-ended question about relevance factors.",
        [],
    ),
    # bm25
    (
        "Find exact keyword FlashRank",
        "bm25",
        0.97,
        "Explicit exact keyword search request.",
        ["FlashRank"],
    ),
    (
        "Find all mentions of pgvector in the documents",
        "bm25",
        0.96,
        "Requests keyword mentions lookup.",
        ["pgvector"],
    ),
    (
        'Show every occurrence of "hybrid retrieval"',
        "bm25",
        0.96,
        "Quoted phrase requests exact match.",
        ["hybrid retrieval"],
    ),
    (
        "Exact phrase 'entity_relations table'",
        "bm25",
        0.95,
        "Explicit exact phrase request.",
        ["entity_relations table"],
    ),
    ("Find keyword 'HNSW index'", "bm25", 0.95, "Explicit keyword search.", ["HNSW index"]),
    (
        "Locate all instances of 'confidence score'",
        "bm25",
        0.94,
        "Exact keyword location request.",
        ["confidence score"],
    ),
    (
        "Search for exact match 'text-embedding-3-small'",
        "bm25",
        0.94,
        "Explicit exact match search.",
        ["text-embedding-3-small"],
    ),
    (
        "Find the phrase 'BM25 keyword retrieval'",
        "bm25",
        0.93,
        "Exact phrase search request.",
        ["BM25 keyword retrieval"],
    ),
    (
        "Show documents mentioning 'HNSW index'",
        "bm25",
        0.93,
        "Keyword mention search in documents.",
        ["HNSW index"],
    ),
    ("Keyword search for asyncpg", "bm25", 0.92, "Explicit keyword search request.", ["asyncpg"]),
    # sql
    (
        "How many software products cost more than 100?",
        "sql",
        0.97,
        "Asks for a filtered numeric count.",
        ["software products"],
    ),
    (
        "Count the total number of documents ingested",
        "sql",
        0.96,
        "Asks for a total count.",
        ["documents"],
    ),
    (
        "What is the average confidence score across queries?",
        "sql",
        0.95,
        "Asks for an aggregate average.",
        ["confidence score"],
    ),
    (
        "How many queries were logged today?",
        "sql",
        0.95,
        "Asks for a time-filtered count.",
        ["queries"],
    ),
    (
        "Sum of all token costs this week",
        "sql",
        0.94,
        "Asks for an aggregate sum.",
        ["token costs"],
    ),
    (
        "Total number of wiki pages in the system",
        "sql",
        0.93,
        "Asks for a total count.",
        ["wiki pages"],
    ),
    (
        "How many products are in the Software category?",
        "sql",
        0.93,
        "Asks for a filtered count.",
        ["products", "Software"],
    ),
    (
        "Average latency by retrieval route",
        "sql",
        0.92,
        "Asks for a grouped average.",
        ["latency", "retrieval route"],
    ),
    (
        "Count of entity relations grouped by relation type",
        "sql",
        0.92,
        "Asks for a grouped count.",
        ["entity relations"],
    ),
    (
        "How many chunks have no embedding?",
        "sql",
        0.91,
        "Asks for a filtered count.",
        ["chunks", "embedding"],
    ),
    # graph
    (
        "Which entities are linked to ContextEngine?",
        "graph",
        0.97,
        "Asks for entity connections.",
        ["ContextEngine"],
    ),
    (
        "How is pgvector related to PostgreSQL?",
        "graph",
        0.96,
        "Asks about a relationship between entities.",
        ["pgvector", "PostgreSQL"],
    ),
    (
        "What is connected to FlashRank?",
        "graph",
        0.95,
        "Asks for connections to a named entity.",
        ["FlashRank"],
    ),
    (
        "Who works with the verification layer?",
        "graph",
        0.94,
        "Asks about relationships involving a component.",
        ["verification layer"],
    ),
    (
        "Show relationships for AWS in the graph",
        "graph",
        0.94,
        "Requests relationship traversal for an entity.",
        ["AWS"],
    ),
    (
        "What does ContextEngine use?",
        "graph",
        0.93,
        "Asks for outgoing relationships.",
        ["ContextEngine"],
    ),
    (
        "Which entities are linked to the graph retriever?",
        "graph",
        0.93,
        "Asks for connections to a component.",
        ["graph retriever"],
    ),
    (
        "What is deployed on ECS Fargate?",
        "graph",
        0.92,
        "Asks about a deployment relationship.",
        ["ECS Fargate"],
    ),
    (
        "What relationship exists between pgvector and chunks?",
        "graph",
        0.92,
        "Asks about a specific relationship.",
        ["pgvector", "chunks"],
    ),
    (
        "Show all connections to the wiki memory layer",
        "graph",
        0.91,
        "Requests connection traversal.",
        ["wiki memory layer"],
    ),
    # hybrid
    (
        "Compare exact keyword search and semantic search for ContextEngine",
        "hybrid",
        0.95,
        "Comparison query combining multiple retrieval modes.",
        ["ContextEngine"],
    ),
    (
        "Tell me everything about the retrieval pipeline",
        "hybrid",
        0.94,
        "Broad comprehensive query.",
        ["retrieval pipeline"],
    ),
    (
        "Combine graph and wiki information about PostgreSQL",
        "hybrid",
        0.93,
        "Explicitly requests multiple retrieval modes.",
        ["PostgreSQL"],
    ),
    (
        "Give me a complete overview of all retrieval approaches",
        "hybrid",
        0.93,
        "Broad overview across multiple topics.",
        [],
    ),
    (
        "Both the exact mentions and semantic meaning of hybrid RAG",
        "hybrid",
        0.92,
        "Requests both keyword and semantic retrieval.",
        ["hybrid RAG"],
    ),
    (
        "Compare all retrieval modes and their performance",
        "hybrid",
        0.92,
        "Comparison across multiple modes.",
        [],
    ),
    (
        "Across all sources, what do we know about FlashRank?",
        "hybrid",
        0.91,
        "Cross-source comprehensive query.",
        ["FlashRank"],
    ),
    (
        "Everything about ContextEngine's architecture",
        "hybrid",
        0.91,
        "Broad everything query.",
        ["ContextEngine"],
    ),
    (
        "Compare and contrast wiki and semantic retrieval",
        "hybrid",
        0.90,
        "Explicit comparison of two retrieval modes.",
        ["wiki retrieval", "semantic retrieval"],
    ),
    (
        "All information about the verification and confidence pipeline",
        "hybrid",
        0.90,
        "All-information query spanning multiple topics.",
        ["verification", "confidence"],
    ),
]

_EXAMPLES_BLOCK = "\n".join(
    json.dumps(
        {
            "query": q,
            "route": r,
            "confidence": c,
            "reasoning": reason,
            "entities": entities,
        },
        separators=(",", ":"),
    )
    for q, r, c, reason, entities in _FEW_SHOT_EXAMPLES
)

_ROUTE_DESCRIPTIONS = (
    "Classify the user query into exactly one of these six routes:\n"
    '- wiki: Definitions, documentation, "what is", "explain", "overview", guides, tutorials\n'
    "- semantic: Conceptual, meaning-based questions needing similarity search\n"
    '- bm25: Exact keyword/phrase matching — "find all mentions", "exact phrase", quoted text\n'
    '- sql: Numeric/aggregate queries — "how many", "count", "sum", "average", "total"\n'
    '- graph: Relationship queries — "linked to", "related to", "connected to", "who works with"\n'
    "- hybrid: Broad, multi-faceted, or comparison queries that need multiple retrieval modes"
)

_JSON_SCHEMA_EXAMPLE = (
    '{"route":"wiki|semantic|bm25|sql|graph|hybrid",'
    '"confidence":0.0-1.0,'
    '"reasoning":"one sentence",'
    '"entities":["EntityA","EntityB"]}'
)

_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a query router for ContextEngine, a hybrid RAG system.\n\n"
    f"{_ROUTE_DESCRIPTIONS}\n\n"
    "Respond with valid JSON only — no explanation outside the JSON:\n"
    f"{_JSON_SCHEMA_EXAMPLE}\n\n"
    f"Examples (one per line):\n{_EXAMPLES_BLOCK}"
)

_JSON_RESPONSE_FORMAT: OpenAIResponseFormat = {"type": "json_object"}


async def _classify_with_llm(query: str) -> RouteDecision | None:
    """Call GPT-4o-mini to classify the query into one of six retrieval routes.

    Args:
        query: User query text to classify.

    Returns:
        RouteDecision from the LLM, or None if the LLM is unavailable or fails.
        None triggers the heuristic fallback in RetrievalRouter.route().
    """
    settings = get_settings()
    if not settings.llm_classifier_enabled:
        return None

    api_key = settings.openai_api_key
    if not api_key:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format=_JSON_RESPONSE_FORMAT,
            messages=[
                {"role": "system", "content": _CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        raw = response.choices[0].message.content or "{}"
        data: dict[str, object] = json.loads(raw)

        route_str = str(data.get("route", "")).strip().lower()
        route = QueryRoute(route_str)

        raw_confidence = data.get("confidence", 0.7)
        confidence = float(raw_confidence if isinstance(raw_confidence, int | float) else 0.7)
        confidence = max(0.0, min(1.0, confidence))

        reasoning = str(data.get("reasoning", "LLM classification"))

        raw_entities = data.get("entities", [])
        entities = [str(e) for e in raw_entities] if isinstance(raw_entities, list) else []

        return RouteDecision(
            route=route,
            confidence=confidence,
            reasoning=reasoning,
            entities=entities,
        )
    except Exception as error:
        logger.warning(
            "LLM classifier failed — falling back to heuristic",
            extra={"error": str(error)},
        )
        return None


class RetrievalRouter:
    """Query router that tries GPT-4o-mini classification first and falls back to heuristics."""

    async def route(self, request: QueryRequest) -> RouteDecision:
        """Classify the query into one of six retrieval routes.

        Tries the LLM classifier first. Falls back to keyword heuristics when
        the LLM is unavailable, the API key is missing, or the call fails.
        """
        llm_decision = await _classify_with_llm(request.query)
        if llm_decision is not None:
            return llm_decision
        return self._heuristic_route(request.query)

    def _heuristic_route(self, query_text: str) -> RouteDecision:
        """Classify query using keyword heuristics — fallback when LLM is unavailable.

        Args:
            query_text: Raw user query string.

        Returns:
            RouteDecision based on term-matching heuristics.
        """
        query = query_text.strip().lower()
        sql_terms = ("how many", "count", "sum", "average", "total", "group by", "records")
        graph_terms = (
            "who works with",
            "relationship",
            "relationships",
            "connected to",
            "related to",
            "linked to",
            "association",
            "dependency",
            "dependencies",
            "graph",
            "between",
        )
        keyword_terms = ("exact", "mentions", "keyword", "phrase", '"')
        wiki_terms = (
            "what is",
            "what are",
            "define",
            "definition",
            "explain",
            "documentation",
            "docs",
            "guide",
            "tutorial",
            "how does",
            "overview",
            "wiki",
        )
        hybrid_terms = ("everything", "compare", "all about", "combine", "both", "across")

        signals = {
            QueryRoute.SQL: any(term in query for term in sql_terms),
            QueryRoute.GRAPH: any(term in query for term in graph_terms),
            QueryRoute.BM25: any(term in query for term in keyword_terms),
            QueryRoute.WIKI: any(term in query for term in wiki_terms),
        }
        if any(term in query for term in hybrid_terms) or sum(signals.values()) >= 2:
            return RouteDecision(
                route=QueryRoute.HYBRID,
                confidence=0.82,
                reasoning="The query is broad or combines signals from multiple retrieval modes.",
                entities=[],
            )
        if signals[QueryRoute.SQL]:
            return RouteDecision(
                route=QueryRoute.SQL,
                confidence=0.78,
                reasoning="The query asks for structured or numerical information.",
                entities=[],
            )
        if signals[QueryRoute.GRAPH]:
            return RouteDecision(
                route=QueryRoute.GRAPH,
                confidence=0.74,
                reasoning="The query asks about relationships between entities.",
                entities=[],
            )
        if signals[QueryRoute.BM25]:
            return RouteDecision(
                route=QueryRoute.BM25,
                confidence=0.72,
                reasoning="The query appears to require exact lexical matching.",
                entities=[],
            )
        if signals[QueryRoute.WIKI]:
            return RouteDecision(
                route=QueryRoute.WIKI,
                confidence=0.7,
                reasoning="The query can benefit from synthesized wiki memory.",
                entities=[],
            )
        return RouteDecision(
            route=QueryRoute.SEMANTIC,
            confidence=0.66,
            reasoning="The query is best handled as a meaning-based semantic lookup.",
            entities=[],
        )

    async def retrieve(
        self,
        request: QueryRequest,
        route_decision: RouteDecision,
    ) -> list[SourceCitation]:
        """Dispatch retrieval to the selected route."""
        if route_decision.route == QueryRoute.WIKI:
            wiki_sources = await retrieve_wiki(request.query, request.top_k)
            return await self._merge_and_rerank(request, [wiki_sources])
        if route_decision.route == QueryRoute.SEMANTIC:
            query_embedding = await get_embedding_provider().embed_query(request.query)
            semantic_sources = await retrieve_semantic(
                request.query, request.top_k, query_embedding
            )
            return await self._merge_and_rerank(request, [semantic_sources])
        if route_decision.route == QueryRoute.BM25:
            keyword_sources = await retrieve_keyword(request.query, request.top_k)
            return await self._merge_and_rerank(request, [keyword_sources])
        if route_decision.route == QueryRoute.SQL:
            return await retrieve_sql(request.query, request.top_k)
        if route_decision.route == QueryRoute.GRAPH:
            return await retrieve_graph(request.query, request.top_k)

        query_embedding = await get_embedding_provider().embed_query(request.query)
        retriever_calls = [
            retrieve_semantic(request.query, request.top_k, query_embedding),
            retrieve_keyword(request.query, request.top_k),
        ]
        if should_include_sql_in_hybrid(request.query):
            retriever_calls.append(retrieve_sql(request.query, request.top_k))

        results = await asyncio.gather(*retriever_calls)
        merged_sources = merge_sources(results, top_k=request.top_k)
        return await rerank_hybrid_sources(request.query, merged_sources, request.top_k)

    async def _merge_and_rerank(
        self,
        request: QueryRequest,
        source_groups: list[list[SourceCitation]],
    ) -> list[SourceCitation]:
        """Merge and rerank one or more source groups."""
        merged_sources = merge_sources(source_groups, top_k=request.top_k)
        return await rerank_sources(request.query, merged_sources, request.top_k)


def should_include_sql_in_hybrid(query: str) -> bool:
    """Return whether a hybrid query should include optional SQL retrieval."""
    normalized_query = query.lower()
    return any(
        term in normalized_query
        for term in ("how many", "count", "sum", "average", "total", "group by", "records")
    )


async def rerank_hybrid_sources(
    query: str,
    merged_sources: list[SourceCitation],
    top_k: int,
) -> list[SourceCitation]:
    """Rerank text retrieval sources while preserving SQL snippets safely."""
    sql_sources = [source for source in merged_sources if source.source_type == QueryRoute.SQL]
    text_sources = [source for source in merged_sources if source.source_type != QueryRoute.SQL]
    reranked_text_sources = await rerank_sources(query, text_sources, top_k)
    combined_sources = [*reranked_text_sources, *sql_sources]
    combined_sources.sort(
        key=lambda source: (
            -source.score,
            source.title.lower(),
            source.snippet.lower(),
        )
    )
    return combined_sources[:top_k]
