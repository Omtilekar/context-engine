# ContextEngine — Progress Tracker

> **Claude: Read this file at the start of every session.**
> Update the "Completed" and "Next Task" sections before ending each session.

---

## Current Status

**Overall:** Phase 2 infrastructure code complete · Phase 3 backend foundation in progress
**Last updated:** May 31, 2026
**Next task:** Phase 3 — Task 13: Complete ingestion pipeline

---

## Phase Completion

| Phase | Status | Tasks Done | Total Tasks |
|-------|--------|------------|-------------|
| Phase 0 — Planning | COMPLETE | — | — |
| Phase 1 — AWS Account Setup | COMPLETE | 30 | 30 |
| Phase 2 — Terraform Infrastructure | APPLY DEFERRED | 41 | 47 |
| Phase 3 — Backend RAG Engine | IN PROGRESS | 26 | 63 |
| Phase 4 — API Layer | NOT STARTED | 0 | 34 |
| Phase 5 — Frontend | NOT STARTED | 0 | 38 |
| Phase 6 — Testing & Quality | NOT STARTED | 0 | 22 |
| Phase 7 — CI/CD & Deployment | NOT STARTED | 0 | 23 |
| Phase 8 — Observability & Polish | NOT STARTED | 0 | 24 |

---

## Architecture Version

**Current:** v2 — 8-layer merged architecture
- Layer 1: Data ingestion (PDF, DOCX, Web, DB, API, Spreadsheet)
- Layer 2: Preprocessing (clean → chunk+digest → entity extract → fan-out to 5 stores)
- Layer 3: Query understanding + routing (6 routes)
- Layer 4: Hybrid retrieval (wiki + vector + BM25 + graph + SQL in parallel)
- Layer 5: Merge + rerank + compress (RRF → FlashRank → context compression)
- Layer 6: Verification + citation (source grounding + conflict detection + confidence)
- Layer 7: GPT-4o answer generation (SSE streaming + structured output + explainability)
- Layer 8: Memory update (continuous learning → wiki + graph update)

**Five knowledge stores — all in one RDS PostgreSQL instance:**
- pgvector (vector search)
- pg_trgm + tsvector (BM25)
- entity_relations table (Graph RAG)
- wiki_pages table (LLM Wiki / Memory)
- raw SQL tables (structured data)

---

## Completed Tasks

### Phase 0 — Planning (complete)
- [x] Project named: ContextEngine
- [x] Tagline decided
- [x] GitHub repo: github.com/Omtilekar/context-engine (public)
- [x] AWS resource prefix: `context-engine-*`
- [x] Full tech stack locked
- [x] Cost strategy locked ($50/month, start/stop model)
- [x] 272-task checklist created
- [x] CLAUDE.md, PROGRESS.md, ARCHITECTURE.md, DECISIONS.md, CONVENTIONS.md created
- [x] Architecture upgraded to v2 — 8-layer merged system

### Phase 1 — AWS Account Setup (complete)

#### IAM & Security
- [x] IAM admin user: `context-engine-admin`
- [x] MFA on root account
- [x] MFA on `context-engine-admin`
- [x] IAM policy for GitHub Actions: `context-engine-github-actions-policy`
- [x] IAM user for GitHub Actions: `context-engine-github-actions`
- [x] ECS execution role: `context-engine-ecs-execution-role`
- [x] ECS task role: `context-engine-ecs-task-role`

#### Billing & Alerts
- [x] IAM billing access enabled
- [x] Billing alarm at $30: `context-engine-billing-warning-30`
- [x] Cost Explorer enabled
- [x] Free Tier alerts enabled
- [x] Tagging strategy: Project=context-engine

#### Local Tooling (Windows 11)
- [x] AWS CLI v2
- [x] AWS CLI profiles: `context-engine-admin` + `context-engine`
- [x] Terraform 1.15.5
- [x] Docker 28.5.1
- [x] Python 3.14.3
- [x] Poetry 2.4.1
- [x] Node v24 + pnpm
- [x] Make 4.4.1

