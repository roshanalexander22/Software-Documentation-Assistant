"""
Unified RAG Pipeline for Software Documentation Assistant.
Coordinates document ingestion, chunking, indexing, hybrid retrieval, and grounded generation.
"""

from pathlib import Path
from typing import Any, Optional
import time

from src.config import settings
from src.document_loader import DocumentLoader, Document
from src.chunker import MarkdownCodeAwareChunker, DocumentChunk
from src.embeddings import EmbeddingService
from src.vector_store import VectorStore
from src.retriever import DocumentationRetriever, RetrievalResult
from src.generator import GroundedGenerator, GenerationOutput


class RAGPipeline:
    """
    Complete end-to-end RAG Pipeline for Developer Technical Documentation.
    """

    def __init__(
        self,
        docs_dir: Optional[Path | str] = None,
        cache_dir: Optional[Path | str] = None,
        top_k: int = settings.RETRIEVAL_TOP_K,
        alpha: float = settings.HYBRID_ALPHA,
        abstention_threshold: float = settings.ABSTENTION_SIMILARITY_THRESHOLD,
        gemini_api_key: Optional[str] = None
    ):
        self.docs_dir = Path(docs_dir or settings.DOCS_DIR)
        self.cache_dir = Path(cache_dir or settings.INDEX_CACHE_DIR)
        self.top_k = top_k
        self.alpha = alpha
        self.abstention_threshold = abstention_threshold

        # Initialize subcomponents
        self.loader = DocumentLoader(self.docs_dir)
        self.chunker = MarkdownCodeAwareChunker(
            target_chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            min_chunk_size=settings.MIN_CHUNK_SIZE
        )
        self.embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL,
            dim=settings.EMBEDDING_DIM
        )
        self.vector_store = VectorStore()
        self.retriever = DocumentationRetriever(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            top_k=self.top_k,
            alpha=self.alpha,
            abstention_threshold=self.abstention_threshold
        )
        self.generator = GroundedGenerator(
            api_key=gemini_api_key,
            model_name=settings.GEMINI_MODEL,
            temperature=settings.GENERATION_TEMPERATURE,
            abstention_threshold=self.abstention_threshold
        )

        self.documents: list[Document] = []
        self.chunks: list[DocumentChunk] = []
        self._is_indexed: bool = False

    def build_or_load_index(self, force_reindex: bool = False) -> dict[str, Any]:
        """
        Loads cached vector store from disk if available, otherwise indexes documents from scratch.
        """
        start_time = time.perf_counter()

        if not force_reindex and (self.cache_dir / "chunks.json").exists():
            success = self.vector_store.load(self.cache_dir)
            if success:
                self.chunks = self.vector_store.chunks
                self._is_indexed = True
                duration = time.perf_counter() - start_time
                print(f"[INFO] Loaded existing index ({len(self.chunks)} chunks) in {duration:.2f}s.")
                return {
                    "status": "loaded_from_cache",
                    "total_chunks": len(self.chunks),
                    "duration_seconds": duration
                }

        # Index from scratch
        print("[INFO] Building index from documentation files...")
        self.documents = self.loader.load_all()
        if not self.documents:
            print(f"[WARN] No documents found in {self.docs_dir}")
            return {"status": "empty", "total_documents": 0, "total_chunks": 0}

        self.chunks = self.chunker.chunk_all(self.documents)
        print(f"[INFO] Generated {len(self.chunks)} chunks from {len(self.documents)} documents.")

        # Compute embeddings
        texts = [c.content for c in self.chunks]
        embeddings = self.embedding_service.embed_texts(texts)

        # Populate vector store
        self.vector_store.add_chunks(self.chunks, embeddings)

        # Save to disk cache
        self.vector_store.save(self.cache_dir)

        self._is_indexed = True
        duration = time.perf_counter() - start_time
        print(f"[INFO] Index built and saved successfully in {duration:.2f}s.")

        return {
            "status": "indexed_fresh",
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "duration_seconds": duration
        }

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        version_override: Optional[str] = None,
        code_only: bool = False
    ) -> dict[str, Any]:
        """
        Executes complete RAG pipeline for a developer question.
        """
        if not self._is_indexed:
            self.build_or_load_index()

        total_start = time.perf_counter()

        # Step 1: Retrieval
        retrieval_start = time.perf_counter()
        retrieval_res: RetrievalResult = self.retriever.retrieve(
            query=question,
            top_k=top_k or self.top_k,
            version_override=version_override,
            code_only=code_only
        )
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000.0

        # Step 2: Generation
        gen_start = time.perf_counter()
        gen_output: GenerationOutput = self.generator.generate(retrieval_res)
        generation_time_ms = (time.perf_counter() - gen_start) * 1000.0

        total_time_ms = (time.perf_counter() - total_start) * 1000.0

        # Format retrieved chunks for response
        retrieved_items = []
        for chunk, score in zip(retrieval_res.chunks, retrieval_res.combined_scores):
            retrieved_items.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "section": chunk.section,
                "version": chunk.version,
                "framework": chunk.framework,
                "category": chunk.category,
                "score": round(score, 4),
                "has_code": chunk.has_code,
                "citation": chunk.citation,
                "content_preview": chunk.content[:180] + ("..." if len(chunk.content) > 180 else ""),
            })

        return {
            "query": question,
            "answer": gen_output.answer,
            "citations": gen_output.citations,
            "is_abstained": gen_output.is_abstained,
            "confidence_score": round(gen_output.confidence_score, 4),
            "model_name": gen_output.model_name,
            "detected_version": retrieval_res.detected_version,
            "has_sufficient_evidence": retrieval_res.has_sufficient_evidence,
            "retrieved_chunks": retrieved_items,
            "latency": {
                "total_ms": round(total_time_ms, 2),
                "retrieval_ms": round(retrieval_time_ms, 2),
                "generation_ms": round(generation_time_ms, 2),
            }
        }

    def get_stats(self) -> dict[str, Any]:
        """Returns statistics about the indexed documents and chunks."""
        if not self._is_indexed:
            self.build_or_load_index()

        code_chunks = sum(1 for c in self.chunks if c.has_code)
        versions = list(set(c.version for c in self.chunks))
        frameworks = list(set(c.framework for c in self.chunks))
        categories = list(set(c.category for c in self.chunks))

        return {
            "total_chunks": len(self.chunks),
            "code_chunks": code_chunks,
            "prose_chunks": len(self.chunks) - code_chunks,
            "unique_versions": versions,
            "frameworks": frameworks,
            "categories": categories,
        }
