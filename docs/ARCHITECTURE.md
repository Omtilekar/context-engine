# ContextEngine — Architecture Overview

---

## System Overview

ContextEngine is a next-generation context engine that merges four AI retrieval paradigms into one unified pipeline:

- **Vector RAG** — semantic similarity search
- **Vectorless RAG** — BM25 keyword + SQL structured retrieval
- **Graph RAG** — entity relationship traversal
- **LLM Wiki / Memory** — Karpathy-inspired persistent knowledge accumulation

All five knowledge stores live inside a single RDS PostgreSQL instance. One database, five superpowers, one bill.

---

## High-Level AWS Architecture

```
User (React)
    │
    ▼
CloudFront (S3 static frontend)
    │
    ▼
ALB (Application Load Balancer)
    │
    ▼
ECS Fargate (FastAPI + Celery worker)
    │
    ├── RDS PostgreSQL 16
    │   ├── pgvector (vector store)
    │   ├── pg_trgm + tsvector (BM25 index)
    │   ├── entity_relations table (graph store)
    │   ├── wiki_pages table (wiki/memory store)
    │   └── raw SQL tables (structured data)
    │
    ├── S3 (documents + wiki markdown + frontend)
    ├── SQS (ingestion queue + DLQ)
    ├── DynamoDB (sessions + query logs)
    ├── Cognito (auth)
    └── Secrets Manager (API keys + DB creds)
```

---

## The 8 Layers

### Layer 1 — Data Ingestion

Supported source types:
- PDF / DOCX — pdfplumber + mammoth
- Web pages — Playwright headless scraping
- Databases — SQLAlchemy table reflection
- APIs / JSON — httpx + structured parsing
- Spreadsheets — openpyxl + pandas

All raw files stored to S3 immediately on upload.

---

### Layer 2 — Preprocessing Pipeline

```
Raw source text
    ↓
Cleaning + OCR (if needed)
    ↓
Chunking + digest
  - 512 tokens per chunk
  - 64 token overlap
  - digest step for long sources (your LLM Wiki method):
    split → extract facts per chunk → combine digests
    prevents first-chunk-only problem
    ↓
Entity extraction (GPT-4o-mini)
  - people, organizations, concepts, locations, events
    ↓
Storage routing — fans out to ALL 5 stores simultaneously:
  ├── Vector store (pgvector)
  ├── BM25 index (pg_trgm)
  ├── Graph store (entity_relations)
  ├── Wiki store (wiki_pages via wiki_builder)
  └── Structured data (raw SQL tables if DB source)
```

---

### Layer 3 — Query Understanding + Routing

GPT-4o-mini receives the user query and returns:

```json
{
  "route": "wiki|semantic|bm25|sql|graph|hybrid",
  "confidence": 0.0–1.0,
  "reasoning": "brief explanation",
  "entities": ["named", "entities", "in", "query"]
}
```

**Route decision logic:**

| Query type | Example | Route |
|-----------|---------|-------|
| Pre-synthesized knowledge | "What did Shivaji accomplish?" | wiki |
| Conceptual / meaning-based | "What are the key risks?" | semantic |
| Exact keyword / phrase | "Find all GDPR mentions" | bm25 |
| Numerical / structured | "How many invoices in Q3?" | sql |
| Relationship-based | "Who works with Professor X?" | graph |
| Ambiguous / multi-faceted | "Tell me everything about X" | hybrid |

---

### Layer 4 — Hybrid Retrieval (parallel)

All selected retrievers run simultaneously via `asyncio.gather`:

**Wiki retriever** (`retrievers/wiki.py`)
- Queries `wiki_pages` table by title, tags, wikilinks
- Returns pre-synthesized structured content
- No embedding needed — fastest retriever
- Knowledge compounds with every ingest

**Vector retriever** (`retrievers/vector.py`)
- Embeds query with text-embedding-3-small
- pgvector cosine similarity search
- HNSW index — sub-100ms at this scale
- Returns top-5 chunks

