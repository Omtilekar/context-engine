import asyncio

from app.embeddings.provider import get_embedding_provider
from app.retrieval.graph import retrieve_graph
from app.retrieval.keyword import retrieve_keyword
from app.retrieval.merger import merge_sources
from app.retrieval.reranker import rerank_sources
from app.retrieval.semantic import retrieve_semantic
from app.retrieval.sql import retrieve_sql
from app.retrieval.wiki import retrieve_wiki
from app.schemas.query import QueryRequest, QueryRoute, RouteDecision, SourceCitation


class RetrievalRouter:
    """Heuristic retrieval router used until the LLM classifier is added."""

    async def route(self, request: QueryRequest) -> RouteDecision:
        """Classify the query into one of the six retrieval routes."""
        query = request.query.strip().lower()
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
        wiki_terms = ("what is", "define", "explain", "documentation", "docs", "overview", "wiki")
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
        """Run the placeholder retriever for the selected route."""
        if route_decision.route == QueryRoute.WIKI:
            return await retrieve_wiki(request.query, request.top_k)
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
