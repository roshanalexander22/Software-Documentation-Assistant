---
doc_id: DOC-FA-002
title: FastAPI v0.90 Legacy Event Handlers (Deprecated)
version: v0.90-legacy
framework: FastAPI
category: Lifecycle
tags: [legacy, startup, shutdown, on_event, deprecated]
source_url: https://fastapi.tiangolo.com/tutorial/events/
---

# FastAPI v0.90 Legacy Event Handlers (Deprecated)

In earlier versions of FastAPI (v0.90 and earlier, prior to FastAPI 0.93), lifecycle events were registered using the `@app.on_event()` decorator.

## Legacy Startup and Shutdown Syntax

In FastAPI v0.90, developers had to write two separate functions for initialization and destruction:

```python
from fastapi import FastAPI

app = FastAPI(title="Legacy FastAPI Service", version="0.90.0")

database_session = None

@app.on_event("startup")
async def startup_event():
    global database_session
    database_session = "Initialized Legacy Session"
    print("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    global database_session
    database_session = None
    print("Application shutdown complete.")

@app.get("/status")
def get_status():
    return {"session": database_session}
```

## Architectural Limitations of Legacy Events

1. **No Shared Context**: Startup and shutdown handlers are disconnected functions. There is no simple way to pass variables created in startup to shutdown without relying on module-level global variables.
2. **Exception Handling**: If an exception occurs in an `on_event("startup")` handler, graceful resource cleanup in `shutdown` cannot be guaranteed.
3. **Migration Recommendation**: Upgrade to FastAPI >=0.100.0 and replace `@app.on_event("startup")` with the `@asynccontextmanager` `lifespan` handler parameter on `FastAPI(lifespan=...)`.

