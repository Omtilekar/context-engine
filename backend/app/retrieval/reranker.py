import importlib
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.query import SourceCitation

logger = get_logger(__name__)

FLASHRANK_MODEL_NAME = "ms-marco-MiniLM-L-12-v2"


class SourceReranker(Protocol):
    """Interface for local source rerankers."""

    async def rerank(
        self,
        query: str,
        sources: list[SourceCitation],
        top_k: int,
    ) -> list[SourceCitation]:
        """Rerank sources for a query."""


class DisabledReranker:
    """No-op reranker used by default for local development and tests."""

    async def rerank(
        self,
        query: str,
        sources: list[SourceCitation],
        top_k: int,
    ) -> list[SourceCitation]:
        """Return merged sources in their existing score order."""
        return sources[: max(top_k, 0)]


class FlashRankReranker:
    """Optional FlashRank reranker with safe fallback semantics."""

    def __init__(self) -> None:
        """Create a FlashRank reranker if the optional package is installed."""
        self._ranker: Any | None = None
        self._request_cls: Any | None = None

    async def rerank(
        self,
        query: str,
        sources: list[SourceCitation],
        top_k: int,
    ) -> list[SourceCitation]:
        """Rerank merged text sources using FlashRank when available."""
        if top_k <= 0 or not sources:
            return []

        try:
            ranker, request_cls = self._load_flashrank()
            passages = [
                {
                    "id": str(index),
                    "text": source.snippet,
                    "meta": {"source_index": index},
                }
                for index, source in enumerate(sources)
            ]
            request = request_cls(query=query, passages=passages)
            ranked_passages = ranker.rerank(request)
        except Exception as error:
            logger.warning("FlashRank reranking failed", extra={"error": str(error)})
            return sources[:top_k]

        reranked_sources: list[SourceCitation] = []
        for passage in ranked_passages[:top_k]:
            source_index = int(passage["meta"]["source_index"])
            score = float(passage.get("score", sources[source_index].score))
            source = sources[source_index]
            metadata = {
                **source.metadata,
                "reranker": "flashrank",
                "reranker_score": f"{score:.6f}",
            }
            reranked_sources.append(
                source.model_copy(
                    update={
                        "score": max(0.0, min(1.0, round(score, 4))),
                        "metadata": metadata,
                    },
                    deep=True,
                )
            )
        return reranked_sources

    def _load_flashrank(self) -> tuple[Any, Any]:
        """Load FlashRank lazily so normal tests do not import or download models."""
        if self._ranker is None or self._request_cls is None:
            flashrank: Any = importlib.import_module("flashrank")
            ranker_cls = flashrank.Ranker
            request_cls = flashrank.RerankRequest
            self._ranker = ranker_cls(model_name=FLASHRANK_MODEL_NAME)
            self._request_cls = request_cls
        return self._ranker, self._request_cls


def get_reranker() -> SourceReranker:
    """Return the configured reranker implementation."""
    settings = get_settings()
    if settings.reranker_mode == "flashrank":
        return FlashRankReranker()
    return DisabledReranker()


async def rerank_sources(
    query: str,
    sources: list[SourceCitation],
    top_k: int,
    reranker: SourceReranker | None = None,
) -> list[SourceCitation]:
    """Rerank sources using the configured reranker with no-fail fallback."""
    if top_k <= 0 or not sources:
        return []
    active_reranker = reranker or get_reranker()
    try:
        return await active_reranker.rerank(query, sources, top_k)
    except Exception as error:
        logger.warning("Reranker fallback used", extra={"error": str(error)})
        return sources[:top_k]
