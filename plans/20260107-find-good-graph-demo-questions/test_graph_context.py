#!/usr/bin/env python3
"""Test questions and measure graph context quality."""
import requests
import json
from typing import List, Dict

API_URL = "http://localhost:8000/api/rag/compare"

# Test questions from multiple sources
FRONTEND_QUESTIONS = [
    "Thuế suất VAT cho dịch vụ giáo dục là bao nhiêu?",
    "Điều kiện được miễn thuế thu nhập cá nhân?",
    "Chi phí nào được trừ khi tính thuế TNDN?",
]

FALLBACK_QUESTIONS = [
    "Thời hạn nộp thuế GTGT hàng tháng là khi nào?",
    "Cách tính thuế thu nhập doanh nghiệp?",
    "Thu nhập nào được miễn thuế TNDN?",
    "Doanh nghiệp nào được ưu đãi thuế TNDN?",
    "Thuế suất thuế TNDN hiện hành là bao nhiêu?",
]

# Questions from CSV showing good patterns
CSV_QUESTIONS = [
    "Theo Điều 3 Luật Giá, Nhà nước định giá một số mặt hàng như thế nào và các quy định pháp luật nào liên quan đến việc định giá này?",
    "Tại sao các hành vi liên quan đến giá, thẩm định giá bị nghiêm cấm theo quy định pháp luật?",
    "Làm thế nào việc thực hiện bình ổn giá trên phạm vi cả nước khác với việc thực hiện bình ổn giá tại phạm vi địa phương theo quy định tại Điều 20 của Luật này?",
]

ALL_QUESTIONS = FRONTEND_QUESTIONS + FALLBACK_QUESTIONS + CSV_QUESTIONS


def test_question(question: str) -> Dict:
    """Test a single question and extract graph metrics."""
    try:
        response = requests.post(API_URL, json={"question": question}, timeout=30)
        response.raise_for_status()
        data = response.json()

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
            "vector_latency": graph_metrics.get("latencyMs", 0),
            "graph_latency": graph_metrics.get("latencyMs", 0),
            "quality_score": quality_score,
            "vector_sources_count": len(data.get("vector", {}).get("sources", [])),
            "graph_sources_count": len(data.get("graph", {}).get("sources", [])),
        }

        return metrics

    except requests.exceptions.RequestException as e:
        print(f"Error testing question: {e}")
        return {
            "question": question[:120],
            "question_full": question,
            "error": str(e),
            "quality_score": 0
        }


def main():
    """Run all tests and generate report."""
    print(f"Testing {len(ALL_QUESTIONS)} questions...\n")

    results = []
    for i, question in enumerate(ALL_QUESTIONS, 1):
        print(f"[{i}/{len(ALL_QUESTIONS)}] Testing: {question[:80]}...")
        result = test_question(question)
        results.append(result)

        if "error" not in result:
            print(f"  ✓ Quality Score: {result['quality_score']:.1f}, "
                  f"Nodes: {result['graph_nodes_used']}, "
                  f"Context: {result['graph_context_count']}, "
                  f"Hops: {result['graph_hops']}")
        else:
            print(f"  ✗ Error: {result['error']}")
        print()

    # Sort by quality score
    results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

    # Save to JSON
    output_file = "test-results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "tested_count": len(results),
            "high_quality_count": len([r for r in results if r.get("quality_score", 0) >= 6]),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"Results saved to {output_file}")
    print(f"Total tested: {len(results)}")
    print(f"High quality (score >= 6): {len([r for r in results if r.get('quality_score', 0) >= 6])}")
    print(f"\nTop 5 questions by quality:")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. Score: {r.get('quality_score', 0):.1f} - {r['question']}")


if __name__ == "__main__":
    main()
