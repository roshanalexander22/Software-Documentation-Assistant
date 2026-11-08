"""
Retriever module for Software Documentation Assistant.
Orchestrates hybrid retrieval, query version hint extraction, and evidence threshold checks.
"""

from dataclasses import dataclass
from typing import Optional
import re
from src.embeddings import EmbeddingService
from src.vector_store import VectorStore
from src.chunker import DocumentChunk


@dataclass
class RetrievalResult:
    """Encapsulates retrieved passages, scoring metrics, and evidence sufficiency."""
    query: str
    chunks: list[DocumentChunk]
    combined_scores: list[float]
    dense_scores: list[float]
    sparse_scores: list[float]
    has_sufficient_evidence: bool
    top_score: float
    detected_version: Optional[str] = None
    formatted_context: str = ""


class DocumentationRetriever:
    """
    Retriever capable of version-aware filtering, hybrid dense-sparse scoring,
    and confidence threshold evaluation to support reliable abstention.
    """

    VERSION_PATTERNS = {
        "v2.0": ["pydantic v2", "pydantic 2", "pydantic version 2"],
        "v1.10-legacy": ["pydantic v1", "pydantic 1", "legacy pydantic"],
        "v0.115": ["fastapi 0.115", "fastapi v0.115", "0.115"],
        "v0.90-legacy": ["fastapi 0.90", "fastapi v0.90", "0.90"],
    }

    GENERIC_WORDS = {
        "how", "do", "i", "what", "is", "the", "in", "to", "for", "of", "and", "a",
        "an", "using", "with", "fastapi", "pydantic", "python", "can", "way", "from",
        "work", "differ", "between", "work", "set", "up", "test", "endpoints", "syntax",
        "code", "example", "recommended", "manage", "explain", "explanation", "official"
    }

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        top_k: int = 4,
        alpha: float = 0.65,
        abstention_threshold: float = 0.38
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.top_k = top_k
        self.alpha = alpha
        self.abstention_threshold = abstention_threshold

    def detect_version_hint(self, query: str) -> Optional[str]:
        """Detects if a user query explicitly targets a specific version."""
        q_lower = query.lower()
        for version_key, keywords in self.VERSION_PATTERNS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                    return version_key
        return None

    def check_out_of_scope_terms(self, query: str) -> bool:
        """
        Detects if query contains distinct technical concepts absent from the knowledge base.
        (e.g., ethereum, blockchain, quantum, quantum_accelerator, fpga, verilog).
        """
        raw_tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
        distinctive = []
        for t in raw_tokens:
            stem = t.rstrip("s")
            if len(stem) > 3 and stem not in self.GENERIC_WORDS and t not in self.GENERIC_WORDS:
                distinctive.append(stem)

        if not distinctive:
            return False

        doc_freqs = self.vector_store._doc_frequencies
        missing_count = 0
        for t in distinctive:
            found = any(t in k or k in t for k in doc_freqs.keys())
            if not found:
                missing_count += 1

        # If at least 2 missing technical terms or > 35% of distinctive terms absent
        if missing_count >= 2 or (len(distinctive) > 0 and (missing_count / len(distinctive)) > 0.35):
            return True
        return False

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        version_override: Optional[str] = None,
        code_only: bool = False
    ) -> RetrievalResult:
        """
        Executes hybrid retrieval with soft version boost and vocabulary grounding check.
        """
        k = top_k or self.top_k
        detected_version = version_override or self.detect_version_hint(query)
        is_out_of_scope = self.check_out_of_scope_terms(query)

        # Generate query embedding
        query_emb = self.embedding_service.embed_query(query)

        # Execute hybrid search with soft version boost
        results = self.vector_store.hybrid_search(
            query=query,
            query_embedding=query_emb,
            top_k=k,
            alpha=self.alpha,
            version_filter=version_override,
            version_boost=detected_version,
            code_only=code_only
        )

        if not results:
            return RetrievalResult(
                query=query,
                chunks=[],
                combined_scores=[],
                dense_scores=[],
                sparse_scores=[],
                has_sufficient_evidence=False,
                top_score=0.0,
                detected_version=detected_version,
                formatted_context=""
            )

        chunks = [r[0] for r in results]
        combined = [r[1] for r in results]
        dense = [r[2] for r in results]
        sparse = [r[3] for r in results]
        top_score = combined[0]

        # Evidence sufficiency: meets threshold and no out-of-scope concepts
        has_sufficient_evidence = (
            top_score >= self.abstention_threshold and
            not is_out_of_scope
        )

        formatted_context = self._format_context(chunks, combined)

        return RetrievalResult(
            query=query,
            chunks=chunks,
            combined_scores=combined,
            dense_scores=dense,
            sparse_scores=sparse,
            has_sufficient_evidence=has_sufficient_evidence,
            top_score=top_score,
            detected_version=detected_version,
            formatted_context=formatted_context
        )

        formatted_context = self._format_context(chunks, combined)

        return RetrievalResult(
            query=query,
            chunks=chunks,
            combined_scores=combined,
            dense_scores=dense,
            sparse_scores=sparse,
            has_sufficient_evidence=has_sufficient_evidence,
            top_score=top_score,
            detected_version=detected_version,
            formatted_context=formatted_context
        )

    def _format_context(self, chunks: list[DocumentChunk], scores: list[float]) -> str:
        """Constructs grounded context string with unambiguous citation headers."""
        context_blocks = []
        for i, (chunk, score) in enumerate(zip(chunks, scores), 1):
            block = (
                f"--- EVIDENCE PASSAGE {i} ---\n"
                f"Source Citation: {chunk.citation}\n"
                f"Document: {chunk.title} (Doc ID: {chunk.doc_id})\n"
                f"Section: {chunk.section}\n"
                f"Target Version: {chunk.version} | Framework: {chunk.framework}\n"
                f"Relevance Score: {score:.4f}\n"
                f"Content:\n{chunk.content}\n"
            )
            context_blocks.append(block)
        return "\n".join(context_blocks)
