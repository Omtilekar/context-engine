from typing import Any

import pytest

from app.db.models import EntityRelation
from app.scripts.seed_local import GRAPH_RELATIONS, seed_graph_relations


class FakeSeedSession:
    """Async session double for local seed script regression tests."""

    def __init__(self) -> None:
        """Track existing graph relations and inserted ORM objects."""
        self.existing_relations: set[tuple[str, str, str]] = set()
        self.added: list[EntityRelation] = []
        self.commits = 0

    async def scalar(self, statement: Any) -> object | None:
        """Return an existing relation by inspecting ORM-bound statement params."""
        params = statement.compile().params
        key = (
            str(params["entity_a_1"]),
            str(params["relation_type_1"]),
            str(params["entity_b_1"]),
        )
        if key in self.existing_relations:
            return object()
        return None

    def add(self, item: EntityRelation) -> None:
        """Persist a fake ORM relation in memory."""
        key = (item.entity_a, item.relation_type, item.entity_b)
        self.added.append(item)
        self.existing_relations.add(key)

    async def commit(self) -> None:
        """Track commit calls."""
        self.commits += 1


class FakeSeedSessionContext:
    """Async context manager returning one fake seed session."""

    def __init__(self, session: FakeSeedSession) -> None:
        """Store the fake session."""
        self.session = session

    async def __aenter__(self) -> FakeSeedSession:
        """Return the fake session."""
        return self.session

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Leave the fake session context."""


def fake_session_maker(session: FakeSeedSession) -> object:
    """Return a SQLAlchemy-like async session factory."""

    def make_session() -> FakeSeedSessionContext:
        return FakeSeedSessionContext(session)

    return make_session


async def test_seed_graph_relations_uses_orm_insert_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph seed avoids reused raw SQL binds and skips existing relations."""
    session = FakeSeedSession()
    monkeypatch.setattr(
        "app.scripts.seed_local.get_session_maker",
        lambda: fake_session_maker(session),
    )

    await seed_graph_relations()
    await seed_graph_relations()

    assert len(session.added) == len(GRAPH_RELATIONS)
    assert session.commits == 2
    assert {
        (relation.entity_a, relation.relation_type, relation.entity_b) for relation in session.added
    } == set(GRAPH_RELATIONS)
    assert all(relation.confidence == 1.0 for relation in session.added)
