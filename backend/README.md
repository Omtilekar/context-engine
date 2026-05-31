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

Seed local keyword, semantic-search, and structured SQL sample data:

```powershell
docker compose exec backend python -m app.scripts.seed_local
```

Local development uses `EMBEDDING_PROVIDER=local`, which generates deterministic 1536-dim
hash embeddings. This is only for local testing and demos without OpenAI calls; production
OpenAI embeddings will be wired in a later Phase 3 task.

Test the health endpoint:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

Test the keyword/BM25 route:

```powershell
$body = @{ query = 'keyword retrieval'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

Test the semantic pgvector route:

```powershell
$body = @{ query = 'How does semantic search find related meaning?'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

Test the hybrid route:

```powershell
$body = @{ query = 'Compare exact keyword retrieval across semantic meaning'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

Hybrid retrieval runs semantic pgvector and BM25 keyword retrieval in parallel, optionally adds
SQL results when the query has structured/numeric signals, deduplicates by `chunk_id` or
normalized title/snippet fallback, combines duplicate scores, and records provenance in
`retrieval_modes`. SQL snippets are merged into the final context list but are not sent through
FlashRank.

FlashRank reranking is optional and disabled locally by default:

```powershell
RERANKER_MODE=disabled
```

Set `RERANKER_MODE=flashrank` only after installing the optional `flashrank` package in the
backend environment. If FlashRank is unavailable or fails, the API falls back to merged-score
ordering and still returns a normal response. Normal tests never import FlashRank or download a
model.

The verification layer runs before final answer generation. It checks whether evidence was
retrieved, source count, retrieval-mode diversity, duplicate snippets, weak source scores,
missing citation metadata, and simple lexical conflict signals such as increase/decrease,
allowed/not allowed, true/false, and obvious numeric mismatches. This deterministic pass is
intentionally conservative; it can flag likely conflicts, but it is not a substitute for the
later GPT-4o-mini verification pass.

Confidence scoring combines the router confidence, average source score, evidence count,
retrieval-mode diversity, and verification penalties for no evidence, duplicate evidence,
weak evidence, and conflicts. The API returns both the legacy verification confidence float
and a structured top-level confidence object with `score`, `label`, `reasons`, and
`explanation`.

The response includes the route decision, verification, confidence, and source citations
shaped like:

```json
{
  "route_decision": {
    "route": "semantic",
    "confidence": 0.66,
    "reasoning": "The query is best handled as a meaning-based semantic lookup.",
    "entities": []
  },
  "verification": {
    "grounded": true,
    "is_grounded": true,
    "has_conflicts": false,
    "warnings": ["single_source_evidence"],
    "evidence_count": 1,
    "retrieval_modes": ["semantic"],
    "conflict_notes": [],
    "conflicts": [],
    "confidence": 0.62
  },
  "confidence": {
    "score": 0.62,
    "label": "medium",
    "reasons": [
      "route_confidence=0.66",
      "average_source_score=0.82",
      "evidence_count=1"
    ],
    "explanation": "route_confidence=0.66; average_source_score=0.82; evidence_count=1"
  },
  "sources": [
    {
      "title": "local-keyword-demo.txt",
      "score": 0.82,
      "source_type": "semantic",
      "snippet": "The local development stack runs pgvector PostgreSQL...",
      "source_id": "<chunk-uuid>",
      "chunk_id": "<chunk-uuid>",
      "document_id": "<document-uuid>",
      "retrieval_mode": "semantic",
      "retrieval_modes": ["semantic", "keyword"],
      "metadata": {
        "distance": "0.180000",
        "similarity_score": "0.820000",
        "retrieval_modes": "semantic,keyword",
        "chunk_index": "2",
        "document_source_type": "text"
      }
    }
  ]
}
```

Test the SQL route (text-to-SQL via GPT-4o-mini, requires `OPENAI_API_KEY` in `backend/.env`):

```powershell
$body = @{ query = 'how many products cost more than 100?'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

The SQL retriever is disabled unless `OPENAI_API_KEY` is configured. When enabled, it
introspects only allowlisted tables, generates a single SELECT statement, validates it
through an injection guard, enforces a 50-row limit and a 5-second execution timeout, and
returns each row as a `SourceCitation` with `retrieval_mode: "sql"`.

The guard rejects non-SELECT statements, destructive keywords, SQL comments (`--`, `/* */`),
semicolon chaining, multi-statement SQL, and access to tables outside `SQL_ALLOWED_TABLES`.
The default local allowlist is:

```powershell
SQL_ALLOWED_TABLES=product_catalog
```

`product_catalog` is a local-only portfolio demo table created by `seed_local`; it is not part
of the core Alembic RAG schema. Production structured-source tables should be added through
their own migrations or controlled ingestion flow before being added to `SQL_ALLOWED_TABLES`.

If `OPENAI_API_KEY` is not set, the SQL retriever returns an empty result instead of raising
or touching the database. All guard, row-mapping, and endpoint tests run without a real API
key.

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
