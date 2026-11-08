"""
API integration tests for FastAPI application endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Software-Documentation-Assistant"


def test_stats_endpoint(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_chunks"] >= 50
    assert data["code_chunks"] >= 10


def test_documents_endpoint(client):
    res = client.get("/api/documents")
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 10
    doc_ids = [d["doc_id"] for d in docs]
    assert "DOC-FA-001" in doc_ids
    assert "DOC-PYD-001" in doc_ids


def test_query_answerable_endpoint(client):
    res = client.post("/api/query", json={
        "query": "How do I implement OAuth2 password bearer token authentication with JWT in FastAPI?",
        "top_k": 3
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_abstained"] is False
    assert len(data["citations"]) > 0
    assert len(data["retrieved_chunks"]) == 3
    assert data["confidence_score"] > 0.5


def test_query_abstention_endpoint(client):
    res = client.post("/api/query", json={
        "query": "How do I deploy FastAPI directly to an Ethereum smart contract blockchain virtual machine?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_abstained"] is True
    assert "[ABSTENTION]" in data["answer"]


def test_ui_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Software Documentation Assistant" in res.text
    assert "<html" in res.text
