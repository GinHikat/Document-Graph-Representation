# Phase 2: Graph Context Testing

**Goal:** Empirically test candidate questions and measure graph context quality

---

## Testing Methodology

### API Endpoint
```
POST /api/rag/compare
Body: { "question": "..." }
```

### Response Structure
```json
{
  "questionId": "q_abc123",
  "question": "...",
  "vector": {
    "answer": "...",
    "sources": [...],
    "metrics": { "latencyMs": 500, "chunksUsed": 5 }
  },
  "graph": {
    "answer": "...",
    "sources": [...],
    "cypherQuery": "hybrid_word_match_embedding_graph",
    "graphContext": [
      { "node_id": "...", "relationship": "MENTIONS", "text_preview": "..." }
    ],
    "metrics": {
      "latencyMs": 800,
      "chunksUsed": 5,
      "graphNodesUsed": 8,
      "graphHops": 1
    }
  }
}
```

---

## Quality Metrics

### Primary Metrics (Higher = Better Graph Impact)
| Metric | Formula | Threshold |
|--------|---------|-----------|
| Graph Context Count | `len(graph.graphContext)` | >= 3 |
| Graph Nodes Used | `graph.metrics.graphNodesUsed` | >= 5 |
| Graph Hops | `graph.metrics.graphHops` | >= 1 |
| Unique Relationships | `count(distinct relationship types)` | >= 2 |

### Secondary Metrics
| Metric | Formula | Threshold |
|--------|---------|-----------|
| Answer Difference | `similarity(vector.answer, graph.answer)` | < 0.95 |
| Latency Overhead | `graph.latencyMs / vector.latencyMs` | < 2.0 |
| Source Overlap | `overlap(vector.sources, graph.sources)` | < 80% |

---

## Testing Script Template

```python
import requests
import json

API_URL = "http://localhost:8000/api/rag/compare"

def test_question(question: str) -> dict:
    response = requests.post(API_URL, json={"question": question})
    data = response.json()

    metrics = {
        "question_id": data["questionId"],
        "question": question[:100],

        # Graph metrics
        "graph_context_count": len(data["graph"]["graphContext"]),
        "graph_nodes_used": data["graph"]["metrics"].get("graphNodesUsed", 0),
        "graph_hops": data["graph"]["metrics"].get("graphHops", 0),

        # Relationship types
        "relationship_types": list(set(
            ctx.get("relationship", "NONE")
            for ctx in data["graph"]["graphContext"]
        )),

        # Answer comparison
        "vector_answer_len": len(data["vector"]["answer"]),
        "graph_answer_len": len(data["graph"]["answer"]),

        # Latency
        "vector_latency": data["vector"]["metrics"]["latencyMs"],
        "graph_latency": data["graph"]["metrics"]["latencyMs"],
    }

    # Quality score (0-10)
    metrics["quality_score"] = min(10, (
        metrics["graph_context_count"] * 1.5 +
        metrics["graph_nodes_used"] * 0.5 +
        metrics["graph_hops"] * 2 +
        len(metrics["relationship_types"]) * 1
    ))

    return metrics

# Test all candidates
results = []
for question in candidates:
    result = test_question(question)
    results.append(result)

# Sort by quality score
results.sort(key=lambda x: x["quality_score"], reverse=True)
```

---

## Expected Output

File: `test-results.json`
```json
{
  "tested_count": 50,
  "high_quality_count": 12,
  "results": [
    {
      "question_id": "q_abc123",
      "question": "Lam the nao...",
      "quality_score": 8.5,
      "graph_context_count": 5,
      "graph_nodes_used": 10,
      "relationship_types": ["MENTIONS", "REFERENCES", "RELATED_TO"]
    }
  ]
}
```

---

## Ranking Criteria for Final Selection

1. **Quality Score >= 6**: Indicates strong graph contribution
2. **Diverse Categories**: Select across factual, compare, explain types
3. **Different Documents**: Cover multiple law documents
4. **Clear Answer Difference**: Vector vs Graph shows visible improvement