**BM25 retriever** (`retrievers/bm25.py`)
- PostgreSQL full-text search via pg_trgm + tsvector
- GIN index for fast lookup
- Returns top-5 exact matches

**Graph retriever** (`retrievers/graph.py`)
- Extracts entities from query
- Traverses entity_relations table
- Returns connected facts up to 2 hops
- Example: Professor → works_on → Project → uses → Technology

**SQL retriever** (`retrievers/sql.py`)
- GPT-4o-mini generates SELECT statement from query
- SQL injection guard: SELECT only, max 50 rows, 5s timeout
- Executes against structured RDS tables
- Returns formatted results

**Hybrid merger** (`retrievers/merger.py`)
- Reciprocal Rank Fusion (RRF) algorithm
- Deduplication by chunk_id
- Normalized scores across all retrievers
- Returns top-10 candidates

---

### Layer 5 — Merge · Rerank · Compress

```
Top-10 merged candidates
    ↓
FlashRank re-ranker (ms-marco-MiniLM-L-12-v2)
  - Cross-encoder scores all 10 candidates
  - Returns top-3 highest quality
    ↓
Context compression
  - Remove redundancy across top-3
  - Pack 8–12 most relevant chunks
  - Fit within GPT-4o context window efficiently
```

---

### Layer 6 — Verification + Citation

Before generating the answer, a lightweight verification pass:

```
Top-3 context chunks + query
    ↓
Source grounding check (GPT-4o-mini)
  - Does every claim in the context trace to a source?
    ↓
Conflict detection
  - Are there contradictions between sources?
  - Flag and note conflicts in the answer
    ↓
Confidence scoring
  - 0.0–1.0 score based on source quality + grounding
  - Shown in UI alongside the answer
    ↓
Citation anchor injection
  - [Source 1], [Source 2] anchors added to context
  - LLM instructed to cite inline
```

---

### Layer 7 — GPT-4o Answer Generation

```
System prompt + verified context + citation anchors + user query
    ↓
GPT-4o (stream=True)
    ↓
SSE token stream → React UI
    ↓
Final events:
  - verification result (grounded, conflicts, confidence)
  - sources panel (title, page, score, retriever type)
  - done event (tokens used, cost, route taken)
```

---

### Layer 8 — Memory Update (continuous learning)

After every conversation turn:

```
Conversation turn
    ↓
GPT-4o-mini decides: should this be remembered?
  - Is this a stable fact?
  - Is this a reusable insight?
  - Is this a decision worth persisting?
    ↓
If yes:
  ├── Update wiki_pages (new or enriched page)
  └── Update entity_relations (new relationships)
```

This makes ContextEngine smarter with every conversation — not just every document ingest.

---

## Ingestion Pipeline (detailed)

```
User uploads source (PDF / URL / DB / API / Spreadsheet)
    │
POST /api/v1/ingest/*
    │
    ├── Raw file → S3
    ├── Document record → RDS (status: pending)
    └── Job → SQS queue
                │
                ▼
        Celery worker picks up job
                │
                ▼
        Parser (by source type)
                │
                ▼
        Chunker (512 tok, 64 overlap)
        + Digest step for long sources
                │
                ▼
        Entity extractor (GPT-4o-mini)
        → people, orgs, concepts, events
                │
        ┌───────┼───────────────────┐
        ▼       ▼                   ▼
    Embedder  Wiki builder      Graph builder
    (batch)   (GPT-4o)         (entity_relations)
        │       │                   │
        ▼       ▼                   ▼
    pgvector  wiki_pages        entity_relations
    chunks    table             table
                │
                ▼
        Update document status → completed
```

---

## Data Models

### documents table
```sql
id          UUID PK DEFAULT gen_random_uuid()
filename    VARCHAR(255) NOT NULL
source_type VARCHAR(50)  -- pdf, web, database, api, spreadsheet
s3_key      VARCHAR(500)
status      VARCHAR(50) DEFAULT 'pending'  -- pending, processing, completed, failed
created_at  TIMESTAMP DEFAULT NOW()
updated_at  TIMESTAMP DEFAULT NOW()
```

