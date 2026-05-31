# ContextEngine — Progress Tracker

> **Claude: Read this file at the start of every session.**
> Update the "Completed" and "Next Task" sections before ending each session.

---

## Current Status

**Overall:** Phase 1 complete · Phase 2 in progress
**Last updated:** May 31, 2026
**Next task:** Phase 2 — Task 5: Build S3 module

---

## Phase Completion

| Phase | Status | Tasks Done | Total Tasks |
|-------|--------|------------|-------------|
| Phase 0 — Planning | COMPLETE | — | — |
| Phase 1 — AWS Account Setup | COMPLETE | 30 | 30 |
| Phase 2 — Terraform Infrastructure | IN PROGRESS | 24 | 47 |
| Phase 3 — Backend RAG Engine | NOT STARTED | 0 | 63 |
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

## Phase 2 — Terraform Infrastructure (NEXT)

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
- [ ] S3 frontend bucket (private, OAC for CloudFront)
- [ ] S3 documents bucket (private)
- [ ] S3 wiki bucket (private)
- [ ] CloudFront distribution (OAC + SPA routing)

### Supporting Services
- [ ] DynamoDB: `context-engine-prod-sessions` (PAY_PER_REQUEST)
- [ ] SQS queue: `context-engine-prod-ingest-queue`
- [ ] SQS DLQ: `context-engine-prod-ingest-dlq`
- [ ] Cognito user pool + app client
- [ ] Secrets Manager: OPENAI_API_KEY, DB_PASSWORD
- [ ] CloudWatch log group (7 day retention)

### Start/Stop Automation
- [ ] Makefile: demo-on (start ECS + RDS)
- [ ] Makefile: demo-off (stop ECS + RDS)
- [ ] Makefile: status (check running state)
- [ ] Health check poll in demo-on

---

## Phase 3 — Backend RAG Engine (NOT STARTED)

Will be detailed when Phase 2 is complete. Key additions vs original plan:
- `retrievers/graph.py` — Graph RAG via entity_relations table
- `retrievers/wiki.py` — Wiki page retrieval
- `ingestion/entity_extractor.py` — GPT-4o-mini entity extraction
- `ingestion/wiki_builder.py` — LLM Wiki page builder (Karpathy method)
- `verification/` module — grounding + conflict detection + confidence
- `memory/updater.py` — continuous learning layer

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
| Terraform command unavailable in current shell PATH | Open — needed before fmt/validate/plan |

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
