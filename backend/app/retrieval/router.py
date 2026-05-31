import asyncio

from app.embeddings.provider import get_embedding_provider
from app.retrieval.graph import retrieve_graph
from app.retrieval.keyword import retrieve_keyword
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
            "connected to",
            "related to",
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
            return await retrieve_semantic(request.query, request.top_k, query_embedding)
        if route_decision.route == QueryRoute.BM25:
            return await retrieve_keyword(request.query, request.top_k)
        if route_decision.route == QueryRoute.SQL:
            return await retrieve_sql(request.query, request.top_k)
        if route_decision.route == QueryRoute.GRAPH:
            return await retrieve_graph(request.query, request.top_k)

        query_embedding = await get_embedding_provider().embed_query(request.query)
        results = await asyncio.gather(
            retrieve_wiki(request.query, request.top_k),
            retrieve_semantic(request.query, request.top_k, query_embedding),
            retrieve_keyword(request.query, request.top_k),
            retrieve_graph(request.query, request.top_k),
        )
        return [source for retriever_results in results for source in retriever_results]
