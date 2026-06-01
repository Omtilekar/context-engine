import pytest

from app.db.query_logging import QueryPersistenceResult


@pytest.fixture(autouse=True)
def disable_query_audit_for_non_logging_tests(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Keep normal endpoint tests from attempting live database audit writes."""
    if request.module.__name__.endswith("test_query_logging"):
        return

    async def fake_persist_query_audit(*args: object, **kwargs: object) -> QueryPersistenceResult:
        """Return no audit IDs without touching a database."""
        return QueryPersistenceResult()

    monkeypatch.setattr("app.main.persist_query_audit", fake_persist_query_audit)
