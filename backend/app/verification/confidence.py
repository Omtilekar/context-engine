from collections.abc import Sequence

from app.schemas.query import SourceCitation


def score_confidence(sources: Sequence[SourceCitation], route_confidence: float) -> float:
    """Score answer confidence from route confidence and placeholder source evidence."""
    if not sources:
        return round(route_confidence * 0.5, 2)

    average_source_score = sum(source.score for source in sources) / len(sources)
    blended = (route_confidence * 0.7) + (average_source_score * 0.3)
    return round(max(0.0, min(1.0, blended)), 2)
