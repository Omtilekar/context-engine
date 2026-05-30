# ContextEngine — Architecture Decision Records

> These explain WHY each technology was chosen.
> Never revisit a closed decision without a very good reason.
> All decisions were made with cost ($50/month budget) and resume value in mind.

---

## ADR-001 — pgvector instead of OpenSearch or Qdrant

**Status:** Closed
**Decision:** Use pgvector extension on RDS PostgreSQL for vector search.

**Why not OpenSearch / Qdrant / Pinecone:**
- OpenSearch: ~$60/month minimum — blows the entire budget on one service
- Qdrant: separate managed service, extra cost, extra operational complexity
- Pinecone: API cost per query, vendor lock-in

**Why pgvector:**
- Runs inside RDS we already pay for — $0 extra
- HNSW index gives sub-100ms similarity search at demo scale
- Resume reads "vector search, PostgreSQL, HNSW indexing" — technically accurate and impressive
- Shows deeper understanding than just configuring a managed vector DB

---

## ADR-002 — pg_trgm instead of Elasticsearch/OpenSearch for BM25

**Status:** Closed
**Decision:** Use pg_trgm + tsvector inside PostgreSQL for BM25-style lexical search.

**Why not Elasticsearch / OpenSearch:**
- Elasticsearch: separate service, $60–100/month managed
- OpenSearch: same problem as above

**Why pg_trgm:**
- Built into PostgreSQL — $0 extra cost
- GIN index gives fast full-text search
- Handles BM25-style ranking with ts_rank
- All retrieval in one database — simpler architecture

---

## ADR-003 — entity_relations table instead of Neo4j

**Status:** Closed
**Decision:** Implement Graph RAG using a PostgreSQL table instead of a dedicated graph database.

**Why not Neo4j:**
- Neo4j managed: $65+/month — exceeds budget
- Separate service to manage, secure, connect
- Cypher query language adds complexity

**Why entity_relations table:**
- Zero extra cost — same RDS instance
- Simple (entity_a, relation_type, entity_b) schema covers 80% of graph use cases
- Indexed on both entity columns for fast traversal
- Can traverse up to 2-3 hops with recursive SQL queries
- Resume still says "Graph RAG, entity relationship traversal" — accurate

---

## ADR-004 — wiki_pages table + S3 instead of file system

**Status:** Closed
**Decision:** Store wiki pages in PostgreSQL (queryable) with S3 backup (human-readable markdown).

**Why not local filesystem:**
- ECS containers are ephemeral — filesystem resets on deploy
- Not accessible across multiple container instances

**Why not S3 only:**
- S3 is not queryable — can't search by tags, wikilinks, title
- Would need extra indexing layer

**Why wiki_pages table + S3:**
- Table is queryable by title, tags, wikilinks, source_ids
- S3 backup is human-readable markdown (can view in Obsidian — Karpathy's vision)
- Zero extra cost — same RDS + existing S3 bucket

---

## ADR-005 — FlashRank instead of Cohere Rerank

**Status:** Closed
**Decision:** Use FlashRank (local, open-source cross-encoder) for re-ranking.

**Why not Cohere Rerank v3:**
- $20/month API cost
- External dependency — latency + failure mode

**Why FlashRank:**
- Runs inside Docker container — $0 cost
- ms-marco-MiniLM-L-12-v2 cross-encoder model
- Legitimate cross-encoder re-ranking — not a fake
- Resume reads "cross-encoder re-ranking" — accurate

---

## ADR-006 — TTLCache instead of Redis/ElastiCache

**Status:** Closed
**Decision:** In-process TTLCache for query result caching.

**Why not ElastiCache / Redis:**
- $15/month minimum — unnecessary at demo scale

**Why TTLCache:**
- Zero cost
- TTL = 1 hour, max 200 entries
- Sufficient for demo traffic
- Reduces OpenAI costs during demos

---

## ADR-007 — ECS Fargate with start/stop model

**Status:** Closed
**Decision:** ECS Fargate, desired_count=0 when idle.

**Start/stop savings:**
- Always-on: ~$45/month
- 5 demo days/month: ~$8/month
- Saving: ~$37/month

---

## ADR-008 — LlamaIndex instead of LangChain

**Status:** Closed
**Decision:** LlamaIndex as the RAG framework.

**Why:** Purpose-built for RAG — document ingestion, chunking, retrieval are first-class. LangChain is broader but more verbose for this specific use case.

---

## ADR-009 — GPT-4o as primary LLM

**Status:** Closed
**Decision:** GPT-4o for answers + wiki ingest, GPT-4o-mini for classifier + SQL + verification.

**Cost split:**
- GPT-4o: quality where it matters (answers, wiki extraction)
- GPT-4o-mini: speed and cost where it doesn't (routing, SQL, claim checking)

---

## ADR-010 — Terraform instead of CDK or SAM

**Status:** Closed
**Decision:** Terraform for all IaC.

**Why:** Industry standard, cloud-agnostic, HCL is readable, mature module ecosystem, best resume signal.

---

## ADR-011 — Single ECS task (API + Celery worker combined)

**Status:** Closed
**Decision:** Run API and worker in same ECS task to halve cost.

**Cost:** ~$8/month vs ~$16/month for separate tasks.
**Trade-off:** Acceptable for demo scale. Can be split in v2.

---

## ADR-012 — GPT-4o for wiki ingest (not GPT-4o-mini)

**Status:** Closed
**Decision:** Use GPT-4o for wiki page extraction, not GPT-4o-mini.

**Why GPT-4o:**
- Wiki extraction runs once per document (not per query)
- Quality of extracted facts directly impacts all future answers
- Getting facts wrong at ingest time = wrong answers forever
- Cost: ~$0.05 per document — acceptable one-time cost

---

## ADR-013 — Verification layer using GPT-4o-mini (not GPT-4o)

**Status:** Closed
**Decision:** Use GPT-4o-mini for the verification pass.

**Why GPT-4o-mini:**
- Verification is a structured task (does claim X appear in source Y?)
- Doesn't need GPT-4o reasoning quality
- Runs on every query — cost matters here
- Cost: ~$0.001 per verification pass

---

## ADR-014 — No custom domain (for now)

**Status:** Open
**Decision:** Use CloudFront default URL. Domain deferred.

**Options when ready:**
- `contextengine.dev` (~$12/year)
- Personal subdomain (free)

---

## ADR-015 — Digest method for long source chunking

**Status:** Closed
**Decision:** Use the chunking + digest approach from the LLM Wiki project.

**Why:**
- Naive chunking only passes the first chunk to the LLM for wiki extraction
- Digest method: split → extract facts per chunk → combine digests → final integration
- Prevents the "first-chunk-only" problem discovered during Shivaji Wikipedia test
- Preserves numbered references for citation queries

**Credit:** This solution was built and tested in the LLM Wiki project before ContextEngine.