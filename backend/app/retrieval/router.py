import asyncio

from app.retrieval.graph import retrieve_graph
from app.retrieval.keyword import retrieve_keyword
from app.retrieval.semantic import retrieve_semantic
from app.retrieval.structured import retrieve_structured
from app.retrieval.wiki import retrieve_wiki
from app.schemas.query import QueryRequest, QueryRoute, RouteDecision, SourceCitation


class RetrievalRouter:
    """Heuristic retrieval router used until the LLM classifier is added."""

    async def route(self, request: QueryRequest) -> RouteDecision:
        """Classify the query into one of the six retrieval routes."""
        query = request.query.lower()
        if any(term in query for term in ("how many", "count", "sum", "average", "total")):
            return RouteDecision(
                route=QueryRoute.SQL,
                confidence=0.78,
                reasoning="The query asks for structured or numerical information.",
                entities=[],
            )
        if any(term in query for term in ("who works with", "relationship", "connected to")):
            return RouteDecision(
                route=QueryRoute.GRAPH,
                confidence=0.74,
                reasoning="The query asks about relationships between entities.",
                entities=[],
            )
        if any(term in query for term in ("exact", "mentions", "keyword", '"')):
            return RouteDecision(
                route=QueryRoute.BM25,
                confidence=0.72,
                reasoning="The query appears to require exact lexical matching.",
                entities=[],
            )
        if any(term in query for term in ("what did", "summary", "overview", "wiki")):
            return RouteDecision(
                route=QueryRoute.WIKI,
                confidence=0.7,
                reasoning="The query can benefit from synthesized wiki memory.",
                entities=[],
            )
        if any(term in query for term in ("everything", "compare", "all about")):
            return RouteDecision(
                route=QueryRoute.HYBRID,
                confidence=0.69,
                reasoning="The query is broad and benefits from multiple retrievers.",
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
            return await retrieve_semantic(request.query, request.top_k)
        if route_decision.route == QueryRoute.BM25:
            return await retrieve_keyword(request.query, request.top_k)
        if route_decision.route == QueryRoute.SQL:
            return await retrieve_structured(request.query, request.top_k)
        if route_decision.route == QueryRoute.GRAPH:
            return await retrieve_graph(request.query, request.top_k)

        results = await asyncio.gather(
            retrieve_wiki(request.query, request.top_k),
            retrieve_semantic(request.query, request.top_k),
            retrieve_keyword(request.query, request.top_k),
            retrieve_graph(request.query, request.top_k),
        )
        return [source for retriever_results in results for source in retriever_results]
