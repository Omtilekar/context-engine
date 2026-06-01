# ContextEngine - Full Project Guide

Last updated: June 1, 2026

This document explains ContextEngine end to end. It is written for recruiters,
reviewers, future maintainers, and for interview prep. It describes what the project
is, why it exists, what has been built, how the system works internally, how to run it
locally, and what remains planned.

## 1. Executive Summary

ContextEngine is a portfolio-grade hybrid context engine for retrieval-augmented
generation. It merges four retrieval paradigms into one pipeline:

- Vector RAG: semantic similarity search with pgvector.
- Vectorless RAG: PostgreSQL full-text/BM25-style keyword retrieval and structured SQL.
- Graph RAG: entity relationship traversal using PostgreSQL tables.
- LLM Wiki Memory: durable wiki-style knowledge pages stored in PostgreSQL.

The key design idea is that all five knowledge stores live inside one PostgreSQL
instance instead of separate managed services. This keeps the AWS cost low while still
showing serious AI system design:

- `chunks.embedding` for vector search.
- `chunks.content` full-text indexes for keyword search.
- `entity_relations` for graph retrieval.
- `wiki_pages` for wiki memory.
- raw structured SQL tables for business data queries.

The project is optimized around three priorities:

1. Correctness: retrieval, grounding, confidence, and citations come before polish.
2. Cost: the target budget is around $50/month or less on AWS.
3. Resume value: choices should be technically meaningful and easy to explain.

## 2. Current Project Status

Current state as of June 1, 2026:

- Phase 2 Terraform infrastructure code is complete.
- Terraform `apply` has not been run and must not be run without explicit approval.
- Local backend RAG pipeline is implemented and testable.
- Local Docker Compose stack includes pgvector PostgreSQL, backend, and frontend.
- Frontend dashboard foundation exists in `frontend/`.
- Local portfolio demo exists through `make demo-local`.
- Backend tests currently pass with `186 passed, 2 skipped`.
- Frontend build and lint passed after the frontend foundation task.

Important distinction:

- The local pipeline is real and working.
- AWS deployment is provisioned as Terraform code but not applied yet.
- Some production API-layer items such as Cognito auth, SSE streaming, and async workers
  are still planned.

## 3. Why This Project Exists

ContextEngine is intended to demonstrate production-style AI engineering skills. It is
not just a simple chat wrapper around an LLM. It shows:

- Data modeling for RAG systems.
- PostgreSQL vector search with pgvector.
- PostgreSQL full-text search for vectorless retrieval.
- Safe text-to-SQL guardrails.
- Graph retrieval without a graph database.
- Wiki-style persistent memory.
- Retrieval routing across multiple modes.
- Source merging, reranking, verification, confidence scoring, and citations.
- FastAPI backend design.
- React dashboard design.
- Terraform AWS infrastructure design with cost control.
- Local demo workflow suitable for interviews.

The intended demo story is:

1. Ingest a few documents.
2. Ask a wiki/definition question.
3. Ask a semantic meaning-based question.
4. Ask an exact keyword question.
5. Ask a SQL/numeric question.
6. Ask a relationship/graph question.
7. Ask a broad hybrid question.
8. Show route decision, sources, citations, verification, confidence, and raw JSON.

## 4. High-Level Architecture

Production target:

```text
React frontend
  -> CloudFront
  -> S3 static frontend
  -> ALB
  -> ECS Fargate FastAPI backend
  -> RDS PostgreSQL 16
       -> pgvector vector store
       -> full-text/BM25 keyword store
       -> entity_relations graph store
       -> wiki_pages memory store
       -> structured SQL tables
  -> S3 documents/wiki backups
  -> SQS ingestion queue and DLQ
  -> DynamoDB metadata/session storage
  -> Cognito auth
  -> Secrets Manager
  -> CloudWatch logs and alarms
```

Local development:

```text
React Vite frontend on localhost:5173
  -> FastAPI backend on localhost:8000
  -> pgvector PostgreSQL on localhost:5432
```

