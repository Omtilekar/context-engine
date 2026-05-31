# ContextEngine Backend

FastAPI foundation for the ContextEngine hybrid RAG pipeline.

## Local Setup

```powershell
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Checks

```powershell
cd backend
poetry run ruff format .
poetry run ruff check .
poetry run pytest
```

## Endpoints

- `GET /health`
- `GET /status`
- `POST /query`
- `POST /ingest`

All LLM, retrieval, ingestion, and verification behavior is intentionally skeletal in this
foundation slice. The interfaces are in place so the full RAG pipeline can be filled in
without changing the API shape.

