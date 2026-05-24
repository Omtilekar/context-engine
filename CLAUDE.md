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

---

## Non-Negotiable Rules

These are locked decisions. Do NOT suggest alternatives, do NOT deviate.

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

---

## Locked Tech Stack

### Backend
| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12 |
| Framework | FastAPI | latest |
| RAG Framework | LlamaIndex | latest |
| ORM | SQLAlchemy | 2.x async |
| Validation | Pydantic | v2 |
| Task Queue | Celery | latest |
| Dependency Mgmt | Poetry | latest |
| Migrations | Alembic | latest |

### AI / Models
| Component | Choice | Notes |
|-----------|--------|-------|
| LLM (answers) | GPT-4o | Primary |
| LLM (classifier) | GPT-4o-mini | Fast, cheap |
| LLM (SQL gen) | GPT-4o-mini | Text-to-SQL |
| Embeddings | text-embedding-3-small | 1536 dims |
| Re-ranker | FlashRank (local) | ms-marco-MiniLM-L-12-v2 — NOT Cohere |
| PDF parsing | pdfplumber | |
| Web scraping | Playwright | Headless |

### Database & Storage
| Component | Choice | Notes |
|-----------|--------|-------|
| Primary DB | RDS PostgreSQL 16 | db.t3.micro |
| Vector search | pgvector extension | HNSW index |
| Lexical search | pg_trgm + tsvector | BM25-style, GIN index |
| Document storage | S3 | Private bucket |
| Sessions / metadata | DynamoDB | PAY_PER_REQUEST |
| Cache | TTLCache (in-process) | NOT Redis / ElastiCache |

### Frontend
| Component | Choice |
|-----------|--------|
| Framework | React 18 |
| Language | TypeScript |
| Build tool | Vite |
| Styling | Tailwind CSS |
| State management | Zustand |
| API client | TanStack Query |
| Streaming | SSE (EventSource) |
| Package manager | pnpm |

### AWS Infrastructure
| Service | Purpose |
|---------|---------|
| ECS Fargate | API container (0.25 vCPU / 0.5 GB RAM) |
| ECR | Container image registry |
| RDS PostgreSQL | Primary database + pgvector |
| S3 (documents) | Raw uploaded files |
| S3 (frontend) | React build artifacts |
| CloudFront | CDN for frontend |
| ALB | Load balancer for ECS |
| SQS | Ingestion job queue |
| SQS DLQ | Dead-letter queue for failed jobs |
| DynamoDB | Sessions and query logs |
| Cognito | User authentication |
| Secrets Manager | API keys and DB credentials |
| CloudWatch | Logs, metrics, alarms |
| X-Ray | Distributed tracing |
| WAF | Web application firewall |

### DevOps
| Component | Choice |
|-----------|--------|
| IaC | Terraform (NOT CDK, NOT SAM, NOT CloudFormation) |
| CI/CD | GitHub Actions |
| Containers | Docker |
| Linting (Python) | Ruff |
| Type checking | mypy |
| Testing | pytest + httpx |
| Linting (TS) | ESLint |

---

## AWS Configuration

```
Region:           us-east-1
Resource prefix:  context-engine-*
Account:          (your AWS account ID)
Terraform state:  s3://context-engine-tf-state-<account-id>
TF lock table:    context-engine-tf-lock
```

### Resource Naming Convention
All AWS resources MUST follow this pattern:
```
context-engine-{environment}-{resource-type}
```
Examples:
- `context-engine-prod-vpc`
- `context-engine-prod-rds`
- `context-engine-prod-ecs-cluster`
- `context-engine-staging-s3-documents`

---

## Project Structure

