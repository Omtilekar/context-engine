import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.connection import get_session_maker
from app.schemas.query import QueryRoute, SourceCitation

logger = get_logger(__name__)

GRAPH_ONE_HOP_SQL = """
SELECT
    id::text AS relation_id,
    entity_a AS source_entity,
    relation_type AS relationship_type,
    entity_b AS target_entity,
    source_chunk_id::text AS source_chunk_id,
    confidence AS confidence,
    1 AS hop_count,
    NULL::text AS intermediate_entity,
    CASE
        WHEN lower(entity_a) IN :entities AND lower(entity_b) IN :entities THEN 1
        ELSE 0
    END AS match_rank
FROM entity_relations
WHERE lower(entity_a) IN :entities OR lower(entity_b) IN :entities
ORDER BY match_rank DESC, confidence DESC, entity_a, relation_type, entity_b
LIMIT :top_k
"""

GRAPH_TWO_HOP_SQL = """
SELECT
    (r1.id::text || ':' || r2.id::text) AS relation_id,
    r1.entity_a AS source_entity,
    (r1.relation_type || ' -> ' || r2.relation_type) AS relationship_type,
    r2.entity_b AS target_entity,
    r1.source_chunk_id::text AS source_chunk_id,
    LEAST(r1.confidence, r2.confidence) * 0.9 AS confidence,
    2 AS hop_count,
    r1.entity_b AS intermediate_entity,
    CASE
        WHEN lower(r2.entity_b) IN :entities THEN 1
        ELSE 0
    END AS match_rank
FROM entity_relations r1
JOIN entity_relations r2
    ON lower(r1.entity_b) = lower(r2.entity_a)
WHERE lower(r1.entity_a) IN :entities
  AND lower(r2.entity_b) <> lower(r1.entity_a)
ORDER BY match_rank DESC, confidence DESC, r1.entity_a, r1.relation_type, r2.entity_b
LIMIT :top_k
"""

GRAPH_STOPWORDS = {
    "a",
    "an",
    "and",
    "association",
    "connected",
    "dependency",
    "entities",
    "entity",
    "for",
    "graph",
    "how",
    "is",
    "linked",
    "relationship",
    "relationships",
    "related",
    "show",
    "the",
    "to",
    "what",
    "which",
}
ENTITY_CLEANUP_PATTERN = re.compile(r"^[\s\"'`]+|[\s\"'`?.!,;:]+$")
ENTITY_SEPARATOR_PATTERN = re.compile(r"\s+(?:and|to|with)\s+", re.IGNORECASE)
QUOTED_ENTITY_PATTERN = re.compile(r"['\"]([^'\"]+)['\"]")
CAPITALIZED_ENTITY_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)?(?:\s+[A-Z][A-Za-z0-9]*)*\b"
)

GRAPH_ENTITY_PATTERNS = [
    re.compile(
        r"\bhow\s+is\s+(.+?)\s+(?:related|connected|linked)\s+to\s+(.+?)(?:[?.!]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:relationship|relationships|association|dependency)\s+between\s+(.+?)\s+and\s+(.+?)(?:[?.!]|$)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:connected|linked|related)\s+to\s+(.+?)(?:[?.!]|$)", re.IGNORECASE),
    re.compile(
        r"\b(?:relationships?|associations?|dependencies?)\s+(?:for|of)\s+(.+?)(?:[?.!]|$)",
        re.IGNORECASE,
    ),
    re.compile(r"\bgraph\s+(?:for|around|of)\s+(.+?)(?:[?.!]|$)", re.IGNORECASE),
]


async def retrieve_graph(
    query: str,
    top_k: int,
    session: AsyncSession | None = None,
    include_two_hop: bool = True,
) -> list[SourceCitation]:
    """Retrieve graph evidence from the PostgreSQL entity_relations table.

    Args:
        query: User relationship query.
        top_k: Maximum number of graph evidence sources to return.
        session: Optional async SQLAlchemy session for tests/orchestration.
        include_two_hop: Whether to include directed 2-hop traversal paths.

    Returns:
        Source citations representing graph relationships and paths.
    """
    entities = extract_graph_entities(query)
    if not query.strip() or top_k <= 0 or not entities:
        return []

    if session is not None:
        return await fetch_graph_sources(session, entities, top_k, include_two_hop)

    session_maker = get_session_maker()
    try:
        async with session_maker() as database_session:
            return await fetch_graph_sources(database_session, entities, top_k, include_two_hop)
    except (OSError, SQLAlchemyError) as error:
        logger.warning("Graph retrieval failed", extra={"error": str(error)})
        return []


async def fetch_graph_sources(
    session: AsyncSession,
    entities: Sequence[str],
    top_k: int,
    include_two_hop: bool,
) -> list[SourceCitation]:
    """Fetch graph rows with an existing database session."""
    bounded_top_k = max(top_k, 1)
    rows = await execute_graph_query(session, GRAPH_ONE_HOP_SQL, entities, bounded_top_k)
    if include_two_hop:
        rows.extend(await execute_graph_query(session, GRAPH_TWO_HOP_SQL, entities, bounded_top_k))

    sources = [graph_row_to_source(row) for row in rows]
    return dedupe_graph_sources(sources)[:bounded_top_k]