#### Terraform State Bootstrap
- [x] S3 bucket: `context-engine-tf-state-256716302630` (versioned + encrypted + private)
- [x] DynamoDB lock table: `context-engine-tf-lock`

#### GitHub Repo Setup
- [x] Repository created: github.com/Omtilekar/context-engine (public)
- [x] GitHub Actions secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, OPENAI_API_KEY
- [x] .gitignore created
- [x] CLAUDE.md + docs/ committed and pushed

---

## Phase 2 — Terraform Infrastructure (APPLY DEFERRED)

### Project Structure
- [x] Create infra/ root module (main.tf, variables.tf, outputs.tf, versions.tf)
- [x] Create infra/modules/ subfolders (vpc, ecs, rds, s3, cloudfront, cognito, cloudwatch)
- [x] Create infra/envs/prod/
- [x] Configure Terraform backend (S3 + DynamoDB state)
- [x] Pin provider versions (aws ~> 5.0)

### VPC Module
- [x] VPC (CIDR 10.0.0.0/16)
- [x] 2 public subnets (ALB + NAT)
- [x] 2 private subnets (ECS + RDS)
- [x] Internet Gateway
- [x] NAT Gateway (1x — single AZ saves cost)
- [x] Public + private route tables
- [x] Security group: ALB (80/443 inbound)
- [x] Security group: ECS (8000 from ALB only)
- [x] Security group: RDS (5432 from ECS only)

### RDS Module
- [x] RDS subnet group (both private subnets)
- [x] RDS PostgreSQL 16 (db.t3.micro, 20GB gp3)
- [x] DB password in Secrets Manager
- [x] Automated backups (1 day retention)
- [x] Enable pgvector + pg_trgm via Alembic migration (not Terraform)

### ECS Module
- [x] ECS cluster: `context-engine-prod-ecs-cluster`
- [x] ECS task definition (0.25 vCPU, 0.5 GB)
- [x] ECS service (desired count 0 idle, demo-on to 1, in private subnets)
- [x] ALB + target group + listener
- [x] ECR repository: `context-engine-backend`

### S3 & CloudFront
- [x] S3 frontend bucket (private, OAC for CloudFront)
- [x] S3 documents bucket (private)
- [x] S3 wiki bucket (private)
- [x] CloudFront distribution (OAC + SPA routing)

### Supporting Services
- [x] DynamoDB: `context-engine-prod-sessions` (PAY_PER_REQUEST)
- [x] SQS queue: `context-engine-prod-ingest-queue`
- [x] SQS DLQ: `context-engine-prod-ingest-dlq`
- [x] Cognito user pool + app client
- [x] Secrets Manager: OPENAI_API_KEY, DB_PASSWORD (RDS-managed)
- [x] CloudWatch log group (7 day retention)

### Start/Stop Automation
- [x] Makefile: demo-on (start ECS + RDS)
- [x] Makefile: demo-off (stop ECS + RDS)
- [x] Makefile: status (check running state)
- [x] Health check poll in demo-on

### Terraform Review
- [x] terraform fmt
- [x] terraform validate
- [x] terraform plan (60 to add, 0 to change, 0 to destroy)
- [ ] terraform apply (requires explicit approval)

---

## Phase 3 — Backend RAG Engine (IN PROGRESS)

### Backend Foundation
- [x] Create backend app structure
- [x] Add FastAPI app
- [x] Add `/health`, `/query`, `/ingest`, and `/status` endpoints
- [x] Add Pydantic settings/config module
- [x] Add async PostgreSQL connection module
- [x] Add SQLAlchemy models with pgvector placeholder support
- [x] Add retrieval router skeleton for wiki, semantic, BM25, SQL, graph, hybrid
- [x] Add ingestion pipeline and chunking skeleton
- [x] Add verification and confidence skeleton
- [x] Add backend Dockerfile and local run instructions
- [x] Add minimal tests for health and query placeholders

