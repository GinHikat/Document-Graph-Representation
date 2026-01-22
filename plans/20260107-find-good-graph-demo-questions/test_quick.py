#!/usr/bin/env python3
"""Test questions and measure graph context quality - with extended timeout."""
import requests
import json
from typing import List, Dict
import time

API_URL = "http://localhost:8000/api/rag/compare"
TIMEOUT = 120  # 2 minutes per question

# Test just a few questions first
TEST_QUESTIONS = [
    "Thuế suất VAT cho dịch vụ giáo dục là bao nhiêu?",
    "Theo Điều 3 Luật Giá, Nhà nước định giá một số mặt hàng như thế nào và các quy định pháp luật nào liên quan đến việc định giá này?",
]


def test_question(question: str) -> Dict:
    """Test a single question and extract graph metrics."""
    print(f"  Testing: {question[:80]}...")
    start_time = time.time()

    try:
        response = requests.post(API_URL, json={"question": question}, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        elapsed = time.time() - start_time
        print(f"  ✓ Completed in {elapsed:.1f}s")

        graph_context = data.get("graph", {}).get("graphContext", [])
        graph_metrics = data.get("graph", {}).get("metrics", {})

        # Extract relationship types
        relationship_types = list(set(
            ctx.get("relationship", "NONE")
            for ctx in graph_context
        ))

        # Calculate quality score
        graph_context_count = len(graph_context)
        graph_nodes_used = graph_metrics.get("graphNodesUsed", 0)
        graph_hops = graph_metrics.get("graphHops", 0)
        unique_relationships = len(relationship_types)

        quality_score = min(10, (
            graph_context_count * 1.5 +
            graph_nodes_used * 0.5 +
            graph_hops * 2 +
            unique_relationships * 1
        ))

        metrics = {
            "question": question[:120],
            "question_full": question,
            "graph_context_count": graph_context_count,
            "graph_nodes_used": graph_nodes_used,
            "graph_hops": graph_hops,
            "relationship_types": relationship_types,
            "unique_relationships": unique_relationships,
            "vector_answer_len": len(data.get("vector", {}).get("answer", "")),
            "graph_answer_len": len(data.get("graph", {}).get("answer", "")),
            "vector_latency_ms": data.get("vector", {}).get("metrics", {}).get("latencyMs", 0),
            "graph_latency_ms": graph_metrics.get("latencyMs", 0),
            "quality_score": quality_score,
            "vector_sources_count": len(data.get("vector", {}).get("sources", [])),
            "graph_sources_count": len(data.get("graph", {}).get("sources", [])),
            "api_elapsed_seconds": elapsed,
        }

        print(f"  Quality Score: {quality_score:.1f}")
        print(f"  Graph Context: {graph_context_count}, Nodes: {graph_nodes_used}, Hops: {graph_hops}")

        return metrics

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"  ✗ Timeout after {elapsed:.1f}s")
        return {
            "question": question[:120],
            "question_full": question,
            "error": f"Timeout after {elapsed:.1f}s",
            "quality_score": 0
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ✗ Error after {elapsed:.1f}s: {e}")
        return {
            "question": question[:120],
            "question_full": question,
            "error": str(e),
            "quality_score": 0
        }


def main():
    """Run all tests and generate report."""
    print(f"\n{'='*80}")
    print(f"Testing {len(TEST_QUESTIONS)} questions with {TIMEOUT}s timeout...")
    print(f"{'='*80}\n")

    results = []
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}]")
        result = test_question(question)
        results.append(result)
        print()

    # Sort by quality score
    results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

    # Save to JSON
    output_file = "/Users/hieudinh/Documents/my-projects/GP/Document-Graph-Representation/plans/20260107-find-good-graph-demo-questions/test-results-quick.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "tested_count": len(results),
            "high_quality_count": len([r for r in results if r.get("quality_score", 0) >= 6]),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"Results saved to: test-results-quick.json")
    print(f"Total tested: {len(results)}")
    print(f"High quality (score >= 6): {len([r for r in results if r.get('quality_score', 0) >= 6])}")
    print(f"\nTop questions by quality:")
    for i, r in enumerate(results, 1):
        score = r.get('quality_score', 0)
        status = "✓" if score >= 6 else "✗"
        print(f"{i}. {status} Score: {score:.1f} - {r['question']}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
