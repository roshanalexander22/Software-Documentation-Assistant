"""
Unit tests for DocumentationRetriever: version detection, hybrid retrieval, and out-of-scope term filtering.
"""

import pytest
from src.rag_pipeline import RAGPipeline
from src.retriever import DocumentationRetriever


@pytest.fixture(scope="module")
def pipeline():
    p = RAGPipeline()
    p.build_or_load_index(force_reindex=False)
    return p


def test_version_hint_detection(pipeline):
    retriever = pipeline.retriever

    assert retriever.detect_version_hint("How do I migrate to Pydantic v2?") == "v2.0"
    assert retriever.detect_version_hint("What was the syntax in FastAPI 0.90?") == "v0.90-legacy"
    assert retriever.detect_version_hint("Explain FastAPI 0.115 lifespan events") == "v0.115"
    assert retriever.detect_version_hint("General question without version") is None


def test_out_of_scope_abstention_detection(pipeline):
    retriever = pipeline.retriever

    # Completely ungrounded topics
    assert retriever.check_out_of_scope_terms("Deploy FastAPI directly to an Ethereum smart contract blockchain") is True
    assert retriever.check_out_of_scope_terms("What is @app.quantum_accelerator() decorator in FastAPI for quantum computing?") is True
    assert retriever.check_out_of_scope_terms("Compile Pydantic models to FPGA hardware bitstream using Verilog") is True

    # Valid in-scope topics
    assert retriever.check_out_of_scope_terms("How do I migrate from BaseModel.dict() to Pydantic v2?") is False
    assert retriever.check_out_of_scope_terms("How do I implement OAuth2 JWT authentication in FastAPI?") is False


def test_retriever_ranking_accuracy(pipeline):
    retriever = pipeline.retriever

    res = retriever.retrieve("How do I stream LLM tokens using StreamingResponse in FastAPI?")
    assert res.has_sufficient_evidence is True
    assert len(res.chunks) > 0
    top_chunk = res.chunks[0]
    assert top_chunk.doc_id == "DOC-FA-007"
    assert "Streaming" in top_chunk.title