Local services are defined in `docker-compose.yml`.

## 5. The 8-Layer System

ContextEngine is designed around eight layers.

### Layer 1: Data Ingestion

Goal: accept content from multiple source types.

Planned source types:

- PDF
- DOCX
- Web pages
- Databases
- APIs
- Spreadsheets
- Plain text

Current implementation:

- `/ingest` supports plain text ingestion.
- The ingestion pipeline persists a `documents` row.
- It chunks text.
- It generates deterministic local embeddings.
- It stores chunk rows.
- It marks the document as completed or failed.

Key files:

- `backend/app/ingestion/pipeline.py`
- `backend/app/ingestion/chunking.py`
- `backend/app/schemas/document.py`

### Layer 2: Preprocessing

Goal: transform raw content into retrieval-ready knowledge.

Current implemented pieces:

- Text normalization.
- Chunking.
- Deterministic local embeddings.
- Storage into `documents` and `chunks`.

Planned future pieces:

- PDF/DOCX parsers.
- Web scraper.
- Database/API/spreadsheet ingesters.
- Entity extraction.
- Wiki builder using chunk digest method.
- Graph relation extraction.

Important wiki ingestion design:

Do not send a whole long document to GPT-4o in one shot. Instead:

1. Split into chunks.
2. Extract durable facts per chunk.
3. Combine chunk digests.
4. Pass digest to GPT-4o for wiki page extraction.
5. Create or update wiki pages.
6. Resolve wikilinks.
7. Store markdown backup to S3.

This avoids the "first chunk only" failure mode.

### Layer 3: Query Routing

Goal: decide which retrieval mode should answer a query.

Routes:

- `wiki`
- `semantic`
- `bm25`
- `sql`
- `graph`
- `hybrid`

Current implementation:

- Uses deterministic heuristic routing.
- Future planned classifier is GPT-4o-mini.
- Route output follows the locked schema:

```json
{
  "route": "wiki|semantic|bm25|sql|graph|hybrid",
  "confidence": 0.0,
  "reasoning": "one sentence",
  "entities": []
}
```

Key file:

- `backend/app/retrieval/router.py`

Route examples:

| Query | Route |
| --- | --- |
| `What is ContextEngine?` | `wiki` |
| `Which retrieval approach finds similar meaning?` | `semantic` |
| `Find exact keyword FlashRank` | `bm25` |
| `How many products cost more than 100?` | `sql` |
| `Which entities are linked to ContextEngine?` | `graph` |
| `Compare exact keyword search and semantic search` | `hybrid` |

### Layer 4: Hybrid Retrieval

Goal: retrieve evidence from the selected knowledge stores.

Implemented retrievers:

- Keyword/BM25 retriever.
- Semantic pgvector retriever.
- Hardened SQL retriever.
- Graph retriever.
- Wiki retriever.

Key files:

- `backend/app/retrieval/keyword.py`
- `backend/app/retrieval/semantic.py`
- `backend/app/retrieval/sql.py`
- `backend/app/retrieval/graph.py`
- `backend/app/retrieval/wiki.py`
- `backend/app/retrieval/router.py`

Output type:

All retrievers return `SourceCitation` objects. This gives the rest of the pipeline a
single shape regardless of source type.

Important fields:

- `title`
- `score`
- `source_type`
- `snippet`
- `source_id`
- `chunk_id`
- `document_id`
- `retrieval_mode`
- `retrieval_modes`
- `metadata`

### Layer 5: Merge and Rerank

Goal: combine results from multiple retrievers and keep the best evidence.

Implemented:

- Deduplication by `chunk_id` when available.
- Fallback deduplication by normalized title/snippet.
- Score combination across retrieval modes.
- Provenance preservation with `retrieval_modes`.
- Optional FlashRank reranking abstraction.
- Disabled reranker mode by default for local tests.

Key files:

- `backend/app/retrieval/merger.py`
- `backend/app/retrieval/reranker.py`

