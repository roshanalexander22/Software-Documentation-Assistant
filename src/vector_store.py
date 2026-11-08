"""
In-memory and Persistent Hybrid Vector Store.
Combines dense cosine similarity retrieval with sparse BM25/TF-IDF keyword matching,
supporting metadata filtering (version, framework, code presence) and disk persistence.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional
import json
import math
import numpy as np
from src.chunker import DocumentChunk


class VectorStore:
    """
    Hybrid Vector Index:
    1. Dense cosine similarity over normalized embeddings.
    2. BM25 / TF-IDF sparse lexical scoring for precise technical symbol matches.
    3. Metadata filtering by version, framework, and code flags.
    4. Serialization to JSON + Numpy array.
    """

    def __init__(self):
        self.chunks: list[DocumentChunk] = []
        self.embeddings: Optional[np.ndarray] = None  # shape: [N, dim]
        self._doc_frequencies: dict[str, int] = {}
        self._doc_lengths: list[int] = []
        self._avg_doc_len: float = 0.0
        self._term_freqs: list[dict[str, int]] = []
        self.k1: float = 1.5
        self.b: float = 0.75

    def add_chunks(self, chunks: list[DocumentChunk], embeddings: np.ndarray):
        """Adds chunks and their corresponding embedding vectors to the index."""
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")

        self.chunks.extend(chunks)

        if self.embeddings is None:
            self.embeddings = embeddings.astype(np.float32)
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings.astype(np.float32)])

        self._build_lexical_index()

    STOPWORDS = {
        "how", "do", "i", "what", "is", "the", "in", "to", "for", "of", "and", "a",
        "an", "using", "with", "from", "can", "as", "by", "or", "on", "it", "be",
        "this", "that", "are", "were", "into", "their", "there", "then"
    }

    def _tokenize(self, text: str) -> list[str]:
        """Simple technical-friendly tokenizer preserving identifiers and dots."""
        clean = ""
        for char in text.lower():
            if char.isalnum() or char in ("_", ".", "-", "@"):
                clean += char
            else:
                clean += " "
        return [w for w in clean.split() if len(w) > 1 and w not in self.STOPWORDS]

    def _build_lexical_index(self):
        """Builds BM25 term frequency structures across all indexed chunks."""
        self._term_freqs = []
        self._doc_lengths = []
        self._doc_frequencies = {}

        for chunk in self.chunks:
            tokens = self._tokenize(chunk.content + " " + chunk.title + " " + chunk.section)
            self._doc_lengths.append(len(tokens))
            tf: dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            self._term_freqs.append(tf)

            for unique_token in tf.keys():
                self._doc_frequencies[unique_token] = self._doc_frequencies.get(unique_token, 0) + 1

        total_tokens = sum(self._doc_lengths)
        self._avg_doc_len = total_tokens / max(len(self._doc_lengths), 1)

    def _bm25_score(self, query: str) -> np.ndarray:
        """Computes BM25 scores for the given query against all chunks."""
        query_tokens = self._tokenize(query)
        num_docs = len(self.chunks)
        scores = np.zeros(num_docs, dtype=np.float32)

        if num_docs == 0 or not query_tokens:
            return scores

        for token in query_tokens:
            df = self._doc_frequencies.get(token, 0)
            if df == 0:
                continue
            # Standard Robertson-Spärck Jones IDF
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            for i, tf_dict in enumerate(self._term_freqs):
                tf = tf_dict.get(token, 0)
                if tf == 0:
                    continue
                doc_len = self._doc_lengths[i]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(self._avg_doc_len, 1e-6)))
                scores[i] += idf * (tf * (self.k1 + 1.0)) / max(denom, 1e-6)

        # Smooth scaling into [0, 1] range without forcing arbitrary max to 1.0
        scores = scores / (scores + 5.0)
        return scores

    def hybrid_search(
        self,
        query: str,
        query_embedding: np.ndarray,
        top_k: int = 4,
        alpha: float = 0.65,
        version_filter: Optional[str] = None,
        version_boost: Optional[str] = None,
        framework_filter: Optional[str] = None,
        code_only: bool = False
    ) -> list[tuple[DocumentChunk, float, float, float]]:
        """
        Executes hybrid search combining dense similarity and sparse BM25 scores.
        
        Returns:
            list of tuples: (chunk, combined_score, dense_score, sparse_score)
        """
        if len(self.chunks) == 0 or self.embeddings is None:
            return []

        # 1. Dense Cosine Similarity (vectors are unit normalized)
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            q_emb = query_embedding / query_norm
        else:
            q_emb = query_embedding

        dense_scores = np.dot(self.embeddings, q_emb)
        dense_scores = np.clip((dense_scores + 1.0) / 2.0, 0.0, 1.0)

        # 2. Sparse Lexical BM25
        sparse_scores = self._bm25_score(query)

        # 3. Hybrid Combination: alpha * dense + (1 - alpha) * sparse
        combined_scores = alpha * dense_scores + (1.0 - alpha) * sparse_scores

        # 4. Metadata Filtering & Ranking
        results: list[tuple[DocumentChunk, float, float, float]] = []
        for i, chunk in enumerate(self.chunks):
            # Hard version filter check if explicitly set
            if version_filter and version_filter.lower() not in chunk.version.lower():
                continue
            # Framework filter check
            if framework_filter and framework_filter.lower() not in chunk.framework.lower():
                continue
            # Code only check
            if code_only and not chunk.has_code:
                continue

            score = float(combined_scores[i])
            # Soft version boost
            if version_boost and version_boost.lower() in chunk.version.lower():
                score = min(score * 1.15, 1.0)

            results.append((chunk, score, float(dense_scores[i]), float(sparse_scores[i])))

        # Sort descending by combined score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def save(self, directory: Path | str):
        """Persists the vector index (chunks metadata + numpy embeddings) to disk."""
        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        chunks_data = [asdict(c) for c in self.chunks]
        with open(target_dir / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2)

        if self.embeddings is not None:
            np.save(target_dir / "embeddings.npy", self.embeddings)

        print(f"[INFO] Vector store saved to {target_dir} ({len(self.chunks)} chunks).")

    def load(self, directory: Path | str) -> bool:
        """Loads index from disk. Returns True if successfully loaded."""
        target_dir = Path(directory)
        chunks_file = target_dir / "chunks.json"
        emb_file = target_dir / "embeddings.npy"

        if not chunks_file.exists() or not emb_file.exists():
            return False

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)

        self.chunks = [DocumentChunk(**item) for item in chunks_data]
        self.embeddings = np.load(emb_file)
        self._build_lexical_index()
        print(f"[INFO] Vector store loaded from {target_dir} ({len(self.chunks)} chunks).")
        return True

    def count(self) -> int:
        return len(self.chunks)
