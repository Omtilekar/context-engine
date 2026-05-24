# ContextEngine — Progress Tracker

> **Claude: Read this file at the start of every session.**
> Update the "Completed" and "Next Task" sections before ending each session.

---

## Current Status

**Overall:** Phase 0 — Pre-build planning complete, nothing built yet
**Last updated:** Project kickoff
**Next task:** Decide AWS region → then begin Phase 1 (AWS account setup)

---

## Blocking Decision

> **AWS region not yet chosen.**
> Ask the user which region before starting Phase 1.
> Default recommendation: `us-east-1` (cheapest, most services)
> Options: `us-east-1` / `us-west-2` / `eu-west-1` / `ap-south-1`
> Once decided, update `CLAUDE.md` under "AWS Configuration" and remove this block.

---

## Phase Completion

| Phase | Status | Tasks Done | Total Tasks |
|-------|--------|------------|-------------|
| Phase 0 — Planning | COMPLETE | — | — |
| Phase 1 — AWS Account Setup | NOT STARTED | 0 | 30 |
| Phase 2 — Terraform Infrastructure | NOT STARTED | 0 | 47 |
| Phase 3 — Backend RAG Engine | NOT STARTED | 0 | 63 |
| Phase 4 — API Layer | NOT STARTED | 0 | 34 |
| Phase 5 — Frontend | NOT STARTED | 0 | 38 |
| Phase 6 — Testing & Quality | NOT STARTED | 0 | 22 |
| Phase 7 — CI/CD & Deployment | NOT STARTED | 0 | 23 |
| Phase 8 — Observability & Polish | NOT STARTED | 0 | 24 |

---

## Completed Tasks

### Phase 0 — Planning (complete)
- [x] Project named: ContextEngine
- [x] Tagline decided
- [x] GitHub repo name: `context-engine`
- [x] AWS resource prefix: `context-engine-*`
- [x] Full tech stack locked (see CLAUDE.md)
- [x] Cost strategy locked ($50/month, start/stop model)
- [x] 272-task checklist created (Hybrid_RAG_Project_Checklist.xlsx)
- [x] CLAUDE.md created
- [x] PROGRESS.md created

---

## In Progress

_Nothing in progress yet._

---

## Phase 1 — AWS Account Setup (NOT STARTED)

Work through these in order. Check off as completed.

### IAM & Security
- [ ] Create IAM admin user (do NOT use root)
- [ ] Enable MFA on root account
- [ ] Enable MFA on IAM admin user
- [ ] Create IAM policy for GitHub Actions (least-privilege)
- [ ] Create IAM role for ECS task execution
- [ ] Create IAM role for ECS task (app role)

### Billing & Alerts
- [ ] Set billing alarm at $30 (warning)
- [ ] Set billing alarm at $45 (critical)
- [ ] Enable Cost Explorer
- [ ] Enable AWS Free Tier usage alerts
- [ ] Tag strategy: Project=context-engine on all resources

### Local Tooling
- [ ] AWS CLI v2 installed and configured (`--profile context-engine`)
- [ ] Terraform >= 1.7 installed
- [ ] Docker Desktop installed
- [ ] Python 3.12 installed (via pyenv)
- [ ] Poetry installed
- [ ] Node 20 + pnpm installed

### Terraform State Bootstrap
- [ ] S3 bucket created: `context-engine-tf-state-<account-id>`
- [ ] Versioning enabled on state bucket
- [ ] Encryption enabled on state bucket
- [ ] Public access blocked on state bucket
- [ ] DynamoDB table created: `context-engine-tf-lock` (PK: LockID)

### GitHub Repo Setup
- [ ] Repository created: `context-engine`
- [ ] Branch protection on main
- [ ] GitHub Actions secrets added (AWS keys, OPENAI_API_KEY)
- [ ] .gitignore created
- [ ] Root README.md created
- [ ] Monorepo folder structure created

---

## Phase 2 — Terraform Infrastructure (NOT STARTED)

_Will be populated when Phase 1 is complete._

---

## Phase 3 — Backend RAG Engine (NOT STARTED)

_Will be populated when Phase 2 is complete._

---

## Phase 4 — API Layer (NOT STARTED)

_Will be populated when Phase 3 is complete._

---

## Phase 5 — Frontend (NOT STARTED)

_Will be populated when Phase 4 is complete._

---

## Phase 6 — Testing & Quality (NOT STARTED)

_Will be populated when Phase 5 is complete._

---

## Phase 7 — CI/CD & Deployment (NOT STARTED)

_Will be populated when Phase 6 is complete._

---

## Phase 8 — Observability & Polish (NOT STARTED)

_Will be populated when Phase 7 is complete._

---

## Known Issues / Blockers

| Issue | Severity | Notes |
|-------|----------|-------|
| AWS region not decided | Blocker | Needed before any Terraform work |

---

## Decisions Made This Project

All major decisions are documented in `docs/DECISIONS.md`.
Summary of key ones:

| Decision | Choice | Reason |
|----------|--------|--------|
| Vector store | pgvector on RDS | Saves $60/mo vs OpenSearch |
| Re-ranker | FlashRank (local) | Saves $20/mo vs Cohere |
| Cache | In-process TTLCache | Saves $15/mo vs ElastiCache |
| Compute | ECS Fargate (start/stop) | Saves ~$37/mo vs always-on |
| LLM | GPT-4o | User preference |
| Embeddings | text-embedding-3-small | Cost-efficient, 1536 dims |
| IaC | Terraform | Industry standard, resume value |
| Frontend hosting | S3 + CloudFront | Near-zero cost |

---

## Session Log

| Date | What was done | Completed by |
|------|---------------|--------------|
| Kickoff | Full planning, stack decisions, checklist, CLAUDE.md | Chat session |

---

## Resume Talking Points (update as built)

_Add bullet points here as features get built — ready to paste into resume_

- [ ] Designed and built hybrid RAG pipeline with intelligent query routing (semantic / BM25 / SQL / hybrid)
- [ ] Deployed containerised FastAPI backend to AWS ECS Fargate via Terraform IaC
- [ ] Implemented pgvector HNSW index for sub-100ms vector similarity search
- [ ] Built text-to-SQL retriever with injection guard for structured data queries
- [ ] Achieved <$50/month AWS cost via start/stop architecture (idle: ~$3/month)
- [ ] Implemented streaming SSE responses with real-time token delivery
- [ ] Set up GitHub Actions CI/CD pipeline with automated ECS blue/green deployment
- [ ] Documented RAGAS evaluation scores (faithfulness and answer relevance)