FlashRank behavior:

- `RERANKER_MODE=disabled` by default.
- `RERANKER_MODE=flashrank` can enable local reranking later.
- Query must not fail if reranking fails.
- Normal tests do not download or import the model.

### Layer 6: Verification and Confidence

Goal: check whether the answer is grounded before presenting it.

Implemented verification checks:

- No sources.
- Source count.
- Retrieval mode diversity.
- Duplicate or near-duplicate snippets.
- Low source scores.
- Missing metadata/citations.
- Simple conflict signals:
  - increase vs decrease
  - allowed vs not allowed
  - true vs false
  - obvious numeric mismatch

Verification output:

- `is_grounded`
- `grounded`
- `has_conflicts`
- `warnings`
- `evidence_count`
- `retrieval_modes`
- `conflict_notes`
- `conflicts`
- `confidence`

Confidence scoring combines:

- Router confidence.
- Average source score.
- Number of sources.
- Retrieval mode diversity.
- Verification warnings.
- Duplicate evidence penalty.
- Conflict penalty.
- No evidence penalty.

Key files:

- `backend/app/verification/verifier.py`
- `backend/app/verification/confidence.py`

### Layer 7: Answer Generation

Goal: generate a grounded answer with citations.

Implemented:

- Generation module.
- Provider abstraction.
- Disabled local provider.
- OpenAI provider path.
- GPT-4o model setting.
- Grounded prompt design.
- Citation extraction.
- Fallback behavior if OpenAI is unavailable.

Local default:

```text
LLM_PROVIDER=disabled
OPENAI_MODEL=gpt-4o
```

When disabled, the system returns deterministic answers such as:

```text
Based on 3 retrieved sources, the evidence suggests...
```

This keeps local development free from OpenAI calls.

Key files:

- `backend/app/generation/generator.py`
- `backend/app/generation/provider.py`

### Layer 8: Memory Update

Goal: continuously improve wiki and graph memory after interactions.

Current state:

- Planned.
- Wiki and graph stores exist.
- Wiki and graph retrievers exist.
- Local seed data exists.

Future behavior:

- Decide whether a conversation contains durable knowledge.
- Update `wiki_pages` if useful.
- Add or update `entity_relations` if useful.
- Store wiki markdown backup to S3.

## 6. Knowledge Stores

ContextEngine intentionally uses one PostgreSQL instance for multiple retrieval modes.

### Store 1: Vector Store

Table:

- `chunks`

Column:

- `embedding VECTOR(1536)`

Index:

- HNSW cosine index.

Purpose:

- Semantic search.
- Meaning-based matching.

Implementation:

- Query embedding is generated.
- PostgreSQL pgvector distance operator searches nearest chunks.
- Results become `SourceCitation` objects.

### Store 2: Keyword/BM25 Store

Table:

- `chunks`

Column:

- `content`

Index:

- GIN index on `to_tsvector('english', content)`.

Purpose:

- Exact keyword and phrase matching.
- Vectorless retrieval.

Implementation:

- Uses PostgreSQL full-text search.
- Uses `websearch_to_tsquery` or equivalent text search.
- Uses rank scoring.
- Avoids SQL injection through parameter binding.

### Store 3: Structured SQL Store

Tables:

- Core tables such as `documents`, `chunks`, `query_logs`, `retrieval_runs`.
- Local demo table `product_catalog`.
- Future ingested structured tables.

Purpose:

- Numeric, aggregate, filter, and table-like questions.

Safety rules:

- Only `SELECT`.
- No comments.
- No semicolon chaining.
- No multi-statement SQL.
- No destructive keywords.
- Only allowlisted tables.
- Max 50 rows.
- 5 second timeout.
- If blocked, return an empty result with warning instead of crashing.

Important:

- Text-to-SQL is disabled unless `OPENAI_API_KEY` exists.
- Normal tests do not require OpenAI.

### Store 4: Graph Store

Table:

- `entity_relations`