async def execute_graph_query(
    session: AsyncSession,
    sql: str,
    entities: Sequence[str],
    top_k: int,
) -> list[Mapping[str, Any]]:
    """Execute a parameterized graph SQL statement and return mapping rows."""
    statement = text(sql).bindparams(bindparam("entities", expanding=True))
    result = await session.execute(
        statement,
        {"entities": tuple(normalize_entity(entity) for entity in entities), "top_k": top_k},
    )
    return cast(list[Mapping[str, Any]], list(result.mappings().all()))


def graph_row_to_source(row: Mapping[str, Any]) -> SourceCitation:
    """Map an entity_relations row or 2-hop path row into a SourceCitation."""
    source_entity = str(row["source_entity"])
    target_entity = str(row["target_entity"])
    relationship_type = str(row["relationship_type"])
    hop_count = int(row.get("hop_count", 1) or 1)
    intermediate_entity = row.get("intermediate_entity")
    confidence = normalize_graph_score(float(row.get("confidence", 1.0) or 0.0))
    relation_id = str(row.get("relation_id", ""))
    source_chunk_id = row.get("source_chunk_id")

    metadata = {
        "source_entity": source_entity,
        "target_entity": target_entity,
        "relationship_type": relationship_type,
        "hop_count": hop_count,
        "relation_id": relation_id,
    }
    if intermediate_entity:
        metadata["intermediate_entity"] = str(intermediate_entity)
    if source_chunk_id:
        metadata["source_chunk_id"] = str(source_chunk_id)

    return SourceCitation(
        title=graph_title(source_entity, target_entity, intermediate_entity),
        score=confidence,
        source_type=QueryRoute.GRAPH,
        snippet=graph_snippet(source_entity, relationship_type, target_entity, intermediate_entity),
        source_id=relation_id or None,
        chunk_id=str(source_chunk_id) if source_chunk_id else None,
        retrieval_mode="graph",
        retrieval_modes=["graph"],
        metadata=metadata,
    )


def dedupe_graph_sources(sources: Sequence[SourceCitation]) -> list[SourceCitation]:
    """Deduplicate graph sources and return a deterministic score order."""
    deduped: dict[str, SourceCitation] = {}
    for source in sources:
        key = source.source_id or (
            f"{source.metadata.get('source_entity')}|"
            f"{source.metadata.get('relationship_type')}|"
            f"{source.metadata.get('target_entity')}|"
            f"{source.metadata.get('hop_count')}"
        )
        existing = deduped.get(key)
        if existing is None or source.score > existing.score:
            deduped[key] = source

    ordered = list(deduped.values())
    ordered.sort(
        key=lambda source: (
            -source.score,
            int(source.metadata.get("hop_count", 1)),
            source.title.lower(),
            source.snippet.lower(),
        )
    )
    return ordered


def extract_graph_entities(query: str) -> list[str]:
    """Extract likely graph entity names from supported relationship queries."""
    candidates: list[str] = []
    candidates.extend(match.group(1) for match in QUOTED_ENTITY_PATTERN.finditer(query))
    for pattern in GRAPH_ENTITY_PATTERNS:
        match = pattern.search(query)
        if not match:
            continue
        for group in match.groups():
            candidates.extend(split_entity_candidate(group))

    if not candidates:
        candidates.extend(match.group(0) for match in CAPITALIZED_ENTITY_PATTERN.finditer(query))

    normalized_entities: list[str] = []
    for candidate in candidates:
        normalized = normalize_entity(candidate)
        if (
            normalized
            and normalized not in GRAPH_STOPWORDS
            and normalized not in normalized_entities
        ):
            normalized_entities.append(normalized)
    return normalized_entities


def split_entity_candidate(candidate: str) -> list[str]:
    """Split a captured query phrase into one or more possible entity names."""
    return [part for part in ENTITY_SEPARATOR_PATTERN.split(candidate) if part.strip()]


def normalize_entity(entity: str) -> str:
    """Normalize an entity name for case-insensitive matching."""
    cleaned = ENTITY_CLEANUP_PATTERN.sub("", entity)
    cleaned = " ".join(cleaned.split())
    while cleaned.lower().startswith(("the ", "a ", "an ")):
        cleaned = cleaned.split(" ", 1)[1].strip()
    return cleaned.lower()


def normalize_graph_score(value: float) -> float:
    """Clamp graph confidence into the SourceCitation score range."""
    return round(max(0.0, min(1.0, value)), 4)


def graph_title(
    source_entity: str,
    target_entity: str,
    intermediate_entity: object | None,
) -> str:
    """Return a concise graph source title."""
    if intermediate_entity:
        return f"Graph: {source_entity} -> {intermediate_entity} -> {target_entity}"
    return f"Graph: {source_entity} -> {target_entity}"


def graph_snippet(
    source_entity: str,
    relationship_type: str,
    target_entity: str,
    intermediate_entity: object | None,
) -> str:
    """Return a human-readable graph evidence snippet."""
    relations = [part.strip() for part in relationship_type.split("->")]
    if intermediate_entity and len(relations) >= 2:
        return (
            f"{source_entity} {format_relation(relations[0])} {intermediate_entity}, "
            f"then {intermediate_entity} {format_relation(relations[1])} {target_entity}."
        )
    return f"{source_entity} {format_relation(relationship_type)} {target_entity}."


def format_relation(relation_type: str) -> str:
    """Convert stored relation_type values into readable text."""
    return relation_type.strip().replace("_", " ")