### chunks table
```sql
id          UUID PK DEFAULT gen_random_uuid()
document_id UUID FK → documents.id
content     TEXT NOT NULL
embedding   VECTOR(1536)
chunk_index INTEGER
page_number INTEGER
created_at  TIMESTAMP DEFAULT NOW()
```

### entity_relations table (Graph store — NEW)
```sql
id            UUID PK DEFAULT gen_random_uuid()
entity_a      VARCHAR(255) NOT NULL
relation_type VARCHAR(100) NOT NULL
entity_b      VARCHAR(255) NOT NULL
source_chunk_id UUID REFERENCES chunks(id)
confidence    FLOAT DEFAULT 1.0
created_at    TIMESTAMP DEFAULT NOW()
```

### wiki_pages table (Wiki/Memory store — NEW)
```sql
id         UUID PK DEFAULT gen_random_uuid()
title      VARCHAR(255) UNIQUE NOT NULL
content    TEXT NOT NULL
tags       TEXT[] DEFAULT '{}'
source_ids UUID[] DEFAULT '{}'
wikilinks  TEXT[] DEFAULT '{}'
created_at TIMESTAMP DEFAULT NOW()
updated_at TIMESTAMP DEFAULT NOW()
```

### query_logs table
```sql
id             UUID PK DEFAULT gen_random_uuid()
query          TEXT NOT NULL
route_decision VARCHAR(50)  -- wiki, semantic, bm25, sql, graph, hybrid
confidence     FLOAT
retrievers_used TEXT[]
latency_ms     INTEGER
tokens_used    INTEGER
cost_usd       FLOAT
grounded       BOOLEAN
conflicts      TEXT[]
created_at     TIMESTAMP DEFAULT NOW()
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | ALB health check |
| POST | `/api/v1/query` | Main query — SSE streaming |
| POST | `/api/v1/ingest/upload` | Upload PDF/DOCX |
| POST | `/api/v1/ingest/url` | Ingest web page |
| POST | `/api/v1/ingest/database` | Ingest SQL table |
| POST | `/api/v1/ingest/api` | Ingest API endpoint |
| POST | `/api/v1/ingest/spreadsheet` | Ingest Excel/CSV |
| GET | `/api/v1/ingest/status/:id` | Poll ingestion status |
| GET | `/api/v1/documents` | List documents |
| DELETE | `/api/v1/documents/:id` | Delete document |
| GET | `/api/v1/wiki` | List wiki pages |
| GET | `/api/v1/wiki/:title` | Get wiki page |
| GET | `/api/v1/graph/entities` | List known entities |
| GET | `/api/v1/analytics/overview` | Query stats |
| GET | `/api/v1/analytics/queries` | Recent query log |
| POST | `/auth/token` | Cognito JWT exchange |

---

## Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/contextengine

# AWS
AWS_REGION=us-east-1
S3_DOCUMENTS_BUCKET=context-engine-prod-documents-256716302630
S3_WIKI_BUCKET=context-engine-prod-wiki-256716302630
SQS_INGEST_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/256716302630/context-engine-prod-ingest-queue

# Auth
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1

# App
ENVIRONMENT=production
LOG_LEVEL=INFO

# Feature flags
WIKI_ENABLED=true
GRAPH_ENABLED=true
VERIFICATION_ENABLED=true
MEMORY_UPDATE_ENABLED=true
```

---

## Local Development

```bash
# Start local services
docker compose up -d  # postgres+pgvector, backend

# Run migrations
cd backend && poetry run alembic upgrade head

# Start API
poetry run uvicorn app.main:app --reload --port 8000

# Start frontend
cd frontend && pnpm dev
```

Docker Compose runs:
- `pgvector/pgvector:pg16` — PostgreSQL with pgvector extension
- Backend FastAPI + Celery worker (combined for local dev)

No Redis, no OpenSearch, no separate vector DB needed locally.