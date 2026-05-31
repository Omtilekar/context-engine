import asyncio

from sqlalchemy import select

from app.db.connection import close_database_connections, get_session_maker
from app.db.models import Chunk, Document

SAMPLE_FILENAME = "local-keyword-demo.txt"
SAMPLE_CHUNKS = [
    (
        "ContextEngine uses PostgreSQL full-text search with pg_trgm and tsvector indexes "
        "for BM25-style keyword retrieval over document chunks."
    ),
    (
        "The verification layer checks grounding, conflicts, confidence, and citation "
        "coverage before an answer is returned to the user."
    ),
    (
        "The local development stack runs pgvector PostgreSQL and the FastAPI backend with "
        "Docker Compose, avoiding any dependency on AWS RDS."
    ),
]


async def seed_sample_data() -> None:
    """Insert idempotent local sample documents and chunks for keyword retrieval testing."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        existing_document = await session.scalar(
            select(Document).where(Document.filename == SAMPLE_FILENAME)
        )
        if existing_document is not None:
            print(f"Sample keyword document already exists: {SAMPLE_FILENAME}")
            return

        document = Document(
            filename=SAMPLE_FILENAME,
            source_type="text",
            status="completed",
        )
        session.add(document)
        await session.flush()

        for chunk_index, content in enumerate(SAMPLE_CHUNKS):
            session.add(
                Chunk(
                    document_id=document.id,
                    content=content,
                    chunk_index=chunk_index,
                )
            )

        await session.commit()
        print(f"Seeded {len(SAMPLE_CHUNKS)} keyword chunks for {SAMPLE_FILENAME}")


async def main() -> None:
    """Run the local seed script and close database connections."""
    try:
        await seed_sample_data()
    finally:
        await close_database_connections()


if __name__ == "__main__":
    asyncio.run(main())
