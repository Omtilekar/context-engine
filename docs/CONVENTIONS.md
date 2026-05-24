# ContextEngine — Conventions & Code Style

> Claude: Follow these rules on every file you create or modify.

---

## AWS Naming

```
Pattern:  context-engine-{env}-{resource}
Env:      prod | staging
```

| Resource | Name |
|----------|------|
| VPC | `context-engine-prod-vpc` |
| ECS Cluster | `context-engine-prod-ecs-cluster` |
| ECS Service | `context-engine-prod-api` |
| RDS Instance | `context-engine-prod-rds` |
| S3 (documents) | `context-engine-prod-documents-<account-id>` |
| S3 (frontend) | `context-engine-prod-frontend-<account-id>` |
| S3 (tf state) | `context-engine-tf-state-<account-id>` |
| DynamoDB | `context-engine-prod-sessions` |
| SQS Queue | `context-engine-prod-ingest-queue` |
| SQS DLQ | `context-engine-prod-ingest-dlq` |
| Cognito Pool | `context-engine-prod-users` |
| CloudWatch Group | `/ecs/context-engine-prod` |
| ECR Repo | `context-engine-backend` |

---

## Python Code Style

- **Formatter:** Ruff (replaces Black + isort)
- **Line length:** 100 characters
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all public classes and functions (Google style)
- **Async:** Use `async/await` throughout — no synchronous DB calls

```python
# Good
async def get_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
) -> list[Chunk]:
    """Retrieve the top-K most similar chunks using pgvector cosine search.

    Args:
        query_embedding: The embedded query vector (1536 dimensions).
        top_k: Number of results to return.

    Returns:
        List of Chunk objects ordered by similarity descending.
    """
    ...

# Bad — no type hints, no docstring
async def get_chunks(embedding, k=5):
    ...
```

---

## Python File Structure

Every Python file should follow this order:
```python
# 1. Standard library imports
# 2. Third-party imports
# 3. Local imports (relative)
# 4. Constants
# 5. Classes / functions
```

---

## Pydantic Schemas

- All request/response models in `app/models/schemas.py`
- Use `model_config = ConfigDict(from_attributes=True)` on ORM models
- Field names: `snake_case`
- No `Optional[X]` — use `X | None` (Python 3.10+ style)

```python
# Good
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    session_id: str | None = None

# Bad
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
```

---

## SQLAlchemy Models

- All models in `app/models/db.py`
- Use `mapped_column` and `Mapped` (SQLAlchemy 2.x style)
- Table names: `snake_case` plural (e.g. `documents`, `chunks`)

```python
# Good (SQLAlchemy 2.x)
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

# Bad (SQLAlchemy 1.x style)
class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID, primary_key=True)
```

---

## TypeScript / React Style

- **Component files:** PascalCase (`ChatMessage.tsx`)
- **Hook files:** camelCase with `use` prefix (`useQueryStream.ts`)
- **Service files:** camelCase (`api.ts`, `sse.ts`)
- **Type files:** camelCase (`types.ts`)
- **No `any` types** — ever
- **No default exports** on hooks and utilities (only components)

```typescript
// Good
export interface QueryResponse {
  answer: string
  routeDecision: RouteDecision
  sources: SourceCitation[]
  tokensUsed: number
}

// Bad
export interface QueryResponse {
  answer: any
  route: any
}
```

---

## Terraform Style

- One `.tf` file per resource type within a module
- All variables must have `description` and `type`
- All outputs must have `description`
- Use `locals` for computed values — never inline expressions in resources
- Tag every resource:

```hcl
locals {
  common_tags = {
    Project     = "context-engine"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
  tags       = merge(local.common_tags, { Name = "context-engine-${var.environment}-vpc" })
}
```

---

## Git Commit Messages

Format: `{type}: {description}`

Types:
- `feat:` — new feature or file
- `fix:` — bug fix
- `infra:` — Terraform / AWS changes
- `test:` — adding or fixing tests
- `docs:` — documentation only
- `chore:` — tooling, config, dependencies

Examples:
```
feat: add pgvector cosine similarity retriever
infra: create RDS PostgreSQL instance with pgvector
fix: handle empty results from BM25 retriever
test: add unit tests for query classifier
docs: update PROGRESS.md after Phase 1 completion
chore: add ruff and mypy to pyproject.toml
```

---

## Environment Variables

Never commit real values. All secrets go in AWS Secrets Manager.
`.env.example` must be kept up to date with every new variable added.

```bash
# Naming convention: UPPER_SNAKE_CASE
OPENAI_API_KEY=
DATABASE_URL=
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
S3_DOCUMENTS_BUCKET=
SQS_INGEST_QUEUE_URL=
ENVIRONMENT=development
```

---

## Error Handling

- All API endpoints must return structured error responses
- Never expose internal error messages to the client
- Log full error with stack trace server-side

```python
# Good
@router.post("/query")
async def query(request: QueryRequest) -> StreamingResponse:
    try:
        ...
    except OpenAIError as e:
        logger.error("OpenAI API error", error=str(e), query=request.query)
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
```
