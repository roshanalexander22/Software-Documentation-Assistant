---
doc_id: DOC-FA-001
title: FastAPI Lifespan Events and Application State Management
version: v0.115
framework: FastAPI
category: Lifecycle
tags: [lifespan, startup, shutdown, asynccontextmanager, state, modern]
source_url: https://fastapi.tiangolo.com/advanced/events/
---

# FastAPI Lifespan Events and Application State Management

In modern FastAPI (version 0.93.0 and newer, including FastAPI 0.115+), the recommended way to handle application startup and shutdown lifecycle events is by using the `lifespan` parameter with an asynchronous context manager (`@asynccontextmanager`).

This modern lifespan interface supersedes and replaces the legacy `@app.on_event("startup")` and `@app.on_event("shutdown")` event decorators, which are now deprecated.

## Why Use Lifespan Over on_event?

1. **Unified Context**: The lifespan context manager executes logic before the application starts receiving requests, pauses at `yield`, and resumes when the application shuts down. This allows using standard Python `try...finally` resource managers.
2. **State Sharing**: The lifespan function can yield a dictionary of state objects or populate `app.state`, making database pools, machine learning models, and HTTP client sessions safely accessible inside request handlers via `request.state`.
3. **Type Safety and ASGI Standard**: The lifespan protocol adheres directly to the ASGI specification (ASGI Lifespan Protocol).

## Modern Lifespan Implementation Example

Here is the production-standard pattern for initializing resources (such as database connection pools or ML models) during startup and cleanly releasing them at shutdown:

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI, Request
import httpx

# Simulated database or heavy client
class DatabaseConnection:
    async def connect(self):
        print("Connected to database.")
    async def disconnect(self):
        print("Disconnected from database.")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[dict]:
    # --- STARTUP LOGIC ---
    db = DatabaseConnection()
    await db.connect()
    http_client = httpx.AsyncClient(timeout=10.0)
    
    # Yield state accessible via request.state or lifespan context
    yield {
        "db": db,
        "http_client": http_client
    }
    
    # --- SHUTDOWN LOGIC ---
    await http_client.aclose()
    await db.disconnect()

# Initialize application with lifespan handler
app = FastAPI(
    title="Documented Service",
    version="0.115.0",
    lifespan=lifespan
)

@app.get("/items")
async def read_items(request: Request):
    # Access shared resource from request state
    client: httpx.AsyncClient = request.state.http_client
    return {"status": "healthy", "client_active": not client.is_closed}
```

## Deprecation Notice for on_event

In legacy FastAPI codebases, developers used:
```python
# DEPRECATED IN MODERN FASTAPI
@app.on_event("startup")
async def startup_event():
    ...
```
Do not use `on_event` in new applications. It does not support shared context yield, makes teardown error handling difficult, and will be removed in future ASGI/Starlette versions.
