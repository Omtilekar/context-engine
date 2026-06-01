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

Seed local keyword, semantic-search, structured SQL, graph, and wiki sample data:

```powershell
docker compose exec backend python -m app.scripts.seed_local
```

Run the polished local portfolio demo:

```powershell
make local-up
make demo-local
```

`make demo-local` runs migrations, seeds local SQL/wiki/graph data, ingests the text files in
`demo/data/`, and asks one sample question for each route: wiki, semantic, BM25 keyword, SQL,
graph, and hybrid. It prints the selected route, route confidence, final confidence label,
answer, source count, citations, and query audit IDs when persistence succeeds. The SQL route
runs without OpenAI, but SQL rows are returned only when `OPENAI_API_KEY` enables text-to-SQL.

Demo questions:

- `What is ContextEngine?`
- `Which retrieval approach finds similar meaning in stored chunks?`
- `Find exact keyword FlashRank`
- `How many software products cost more than 100?`
- `Which entities are linked to ContextEngine?`
- `Compare exact keyword search and semantic search for ContextEngine`

Local development uses `EMBEDDING_PROVIDER=local`, which generates deterministic 1536-dim
hash embeddings. This is only for local testing and demos without OpenAI calls; production
OpenAI embeddings will be wired in a later Phase 3 task.

The `/ingest` endpoint now persists text documents into local PostgreSQL. It creates a
`documents` row, chunks the supplied `content`, generates deterministic local embeddings for
each chunk, writes `chunks` rows, and marks the document `completed`. Empty text is handled
as a failed ingestion with zero chunks. Parser-specific ingestion for PDFs, DOCX, URLs, APIs,
databases, and spreadsheets is still a later ingestion expansion; for now, provide extracted
text in `content`.

Local ingest-then-query flow:

```powershell
make local-up
make local-migrate

$body = @{
  title = 'Demo Hybrid RAG Document'
  content = 'ContextEngine combines BM25 keyword search, pgvector semantic search, SQL retrieval, graph retrieval, wiki retrieval, verification, confidence scoring, and grounded answer generation.'
  source_type = 'text'
} | ConvertTo-Json

Invoke-WebRequest -UseBasicParsing http://localhost:8000/ingest -Method POST -ContentType 'application/json' -Body $body

$query = @{ query = 'What retrieval modes does ContextEngine combine?'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $query

make local-down
```

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
$body = @{ query = 'Which retrieval approach finds related meaning?'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

Test the wiki route:

```powershell
$body = @{ query = 'What is ContextEngine?'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

Wiki retrieval uses the PostgreSQL `wiki_pages` table for documentation-style memory. It checks
exact page-title matches, partial title matches, and full-text content matches, then returns
normal `SourceCitation` objects with `retrieval_mode: "wiki"` and metadata such as:

```json
{
  "page_title": "ContextEngine",
  "match_type": "exact",
  "wiki_score": 1.0
}
```

The router sends definition and documentation questions to wiki retrieval, including:

- `What is ContextEngine?`
- `Explain pgvector`
- `Definition of Hybrid RAG`
- `Documentation for PostgreSQL`
- `Docs for FlashRank`
- `Guide to Verification Layer`
- `Tutorial for Hybrid RAG`
- `How does pgvector work?`
- `Overview of ContextEngine`

The local seed script inserts idempotent wiki pages for `ContextEngine`, `PostgreSQL`,
`pgvector`, `FlashRank`, `Hybrid RAG`, and `Verification Layer`.

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

Test the graph route:

```powershell
$body = @{ query = 'Which entities are linked to ContextEngine?'; top_k = 5 } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing http://localhost:8000/query -Method POST -ContentType 'application/json' -Body $body
```

Graph retrieval uses the PostgreSQL `entity_relations` table, not a graph database. It supports
1-hop relationship lookup and directed 2-hop traversal for questions like:

- `How is ContextEngine related to PostgreSQL?`
- `What is connected to pgvector?`
- `Show relationships for FlashRank`
- `Which entities are linked to AWS?`

The local seed script inserts idempotent graph demo data:

```text
ContextEngine uses PostgreSQL
ContextEngine uses pgvector
ContextEngine uses FlashRank
ContextEngine deployed_on AWS
pgvector stored_in PostgreSQL
FlashRank reranks RetrievalResults
```

Graph sources are returned as normal `SourceCitation` objects with `retrieval_mode: "graph"`
and metadata such as:

```json
{
  "source_entity": "ContextEngine",
  "target_entity": "PostgreSQL",
  "relationship_type": "uses",
  "hop_count": 1
}
```

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

The generation layer runs after verification and confidence scoring. Local development uses
the deterministic disabled provider by default:

```powershell
LLM_PROVIDER=disabled
OPENAI_MODEL=gpt-4o
```

When disabled, `/query` still returns a grounded answer such as "Based on 3 retrieved
sources..." using only retrieved snippets. To enable GPT-4o answer synthesis, set
`LLM_PROVIDER=openai`, keep `OPENAI_MODEL=gpt-4o`, and provide `OPENAI_API_KEY` through
`backend/.env` locally or AWS Secrets Manager in production. If the key is missing or OpenAI
generation fails, the backend falls back to the deterministic answer and still returns a
normal response.

Generated answers cite retrieved sources using inline anchors like `[1]`. The public
`citations` field only includes retrieved sources referenced by the answer:

```json
{
  "title": "local-keyword-demo.txt",
  "retrieval_mode": "semantic",
  "score": 0.82
}
```

Each `/query` request is persisted to PostgreSQL on a best-effort basis. `query_logs` stores
the user query, selected route, route confidence, generated answer, final confidence score
and label, grounding/conflict flags, source count, citation count, token/cost metadata, latency,
and non-secret JSONB audit metadata. `retrieval_runs` stores the retrieval modes used, `top_k`,
source IDs, chunk IDs, source scores, reranker mode, verification warnings, generation provider,
and a `query_log_id` reference when the query log row is written successfully.

Query logging is failure-safe: if PostgreSQL logging fails, the API logs a warning and still
returns the normal answer. The response includes `query_log_id` and `retrieval_run_id` only when
audit persistence succeeds. Do not store secrets in queries or source metadata; the logger does
not read environment secrets or AWS credentials.

The response includes the route decision, verification, confidence, citations, generation
metadata, and source citations shaped like:

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
  "citations": [
    {
      "title": "local-keyword-demo.txt",
      "retrieval_mode": "semantic",
      "score": 0.82
    }
  ],
  "generation_metadata": {
    "provider": "disabled",
    "model": "gpt-4o",
    "tokens_used": 0,
    "cost_usd": 0.0,
    "citation_count": 1,
    "source_count": 1,
    "fallback_reason": "llm_provider_disabled"
  },
  "query_log_id": "<query-log-uuid>",
  "retrieval_run_id": "<retrieval-run-uuid>",
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

Retrieval, verification, confidence scoring, and disabled-mode answer generation now run
locally without OpenAI or AWS. GPT-4o answer synthesis is optional behind `LLM_PROVIDER=openai`;
streaming SSE and production auth move into later API-layer tasks.