```
context-engine/
├── CLAUDE.md                    ← You are here
├── Makefile                     ← demo-on / demo-off / status commands
├── docker-compose.yml           ← Local dev environment
├── .env.example                 ← All required env vars (no real values)
├── .gitignore
├── README.md
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/
│   ├── app/
│   │   ├── main.py              ← FastAPI entry point
│   │   ├── api/                 ← Route handlers
│   │   │   ├── query.py         ← POST /api/v1/query (SSE streaming)
│   │   │   ├── ingest.py        ← POST /api/v1/ingest/*
│   │   │   ├── documents.py     ← GET/DELETE /api/v1/documents
│   │   │   ├── analytics.py     ← GET /api/v1/analytics/*
│   │   │   └── auth.py          ← POST /auth/token
│   │   ├── core/
│   │   │   ├── config.py        ← Pydantic BaseSettings
│   │   │   ├── database.py      ← SQLAlchemy async engine
│   │   │   ├── auth.py          ← Cognito JWT verification
│   │   │   └── pipeline.py      ← Main RAG orchestrator
│   │   ├── retrievers/
│   │   │   ├── vector.py        ← pgvector cosine search
│   │   │   ├── bm25.py          ← PostgreSQL FTS
│   │   │   ├── sql.py           ← Text-to-SQL retriever
│   │   │   ├── merger.py        ← RRF hybrid fusion
│   │   │   └── reranker.py      ← FlashRank re-ranker
│   │   ├── router/
│   │   │   └── classifier.py    ← GPT-4o-mini query classifier
│   │   ├── ingestion/
│   │   │   ├── base.py          ← Abstract BaseIngester
│   │   │   ├── pdf.py           ← pdfplumber ingester
│   │   │   ├── web.py           ← Playwright ingester
│   │   │   ├── db.py            ← SQL table ingester
│   │   │   ├── chunker.py       ← 512 token / 64 overlap
│   │   │   └── embedder.py      ← OpenAI batch embedder
│   │   ├── llm/
│   │   │   ├── client.py        ← Async OpenAI wrapper
│   │   │   └── prompts.py       ← Prompt templates
│   │   ├── models/
│   │   │   ├── db.py            ← SQLAlchemy models
│   │   │   └── schemas.py       ← Pydantic request/response
│   │   └── utils/
│   │       ├── cache.py         ← TTLCache wrapper
│   │       └── logging.py       ← Structured JSON logger
│   └── workers/
│       └── ingest_worker.py     ← Celery task definitions
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       │   ├── api.ts           ← Typed fetch wrapper
│       │   └── sse.ts           ← SSE client
│       ├── stores/              ← Zustand stores
│       └── types/               ← TypeScript interfaces
│
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf              ← Provider pins + S3 backend config
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
│
├── docs/
│   ├── PROGRESS.md              ← Current status — read every session
│   ├── ARCHITECTURE.md          ← System design decisions
│   ├── DECISIONS.md             ← Why we chose each technology
│   └── CONVENTIONS.md           ← Naming rules and code style
│
└── .github/
    └── workflows/
        ├── ci.yml               ← Runs on PR to main
        └── deploy.yml           ← Runs on push to main
```

---

## Cost Constraints

**Hard budget: $50/month maximum**

| State | Cost |
|-------|------|
| Idle (stopped) | ~$2–5/month |
| Active (demo day) | ~$7–10/day |
| Target: 5 demo days/month | ~$35–45/month |

### Start/Stop Model
- ECS service: stop when not demoing (`desired_count = 0`)
- RDS instance: stop via console or CLI when not demoing
- Frontend (S3 + CloudFront): always live, ~$0 cost
- `make demo-on` → spins up ECS + RDS (~4 min)
- `make demo-off` → stops ECS + RDS

### Cost Alerts
- CloudWatch billing alarm at $30 (warning)
- CloudWatch billing alarm at $45 (critical)

---

## RAG Pipeline Summary

```
User query
    │
    ▼
Query Classifier (GPT-4o-mini)
    │
    ├── semantic ──► Vector Retriever (pgvector cosine)
    ├── structured ► BM25 Retriever (pg_trgm FTS) + SQL Retriever (text-to-SQL)
    └── hybrid ────► Both pipelines (asyncio.gather) → RRF Merger
                                                              │
                                                              ▼
                                                    FlashRank Re-ranker
                                                    (top-10 → top-3)
                                                              │
                                                              ▼
                                                    Prompt Builder
                                                    (system + context + query)
                                                              │
                                                              ▼
                                                    GPT-4o (streaming SSE)
                                                              │
                                                              ▼
                                                    Answer + citations
```

---

## Key Implementation Details

### pgvector Setup
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- HNSW index (faster than ivfflat for this scale)
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
-- GIN index for FTS
CREATE INDEX ON chunks USING gin(to_tsvector('english', content));
```

### Query Classifier Output Format
```json
{
  "route": "semantic" | "structured" | "hybrid",
  "confidence": 0.0–1.0,
  "reasoning": "brief explanation"
}
```

### SSE Event Format
```
event: route
data: {"decision": "hybrid", "confidence": 0.92}

event: token
data: {"text": "Based on"}

event: sources
data: [{"title": "...", "page": 3, "score": 0.94}]

event: done
data: {"tokens_used": 312, "cost_usd": 0.0031}
```

### SQL Injection Guard
- Only SELECT statements allowed
- Block: DROP, DELETE, INSERT, UPDATE, TRUNCATE, ALTER, CREATE
- Max rows returned: 50
- Timeout: 5 seconds

---

## Demo Script (for interviews)

1. Open `https://<cloudfront-url>/demo`
2. Show pre-loaded documents (1 PDF, 1 URL, 1 DB table)
3. Run a **semantic query** → show Vector route badge
4. Run a **structured query** (exact keyword) → show BM25 route badge
5. Run a **SQL query** (e.g. "how many records...") → show SQL route badge
6. Run an **ambiguous query** → show Hybrid route badge + RRF merger
7. Point to source citations panel
8. Show analytics dashboard (route distribution chart)
9. Show GitHub → CI/CD pipeline → Terraform code

---

## Session End Checklist

Before ending any Claude Code session:
- [ ] All written code is committed with descriptive message
- [ ] `docs/PROGRESS.md` updated with what was completed
- [ ] Next task clearly noted in PROGRESS.md
- [ ] No `.env` files or secrets committed
- [ ] No broken tests left behind
