# ContextEngine — Claude Instructions

> Read this file completely before doing anything else.
> Then read `docs/PROGRESS.md` to find out where we left off.
> Do not write any code until you have done both.

---

## Project Overview

**Name:** ContextEngine
**Tagline:** Hybrid RAG system with intelligent query routing across semantic and structured retrieval pipelines
**Type:** Solo showcase project (portfolio / resume)
**Goal:** Demonstrate production-level AI engineering skills to potential employers
**GitHub:** https://github.com/Omtilekar/context-engine

---

## Non-Negotiable Rules

1. **Always read `docs/PROGRESS.md` first** — never assume what is or isn't built
2. **Never write code without being asked** — confirm the task before starting
3. **Never run `terraform apply`** without showing the plan output first and getting confirmation
4. **Never hardcode secrets** — always use AWS Secrets Manager
5. **Always use the `context-engine-*` prefix** for every AWS resource name
6. **AWS region is `us-east-1`** — do not use any other region, ever
7. **Never suggest switching tech** — the stack is locked (see below)
8. **Commit after every completed task** — use the checklist task name as the commit message
9. **Never create files outside the project structure** defined in `docs/ARCHITECTURE.md`
10. **Update `docs/PROGRESS.md`** at the end of every session
11. **Admin CLI profile:** `context-engine-admin`
12. **GitHub Actions CLI profile:** `context-engine`

---

## Architecture — 8-Layer Merged System

Merges four paradigms: Vector RAG + Vectorless RAG + Graph RAG + LLM Wiki Memory

### The 8 Layers

```
Layer 1 — Data Ingestion
  PDF · DOCX · Web pages · Databases · APIs · Spreadsheets

Layer 2 — Preprocessing Pipeline
  Cleaning → Chunking + digest → Entity extraction → Storage routing (fans out to all 5 stores)

Layer 3 — Query Understanding + Routing
  Intent detection → Entity extraction → Query type → Route decision (6 routes) → Confidence

Layer 4 — Hybrid Retrieval (asyncio.gather — all run in parallel)
  Wiki retrieval · Vector retrieval · BM25 retrieval · Graph retrieval · SQL retrieval

Layer 5 — Merge · Rerank · Compress
  RRF merger → FlashRank re-ranker → Context compression (digest method)

Layer 6 — Verification + Citation
  Source grounding → Conflict detection → Confidence scoring → Citation anchors

Layer 7 — GPT-4o Answer Generation
  Streaming SSE · Structured output · Explainability (why this answer, which route)

Layer 8 — Memory Update (continuous learning)
  Should this be remembered? → Wiki page update → Graph relation update
```

### Five Knowledge Stores — all inside ONE RDS PostgreSQL instance

| Store | Technology | Cost |
|-------|-----------|------|
| Vector store | pgvector HNSW index | $0 extra |
| BM25 index | pg_trgm + tsvector GIN index | $0 extra |
| Graph store | entity_relations table | $0 extra |
| Wiki / memory | wiki_pages table + S3 markdown | $0 extra |
| Structured data | raw SQL tables | $0 extra |

### Six Query Routes

1. **wiki** — pre-synthesized pages, fastest, no embedding
2. **semantic** — pgvector cosine similarity
3. **bm25** — pg_trgm full-text, exact keyword
4. **sql** — GPT-4o-mini generates SQL, executes on RDS
5. **graph** — entity → relations → connected facts
6. **hybrid** — any combination via asyncio.gather + RRF

---

## Locked Tech Stack

### Backend
| Component | Choice |
|-----------|--------|
| Language | Python 3.14 |
| Framework | FastAPI |
| RAG Framework | LlamaIndex |
| ORM | SQLAlchemy 2.x async |
| Validation | Pydantic v2 |
| Task Queue | Celery |
| Dependency Mgmt | Poetry 2.4.1 |
| Migrations | Alembic |

