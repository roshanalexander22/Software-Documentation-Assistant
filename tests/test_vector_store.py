"""
Unit tests for VectorStore: dense cosine similarity, BM25 keyword matching, and serialization.
"""

import numpy as np
import pytest
from pathlib import Path
from src.chunker import DocumentChunk
from src.vector_store import VectorStore


def _create_mock_chunk(chunk_id: str, title: str, section: str, version: str, content: str, has_code: bool = False):
    return DocumentChunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("_")[0],
        title=title,
        section=section,
        version=version,
        framework="FastAPI",
        category="Test",
        content=content,
        char_count=len(content),
        has_code=has_code,
        code_language="python" if has_code else "",
        citation=f"[Doc: {chunk_id.split('_')[0]} | Ver: {version}]"
    )


def test_vector_store_add_and_search(tmp_path):
    store = VectorStore()

    c1 = _create_mock_chunk("DOC-1_chk01", "Lifespan Events", "Setup", "v0.115", "Lifespan context manager with asynccontextmanager in FastAPI.")
    c2 = _create_mock_chunk("DOC-2_chk01", "JWT Security", "Auth", "v0.115", "OAuth2 password bearer and JWT token encoding using HS256.")
    c3 = _create_mock_chunk("DOC-3_chk01", "Legacy Events", "Startup", "v0.90-legacy", "Legacy startup event using on_event startup decorator.")

    chunks = [c1, c2, c3]

    # Create distinct normalized 4-dim embeddings
    emb = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ], dtype=np.float32)

    store.add_chunks(chunks, emb)
    assert store.count() == 3

    # Query matching c1 in dense vector
    q_vec = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    results = store.hybrid_search("Lifespan asynccontextmanager", q_vec, top_k=2)

    assert len(results) == 2
    top_chunk, combined, dense, sparse = results[0]
    assert top_chunk.chunk_id == "DOC-1_chk01"
    assert combined > 0.5


def test_vector_store_persistence(tmp_path):
    store = VectorStore()
    c1 = _create_mock_chunk("DOC-A_chk01", "Doc A", "Sec 1", "v1.0", "Persistent storage content testing.")
    emb = np.array([[0.5, 0.5, 0.5, 0.5]], dtype=np.float32)
    store.add_chunks([c1], emb)

    # Save to temp dir
    store.save(tmp_path)
    assert (tmp_path / "chunks.json").exists()
    assert (tmp_path / "embeddings.npy").exists()

    # Load into fresh store
    new_store = VectorStore()
    success = new_store.load(tmp_path)
    assert success is True
    assert new_store.count() == 1
    assert new_store.chunks[0].chunk_id == "DOC-A_chk01"