Fields:

- `entity_a`
- `relation_type`
- `entity_b`
- `source_chunk_id`
- `confidence`
- timestamps

Purpose:

- Relationship questions.
- Entity connections.
- One-hop and two-hop traversal.

Example local relations:

```text
ContextEngine uses PostgreSQL
ContextEngine uses pgvector
ContextEngine uses FlashRank
ContextEngine deployed_on AWS
pgvector stored_in PostgreSQL
FlashRank reranks RetrievalResults
```

### Store 5: Wiki Store

Table:

- `wiki_pages`

Fields:

- `title`
- `content`
- `tags`
- `source_ids`
- `wikilinks`
- timestamps

Purpose:

- Pre-synthesized durable knowledge.
- Fast documentation-style answers.
- Long-term memory.

Local wiki pages:

- ContextEngine
- PostgreSQL
- pgvector
- FlashRank
- Hybrid RAG
- Verification Layer

## 7. Database Schema

The initial migration creates:

- PostgreSQL extensions:
  - `vector`
  - `pg_trgm`
- `documents`
- `chunks`
- `entity_relations`
- `wiki_pages`
- `retrieval_runs`
- `query_logs`

The audit metadata migration adds richer logging metadata.

Migration files:

- `backend/alembic/versions/0001_initial_schema.py`
- `backend/alembic/versions/0002_query_audit_metadata.py`

Core SQLAlchemy models:

- `Document`
- `Chunk`
- `EntityRelation`
- `WikiPage`
- `RetrievalRun`
- `QueryLog`

Model file:

- `backend/app/db/models.py`

Database connection file:

- `backend/app/db/connection.py`

## 8. Backend API

Current implemented endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Backend health check |
| GET | `/status` | Runtime feature status |
| POST | `/query` | Run RAG query pipeline |
| POST | `/ingest` | Ingest text document |

### GET `/health`

Returns:

```json
{
  "status": "ok",
  "service": "context-engine-backend"
}
```

Purpose:

- Local health checks.
- ALB health checks later.

### GET `/status`

Returns service configuration status:

- service name
- environment
- database configured
- vector support
- wiki enabled
- graph enabled
- verification enabled
- memory update enabled

### POST `/ingest`

Request example:

```json
{
  "source_type": "text",
  "title": "Demo Hybrid RAG Document",
  "filename": "demo-hybrid-rag.txt",
  "content": "ContextEngine combines BM25 keyword search, pgvector semantic search...",
  "metadata": {
    "source": "frontend"
  }
}
```

Response includes:

- `document_id`
- `status`
- `source_type`
- `chunks_planned`
- `chunk_count`
- `title`
- `filename`
- `metadata`
- `message`

### POST `/query`

Request example:

```json
{
  "query": "What retrieval modes does ContextEngine combine?",
  "top_k": 5
}
```

Pipeline:

```text
QueryRequest
  -> RetrievalRouter.route
  -> RetrievalRouter.retrieve
  -> merge/rerank if needed
  -> verify_response
  -> score_confidence
  -> generate_answer
  -> persist_query_audit
  -> QueryResponse
```

Response includes:

- answer
- route decision
- sources
- citations
- verification
- confidence
- generation metadata
- optional query log id
- optional retrieval run id
- token and cost metadata

## 9. Query Pipeline Detailed Walkthrough

When a user asks a question:

1. FastAPI receives `QueryRequest`.
2. Router normalizes the query.
3. Router selects route:
   - wiki
   - semantic
   - bm25
   - sql
   - graph
   - hybrid
4. Retriever or retrievers run.
5. Hybrid route runs semantic and keyword in parallel.
6. Hybrid can include SQL if structured signals are present.
7. Merge layer deduplicates results.
8. Reranker layer optionally reorders results.
9. Verification checks evidence quality.
10. Confidence scorer creates a score and label.
11. Generator creates grounded answer and citations.
12. Audit layer writes query log and retrieval run metadata.
13. API returns structured response.

