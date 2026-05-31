from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    """Chunked text with deterministic ordering metadata."""

    content: str
    chunk_index: int
    start_word: int
    end_word: int


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[TextChunk]:
    """Split text into overlapping word chunks as a tokenization placeholder."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    chunks: list[TextChunk] = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start : start + chunk_size]
        chunks.append(
            TextChunk(
                content=" ".join(chunk_words),
                chunk_index=len(chunks),
                start_word=start,
                end_word=end,
            )
        )
        if start + chunk_size >= len(words):
            break
    return chunks
