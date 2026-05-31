# ContextEngine Backend

FastAPI foundation for the ContextEngine hybrid RAG pipeline.

## Local Setup

```powershell
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Docker Compose Local Stack

First-time setup:

```powershell
Copy-Item backend\.env.example backend\.env
```

Start local PostgreSQL with pgvector and the FastAPI backend:

```powershell
make local-up
```

Run migrations against the local Compose database:

```powershell
make local-migrate
```

Test the health endpoint:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

Stop the local stack:

```powershell
make local-down
```

Useful local commands:

```powershell
make local-logs
make local-test
docker compose config
```

## Checks

```powershell
cd backend
poetry run ruff format .
poetry run ruff check .
poetry run mypy app
poetry run pytest
```

## Database Migrations

Alembic is configured for async PostgreSQL and reads `DATABASE_URL` from the environment.
Use a local pgvector-enabled PostgreSQL database for these commands; do not point them at RDS
unless deployment has been explicitly approved.

```powershell
cd backend

# Create a new migration after model changes
poetry run alembic revision --autogenerate -m "describe change"

# Run migrations
poetry run alembic upgrade head

# Roll back one migration
poetry run alembic downgrade -1
```

If Poetry is not available on PATH in this shell, the local virtualenv commands are:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic downgrade -1
```

## Endpoints

- `GET /health`
- `GET /status`
- `POST /query`
- `POST /ingest`

All LLM, retrieval, ingestion, and verification behavior is intentionally skeletal in this
foundation slice. The interfaces are in place so the full RAG pipeline can be filled in
without changing the API shape.
