# ContextEngine — Architecture Overview

---

## System Overview

ContextEngine is a hybrid RAG (Retrieval-Augmented Generation) system that intelligently routes queries to the most appropriate retrieval strategy based on query type.

```
                         ┌─────────────────────────────────────┐
                         │           AWS us-east-1             │
                         │                                     │
  User ──► CloudFront ──►│ ALB ──► ECS Fargate (FastAPI)      │
  (React)   (S3 static)  │              │                     │
                         │    ┌─────────┴──────────┐          │
                         │    │   Query Classifier  │          │
                         │    │   (GPT-4o-mini)     │          │
                         │    └─────────┬──────────┘          │
                         │    ┌─────────┼──────────┐          │
                         │    │         │          │           │
                         │  Vector    BM25       SQL          │
                         │  (pgvec)  (pg_trgm) (GPT→SQL)     │
                         │    └─────────┼──────────┘          │
                         │          FlashRank                 │
                         │          Re-ranker                 │
                         │              │                     │
                         │         GPT-4o SSE                 │
                         │              │                     │
                         │    RDS PostgreSQL                  │
                         │    S3 │ SQS │ DynamoDB             │
                         │    Cognito │ Secrets Manager       │
                         └─────────────────────────────────────┘
```

---

## Three Retrieval Paths

### Path 1 — Semantic (Vector)
**Trigger:** Conceptual, meaning-based queries
**Example:** "What are the key risks mentioned in the report?"
**Flow:** Embed query → pgvector cosine search → top-5 chunks → FlashRank → GPT-4o

### Path 2 — Structured (Vectorless)
**Trigger:** Exact terms, keywords, database queries
**Sub-paths:**
- **BM25:** "Find all mentions of GDPR compliance" → pg_trgm FTS
- **SQL:** "How many invoices were issued in Q3?" → GPT-4o-mini generates SQL → RDS
**Flow:** BM25 or SQL → normalize results → FlashRank → GPT-4o

### Path 3 — Hybrid
**Trigger:** Ambiguous queries that could benefit from both
**Flow:** Vector + BM25 run in parallel (asyncio.gather) → RRF merger → FlashRank → GPT-4o

---

## Document Ingestion Flow

```
User uploads (PDF / URL / DB)
        │
        ▼
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
            Parser (pdfplumber / Playwright / SQLAlchemy)
                    │
                    ▼
            Chunker (512 tokens, 64 overlap)
                    │
                    ▼
            Embedder (text-embedding-3-small, batched)
                    │
                    ▼
            Write chunks + vectors → RDS (pgvector)
            Write to FTS index → RDS (pg_trgm)
            Update document status → completed
```

---

## Data Models

### documents table
```
id          UUID PK
filename    VARCHAR(255)
source_type ENUM (pdf, web, database)
s3_key      VARCHAR(500)
status      ENUM (pending, processing, completed, failed)
created_at  TIMESTAMP
updated_at  TIMESTAMP
```

### chunks table
```
id          UUID PK
document_id UUID FK → documents.id
content     TEXT
embedding   VECTOR(1536)    ← pgvector
chunk_index INTEGER
page_number INTEGER | NULL
created_at  TIMESTAMP
```

### query_logs table
```
id              UUID PK
query           TEXT
route_decision  ENUM (semantic, structured, hybrid)
confidence      FLOAT
latency_ms      INTEGER
tokens_used     INTEGER
cost_usd        FLOAT
created_at      TIMESTAMP
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | ALB health check |
| POST | `/api/v1/query` | Main RAG query (SSE streaming) |
| POST | `/api/v1/ingest/upload` | Upload PDF |
| POST | `/api/v1/ingest/url` | Ingest URL |
| GET | `/api/v1/ingest/status/:id` | Poll ingestion status |
| GET | `/api/v1/documents` | List documents |
| DELETE | `/api/v1/documents/:id` | Delete document |
| GET | `/api/v1/analytics/overview` | Query stats |
| GET | `/api/v1/analytics/queries` | Recent query log |
| POST | `/auth/token` | Exchange Cognito code for JWT |

---

## Environment Variables Required

```bash
# OpenAI
OPENAI_API_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/contextengine

# AWS
AWS_REGION=us-east-1
S3_DOCUMENTS_BUCKET=context-engine-prod-documents-<account-id>
SQS_INGEST_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/<account-id>/context-engine-prod-ingest-queue

# Auth
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1

# App
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## Local Development

Uses Docker Compose to mirror AWS services locally:

```yaml
services:
  postgres:    # pgvector/pgvector:pg16 image
  backend:     # FastAPI + Celery worker
```

No local Redis needed (TTLCache is in-process).
No local OpenSearch needed (pgvector handles everything).

Start local dev:
```bash
docker compose up -d
cd backend && poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```
