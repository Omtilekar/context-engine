import pytest

from app.ingestion.chunking import TextChunk, chunk_text


def words(count: int) -> str:
    """Return deterministic word-numbered text for chunking tests."""
    return " ".join(f"word{index}" for index in range(count))


def test_short_text_returns_one_chunk() -> None:
    """Short text stays in a single chunk with zero-based metadata."""
    chunks = chunk_text("alpha beta gamma", chunk_size=10, overlap=2)

    assert chunks == [
        TextChunk(
            content="alpha beta gamma",
            chunk_index=0,
            start_word=0,
            end_word=3,
        )
    ]


def test_long_text_splits_into_multiple_chunks() -> None:
    """Long text is split into deterministic overlapping chunks."""
    chunks = chunk_text(words(10), chunk_size=4, overlap=1)

    assert len(chunks) == 3
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert [chunk.content for chunk in chunks] == [
        "word0 word1 word2 word3",
        "word3 word4 word5 word6",
        "word6 word7 word8 word9",
    ]


def test_chunk_overlap_reuses_expected_words() -> None:
    """Adjacent chunks share the configured overlap."""
    chunks = chunk_text(words(8), chunk_size=4, overlap=2)

    first_words = chunks[0].content.split()
    second_words = chunks[1].content.split()

    assert first_words[-2:] == second_words[:2]


def test_chunk_metadata_tracks_order_and_word_offsets() -> None:
    """Chunk metadata includes stable index and source word offsets."""
    chunks = chunk_text(words(9), chunk_size=4, overlap=1)

    for index, chunk in enumerate(chunks):
        assert chunk.chunk_index == index
        assert chunk.start_word < chunk.end_word

    assert [chunk.start_word for chunk in chunks] == [0, 3, 6]
    assert [chunk.end_word for chunk in chunks] == [4, 7, 9]


@pytest.mark.parametrize("text", ["", "   ", "\n\t  "])
def test_empty_or_whitespace_text_returns_no_chunks(text: str) -> None:
    """Empty text produces no chunks."""
    assert chunk_text(text) == []


def test_chunking_output_is_deterministic() -> None:
    """Repeated chunking with the same inputs returns the same chunks."""
    text = words(17)

    assert chunk_text(text, chunk_size=5, overlap=2) == chunk_text(
        text,
        chunk_size=5,
        overlap=2,
    )


def test_no_chunk_exceeds_configured_max_word_count() -> None:
    """No produced chunk exceeds the configured max word count."""
    max_words = 5
    chunks = chunk_text(words(23), chunk_size=max_words, overlap=1)

    assert chunks
    assert all(len(chunk.content.split()) <= max_words for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (4, -1),
        (4, 4),
    ],
)
def test_invalid_chunking_configuration_raises(chunk_size: int, overlap: int) -> None:
    """Invalid chunking settings fail fast."""
    with pytest.raises(ValueError):
        chunk_text("alpha beta", chunk_size=chunk_size, overlap=overlap)
