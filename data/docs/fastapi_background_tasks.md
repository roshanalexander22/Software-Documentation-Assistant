---
doc_id: DOC-FA-006
title: Asynchronous Background Tasks in FastAPI
version: v0.115
framework: FastAPI
category: Async Processing
tags: [background-tasks, async, notifications, concurrency, queues]
source_url: https://fastapi.tiangolo.com/tutorial/background-tasks/
---

# Asynchronous Background Tasks in FastAPI

FastAPI provides an integrated `BackgroundTasks` class to schedule tasks that execute after sending an HTTP response to the client. This is ideal for short post-processing operations like sending transactional emails, logging audit records, or updating cache indices without blocking client latency.

## How BackgroundTasks Work

When you declare a parameter of type `BackgroundTasks` in a route handler, FastAPI instantiates the container and ensures registered callable functions run immediately after the ASGI response body is dispatched.

## Code Example: Email and Audit Logging

```python
import asyncio
from typing import Annotated
from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Background Tasks API", version="0.115.0")

class UserSignup(BaseModel):
    username: str
    email: EmailStr

async def send_welcome_email(email_address: str, username: str):
    # Simulate non-blocking async network I/O
    await asyncio.sleep(0.5)
    print(f"[EMAIL] Sent welcome email to {username} at {email_address}")

def write_audit_log(username: str, action: str):
    # Synchronous functions are run in the external thread pool
    print(f"[AUDIT] User {username} completed action {action}")

@app.post("/signup", status_code=202)
async def signup(user: UserSignup, background_tasks: BackgroundTasks):
    """
    Accepts signup immediately, sends HTTP 202 Accepted, 
    and executes background email and audit logging.
    """
    # Queue async coroutine task
    background_tasks.add_task(send_welcome_email, user.email, user.username)
    # Queue sync blocking task
    background_tasks.add_task(write_audit_log, user.username, "SIGNUP")
    
    return {"message": "Account created. Welcome confirmation is on its way."}
```

## Background Tasks vs Distributed Task Queues (Celery/ARQ)

- **Use FastAPI `BackgroundTasks`**: For lightweight, low-durability tasks (duration < 15 seconds) tied to the current server process (e.g. notifications, metrics, audit logs).
- **Use Distributed Queues (Celery, ARQ, Temporal)**: For long-running heavy computing (video transcoding, ML model batch inference, financial reports) that require task retry semantics, state persistence, and dedicated worker fleets.