No OpenAI call is required in the default local mode.

## 10. Ingestion Pipeline Detailed Walkthrough

When text is ingested:

1. FastAPI receives `DocumentIngestRequest`.
2. `IngestionPipeline` opens an async DB session.
3. It creates a `Document` row with status `processing`.
4. It normalizes the supplied text.
5. It chunks the text.
6. It generates deterministic local embeddings.
7. It inserts `Chunk` rows.
8. It marks the document as `completed`.
9. If text is empty, status becomes `failed`.
10. If chunk persistence fails, rollback is attempted and failed status is recorded.

This makes newly ingested text queryable by:

- keyword retrieval
- semantic retrieval
- hybrid retrieval

## 11. Embeddings

Local mode:

- Provider: deterministic local hash embedding.
- Dimension: 1536.
- No API key required.
- Stable output for tests.
- Suitable for local smoke demos, not production-quality semantics.

Production planned mode:

- OpenAI `text-embedding-3-small`.
- Same 1536 dimensions.
- Stored in `chunks.embedding`.

Key file:

- `backend/app/embeddings/provider.py`

## 12. SQL Safety Design

The SQL retriever is intentionally guarded because text-to-SQL can be dangerous.

Guard behavior:

- Rejects empty SQL.
- Rejects non-SELECT statements.
- Rejects:
  - DROP
  - DELETE
  - INSERT
  - UPDATE
  - TRUNCATE
  - ALTER
  - CREATE
  - EXEC
- Rejects SQL comments:
  - `--`
  - `/* */`
- Rejects semicolon chaining.
- Rejects multi-statement SQL.
- Restricts table access to allowlist.
- Enforces max rows.
- Enforces timeout.

Local allowlist:

```text
SQL_ALLOWED_TABLES=product_catalog
```

The demo table `product_catalog` is local-only and created by the seed script.

Key file:

- `backend/app/retrieval/sql.py`

## 13. Query Logging and Audit

Every query attempts to persist audit metadata.

Tables:

- `query_logs`
- `retrieval_runs`

Query log stores:

- user query
- route decision
- route confidence
- answer
- confidence score
- confidence label
- grounding flag
- conflict flag
- source count
- citation count
- tokens used
- cost
- latency
- non-secret metadata

Retrieval run stores:

- query log id
- route decision
- retrievers used
- top_k
- source ids
- chunk ids
- source scores
- reranker mode
- verification warnings
- generation provider
- latency

Failure behavior:

- Logging must never break `/query`.
- If persistence fails, the API still returns the answer.

Key file:

- `backend/app/db/query_logging.py`

## 14. Local Demo Data

Demo documents live in:

- `demo/data/`

Files:

- `hybrid_rag_overview.txt`
- `pgvector_semantic_search.txt`
- `bm25_keyword_retrieval.txt`
- `graph_rag_relationships.txt`
- `verification_confidence.txt`
- `aws_deployment_cost_controls.txt`
- `portfolio_demo_script.txt`

Local seed script:

- `backend/app/scripts/seed_local.py`

It seeds:

- sample keyword chunks
- `product_catalog`
- graph relations
- wiki pages

Demo script:

- `backend/app/scripts/demo_local.py`

It:

1. Loads demo documents.
2. Seeds SQL/wiki/graph demo knowledge.
3. Ingests demo documents.
4. Runs sample route coverage queries.
5. Prints route, answer, confidence, citations, and audit ids.

Run:

```powershell
make demo-local
```

## 15. Frontend

Frontend path:

- `frontend/`

Stack:

- React 18
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- Zustand
- lucide-react icons

Main implemented UI:

- dashboard layout
- query panel
- ingest document panel
- answer display
- citations/source cards
- route decision badge
- confidence badge
- verification panel
- raw JSON/debug panel
- backend health/status panel

Key files:

