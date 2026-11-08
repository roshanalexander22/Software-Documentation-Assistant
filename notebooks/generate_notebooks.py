"""
Script to generate reproducible Jupyter Notebooks for exploration and benchmarking.
"""

import json
from pathlib import Path

notebooks_dir = Path(__file__).resolve().parent.parent / "notebooks"
notebooks_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Notebook 1: 01_rag_exploration_and_indexing.ipynb
# -----------------------------------------------------------------------------
nb1 = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Software Documentation Assistant: Exploration & Indexing\n",
                "## Week 3 | Retrieval-Augmented Generation Applications (Part C)\n",
                "\n",
                "This notebook demonstrates the end-to-end ingestion and indexing pipeline for developer technical documentation:\n",
                "1. Document loading with YAML frontmatter parsing\n",
                "2. Code-aware hierarchical chunking preserving Markdown code blocks\n",
                "3. Dense vector embeddings with SentenceTransformers (`all-MiniLM-L6-v2`)\n",
                "4. Sparse BM25 lexical indexing\n",
                "5. Index persistence and verification"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys\n",
                "import os\n",
                "from pathlib import Path\n",
                "\n",
                "# Ensure project root is in sys.path\n",
                "project_root = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n",
                "sys.path.insert(0, str(project_root))\n",
                "print(f\"Project root: {project_root}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 1. Ingest Technical Documents\n",
                "We load our curated technical documentation corpus across FastAPI (v0.115 and legacy v0.90) and Pydantic (v2.0 and v1.10)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.document_loader import DocumentLoader\n",
                "from src.config import settings\n",
                "\n",
                "loader = DocumentLoader(settings.DOCS_DIR)\n",
                "docs = loader.load_all()\n",
                "print(f\"Loaded {len(docs)} technical documentation files:\\n\")\n",
                "for d in docs:\n",
                "    print(f\"- [{d.doc_id}] {d.title} (Framework: {d.framework}, Ver: {d.version}, Chars: {d.char_count})\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 2. Code-Aware Hierarchical Chunking\n",
                "Notice that code blocks (` ```python ... ``` `) are kept intact to preserve syntactic validity."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.chunker import MarkdownCodeAwareChunker\n",
                "\n",
                "chunker = MarkdownCodeAwareChunker(target_chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)\n",
                "chunks = chunker.chunk_all(docs)\n",
                "code_chunks = [c for c in chunks if c.has_code]\n",
                "\n",
                "print(f\"Total chunks generated: {len(chunks)}\")\n",
                "print(f\"Chunks containing code examples: {len(code_chunks)} ({len(code_chunks)/len(chunks)*100:.1f}%)\")\n",
                "\n",
                "# Inspect a sample code chunk\n",
                "sample = code_chunks[0]\n",
                "print(f\"\\nSample Chunk ID: {sample.chunk_id}\")\n",
                "print(f\"Citation: {sample.citation}\")\n",
                "print(\"Content Preview:\")\n",
                "print(sample.content[:300] + \"...\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 3. Build Hybrid Vector Store\n",
                "Compute normalized dense vectors and construct the BM25 lexical inverted index."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.rag_pipeline import RAGPipeline\n",
                "\n",
                "pipeline = RAGPipeline()\n",
                "index_stats = pipeline.build_or_load_index(force_reindex=False)\n",
                "print(\"Index status:\", index_stats)\n",
                "print(\"Pipeline stats:\", pipeline.get_stats())"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.13"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

# -----------------------------------------------------------------------------
# Notebook 2: 02_retrieval_and_evaluation_benchmark.ipynb
# -----------------------------------------------------------------------------
nb2 = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Software Documentation Assistant: Retrieval & Evaluation Benchmark\n",
                "## Week 3 | Retrieval-Augmented Generation Applications (Part C)\n",
                "\n",
                "This notebook executes the 15-question benchmark evaluation, measuring:\n",
                "1. Version Sensitivity (FastAPI 0.115 vs 0.90, Pydantic V2 vs V1)\n",
                "2. API Explanation & Code Snippet Retrieval\n",
                "3. Citation Correctness & Grounding\n",
                "4. Unanswerable Question Abstention (Hallucination Prevention)\n",
                "5. Latency and Quantitative IR Metrics (MRR, Hit Rate@4, Precision@4)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys\n",
                "from pathlib import Path\n",
                "project_root = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n",
                "sys.path.insert(0, str(project_root))\n",
                "\n",
                "from src.rag_pipeline import RAGPipeline\n",
                "from src.evaluator import BenchmarkEvaluator, BENCHMARK_15_QUESTIONS\n",
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "import json\n",
                "\n",
                "pipeline = RAGPipeline()\n",
                "pipeline.build_or_load_index(force_reindex=False)\n",
                "evaluator = BenchmarkEvaluator(pipeline)"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 1. Interactive Single Query Demonstration\n",
                "Let's test an answerable migration query and verify citations and code."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "query = \"How do I migrate from BaseModel.dict() to Pydantic v2 syntax?\"\n",
                "response = pipeline.query(query)\n",
                "\n",
                "print(f\"Query: {response['query']}\")\n",
                "print(f\"Abstained: {response['is_abstained']}\")\n",
                "print(f\"Confidence Score: {response['confidence_score']}\")\n",
                "print(f\"Citations: {response['citations']}\")\n",
                "print(f\"Latency: {response['latency']['total_ms']}ms\\n\")\n",
                "print(\"--- Generated Answer ---\")\n",
                "print(response['answer'])"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 2. Abstention Test on Out-of-Scope Query\n",
                "Testing whether the system safely refuses to hallucinate on fictitious features."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "out_of_scope_query = \"What is the @app.quantum_accelerator() decorator in FastAPI for quantum computing speedups?\"\n",
                "refusal_response = pipeline.query(out_of_scope_query)\n",
                "\n",
                "print(f\"Query: {refusal_response['query']}\")\n",
                "print(f\"Abstained: {refusal_response['is_abstained']}\")\n",
                "print(f\"Confidence Score: {refusal_response['confidence_score']}\")\n",
                "print(\"--- Abstention Response ---\")\n",
                "print(refusal_response['answer'])"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 3. Run Complete 15-Question Benchmark Suite\n",
                "Calculates quantitative metrics across all categories."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "bench_results = evaluator.run_benchmark(BENCHMARK_15_QUESTIONS)\n",
                "summary = bench_results['summary']\n",
                "\n",
                "print(\"\\n================ BENCHMARK SUMMARY ================\")\n",
                "print(f\"Total Questions: {summary['total_questions']}\")\n",
                "print(f\"Hit Rate@4: {summary['hit_rate_at_k']*100:.1f}%\")\n",
                "print(f\"MRR (Mean Reciprocal Rank): {summary['mrr']:.4f}\")\n",
                "print(f\"Citation Correctness: {summary['citation_correctness_pct']}%\")\n",
                "print(f\"Abstention Accuracy: {summary['abstention_accuracy_pct']}%\")\n",
                "print(f\"Confusion Matrix: {summary['confusion_matrix']}\")\n",
                "print(f\"Median Latency: {summary['latency_stats']['median_ms']}ms\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 4. Results Breakdown Table"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "df = pd.DataFrame(bench_results['results'])[['id', 'category', 'question', 'confidence_score', 'is_abstained', 'abstention_status', 'latency_ms']]\n",
                "df"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.13"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

with open(notebooks_dir / "01_rag_exploration_and_indexing.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb1, f, indent=2)

with open(notebooks_dir / "02_retrieval_and_evaluation_benchmark.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb2, f, indent=2)

print(f"[INFO] Jupyter notebooks written to {notebooks_dir}")

