"""
Evaluation and Benchmarking Suite for Software Documentation Assistant RAG.
Runs the 15 standard evaluation questions, measuring retrieval accuracy,
citation correctness, abstention reliability, and system latency.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import json
import time
import numpy as np

from src.rag_pipeline import RAGPipeline
from src.config import settings


@dataclass
class EvalQuestion:
    """Definition of a benchmark evaluation question."""
    id: int
    category: str
    question: str
    expected_doc_ids: list[str]
    expected_version: Optional[str]
    should_abstain: bool
    requires_code: bool
    description: str


# 15 Standard Benchmark Questions
BENCHMARK_15_QUESTIONS: list[EvalQuestion] = [
    # Category 1: Version Sensitivity & Migration
    EvalQuestion(
        id=1,
        category="Version Sensitivity",
        question="How do I migrate from BaseModel.dict() to Pydantic v2 syntax?",
        expected_doc_ids=["DOC-PYD-001"],
        expected_version="v2.0",
        should_abstain=False,
        requires_code=True,
        description="Pydantic V1 .dict() to V2 .model_dump() migration"
    ),
    EvalQuestion(
        id=2,
        category="Version Sensitivity",
        question="What is the recommended modern way to manage startup and shutdown events in FastAPI 0.115?",
        expected_doc_ids=["DOC-FA-001"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="FastAPI Lifespan context manager replacing deprecated on_event"
    ),
    EvalQuestion(
        id=3,
        category="Version Sensitivity",
        question="How were startup events registered in legacy FastAPI 0.90?",
        expected_doc_ids=["DOC-FA-002"],
        expected_version="v0.90-legacy",
        should_abstain=False,
        requires_code=True,
        description="Legacy @app.on_event('startup') registration"
    ),
    EvalQuestion(
        id=4,
        category="Version Sensitivity",
        question="How do field validators differ between Pydantic v1 and Pydantic v2?",
        expected_doc_ids=["DOC-PYD-001", "DOC-PYD-002"],
        expected_version="v2.0",
        should_abstain=False,
        requires_code=True,
        description="V1 @validator vs V2 @field_validator with classmethod"
    ),
    EvalQuestion(
        id=5,
        category="Version Sensitivity",
        question="What replaced the regex parameter in Query and Path validation in modern FastAPI?",
        expected_doc_ids=["DOC-FA-011"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="Replacement of regex keyword with pattern in modern Query validation"
    ),

    # Category 2: API Explanations & Code Examples
    EvalQuestion(
        id=6,
        category="API & Code Examples",
        question="How do I declare dependency injection using typing.Annotated in modern FastAPI?",
        expected_doc_ids=["DOC-FA-003"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="Modern typing.Annotated with Depends() for type aliases"
    ),
    EvalQuestion(
        id=7,
        category="API & Code Examples",
        question="How do I implement OAuth2 password bearer token authentication with JWT in FastAPI?",
        expected_doc_ids=["DOC-FA-004"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="OAuth2PasswordBearer, JWT tokens, and get_current_user dependency"
    ),
    EvalQuestion(
        id=8,
        category="API & Code Examples",
        question="How can I create custom middleware using BaseHTTPMiddleware to measure request time in FastAPI?",
        expected_doc_ids=["DOC-FA-005"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="BaseHTTPMiddleware subclass and X-Process-Time header"
    ),
    EvalQuestion(
        id=9,
        category="API & Code Examples",
        question="How do asynchronous BackgroundTasks work in FastAPI and how do I schedule an email notification?",
        expected_doc_ids=["DOC-FA-006"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="BackgroundTasks parameter and add_task execution"
    ),
    EvalQuestion(
        id=10,
        category="API & Code Examples",
        question="How do I stream generative LLM tokens using StreamingResponse and Server-Sent Events in FastAPI?",
        expected_doc_ids=["DOC-FA-007"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="StreamingResponse with async generator and text/event-stream"
    ),

    # Category 3: Database & Testing Integration
    EvalQuestion(
        id=11,
        category="Architecture & Testing",
        question="How do I set up async database sessions with SQLAlchemy 2.0 in FastAPI?",
        expected_doc_ids=["DOC-FA-009"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="SQLAlchemy 2.0 create_async_engine and async generator dependency"
    ),
    EvalQuestion(
        id=12,
        category="Architecture & Testing",
        question="How do I test async endpoints using httpx AsyncClient and ASGITransport in Pytest?",
        expected_doc_ids=["DOC-FA-010"],
        expected_version="v0.115",
        should_abstain=False,
        requires_code=True,
        description="httpx AsyncClient with ASGITransport and dependency_overrides"
    ),

    # Category 4: Unanswerable & Out-of-Scope (Abstention Verification)
    EvalQuestion(
        id=13,
        category="Abstention & Negative",
        question="How do I deploy FastAPI directly to an Ethereum smart contract blockchain virtual machine?",
        expected_doc_ids=[],
        expected_version=None,
        should_abstain=True,
        requires_code=False,
        description="Out-of-scope blockchain deployment query requiring system abstention"
    ),
    EvalQuestion(
        id=14,
        category="Abstention & Negative",
        question="What is the @app.quantum_accelerator() decorator in FastAPI for quantum computing speedups?",
        expected_doc_ids=[],
        expected_version=None,
        should_abstain=True,
        requires_code=False,
        description="Fictitious API decorator requiring hallucination resistance and abstention"
    ),
    EvalQuestion(
        id=15,
        category="Abstention & Negative",
        question="How do I compile Pydantic models directly to FPGA hardware bitstreams using Verilog?",
        expected_doc_ids=[],
        expected_version=None,
        should_abstain=True,
        requires_code=False,
        description="Out-of-scope hardware compilation query requiring system abstention"
    ),
]


class BenchmarkEvaluator:
    """Runs evaluation benchmarks against the RAGPipeline and outputs metrics."""

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline

    def run_benchmark(self, questions: list[EvalQuestion] = BENCHMARK_15_QUESTIONS) -> dict[str, Any]:
        """
        Executes all benchmark questions and calculates quantitative RAG metrics.
        """
        results_list = []
        reciprocal_ranks = []
        precision_at_k_scores = []
        hit_scores = []
        citation_correct_count = 0
        citation_total_count = 0
        abstention_confusion = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
        latencies = []

        print(f"\n=======================================================")
        print(f"Starting Benchmark Evaluation on {len(questions)} Standard Questions")
        print(f"=======================================================\n")

        for q in questions:
            res = self.pipeline.query(q.question)
            latencies.append(res["latency"]["total_ms"])

            # 1. Abstention Evaluation
            is_abstained = res["is_abstained"]
            if q.should_abstain:
                if is_abstained:
                    abstention_confusion["TN"] += 1  # Correctly abstained
                    abstention_status = "CORRECT_ABSTENTION"
                else:
                    abstention_confusion["FP"] += 1  # Failed to abstain (hallucinated)
                    abstention_status = "FALSE_POSITIVE_ANSWER"
            else:
                if not is_abstained:
                    abstention_confusion["TP"] += 1  # Correctly answered
                    abstention_status = "CORRECT_ANSWER"
                else:
                    abstention_confusion["FN"] += 1  # Improperly abstained on valid question
                    abstention_status = "FALSE_NEGATIVE_ABSTENTION"

            # 2. Retrieval Evaluation (only for answerable questions)
            retrieved_doc_ids = [c["doc_id"] for c in res["retrieved_chunks"]]
            if not q.should_abstain:
                # Hit rate
                hits = [doc_id for doc_id in q.expected_doc_ids if doc_id in retrieved_doc_ids]
                hit_score = 1.0 if hits else 0.0
                hit_scores.append(hit_score)

                # Precision@k: relevant retrieved / total retrieved
                prec = len(hits) / max(len(retrieved_doc_ids), 1)
                precision_at_k_scores.append(prec)

                # Reciprocal Rank (MRR)
                first_rank = 0
                for rank, doc_id in enumerate(retrieved_doc_ids, 1):
                    if doc_id in q.expected_doc_ids:
                        first_rank = rank
                        break
                rr = (1.0 / first_rank) if first_rank > 0 else 0.0
                reciprocal_ranks.append(rr)

                # 3. Citation Correctness
                # Check if generated citations reference expected doc IDs
                citations = res["citations"]
                for cite in citations:
                    citation_total_count += 1
                    if any(exp in cite for exp in q.expected_doc_ids):
                        citation_correct_count += 1

            # Format record
            record = {
                "id": q.id,
                "category": q.category,
                "question": q.question,
                "should_abstain": q.should_abstain,
                "is_abstained": is_abstained,
                "abstention_status": abstention_status,
                "confidence_score": res["confidence_score"],
                "expected_doc_ids": q.expected_doc_ids,
                "retrieved_doc_ids": retrieved_doc_ids,
                "citations": res["citations"],
                "latency_ms": res["latency"]["total_ms"],
                "answer_preview": res["answer"][:180] + ("..." if len(res["answer"]) > 180 else ""),
            }
            results_list.append(record)

            status_icon = "✓" if (q.should_abstain == is_abstained) else "✗"
            print(f"[{status_icon}] Q{q.id:02d} ({q.category[:15]}): Score={res['confidence_score']:.3f} | Abstained={is_abstained} | {res['latency']['total_ms']:.1f}ms")

        # Summary Metrics
        mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
        hit_rate = float(np.mean(hit_scores)) if hit_scores else 0.0
        avg_precision = float(np.mean(precision_at_k_scores)) if precision_at_k_scores else 0.0
        citation_correctness = (citation_correct_count / max(citation_total_count, 1)) * 100.0

        total_questions = len(questions)
        correct_abstentions = (abstention_confusion["TP"] + abstention_confusion["TN"])
        abstention_accuracy = (correct_abstentions / total_questions) * 100.0

        summary = {
            "total_questions": total_questions,
            "answerable_questions": len(questions) - sum(1 for q in questions if q.should_abstain),
            "unanswerable_questions": sum(1 for q in questions if q.should_abstain),
            "mrr": round(mrr, 4),
            "hit_rate_at_k": round(hit_rate, 4),
            "precision_at_k": round(avg_precision, 4),
            "citation_correctness_pct": round(citation_correctness, 2),
            "abstention_accuracy_pct": round(abstention_accuracy, 2),
            "confusion_matrix": abstention_confusion,
            "latency_stats": {
                "mean_ms": round(float(np.mean(latencies)), 2),
                "median_ms": round(float(np.median(latencies)), 2),
                "min_ms": round(float(np.min(latencies)), 2),
                "max_ms": round(float(np.max(latencies)), 2),
            }
        }

        # Save to results directory
        self._save_results(results_list, summary)
        self._generate_visualizations(summary, abstention_confusion)

        return {"summary": summary, "results": results_list}

    def _save_results(self, results: list[dict], summary: dict):
        """Saves evaluation results and summary to JSON."""
        res_dir = Path(settings.RESULTS_DIR)
        res_dir.mkdir(parents=True, exist_ok=True)

        with open(res_dir / "evaluation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        with open(res_dir / "metrics_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print(f"\n[INFO] Saved evaluation results to {res_dir / 'evaluation_results.json'}")
        print(f"[INFO] Saved metrics summary to {res_dir / 'metrics_summary.json'}")

    def _generate_visualizations(self, summary: dict, confusion: dict):
        """Generates evaluation visualization plots."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            sns.set_theme(style="whitegrid")
            fig_dir = Path(settings.RESULTS_DIR)

            # Chart 1: Core Performance Metrics Bar Chart
            plt.figure(figsize=(9, 5))
            metric_names = [
                "Hit Rate@4\n(Retrieval)",
                "MRR\n(Ranking)",
                "Precision@4\n(Relevance)",
                "Citation\nCorrectness (%)",
                "Abstention\nAccuracy (%)"
            ]
            metric_values = [
                summary["hit_rate_at_k"] * 100.0,
                summary["mrr"] * 100.0,
                summary["precision_at_k"] * 100.0,
                summary["citation_correctness_pct"],
                summary["abstention_accuracy_pct"]
            ]
            colors = ["#2563EB", "#3B82F6", "#60A5FA", "#10B981", "#8B5CF6"]

            bars = plt.bar(metric_names, metric_values, color=colors, width=0.55, edgecolor="#1E293B", linewidth=1.2)
            plt.ylim(0, 115)
            plt.ylabel("Score Percentage (%)", fontsize=11, fontweight="bold")
            plt.title("RAG Evaluation Benchmark: Retrieval, Citation & Abstention (N=15)", fontsize=13, fontweight="bold", pad=15)

            for bar in bars:
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 2.5,
                    f"{height:.1f}%",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                    fontsize=10
                )

            plt.tight_layout()
            plt.savefig(fig_dir / "evaluation_metrics.png", dpi=300)
            plt.close()

            # Chart 2: Abstention Confusion Matrix Heatmap
            plt.figure(figsize=(6, 5))
            matrix_data = np.array([
                [confusion["TP"], confusion["FN"]],
                [confusion["FP"], confusion["TN"]]
            ])
            labels = np.array([
                [f"True Answer\n(TP: {confusion['TP']})", f"Improper Abstain\n(FN: {confusion['FN']})"],
                [f"Hallucinated Answer\n(FP: {confusion['FP']})", f"Safe Abstention\n(TN: {confusion['TN']})"]
            ])

            sns.heatmap(
                matrix_data,
                annot=labels,
                fmt="",
                cmap="Blues",
                cbar=False,
                xticklabels=["Answer Expected", "Abstain Expected"],
                yticklabels=["Answered", "Abstained"]
            )
            plt.title("Abstention & Groundedness Decision Matrix", fontsize=12, fontweight="bold", pad=12)
            plt.ylabel("Actual System Action", fontweight="bold")
            plt.xlabel("Ground Truth Expectation", fontweight="bold")
            plt.tight_layout()
            plt.savefig(fig_dir / "confusion_matrix.png", dpi=300)
            plt.close()

            print(f"[INFO] Saved evaluation charts to {fig_dir / 'evaluation_metrics.png'} and confusion_matrix.png")
        except Exception as e:
            print(f"[WARN] Failed to generate matplotlib charts: {e}")
