"""
Automated validation of the 15 Standard Benchmark Evaluation Questions.
Verifies citation correctness, hit rate, and 100% safe abstention on out-of-scope queries.
"""

import pytest
from src.rag_pipeline import RAGPipeline
from src.evaluator import BenchmarkEvaluator, BENCHMARK_15_QUESTIONS


@pytest.fixture(scope="module")
def benchmark_results():
    pipeline = RAGPipeline()
    pipeline.build_or_load_index(force_reindex=False)
    evaluator = BenchmarkEvaluator(pipeline)
    return evaluator.run_benchmark(BENCHMARK_15_QUESTIONS)


def test_15_questions_total_count(benchmark_results):
    assert len(benchmark_results["results"]) == 15
    summary = benchmark_results["summary"]
    assert summary["total_questions"] == 15
    assert summary["answerable_questions"] == 12
    assert summary["unanswerable_questions"] == 3


def test_abstention_accuracy_on_unanswerable_questions(benchmark_results):
    results = benchmark_results["results"]
    unanswerable = [r for r in results if r["should_abstain"]]
    assert len(unanswerable) == 3

    # All unanswerable questions (Q13, Q14, Q15) MUST abstain cleanly
    for r in unanswerable:
        assert r["is_abstained"] is True, f"Failed abstention on Q{r['id']}: {r['question']}"
        assert r["abstention_status"] == "CORRECT_ABSTENTION"

    confusion = benchmark_results["summary"]["confusion_matrix"]
    assert confusion["FP"] == 0, "No false positive / hallucinated answers allowed"
    assert confusion["TN"] == 3


def test_retrieval_hit_rate_on_answerable_questions(benchmark_results):
    summary = benchmark_results["summary"]
    # We expect MRR >= 0.85 and Hit Rate >= 0.90
    assert summary["hit_rate_at_k"] >= 0.90
    assert summary["mrr"] >= 0.85
    assert summary["citation_correctness_pct"] >= 90.0


def test_latency_performance(benchmark_results):
    latency = benchmark_results["summary"]["latency_stats"]
    # Median latency must be under 500ms on CPU
    assert latency["median_ms"] < 500.0
