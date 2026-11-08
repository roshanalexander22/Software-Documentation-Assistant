"""
Unit tests for DocumentLoader and MarkdownCodeAwareChunker.
"""

import pytest
from src.document_loader import Document, DocumentLoader
from src.chunker import MarkdownCodeAwareChunker, DocumentChunk
from src.config import settings


def test_document_loader_loads_real_docs():
    loader = DocumentLoader(settings.DOCS_DIR)
    docs = loader.load_all()
    assert len(docs) >= 10
    for doc in docs:
        assert doc.doc_id.startswith("DOC-")
        assert doc.version != ""
        assert doc.framework in ("FastAPI", "Pydantic")
        assert len(doc.content) > 100


def test_chunker_preserves_code_blocks_intact():
    chunker = MarkdownCodeAwareChunker(target_chunk_size=400, chunk_overlap=50)

    sample_doc = Document(
        doc_id="DOC-TEST-001",
        title="Test Document with Code",
        version="v1.0",
        framework="TestFramework",
        category="Testing",
        tags=["unit-test"],
        source_url="https://test.local",
        file_path="mock_test.md",
        content="""# Section 1: Intro

This is explanatory prose introducing the test function.

```python
def calculate_metrics(values: list[float]) -> dict:
    total = sum(values)
    count = len(values)
    mean = total / count if count > 0 else 0.0
    return {"mean": mean, "count": count}
```

## Section 2: Conclusion

Final thoughts on the implementation.
"""
    )

    chunks = chunker.chunk_document(sample_doc)
    assert len(chunks) >= 2

    # Verify at least one chunk has code and contains the full function
    code_chunks = [c for c in chunks if c.has_code]
    assert len(code_chunks) >= 1

    code_content = code_chunks[0].content
    assert "def calculate_metrics" in code_content
    assert 'return {"mean": mean, "count": count}' in code_content
    assert code_content.strip().startswith("```python") or "```python" in code_content
    assert code_chunks[0].citation.startswith("[Doc: DOC-TEST-001")


def test_chunk_citation_and_metadata_format():
    chunker = MarkdownCodeAwareChunker(target_chunk_size=500)
    doc = Document(
        doc_id="DOC-TEST-002",
        title="Metadata Verification",
        version="v2.0",
        framework="Pydantic",
        category="Models",
        tags=["meta"],
        source_url="https://test.local",
        file_path="mock_meta.md",
        content="""# Title Header

Text content for metadata testing with sufficient length.
"""
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    chk = chunks[0]
    assert chk.chunk_id == "DOC-TEST-002_chk01"
    assert chk.version == "v2.0"
    assert chk.framework == "Pydantic"
    assert "[Doc: DOC-TEST-002" in chk.citation
    assert "Ver: v2.0" in chk.citation
