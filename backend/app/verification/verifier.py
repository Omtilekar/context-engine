import re
from collections.abc import Sequence

from app.schemas.query import SourceCitation, VerificationResult
from app.verification.confidence import (
    average_normalized_source_score,
    collect_retrieval_modes,
    score_confidence,
)

WEAK_EVIDENCE_THRESHOLD = 0.45
DUPLICATE_SIMILARITY_THRESHOLD = 0.9
WHITESPACE_PATTERN = re.compile(r"\s+")
TOKEN_PATTERN = re.compile(r"\b[a-z0-9]+(?:\.[0-9]+)?\b")
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%?\b")

INCREASE_TERMS = {
    "increase",
    "increased",
    "increases",
    "rising",
    "rise",
    "rose",
    "growth",
    "higher",
    "grew",
}
DECREASE_TERMS = {
    "decrease",
    "decreased",
    "decreases",
    "decline",
    "declined",
    "drop",
    "dropped",
    "lower",
    "reduced",
    "reduction",
}
ALLOW_TERMS = {"allowed", "allow", "permitted", "permit", "enabled", "approved"}
DENY_TERMS = {"not allowed", "forbidden", "prohibited", "disallowed", "denied"}
TRUE_TERMS = {"true", "correct", "yes"}
FALSE_TERMS = {"false", "incorrect", "no"}


def verify_response(
    query: str,
    answer: str,
    sources: Sequence[SourceCitation],
    route_confidence: float,
) -> VerificationResult:
    """Verify retrieved evidence before answer generation.

    Args:
        query: User query being answered.
        answer: Current generated answer or placeholder text.
        sources: Retrieved source citations used as evidence.
        route_confidence: Confidence from the query router.

    Returns:
        A deterministic verification result with legacy compatibility fields.
    """
    source_list = list(sources)
    evidence_count = len(source_list)
    retrieval_modes = collect_retrieval_modes(source_list)
    conflict_notes = detect_conflicts(source_list)
    warnings = verification_warnings(
        query=query,
        answer=answer,
        sources=source_list,
        retrieval_modes=retrieval_modes,
        conflict_notes=conflict_notes,
    )
    verification = VerificationResult(
        grounded=evidence_count > 0,
        is_grounded=evidence_count > 0,
        has_conflicts=bool(conflict_notes),
        warnings=warnings,
        evidence_count=evidence_count,
        retrieval_modes=retrieval_modes,
        conflict_notes=conflict_notes,
        conflicts=conflict_notes,
        confidence=0.0,
    )
    confidence = score_confidence(source_list, route_confidence, verification)
    return verification.model_copy(update={"confidence": confidence.score})


def verification_warnings(
    query: str,
    answer: str,
    sources: Sequence[SourceCitation],
    retrieval_modes: Sequence[str],
    conflict_notes: Sequence[str],
) -> list[str]:
    """Return stable warning codes for source verification findings."""
    warnings: list[str] = []
    if not query.strip():
        warnings.append("empty_query")
    if not sources:
        warnings.append("no_sources")
    if len(sources) == 1:
        warnings.append("single_source_evidence")
    if sources and len(retrieval_modes) <= 1:
        warnings.append("single_retrieval_mode")
    if duplicate_snippet_count(sources) > 0:
        warnings.append("duplicate_evidence")
    if sources and average_normalized_source_score(sources) < WEAK_EVIDENCE_THRESHOLD:
        warnings.append("weak_evidence")
    if missing_metadata_count(sources) > 0:
        warnings.append("missing_source_metadata")
    if conflict_notes:
        warnings.append("conflicting_evidence")
    return list(dict.fromkeys(warnings))


def duplicate_snippet_count(sources: Sequence[SourceCitation]) -> int:
    """Count exact or near-duplicate snippets in source evidence."""
    unique_snippets: list[str] = []
    duplicate_count = 0
    for source in sources:
        normalized = normalize_text(source.snippet)
        if not normalized:
            continue
        if any(
            normalized == existing
            or jaccard_similarity(tokenize(normalized), tokenize(existing))
            >= DUPLICATE_SIMILARITY_THRESHOLD
            for existing in unique_snippets
        ):
            duplicate_count += 1
            continue
        unique_snippets.append(normalized)
    return duplicate_count


def missing_metadata_count(sources: Sequence[SourceCitation]) -> int:
    """Count sources that lack enough metadata for citation anchoring."""
    return sum(
        1
        for source in sources
        if not (source.source_id or source.chunk_id or source.document_id or source.metadata)
    )


def detect_conflicts(sources: Sequence[SourceCitation]) -> list[str]:
    """Detect simple lexical conflicts across source snippets."""
    notes: list[str] = []
    snippets = [source.snippet for source in sources if source.snippet.strip()]
    if has_cross_snippet_terms(snippets, INCREASE_TERMS, DECREASE_TERMS):
        notes.append("Sources disagree on increase versus decrease direction.")
    if has_allowed_conflict(snippets):
        notes.append("Sources disagree on whether the action is allowed.")
    if has_cross_snippet_terms(snippets, TRUE_TERMS, FALSE_TERMS):
        notes.append("Sources disagree on true versus false status.")
    if has_numeric_mismatch(snippets):
        notes.append("Sources contain an obvious numeric mismatch.")
    return notes


def has_cross_snippet_terms(
    snippets: Sequence[str],
    positive_terms: set[str],
    negative_terms: set[str],
) -> bool:
    """Return whether one snippet has positive terms and another has negative terms."""
    has_positive = False
    has_negative = False
    for snippet in snippets:
        tokens = set(tokenize(snippet))
        if tokens & positive_terms:
            has_positive = True
        if tokens & negative_terms:
            has_negative = True
    return has_positive and has_negative


def has_allowed_conflict(snippets: Sequence[str]) -> bool:
    """Return whether snippets disagree on allowed/not-allowed status."""
    has_allowed = False
    has_denied = False
    for snippet in snippets:
        normalized = normalize_text(snippet)
        tokens = set(tokenize(normalized))
        denied = any(term in normalized for term in DENY_TERMS)
        allowed = bool(tokens & ALLOW_TERMS) and not denied
        has_denied = has_denied or denied
        has_allowed = has_allowed or allowed
    return has_allowed and has_denied


def has_numeric_mismatch(snippets: Sequence[str]) -> bool:
    """Return whether similar snippets contain conflicting numeric values."""
    numbers_by_fingerprint: dict[str, set[str]] = {}
    for snippet in snippets:
        numbers = set(NUMBER_PATTERN.findall(snippet))
        if not numbers:
            continue
        fingerprint = normalize_text(NUMBER_PATTERN.sub("#", snippet))
        existing_numbers = numbers_by_fingerprint.get(fingerprint)
        if existing_numbers and existing_numbers != numbers:
            return True
        numbers_by_fingerprint[fingerprint] = numbers
    return False


def normalize_text(value: str) -> str:
    """Normalize text for deterministic lexical checks."""
    return WHITESPACE_PATTERN.sub(" ", value.strip().lower())


def tokenize(value: str) -> list[str]:
    """Tokenize text for simple lexical verification checks."""
    return TOKEN_PATTERN.findall(normalize_text(value))


def jaccard_similarity(left_tokens: Sequence[str], right_tokens: Sequence[str]) -> float:
    """Compute Jaccard similarity between two token sequences."""
    left = set(left_tokens)
    right = set(right_tokens)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