- `frontend/src/App.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/stores/useDashboardStore.ts`
- `frontend/src/types/api.ts`
- `frontend/src/components/QueryPanel.tsx`
- `frontend/src/components/IngestPanel.tsx`
- `frontend/src/components/AnswerDisplay.tsx`
- `frontend/src/components/SourceCards.tsx`
- `frontend/src/components/RouteDecisionBadge.tsx`
- `frontend/src/components/ConfidenceBadge.tsx`
- `frontend/src/components/VerificationPanel.tsx`
- `frontend/src/components/DebugPanel.tsx`
- `frontend/src/components/SystemStatus.tsx`

Environment:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Local URL:

```text
http://localhost:5173
```

## 16. Infrastructure

Terraform path:

- `infra/`

Terraform status:

- Infrastructure code is complete.
- `terraform plan` has passed.
- Last known plan: 60 to add, 0 to change, 0 to destroy.
- `terraform apply` is deferred and must not run without explicit approval.

Root Terraform files:

- `infra/main.tf`
- `infra/variables.tf`
- `infra/outputs.tf`
- `infra/versions.tf`
- `infra/dynamodb.tf`
- `infra/sqs.tf`
- `infra/secrets.tf`

Modules:

- `infra/modules/vpc`
- `infra/modules/rds`
- `infra/modules/ecs`
- `infra/modules/s3`
- `infra/modules/cloudfront`
- `infra/modules/cognito`
- `infra/modules/cloudwatch`

AWS region:

```text
us-east-1
```

Naming:

```text
context-engine-{environment}-{resource}
```

Resource examples:

- `context-engine-prod-vpc`
- `context-engine-prod-rds`
- `context-engine-prod-ecs-cluster`
- `context-engine-prod-documents-256716302630`

## 17. AWS Resource Design

VPC:

- CIDR `10.0.0.0/16`.
- 2 public subnets.
- 2 private subnets.
- Internet Gateway.
- Single NAT Gateway for cost control.
- ALB security group.
- ECS security group.
- RDS security group.

RDS:

- PostgreSQL 16.
- db.t3.micro.
- gp3 storage.
- Single AZ.
- Password managed with Secrets Manager.
- Extensions enabled by Alembic, not Terraform.

ECS:

- Fargate.
- 0.25 vCPU / 0.5 GB.
- Desired count 0 by default.
- ALB target group and listener.
- ECR backend repository.

S3:

- frontend bucket.
- documents bucket.
- wiki bucket.
- private buckets.
- encryption enabled.
- public access blocked.

CloudFront:

- Origin Access Control.
- SPA routing.

Supporting services:

- DynamoDB sessions table with PAY_PER_REQUEST.
- SQS ingestion queue.
- SQS dead-letter queue.
- Cognito user pool and app client.
- Secrets Manager entries.
- CloudWatch log groups with 7 day retention.

## 18. Cost Controls

Hard goal:

```text
Stay around or below $50/month.
```

Important choices:

- PostgreSQL holds all knowledge stores.
- No OpenSearch.
- No Neo4j.
- No ElastiCache.
- No dedicated vector DB.
- Single NAT Gateway.
- Single-AZ RDS.
- ECS desired count 0 when idle.
- RDS stopped when not demoing.
- DynamoDB PAY_PER_REQUEST.
- CloudWatch logs 7 day retention.
- gp3 storage.

Start demo:

```powershell
make demo-on
```

Stop demo:

```powershell
make demo-off
```

Check status:

```powershell
make status
```

## 19. Local Development Runbook

First-time backend environment:

```powershell
cd C:\Om\Codes\context_engine
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
```

Start backend stack:

```powershell
make local-up
```

Run migrations:

```powershell
make local-migrate
```

Run local demo:

```powershell
make demo-local
```

Start full local stack including frontend:

```powershell
make local-full-up
```

Stop local stack:

```powershell
make local-down
```

Backend health:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health |
  Select-Object -ExpandProperty Content
```

Frontend local dev:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Frontend URL:

```text
http://localhost:5173
```

## 20. Validation Commands

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff format .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run build
npm.cmd run lint
```