### Alembic + Database Schema
- [x] Alembic async PostgreSQL setup
- [x] Initial migration for vector/pg_trgm extensions, documents, chunks, graph, wiki, retrieval runs, query logs
- [x] Migration tests that do not require live RDS

### Next Backend Tasks
- [x] Docker Compose local dev setup with pgvector PostgreSQL
- [x] Backend `.env.example` for Docker Compose local development
- [x] Makefile local commands for up/down/logs/migrate/test
- [x] Expand unit tests for route heuristics and chunking
- [x] Implement BM25 keyword retriever against PostgreSQL
- [x] Implement semantic pgvector retriever
- [x] Implement structured SQL retriever with injection guard
- [x] Harden SQL retriever guard with comments, semicolon, and table allowlist checks
- [x] Hybrid retrieval merger and optional FlashRank reranking layer
- [x] Deterministic verification and confidence layer
- [x] GPT-4o answer generation with citations and disabled local fallback
- [x] Graph retriever using PostgreSQL entity_relations
- [x] Wiki retriever using PostgreSQL wiki_pages
- [ ] Complete ingestion pipeline

---

## AWS Resources Created

| Resource | Name | Type | Status |
|----------|------|------|--------|
| IAM User | context-engine-admin | Admin | Active |
| IAM User | context-engine-github-actions | CI/CD | Active |
| IAM Policy | context-engine-github-actions-policy | Permissions | Active |
| IAM Policy | context-engine-ecs-task-policy | Permissions | Active |
| IAM Role | context-engine-ecs-execution-role | ECS | Active |
| IAM Role | context-engine-ecs-task-role | ECS | Active |
| S3 Bucket | context-engine-tf-state-256716302630 | TF State | Active |
| DynamoDB | context-engine-tf-lock | TF Lock | Active |
| CloudWatch Alarm | context-engine-billing-warning-30 | Billing | Active |
| SNS Topic | context-engine-billing-warning | Notifications | Active |

---

## Key Credentials & IDs

```
AWS Account ID:      256716302630
AWS Region:          us-east-1
TF State Bucket:     context-engine-tf-state-256716302630
TF Lock Table:       context-engine-tf-lock
Admin CLI Profile:   context-engine-admin
CI/CD CLI Profile:   context-engine
GitHub Repo:         https://github.com/Omtilekar/context-engine
AWS Credits:         $48.81 remaining (expires Nov 29, 2026)
OS:                  Windows 11
Project path:        C:\Om\Codes\context_engine
```

---

## Known Issues / Resolved

| Issue | Status |
|-------|--------|
| AWS account suspended (free plan ended) | Resolved — upgraded, $48.81 credits active |
| InvalidClientTokenId on CLI | Resolved — created context-engine-admin access keys |
| Terraform command unavailable in current shell PATH | Resolved — use `C:\tools\terraform\terraform.exe` |
| Terraform remote init/plan blocked by `context-engine-admin` InvalidClientTokenId | Resolved — added backend profile and confirmed STS identity |
| Terraform S3 backend `dynamodb_table` deprecation warning | Open — kept DynamoDB lock table because project state locking is already bootstrapped |
| Poetry command unavailable in current shell PATH | Open — used local `.venv` for Phase 3 checks; install/repair Poetry before lockfile workflow |

---

## Session Log

