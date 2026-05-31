from collections.abc import Sequence

from app.schemas.query import SourceCitation, VerificationResult
from app.verification.confidence import score_confidence


def verify_response(
    query: str,
    answer: str,
    sources: Sequence[SourceCitation],
    route_confidence: float,
) -> VerificationResult:
    """Return a placeholder verification result for a generated answer."""
    grounded = bool(query and answer and sources)
    return VerificationResult(
        grounded=grounded,
        conflicts=[],
        confidence=score_confidence(sources, route_confidence),
    )
