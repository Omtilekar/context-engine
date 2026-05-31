import asyncio

from sqlalchemy import select, text

from app.db.connection import close_database_connections, get_engine, get_session_maker
from app.db.models import Chunk, Document
from app.embeddings.provider import get_embedding_provider

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

PRODUCT_CATALOG_DDL = """
CREATE TABLE IF NOT EXISTS product_catalog (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    category    VARCHAR(100) NOT NULL,
    price       NUMERIC(10, 2) NOT NULL,
    stock_qty   INTEGER NOT NULL DEFAULT 0,
    description TEXT
)
"""

PRODUCT_ROWS = [
    ("ContextEngine Pro", "Software", 299.00, 500, "Hybrid RAG pipeline with 6-route classifier."),
    ("pgvector Starter Kit", "Database", 49.99, 1200, "PostgreSQL vector search with HNSW index."),
    (
        "BM25 Search Module",
        "Software",
        99.00,
        800,
        "Full-text BM25 keyword retrieval for PostgreSQL.",
    ),
    (
        "Graph RAG Add-on",
        "Software",
        149.00,
        350,
        "Entity relationship traversal using PostgreSQL.",
    ),
    (
        "Wiki Memory Pack",
        "Software",
        79.00,
        620,
        "LLM wiki memory layer with knowledge accumulation.",
    ),
    (
        "Semantic Embedder",
        "AI Tools",
        59.00,
        980,
        "Local deterministic embeddings for dev and testing.",
    ),
    (
        "Verification Shield",
        "Software",
        129.00,
        420,
        "Source grounding and conflict detection module.",
    ),
]

GRAPH_RELATIONS = [
    ("ContextEngine", "uses", "PostgreSQL"),
    ("ContextEngine", "uses", "pgvector"),
    ("ContextEngine", "uses", "FlashRank"),
    ("ContextEngine", "deployed_on", "AWS"),
    ("pgvector", "stored_in", "PostgreSQL"),
    ("FlashRank", "reranks", "RetrievalResults"),
]


async def seed_sample_data() -> None:
    """Insert idempotent local sample documents and chunks for keyword retrieval testing."""
    embedding_provider = get_embedding_provider()
    session_maker = get_session_maker()
    async with session_maker() as session:
        existing_document = await session.scalar(
            select(Document).where(Document.filename == SAMPLE_FILENAME)
        )
        if existing_document is not None:
            existing_chunks = await session.scalars(
                select(Chunk).where(Chunk.document_id == existing_document.id)
            )
            chunks_updated = 0
            for chunk in existing_chunks.all():
                if chunk.embedding is None:
                    chunk.embedding = await embedding_provider.embed_document(chunk.content)
                    chunks_updated += 1
            if chunks_updated:
                await session.commit()
            print(
                f"Sample keyword document already exists: {SAMPLE_FILENAME}; "
                f"updated {chunks_updated} missing embeddings"
            )
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
                    embedding=await embedding_provider.embed_document(content),
                    chunk_index=chunk_index,
                )
            )

        await session.commit()
        print(f"Seeded {len(SAMPLE_CHUNKS)} keyword chunks with embeddings for {SAMPLE_FILENAME}")


async def seed_product_catalog() -> None:
    """Create and populate the product_catalog structured demo table.

    This local-only table is used to test the SQL retriever with natural-language
    queries like 'how many software products cost more than $100?'. It is created
    outside Alembic because it is demo data, not part of the core RAG schema.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text(PRODUCT_CATALOG_DDL))

    session_maker = get_session_maker()
    async with session_maker() as session:
        existing_count_result = await session.execute(text("SELECT COUNT(*) FROM product_catalog"))
        existing_count = existing_count_result.scalar() or 0
        if existing_count >= len(PRODUCT_ROWS):
            print(f"product_catalog already has {existing_count} rows — skipping SQL seed")
            return

        for name, category, price, stock_qty, description in PRODUCT_ROWS:
            await session.execute(
                text(
                    "INSERT INTO product_catalog (name, category, price, stock_qty, description) "
                    "VALUES (:name, :category, :price, :stock_qty, :description) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {
                    "name": name,
                    "category": category,
                    "price": price,
                    "stock_qty": stock_qty,
                    "description": description,
                },
            )
        await session.commit()
        print(f"Seeded {len(PRODUCT_ROWS)} rows into product_catalog for SQL retriever testing")


async def seed_graph_relations() -> None:
    """Insert idempotent local entity_relations rows for graph retriever testing."""
    session_maker = get_session_maker()
    inserted = 0
    async with session_maker() as session:
        for entity_a, relation_type, entity_b in GRAPH_RELATIONS:
            result = await session.execute(
                text(
                    "INSERT INTO entity_relations "
                    "(entity_a, relation_type, entity_b, confidence) "
                    "SELECT :entity_a, :relation_type, :entity_b, 1.0 "
                    "WHERE NOT EXISTS ("
                    "  SELECT 1 FROM entity_relations "
                    "  WHERE entity_a = :entity_a "
                    "    AND relation_type = :relation_type "
                    "    AND entity_b = :entity_b"
                    ")"
                ),
                {
                    "entity_a": entity_a,
                    "relation_type": relation_type,
                    "entity_b": entity_b,
                },
            )
            inserted += int(getattr(result, "rowcount", 0) or 0)
        await session.commit()
    print(f"Seeded {inserted} graph relations for entity_relations demo data")


async def main() -> None:
    """Run the local seed script and close database connections."""
    try:
        await seed_sample_data()
        await seed_product_catalog()
        await seed_graph_relations()
    finally:
        await close_database_connections()


if __name__ == "__main__":
    asyncio.run(main())