Compose:

```powershell
docker compose config
```

## 21. Security Notes

Secrets:

- Never commit real secrets.
- Use `.env.example` for placeholders.
- Use AWS Secrets Manager in production.
- Do not store OpenAI keys in Git.

SQL:

- SQL retriever uses strict guardrails.
- Only allowlisted tables can be queried.
- Dangerous statements are blocked.

Network:

- Production RDS is private.
- ECS talks to RDS through security groups.
- ALB is the public backend entry point.
- Frontend is served through CloudFront.

Auth:

- Cognito infrastructure exists in Terraform.
- FastAPI Cognito JWT verification is planned for later API-layer work.

CORS:

- Local frontend origins are configured for `localhost:5173`.

## 22. Important Environment Variables

Backend:

```text
OPENAI_API_KEY=
LLM_PROVIDER=disabled
OPENAI_MODEL=gpt-4o
DATABASE_URL=postgresql+asyncpg://context_engine:context_engine_dev_password@postgres:5432/context_engine
AWS_REGION=us-east-1
ENVIRONMENT=development
LOG_LEVEL=INFO
EMBEDDING_PROVIDER=local
EMBEDDING_DIMENSION=1536
SQL_ALLOWED_TABLES=product_catalog
RERANKER_MODE=disabled
WIKI_ENABLED=true
GRAPH_ENABLED=true
VERIFICATION_ENABLED=true
MEMORY_UPDATE_ENABLED=true
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Frontend:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## 23. Testing Strategy

Backend tests cover:

- health endpoint
- schemas
- route heuristics
- chunking
- embedding provider
- keyword retrieval
- semantic retrieval
- SQL guard and SQL retriever
- graph retrieval
- wiki retrieval
- merger
- reranker
- verification
- confidence
- generation
- ingestion pipeline
- query logging
- local demo script
- seed script idempotency
- migrations

Important testing rule:

- Normal tests do not require live AWS.
- Normal tests do not require RDS.
- Normal tests do not require Docker.
- Normal tests do not require OpenAI.
- Normal tests do not require FlashRank.

Optional integration tests are skipped unless explicitly enabled.

## 24. Portfolio Demo Script

Recommended local demo flow:

```powershell
cd C:\Om\Codes\context_engine
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
make local-up
make local-migrate
make demo-local
make local-full-up
```

Open:

```text
http://localhost:5173
```

Demo questions:

- `What is ContextEngine?`
- `Which retrieval approach finds similar meaning in stored chunks?`
- `Find exact keyword FlashRank`
- `How many software products cost more than 100?`
- `Which entities are linked to ContextEngine?`
- `Compare exact keyword search and semantic search for ContextEngine`

What to show:

- Route decision badge.
- Confidence badge.
- Answer text.
- Citations.
- Source cards.
- Verification warnings/conflicts.
- Raw JSON response.
- Ingest panel.
- Backend status panel.

## 25. Current Limitations

Known current limitations:

- Terraform apply has not been run.
- Production AWS endpoint does not exist yet.
- Cognito JWT auth is not wired into FastAPI yet.
- SSE streaming is planned but current `/query` returns a normal JSON response.
- GPT-4o generation is optional and disabled by default locally.
- SQL text-to-SQL requires `OPENAI_API_KEY`.
- FlashRank is optional and disabled by default locally.
- PDF/DOCX/web/API/spreadsheet parsers are planned.
- Entity extraction and automatic graph/wiki memory update are planned.
- RAGAS evaluation dataset and scores are planned.
- CI/CD workflows are planned.

## 26. Resume Talking Points

Strong resume bullets from the implemented and planned architecture:

- Built a hybrid RAG system combining semantic, keyword, SQL, graph, and wiki retrieval.
- Implemented pgvector semantic search in PostgreSQL with 1536-dimensional embeddings.
- Implemented vectorless retrieval using PostgreSQL full-text search.
- Designed a text-to-SQL retriever with single-statement SELECT enforcement and table allowlisting.
- Implemented Graph RAG using PostgreSQL `entity_relations`, avoiding Neo4j cost.
- Implemented wiki memory retrieval using PostgreSQL `wiki_pages`.
- Added source merging, deduplication, provenance preservation, and optional FlashRank reranking.
- Added deterministic verification and confidence scoring before answer generation.
- Added citation-aware answer generation with a disabled local provider and OpenAI provider path.
- Persisted query logs and retrieval run metadata for audit/debugging.
- Built a React/Vite dashboard for route, confidence, sources, verification, and JSON inspection.
- Designed cost-aware AWS infrastructure using Terraform, ECS Fargate, RDS, S3, CloudFront, SQS,
  DynamoDB, Cognito, Secrets Manager, and CloudWatch.

## 27. Troubleshooting

### Backend healthy check

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health |
  Select-Object -ExpandProperty Content
```