### AI / Models
| Component | Choice | Notes |
|-----------|--------|-------|
| LLM (answers) | GPT-4o | Primary |
| LLM (classifier) | GPT-4o-mini | 6-route classifier |
| LLM (SQL gen) | GPT-4o-mini | Text-to-SQL |
| LLM (wiki ingest) | GPT-4o | Quality extraction |
| LLM (verification) | GPT-4o-mini | Claim checking |
| Embeddings | text-embedding-3-small | 1536 dims |
| Re-ranker | FlashRank (local) | NOT Cohere |
| PDF parsing | pdfplumber | |
| Web scraping | Playwright | Headless |
| Spreadsheets | openpyxl + pandas | |

### Database & Storage
| Component | Choice | Notes |
|-----------|--------|-------|
| Primary DB | RDS PostgreSQL 16 | db.t3.micro |
| Vector search | pgvector HNSW | In RDS |
| Lexical search | pg_trgm + tsvector | In RDS |
| Graph store | entity_relations table | In RDS — NOT Neo4j |
| Wiki store | wiki_pages table | In RDS + S3 |
| Document storage | S3 | Private bucket |
| Sessions / metadata | DynamoDB | PAY_PER_REQUEST |
| Cache | TTLCache (in-process) | NOT Redis |

### Frontend
| Component | Choice |
|-----------|--------|
| Framework | React 18 + Vite |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | Zustand |
| API client | TanStack Query |
| Streaming | SSE (EventSource) |
| Package manager | pnpm |

### AWS Infrastructure
| Service | Purpose |
|---------|---------|
| ECS Fargate | API container (0.25 vCPU / 0.5 GB) |
| ECR | Container registry |
| RDS PostgreSQL 16 | All 5 knowledge stores |
| S3 (documents) | Raw uploads |
| S3 (frontend) | React build |
| S3 (wiki) | Markdown backups |
| CloudFront | Frontend CDN |
| ALB | Load balancer |
| SQS + DLQ | Ingestion queue |
| DynamoDB | Sessions + query logs |
| Cognito | Auth |
| Secrets Manager | API keys + DB creds |
| CloudWatch | Logs + metrics |
| X-Ray | Tracing |

### DevOps
| Component | Choice |
|-----------|--------|
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Containers | Docker |
| Python linting | Ruff |
| Type checking | mypy |
| Testing | pytest + httpx |
| TS linting | ESLint |

---

## AWS Configuration

```
Region:              us-east-1
Resource prefix:     context-engine-*
Account ID:          256716302630
Terraform state:     s3://context-engine-tf-state-256716302630
TF lock table:       context-engine-tf-lock
Admin CLI profile:   context-engine-admin
CI/CD CLI profile:   context-engine
```

### Resource Naming Convention
```
context-engine-{environment}-{resource-type}
```

---

## Project Structure

```
context-engine/
├── CLAUDE.md
├── Makefile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/
│   └── app/
│       ├── main.py
│       ├── api/
│       │   ├── query.py
│       │   ├── ingest.py
│       │   ├── documents.py
│       │   ├── analytics.py
│       │   └── auth.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── auth.py
│       │   └── pipeline.py        ← 8-layer orchestrator
│       ├── retrievers/
│       │   ├── vector.py
│       │   ├── bm25.py
│       │   ├── sql.py
│       │   ├── graph.py           ← NEW
│       │   ├── wiki.py            ← NEW
│       │   ├── merger.py
│       │   └── reranker.py
│       ├── router/
│       │   └── classifier.py      ← 6 routes
│       ├── ingestion/
│       │   ├── base.py
│       │   ├── pdf.py
│       │   ├── web.py
│       │   ├── db.py
│       │   ├── api_ingester.py    ← NEW
│       │   ├── spreadsheet.py     ← NEW
│       │   ├── chunker.py
│       │   ├── embedder.py
│       │   ├── entity_extractor.py ← NEW
│       │   └── wiki_builder.py    ← NEW
│       ├── verification/          ← NEW module
│       │   ├── grounding.py
│       │   ├── conflicts.py
│       │   └── confidence.py
│       ├── memory/                ← NEW module
│       │   └── updater.py
│       ├── llm/
│       │   ├── client.py
│       │   └── prompts.py
│       ├── models/
│       │   ├── db.py
│       │   └── schemas.py
│       └── utils/
│           ├── cache.py
│           └── logging.py
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── stores/
│       └── types/
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   ├── modules/
│   │   ├── vpc/
│   │   ├── ecs/
│   │   ├── rds/
│   │   ├── s3/
│   │   ├── cloudfront/
│   │   ├── cognito/
│   │   └── cloudwatch/
│   └── envs/
│       ├── staging/
│       └── prod/
├── docs/
│   ├── PROGRESS.md
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
└── .github/
    └── workflows/
        ├── ci.yml
        └── deploy.yml
```

