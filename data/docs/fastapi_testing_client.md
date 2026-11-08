---
doc_id: DOC-FA-010
title: Testing Modern FastAPI Applications with Pytest and AsyncClient
version: v0.115
framework: FastAPI
category: Testing
tags: [testing, pytest, asyncclient, httpx, testclient, dependency-overrides]
source_url: https://fastapi.tiangolo.com/tutorial/testing/
---

# Testing Modern FastAPI Applications with Pytest and AsyncClient

FastAPI applications can be tested synchronously using Starlette's `TestClient` or asynchronously using `httpx.AsyncClient` with `ASGITransport`.

## Testing Synchronous Routes with TestClient

`TestClient` wraps requests using `requests` internally:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/items")
    assert response.status_code == 200
    assert "items" in response.json()
```

## Testing Asynchronous Endpoints with httpx.AsyncClient

For testing endpoints that rely on async database connections, WebSockets, or background tasks, use `httpx.AsyncClient` with `ASGITransport`:

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app, get_db

# Mock dependency
async def override_get_db():
    class MockSession:
        async def query(self):
            return ["mock_item"]
    yield MockSession()

@pytest.fixture
def test_app():
    # Set dependency override
    app.dependency_overrides[get_db] = override_get_db
    yield app
    # Clean up after test
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_async_endpoint(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/items")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
```

## Dependency Overrides Pattern
FastAPI's `app.dependency_overrides` dictionary allows swapping any dependency callable (like database sessions, OAuth2 authentication, external weather APIs) with a mock fixture without needing monkeypatching or complex mock libraries.