Expected:

```json
{"status":"ok","service":"context-engine-backend"}
```

### `make demo-local` graph seed issue

Resolved on June 1, 2026.

Cause:

- asyncpg could not infer reused parameter types inside raw SQL.

Fix:

- Graph seed now uses ORM existence check plus ORM insert.
- Regression test ensures idempotency.

### SQL route returns no sources

This is expected when `OPENAI_API_KEY` is not set. The SQL retriever is disabled without
OpenAI credentials.

### Frontend cannot call backend

Check:

- backend is running on `http://localhost:8000`
- frontend `VITE_API_BASE_URL` is `http://localhost:8000`
- `CORS_ALLOWED_ORIGINS` includes `http://localhost:5173`

### Docker Compose data reset

The PostgreSQL data lives in the named volume:

```text
postgres_data
```

Removing Docker volumes will delete local demo data.

## 28. File Map

Most important files:

```text
CLAUDE.md
docs/PROGRESS.md
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/CONVENTIONS.md
docs/PROJECT_GUIDE.md

backend/app/main.py
backend/app/core/config.py
backend/app/db/models.py
backend/app/db/connection.py
backend/app/db/query_logging.py
backend/app/ingestion/pipeline.py
backend/app/ingestion/chunking.py
backend/app/embeddings/provider.py
backend/app/retrieval/router.py
backend/app/retrieval/keyword.py
backend/app/retrieval/semantic.py
backend/app/retrieval/sql.py
backend/app/retrieval/graph.py
backend/app/retrieval/wiki.py
backend/app/retrieval/merger.py
backend/app/retrieval/reranker.py
backend/app/verification/verifier.py
backend/app/verification/confidence.py
backend/app/generation/generator.py
backend/app/generation/provider.py
backend/app/scripts/seed_local.py
backend/app/scripts/demo_local.py

frontend/src/App.tsx
frontend/src/services/api.ts
frontend/src/types/api.ts
frontend/src/stores/useDashboardStore.ts
frontend/src/components/*

infra/main.tf
infra/modules/*

docker-compose.yml
Makefile
```

## 29. What Makes This Project Distinct

ContextEngine is distinct because it does not use expensive specialized services for each
retrieval paradigm. Instead, it demonstrates how far a careful PostgreSQL-centered design
can go:

- vector retrieval
- keyword retrieval
- graph traversal
- wiki memory
- structured SQL
- audit logging
- cost-aware cloud architecture

This makes it both practical for a solo portfolio budget and technically interesting for
engineering interviews.

## 30. Golden Rules

Never violate these project rules:

- Do not run `terraform apply` without explicit approval.
- Do not deploy without explicit approval.
- Do not connect to AWS RDS during local tasks.
- Do not commit secrets.
- Keep ECS desired count at 0 by default.
- Keep AWS region as `us-east-1`.
- Keep resource names prefixed with `context-engine-*`.
- Keep the stack locked unless an architecture decision is explicitly changed.
- Keep local tests independent of AWS, OpenAI, Docker, and production RDS.