---

## Cost Constraints

**Hard budget: $50/month**

| State | Cost |
|-------|------|
| Idle | ~$2–5/month |
| Active demo day | ~$7–10/day |
| 5 demo days/month | ~$35–45/month |
| AWS credits | $48.81 remaining (expires Nov 2026) |

```bash
make demo-on    # Start ECS + RDS (~4 min)
make demo-off   # Stop ECS + RDS
make status     # Check state
```

---

## Key Database Schema

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Vector index
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON chunks USING gin(to_tsvector('english', content));

-- Graph store (NEW)
CREATE TABLE entity_relations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_a VARCHAR(255) NOT NULL,
  relation_type VARCHAR(100) NOT NULL,
  entity_b VARCHAR(255) NOT NULL,
  source_chunk_id UUID REFERENCES chunks(id),
  confidence FLOAT DEFAULT 1.0,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ON entity_relations (entity_a);
CREATE INDEX ON entity_relations (entity_b);

-- Wiki store (NEW)
CREATE TABLE wiki_pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(255) UNIQUE NOT NULL,
  content TEXT NOT NULL,
  tags TEXT[] DEFAULT '{}',
  source_ids UUID[] DEFAULT '{}',
  wikilinks TEXT[] DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## Query Classifier Output (6 routes)
```json
{
  "route": "wiki|semantic|bm25|sql|graph|hybrid",
  "confidence": 0.0,
  "reasoning": "brief explanation",
  "entities": ["extracted", "entities"]
}
```

## SSE Event Format
```
event: route
data: {"decision": "hybrid", "confidence": 0.92, "retrievers": ["wiki", "vector"]}

event: token
data: {"text": "token"}

event: verification
data: {"grounded": true, "conflicts": [], "confidence": 0.89}

event: sources
data: [{"title": "...", "score": 0.94, "type": "wiki|vector|graph|sql"}]

event: done
data: {"tokens_used": 312, "cost_usd": 0.0031}
```

## SQL Injection Guard
- SELECT only — block DROP, DELETE, INSERT, UPDATE, TRUNCATE, ALTER, CREATE
- Max 50 rows · 5 second timeout

---

## Demo Script (interviews)

1. Open `https://<cloudfront-url>/demo`
2. Show 4 pre-loaded sources (PDF, URL, DB table, spreadsheet)
3. Wiki query → Wiki route badge (fastest)
4. Semantic query → Vector route badge
5. Exact keyword → BM25 route badge
6. "How many records..." → SQL route badge
7. "Who works with X?" → Graph route badge
8. Ambiguous query → Hybrid route + RRF merger
9. Show verification panel — confidence + conflict detection
10. Show analytics dashboard
11. Show GitHub → CI/CD → Terraform

---

## Session End Checklist

- [ ] Code committed with descriptive message
- [ ] `docs/PROGRESS.md` updated
- [ ] Next task noted in PROGRESS.md
- [ ] No `.env` or secrets committed
- [ ] No broken tests