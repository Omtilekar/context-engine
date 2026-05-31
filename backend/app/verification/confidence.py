from collections.abc import Sequence
from typing import Literal

from app.schemas.query import ConfidenceResult, SourceCitation, VerificationResult

HIGH_CONFIDENCE_THRESHOLD = 0.75
MEDIUM_CONFIDENCE_THRESHOLD = 0.45


def score_confidence(
    sources: Sequence[SourceCitation],
    route_confidence: float,
    verification: VerificationResult | None = None,
) -> ConfidenceResult:
    """Score answer confidence from routing, evidence, diversity, and verification signals.

    Args:
        sources: Retrieved source citations used for answer generation.
        route_confidence: Confidence from the query router.
        verification: Optional deterministic verification result.

    Returns:
        A bounded confidence result with a label and explainable reasons.
    """
    evidence_count = verification.evidence_count if verification else len(sources)
    retrieval_modes = (
        verification.retrieval_modes if verification else collect_retrieval_modes(sources)
    )
    warnings = verification.warnings if verification else []
    has_conflicts = verification.has_conflicts if verification else False

    normalized_route = normalize_score(route_confidence)
    average_source_score = average_normalized_source_score(sources)
    count_score = min(evidence_count, 4) / 4
    diversity_score = min(len(retrieval_modes), 3) / 3

    raw_score = (
        normalized_route * 0.35
        + average_source_score * 0.35
        + count_score * 0.15
        + diversity_score * 0.15
    )
    penalty = confidence_penalty(evidence_count, warnings, has_conflicts)
    score = round(normalize_score(raw_score - penalty), 2)
    reasons = confidence_reasons(
        route_confidence=normalized_route,
        average_source_score=average_source_score,
        evidence_count=evidence_count,
        retrieval_modes=retrieval_modes,
        warnings=warnings,
        has_conflicts=has_conflicts,
        score=score,
    )
    return ConfidenceResult(
        score=score,
        label=confidence_label(score),
        reasons=reasons,
        explanation="; ".join(reasons),
    )


def normalize_score(value: float) -> float:
    """Clamp any score-like value into the 0.0-1.0 confidence range."""
    return max(0.0, min(1.0, value))


def average_normalized_source_score(sources: Sequence[SourceCitation]) -> float:
    """Return the average bounded score for retrieved sources."""
    if not sources:
        return 0.0
    return sum(normalize_score(source.score) for source in sources) / len(sources)


def collect_retrieval_modes(sources: Sequence[SourceCitation]) -> list[str]:
    """Collect unique retrieval modes from sources in encounter order."""
    modes: list[str] = []
    for source in sources:
        source_modes = source.retrieval_modes or (
            [source.retrieval_mode] if source.retrieval_mode else [source.source_type.value]
        )
        for mode in source_modes:
            if mode and mode not in modes:
                modes.append(mode)
    return modes


def confidence_penalty(
    evidence_count: int,
    warnings: Sequence[str],
    has_conflicts: bool,
) -> float:
    """Compute deterministic confidence penalties from verification findings."""
    penalty = 0.0
    warning_set = set(warnings)
    if evidence_count == 0:
        penalty += 0.45
    if has_conflicts:
        penalty += 0.25
    if "duplicate_evidence" in warning_set:
        penalty += 0.1
    if "weak_evidence" in warning_set:
        penalty += 0.08
    penalty += min(len(warnings) * 0.03, 0.18)
    return penalty


def confidence_label(score: float) -> Literal["low", "medium", "high"]:
    """Return the human-readable confidence label for a score."""
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def confidence_reasons(
    route_confidence: float,
    average_source_score: float,
    evidence_count: int,
    retrieval_modes: Sequence[str],
    warnings: Sequence[str],
    has_conflicts: bool,
    score: float,
) -> list[str]:
    """Build short, deterministic reasons for the confidence score."""
    reasons = [
        f"route_confidence={route_confidence:.2f}",
        f"average_source_score={average_source_score:.2f}",
        f"evidence_count={evidence_count}",
        f"retrieval_mode_count={len(retrieval_modes)}",
    ]
    if evidence_count == 0:
        reasons.append("no evidence was retrieved")
    if warnings:
        reasons.append(f"warnings={','.join(warnings)}")
    if has_conflicts:
        reasons.append("conflict penalty applied")
    reasons.append(f"final_score={score:.2f}")
    return reasons
