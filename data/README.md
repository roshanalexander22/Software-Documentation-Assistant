# Knowledge Base: Software Framework Documentation Corpus

This directory contains the curated technical documentation corpus used by the **Software Documentation Assistant RAG system**.

## Domain & Subject Focus
- **Primary Domain**: Developer Tools & Framework Engineering
- **Target Frameworks**: FastAPI (Modern v0.115 vs Legacy v0.90) and Pydantic (Modern V2.0 vs Legacy V1.10)
- **Primary Use Case**: Retrieving version-relevant API explanations, architectural patterns, migration guides, and complete executable code examples, while reliably abstaining from ungrounded or fictitious technical claims.

---

## Document Corpus Index

| Document ID | Filename | Framework | Version Tag | Category | Key API Topics Covered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DOC-FA-001` | `fastapi_lifespan_state.md` | FastAPI | `v0.115` | Lifecycle | `@asynccontextmanager`, `lifespan`, `app.state`, resource cleanup |
| `DOC-FA-002` | `fastapi_v0_90_legacy_events.md` | FastAPI | `v0.90-legacy` | Lifecycle | `@app.on_event("startup")`, `@app.on_event("shutdown")` (Deprecated) |
| `DOC-FA-003` | `fastapi_dependency_injection.md` | FastAPI | `v0.115` | Dependencies | `typing.Annotated`, `Depends()`, Type aliases, DRY parameters |
| `DOC-FA-004` | `fastapi_security_jwt.md` | FastAPI | `v0.115` | Security | `OAuth2PasswordBearer`, JWT HS256 tokens, password hashing |
| `DOC-FA-005` | `fastapi_middleware.md` | FastAPI | `v0.115` | Middleware | `CORSMiddleware`, `BaseHTTPMiddleware`, request timing headers |
| `DOC-FA-006` | `fastapi_background_tasks.md` | FastAPI | `v0.115` | Async Processing | `BackgroundTasks`, non-blocking notifications, Celery comparison |
| `DOC-FA-007` | `fastapi_streaming_websockets.md` | FastAPI | `v0.115` | Realtime & Streaming | `StreamingResponse`, SSE events, `@app.websocket`, broadcast |
| `DOC-FA-008` | `fastapi_error_handling.md` | FastAPI | `v0.115` | Error Handling | `HTTPException`, `@app.exception_handler`, validation override |
| `DOC-FA-009` | `fastapi_async_database.md` | FastAPI | `v0.115` | Database | SQLAlchemy 2.0 `create_async_engine`, `async with AsyncSession` |
| `DOC-FA-010` | `fastapi_testing_client.md` | FastAPI | `v0.115` | Testing | `TestClient`, `httpx.AsyncClient`, `ASGITransport`, overrides |
| `DOC-FA-011` | `fastapi_v0_90_legacy.md` | FastAPI | `v0.90-legacy` | Validation | Deprecated `regex` parameter in `Query` vs modern `pattern` |
| `DOC-PYD-001` | `pydantic_v2_migration.md` | Pydantic | `v2.0` | Data Modeling | `model_dump()`, `@field_validator`, `@model_validator`, `ConfigDict` |
| `DOC-PYD-002` | `pydantic_v1_legacy.md` | Pydantic | `v1.10-legacy` | Data Modeling | `model.dict()`, `@validator()`, `@root_validator()`, `class Config` |

---

## Metadata Schema
Each markdown document starts with YAML frontmatter conforming to this schema:

```yaml
---
doc_id: string         # Unique document identifier (e.g., DOC-FA-001)
title: string          # Human-readable title
version: string        # Specific release tag (e.g., v0.115, v0.90-legacy, v2.0)
framework: string      # Software framework name (FastAPI, Pydantic)
category: string       # Technical subsystem category
tags: list[string]     # Search tags and keywords
source_url: string     # Upstream official documentation reference
---
```

---

## Chunking & Preservation Strategy
1. **Header-Aware Split**: Documents are partitioned along Markdown section headers (`#`, `##`, `###`), preserving semantic cohesion.
2. **Code Block Preservation**: Fenced code blocks (` ```python ... ``` `) are strictly maintained as atomic units and are never split mid-block, preventing syntax errors in retrieved examples.
3. **Chunk Metadata Inheritance**: Each chunk inherits the parent document's `doc_id`, `version`, `framework`, `category`, and section title.
4. **Target Size**: 400–800 characters per chunk with a 100-character overlap for boundary continuity.

---

## Licensing & Attribution
- Text and code examples derived from and aligned with official FastAPI documentation (MIT License, Tiangolo) and Pydantic documentation (MIT License, Pydantic Services Inc.).