| Date | What was done |
|------|---------------|
| May 29, 2026 | Full planning, stack decisions, 8-layer architecture design |
| May 29, 2026 | Phase 1 complete — IAM, billing, tooling, TF state, GitHub |
| May 30, 2026 | Updated all docs to v2 architecture (Graph RAG + Wiki + Verification + Memory) |
| May 31, 2026 | Phase 2 Task 1 complete — Terraform root structure, backend config, provider pinning |
| May 31, 2026 | Phase 2 Task 2 complete — VPC module with public/private subnets, single NAT, security groups |
| May 31, 2026 | Phase 2 Task 3 complete — RDS module with PostgreSQL 16, gp3, backups, managed secret |
| May 31, 2026 | Phase 2 Task 4 complete — ECS, ECR, ALB, target group, listener, idle service wiring |
| May 31, 2026 | Phase 2 Task 5 complete — private encrypted S3 buckets for documents, frontend, and wiki |
| May 31, 2026 | Phase 2 Task 6 complete — CloudFront OAC distribution with SPA routing |
| May 31, 2026 | Phase 2 Task 7 complete — DynamoDB, SQS, Cognito, Secrets Manager, CloudWatch log group |
| May 31, 2026 | Phase 2 Task 8 complete — Makefile demo-on, demo-off, status, and health polling |
| May 31, 2026 | Terraform fmt and offline validate passed; remote init/plan blocked by invalid AWS profile token |
| May 31, 2026 | Terraform remote init, validate, and plan passed — 60 to add, 0 to change, 0 to destroy |
| May 31, 2026 | Phase 3 backend foundation complete — FastAPI app, config, DB, retrieval, ingestion, verification skeletons |
| May 31, 2026 | Phase 3 Alembic setup complete — async migration env, initial schema migration, offline migration tests |
| May 31, 2026 | Phase 3 Docker Compose local dev complete — pgvector PostgreSQL, backend service, local Make targets |
| May 31, 2026 | Phase 3 route/chunking/schema unit tests expanded — 36 backend tests passing |
| May 31, 2026 | Phase 3 BM25 keyword retriever complete — PostgreSQL full-text search, seed script, 42 backend tests passing |
| May 31, 2026 | Phase 3 semantic pgvector retriever complete — deterministic local embeddings, pgvector search, 56 backend tests passing |
| May 31, 2026 | Phase 3 SQL retriever complete — text-to-SQL via GPT-4o-mini, injection guard (12 blocked keywords), schema introspection, 5s timeout, product_catalog seed table |
| May 31, 2026 | Phase 3 SQL retriever hardening complete — comment blocking, semicolon chaining rejection, table allowlist, OpenAI-off guard, 119 backend tests passing |
| May 31, 2026 | Phase 3 hybrid merge/rerank complete — source dedupe, score fusion, provenance, disabled-by-default FlashRank, 132 backend tests passing |
| May 31, 2026 | Phase 3 verification/confidence complete — deterministic grounding, diversity, duplicate, conflict, and confidence checks, 142 backend tests passing |
| May 31, 2026 | Phase 3 answer generation complete — GPT-4o provider path, disabled local fallback, grounded prompts, citations, 149 backend tests passing |
| May 31, 2026 | Phase 3 graph retriever complete — PostgreSQL entity_relations 1-hop/2-hop traversal, local graph seed, 158 backend tests passing |
| May 31, 2026 | Phase 3 wiki retriever complete — PostgreSQL wiki_pages title/content search, local wiki seed, 168 backend tests passing, 1 optional integration test skipped |

---

## Resume Talking Points (check off as built)

- [ ] Designed 8-layer hybrid context engine merging Vector RAG, Vectorless RAG, Graph RAG, and LLM Wiki Memory
- [ ] Built 6-route query classifier (wiki, semantic, BM25, SQL, graph, hybrid) using GPT-4o-mini
- [ ] Implemented 5 knowledge stores in single PostgreSQL instance (pgvector, pg_trgm, entity_relations, wiki_pages, SQL)
- [ ] Built Karpathy-inspired LLM Wiki layer with chunking digest method for knowledge accumulation
- [ ] Implemented Graph RAG via entity relationship traversal (no Neo4j — pure PostgreSQL)
- [ ] Added verification layer with source grounding, conflict detection, and confidence scoring
- [ ] Built continuous memory update layer — system learns from every conversation
- [ ] Deployed on AWS ECS Fargate via Terraform IaC with GitHub Actions CI/CD
- [ ] Achieved <$50/month AWS cost via start/stop architecture (idle: ~$3/month)
- [ ] Implemented streaming SSE responses with real-time token delivery
- [ ] Documented RAGAS evaluation scores (faithfulness + answer relevance)
