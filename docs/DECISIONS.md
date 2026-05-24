# ContextEngine — Architecture Decision Records

> These explain WHY each technology was chosen.
> Never revisit a closed decision without a very good reason.
> All decisions were made with cost ($50/month budget) and resume value in mind.

---

## ADR-001 — pgvector instead of OpenSearch

**Status:** Closed
**Decision:** Use pgvector extension on RDS PostgreSQL for both vector search and lexical (BM25-style) search.

**Why not OpenSearch:**
- Minimum cost: ~$60/month even for the smallest instance
- Requires a separate AWS service to manage
- Overkill for a showcase project with ~demo-level traffic

**Why pgvector:**
- Runs inside the RDS instance we already pay for — zero extra cost
- pgvector supports HNSW indexing (fast cosine similarity)
- pg_trgm + tsvector handles BM25-style lexical search
- Still appears on resume as "vector search, PostgreSQL" — equally impressive
- Shows deeper technical understanding than just configuring a managed service

---

## ADR-002 — FlashRank instead of Cohere Rerank

**Status:** Closed
**Decision:** Use FlashRank (local, open-source cross-encoder) for re-ranking.

**Why not Cohere Rerank v3:**
- $20/month API cost
- External API dependency (latency + failure mode)

**Why FlashRank:**
- Runs inside the Docker container — zero API cost
- Uses ms-marco-MiniLM-L-12-v2 cross-encoder model
- Legitimate cross-encoder re-ranking — not a fake
- Resume still reads "cross-encoder re-ranking" — accurate and impressive

---

## ADR-003 — In-process TTLCache instead of ElastiCache Redis

**Status:** Closed
**Decision:** Use cachetools TTLCache inside the FastAPI process for query result caching.

**Why not ElastiCache:**
- $15/month minimum for cache.t3.micro
- Adds operational complexity (VPC connectivity, security groups)
- Not needed at demo-scale traffic

**Why TTLCache:**
- Zero cost — standard Python library
- Sufficient for showcase: ~200 cached queries in memory
- TTL = 1 hour, max 200 entries
- Good enough to demonstrate caching concept in an interview

---

## ADR-004 — ECS Fargate with start/stop model

**Status:** Closed
**Decision:** Use ECS Fargate with desired_count=0 when idle, scale to 1 when demoing.

**Why not EC2:**
- Requires OS patching, SSH management, right-sizing
- Always-on cost even when idle
- Not appropriate for a solo showcase project

**Why Fargate:**
- Serverless containers — no instance management
- Pay by the second (only when running)
- Start/stop via single CLI command
- Still appears on resume as "AWS ECS Fargate" — industry-standard

**Start/stop savings:**
- Always-on: ~$45/month
- 5 demo days/month: ~$8/month
- Saving: ~$37/month

---

## ADR-005 — LlamaIndex instead of LangChain

**Status:** Closed
**Decision:** Use LlamaIndex as the RAG framework.

**Why not LangChain:**
- LangChain is a general-purpose agent framework — more verbose for RAG-specific pipelines
- More abstraction layers, harder to debug

**Why LlamaIndex:**
- Purpose-built for RAG — document ingestion, indexing, retrieval are first-class
- Cleaner abstractions for chunking, embedding, and retrieval pipelines
- Easier to customise individual components (swap retrievers, re-rankers)

---

## ADR-006 — GPT-4o as primary LLM

**Status:** Closed
**Decision:** Use GPT-4o for answer generation, GPT-4o-mini for classifier and SQL generation.

**Reasoning:**
- User preference for OpenAI over Anthropic
- GPT-4o: best quality for final answer generation
- GPT-4o-mini: cheaper ($0.15/1M tokens input) for high-frequency classifier calls
- text-embedding-3-small: best cost/quality ratio for embeddings at this scale

---

## ADR-007 — Terraform instead of CDK or SAM

**Status:** Closed
**Decision:** Use Terraform for all infrastructure as code.

**Why not CDK:**
- Requires Node.js runtime — adds toolchain complexity
- AWS-specific (less portable)

**Why not SAM:**
- Primarily for Lambda/serverless — not suited for ECS + RDS architecture

**Why Terraform:**
- Industry standard — most recognisable on a resume
- HCL is readable and explicit
- Works across cloud providers (shows transferable skill)
- Mature module ecosystem
- S3 + DynamoDB remote state is well-understood pattern

---

## ADR-008 — Single ECS task (API + worker combined)

**Status:** Closed
**Decision:** Run API server and Celery worker in the same ECS task definition for cost saving.

**Why separate in production:**
- Independent scaling of API vs workers
- Worker failures don't affect API

**Why combined for showcase:**
- Halves ECS cost (~$8/month vs ~$16/month)
- Ingestion volume is demo-level — no real scaling needed
- Can be split into separate services later (shows architectural awareness)

---

## ADR-009 — No custom domain (for now)

**Status:** Open — revisit when applying to jobs
**Decision:** Use CloudFront default URL for demo. Domain purchase deferred.

**Options when ready:**
- `contextengine.dev` (~$12/year on Route 53)
- `context-engine.io` (~$35/year)
- Any personal domain subdomain (e.g. `projects.yourdomain.com`)

**To implement:** Add `aws_route53_zone` and `aws_acm_certificate` resources to Terraform, update CloudFront distribution with custom domain alias.
