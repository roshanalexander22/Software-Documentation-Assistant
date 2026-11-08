---
doc_id: DOC-FA-005
title: Middleware Architecture and Custom BaseHTTPMiddleware in FastAPI
version: v0.115
framework: FastAPI
category: Middleware
tags: [middleware, cors, logging, timing, starlette, basehttpmiddleware]
source_url: https://fastapi.tiangolo.com/tutorial/middleware/
---

# Middleware Architecture and Custom BaseHTTPMiddleware in FastAPI

Middleware in FastAPI wraps every request before it is processed by path operations and intercepts every response before it is transmitted back to the client.

## Core Middleware Use Cases

1. **Cross-Origin Resource Sharing (CORS)**: Allowing web frontend applications hosted on separate origins to communicate with the API.
2. **Execution Timing & Metrics**: Measuring request latency and adding custom response headers (e.g., `X-Process-Time`).
3. **Correlation ID & Tracing**: Injecting a unique trace identifier into each request context for distributed logging.

## Adding CORS Middleware

FastAPI includes `CORSMiddleware` directly from Starlette:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CORS Configured App", version="0.115.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.domain.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Creating Custom Async Middleware with BaseHTTPMiddleware

To create custom middleware that modifies headers or logs request metrics:

```python
import time
import uuid
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Custom Middleware App", version="0.115.0")

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Before request processing
        start_time = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Pass request down the ASGI chain
        response = await call_next(request)
        
        # 2. After response generation
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.6f}"
        response.headers["X-Request-ID"] = request_id
        
        return response

app.add_middleware(ObservabilityMiddleware)

@app.get("/ping")
async def ping():
    return {"status": "pong"}
```

## Execution Order
Middleware components execute in reverse order of addition (LIFO). The last middleware added with `add_middleware` will be the first to process an incoming request and the last to process the outgoing response.
