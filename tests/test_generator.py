"""
Unit tests for GroundedGenerator: answer formatting, citations, and abstention.
"""

import pytest
from src.retriever import RetrievalResult
from src.chunker import DocumentChunk
from src.generator import GroundedGenerator


def _mock_chunk():
    return DocumentChunk(
        chunk_id="DOC-FA-001_chk01",
        doc_id="DOC-FA-001",
        title="Lifespan Events",
        section="Modern Lifespan",
        version="v0.115",
        framework="FastAPI",
        category="Lifecycle",
        content="Use @asynccontextmanager async def lifespan(app: FastAPI): yield to handle startup and shutdown.",
        char_count=100,
        has_code=True,
        code_language="python",
        citation="[Doc: DOC-FA-001 | Section: 'Modern Lifespan' | Ver: v0.115]"
    )


def test_generator_abstains_when_evidence_insufficient():
    generator = GroundedGenerator(abstention_threshold=0.40)

    res = RetrievalResult(
        query="Deploy to Ethereum blockchain",
        chunks=[],
        combined_scores=[],
        dense_scores=[],
        sparse_scores=[],
        has_sufficient_evidence=False,
        top_score=0.15,
        detected_version=None,
        formatted_context=""
    )

    output = generator.generate(res)
    assert output.is_abstained is True
    assert "[ABSTENTION]" in output.answer
    assert len(output.citations) == 0


def test_generator_produces_citations_for_valid_evidence():
    generator = GroundedGenerator()
    chunk = _mock_chunk()

    res = RetrievalResult(
        query="FastAPI lifespan events",
        chunks=[chunk],
        combined_scores=[0.85],
        dense_scores=[0.85],
        sparse_scores=[0.85],
        has_sufficient_evidence=True,
        top_score=0.85,
        detected_version="v0.115",
        formatted_context=f"Passage: {chunk.content}"
    )

    output = generator.generate(res)
    assert output.is_abstained is False
    assert len(output.citations) >= 1
    assert "DOC-FA-001" in output.citations[0]
    assert "[Doc: DOC-FA-001" in output.answer or "[Doc: DOC-FA-001" in output.citations[0]
