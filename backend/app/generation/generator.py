import re
from collections.abc import Sequence

from app.generation.provider import (
    AnswerProvider,
    GroundedPrompt,
    ProviderCompletion,
    get_generation_provider,
)
from app.schemas.query import (
    Citation,
    ConfidenceResult,
    GenerationMetadata,
    GenerationResult,
    SourceCitation,
    VerificationResult,
)

CITATION_PATTERN = re.compile(r"\[(?:source\s*)?(\d+)\]", re.IGNORECASE)
MAX_PROMPT_SOURCES = 8
MAX_SNIPPET_CHARS = 700
MAX_DISABLED_SNIPPET_CHARS = 220

SYSTEM_PROMPT = """You are ContextEngine, a grounded answer generator.
Answer only from the supplied sources. Do not invent facts or cite missing sources.
When evidence is missing or weak, say so plainly. When verification reports conflicts,
describe the conflict instead of forcing one side to be true. Cite every factual claim with
source numbers like [1] or [2]."""


async def generate_answer(
    query: str,
    sources: Sequence[SourceCitation],
    verification: VerificationResult,
    confidence: ConfidenceResult,
    provider: AnswerProvider | None = None,
) -> GenerationResult:
    """Generate a grounded answer with citations and generation metadata.

    Args:
        query: User query.
        sources: Retrieved sources available for answer synthesis.
        verification: Deterministic verification result.
        confidence: Confidence scoring result.
        provider: Optional provider test double or configured runtime provider.

    Returns:
        Generated answer text, citations used, and generation metadata.
    """
    source_list = list(sources)
    prompt = build_grounded_prompt(query, source_list, verification, confidence)
    fallback_answer = build_disabled_answer(query, source_list, verification, confidence)
    active_provider = provider or get_generation_provider()
    completion = await active_provider.generate(prompt, fallback_answer)
    answer = completion.text.strip() or fallback_answer
    citations = extract_used_citations(answer, source_list)
    metadata = completion_to_metadata(completion, citations, source_list)
    return GenerationResult(answer=answer, citations=citations, metadata=metadata)


def build_grounded_prompt(
    query: str,
    sources: Sequence[SourceCitation],
    verification: VerificationResult,
    confidence: ConfidenceResult,
) -> GroundedPrompt:
    """Build the source-grounded prompt sent to the answer provider."""
    source_context = format_source_context(sources)
    verification_summary = (
        f"is_grounded={verification.is_grounded}; "
        f"has_conflicts={verification.has_conflicts}; "
        f"warnings={', '.join(verification.warnings) or 'none'}; "
        f"conflicts={'; '.join(verification.conflict_notes) or 'none'}"
    )
    confidence_summary = (
        f"score={confidence.score:.2f}; label={confidence.label}; "
        f"reasons={'; '.join(confidence.reasons)}"
    )
    user_prompt = (
        f"User query:\n{query.strip()}\n\n"
        f"Verification summary:\n{verification_summary}\n\n"
        f"Confidence summary:\n{confidence_summary}\n\n"
        "Retrieved sources:\n"
        f"{source_context}\n\n"
        "Instructions:\n"
        "- Use only the retrieved sources above.\n"
        "- If sources are missing, say the answer is not grounded yet.\n"
        "- If confidence is low, mention that the evidence is weak or incomplete.\n"
        "- If conflicts are listed, call them out explicitly.\n"
        "- Cite factual claims with source numbers like [1]."
    )
    return GroundedPrompt(system=SYSTEM_PROMPT, user=user_prompt)


def format_source_context(sources: Sequence[SourceCitation]) -> str:
    """Format retrieved source snippets with citation anchors for prompting."""
    if not sources:
        return "No retrieved sources were available."

    formatted_sources: list[str] = []
    for index, source in enumerate(sources[:MAX_PROMPT_SOURCES], start=1):
        retrieval_mode = source.retrieval_mode or source.source_type.value
        formatted_sources.append(
            "\n".join(
                [
                    f"[{index}] {source.title}",
                    f"retrieval_mode: {retrieval_mode}",
                    f"score: {source.score:.2f}",
                    f"snippet: {trim_text(source.snippet, MAX_SNIPPET_CHARS)}",
                ]
            )
        )
    return "\n\n".join(formatted_sources)


def build_disabled_answer(
    query: str,
    sources: Sequence[SourceCitation],
    verification: VerificationResult,
    confidence: ConfidenceResult,
) -> str:
    """Build a deterministic grounded answer for disabled/local mode."""
    if not sources:
        return (
            "No retrieved sources were available, so ContextEngine cannot answer this "
            "with citations yet. The confidence is low because the response is not grounded."
        )

    source_count = len(sources)
    source_word = "source" if source_count == 1 else "sources"
    if verification.has_conflicts:
        prefix = (
            f"Based on {source_count} retrieved {source_word}, the evidence has "
            "possible conflicts. "
        )
        if verification.conflict_notes:
            prefix += " ".join(verification.conflict_notes) + " "
    elif confidence.label == "low":
        prefix = (
            f"Based on {source_count} retrieved {source_word}, the evidence is low confidence "
            "and should be treated as incomplete. "
        )
    else:
        prefix = f"Based on {source_count} retrieved {source_word}, the evidence suggests: "

    evidence_sentences = [
        f"{trim_text(source.snippet, MAX_DISABLED_SNIPPET_CHARS)} [{index}]"
        for index, source in enumerate(sources[:3], start=1)
    ]
    return prefix + " ".join(evidence_sentences)


def extract_used_citations(
    answer: str,
    sources: Sequence[SourceCitation],
) -> list[Citation]:
    """Extract citations referenced by an answer, limited to retrieved sources."""
    citations: list[Citation] = []
    seen_indexes: set[int] = set()
    for match in CITATION_PATTERN.finditer(answer):
        source_index = int(match.group(1))
        if source_index < 1 or source_index > len(sources) or source_index in seen_indexes:
            continue
        seen_indexes.add(source_index)
        citations.append(source_to_citation(sources[source_index - 1]))
    return citations


def source_to_citation(source: SourceCitation) -> Citation:
    """Convert a retrieved source into the public citation shape."""
    retrieval_mode = source.retrieval_mode or source.source_type.value
    return Citation(title=source.title, retrieval_mode=retrieval_mode, score=source.score)


def completion_to_metadata(
    completion: ProviderCompletion,
    citations: Sequence[Citation],
    sources: Sequence[SourceCitation],
) -> GenerationMetadata:
    """Convert provider completion details into response metadata."""
    return GenerationMetadata(
        provider=completion.provider,
        model=completion.model,
        tokens_used=completion.tokens_used,
        cost_usd=completion.cost_usd,
        citation_count=len(citations),
        source_count=len(sources),
        fallback_reason=completion.fallback_reason,
    )


def trim_text(value: str, max_chars: int) -> str:
    """Trim text to a stable one-line preview."""
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
