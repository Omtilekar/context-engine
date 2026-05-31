import re
from collections.abc import Sequence

from app.schemas.query import SourceCitation

PROVENANCE_SCORE_BONUS = 0.1
TEXT_NORMALIZATION_PATTERN = re.compile(r"\s+")


def merge_sources(
    source_groups: Sequence[Sequence[SourceCitation]],
    top_k: int,
) -> list[SourceCitation]:
    """Merge, deduplicate, and score retrieval results from multiple retrievers.

    Args:
        source_groups: Retrieval outputs grouped by retriever.
        top_k: Maximum number of merged sources to return.

    Returns:
        Deterministically ordered source citations with provenance metadata.
    """
    if top_k <= 0:
        return []

    merged: dict[str, SourceCitation] = {}
    mode_scores: dict[str, dict[str, float]] = {}

    for source_group in source_groups:
        for source in source_group:
            key = source_identity_key(source)
            mode = source_mode(source)
            if key not in merged:
                merged[key] = normalize_source_provenance(source, mode)
                mode_scores[key] = {mode: source.score}
                continue

            existing = merged[key]
            mode_scores[key][mode] = max(mode_scores[key].get(mode, 0.0), source.score)
            merged[key] = combine_duplicate_source(existing, source, mode_scores[key])

    merged_sources = list(merged.values())
    merged_sources.sort(
        key=lambda source: (
            -source.score,
            source.title.lower(),
            normalize_text(source.snippet),
        )
    )
    return merged_sources[:top_k]


def source_identity_key(source: SourceCitation) -> str:
    """Return the deterministic dedupe key for a source citation."""
    if source.chunk_id:
        return f"chunk:{source.chunk_id}"
    return f"text:{normalize_text(source.title)}:{normalize_text(source.snippet)}"


def normalize_text(value: str) -> str:
    """Normalize free text for fallback deduplication."""
    return TEXT_NORMALIZATION_PATTERN.sub(" ", value.strip().lower())


def source_mode(source: SourceCitation) -> str:
    """Return the primary retrieval mode for a source."""
    return source.retrieval_mode or source.source_type.value


def normalize_source_provenance(source: SourceCitation, mode: str) -> SourceCitation:
    """Return a copy of a source with provenance metadata initialized."""
    retrieval_modes = unique_modes([*source.retrieval_modes, mode])
    metadata = {
        **source.metadata,
        "retrieval_modes": ",".join(retrieval_modes),
        f"score_{mode}": f"{source.score:.6f}",
    }
    return source.model_copy(
        update={
            "retrieval_mode": source.retrieval_mode or mode,
            "retrieval_modes": retrieval_modes,
            "metadata": metadata,
        },
        deep=True,
    )


def combine_duplicate_source(
    existing: SourceCitation,
    incoming: SourceCitation,
    scores_by_mode: dict[str, float],
) -> SourceCitation:
    """Combine duplicate source citations and preserve retriever provenance."""
    incoming_mode = source_mode(incoming)
    retrieval_modes = unique_modes(
        [
            *existing.retrieval_modes,
            incoming_mode,
            *incoming.retrieval_modes,
        ]
    )
    best_source = incoming if incoming.score > existing.score else existing
    best_score = max(scores_by_mode.values())
    combined_score = min(1.0, best_score + PROVENANCE_SCORE_BONUS * (len(retrieval_modes) - 1))
    metadata = {
        **existing.metadata,
        **incoming.metadata,
        "retrieval_modes": ",".join(retrieval_modes),
    }
    for mode, score in scores_by_mode.items():
        metadata[f"score_{mode}"] = f"{score:.6f}"

    return best_source.model_copy(
        update={
            "score": round(combined_score, 4),
            "source_id": existing.source_id or incoming.source_id,
            "chunk_id": existing.chunk_id or incoming.chunk_id,
            "document_id": existing.document_id or incoming.document_id,
            "retrieval_mode": retrieval_modes[0],
            "retrieval_modes": retrieval_modes,
            "metadata": metadata,
        },
        deep=True,
    )


def unique_modes(modes: Sequence[str]) -> list[str]:
    """Return unique retrieval modes in encounter order."""
    unique: list[str] = []
    for mode in modes:
        normalized = mode.strip()
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique
