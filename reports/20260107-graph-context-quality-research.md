# Research: Graph Context Quality in RAG System

**Date:** 2026-01-07
**Scope:** Identifying what makes "good" graph context for demo purposes

---

## Executive Summary

Graph context quality depends on: (1) graph density in Neo4j, (2) question type requiring multi-hop retrieval, and (3) presence of meaningful relationships. Current system has sparse graph, limiting demo effectiveness.

---

## Graph Context Flow Analysis

### Current Implementation (`api/services/tools.py`)

```
retrieve_with_graph_context():
  1. Word-match to find seed nodes (top 20)
  2. Embedding-based reranking (top 5)
  3. Graph expansion via OPTIONAL MATCH (10 related nodes per seed)
  4. Combine: seeds (score=1.0) + related (score=0.8)
```

### Cypher Query for Graph Expansion
```cypher
OPTIONAL MATCH (seed)-[r]-(related:{namespace})
WHERE related.text IS NOT NULL
LIMIT 10
```

Key observations:
- Uses bidirectional relationships (`-[r]-`)
- No relationship type filtering
- Related nodes get 0.8 score multiplier
- Max 10 related nodes per seed

---

## What Makes "Good" Graph Context

### Technical Definition
Good graph context = graph retrieval returns **additional relevant nodes** not found by vector-only.

### Quantitative Criteria
| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `graphContext.length` | >= 3 | At least 3 nodes via graph traversal |
| `graphNodesUsed` | >= 5 | Significant graph contribution |
| Source overlap | < 70% | Graph finds different nodes than vector |
| Relationship diversity | >= 2 types | Multiple relationship types traversed |

### Qualitative Criteria
1. **Multi-hop relevance:** Related nodes add info not in seeds
2. **Relationship semantics:** Traversal follows meaningful paths (MENTIONS, REFERENCES)
3. **Context completeness:** Answer quality improves with graph nodes

---

## Question Types Benefiting from Graph

Based on QA data analysis (`source/data/Research_sheet - QA_new.csv`):

### High Graph Potential
| Type | Category | Why Graph Helps |
|------|----------|-----------------|
| how | compare | Needs entities from multiple sources |
| why | analyze | Requires cause-effect chains |
| what | multi_clause=True | Spans multiple article clauses |
| who | multi_source=True | Cross-document entity resolution |

### Low Graph Potential
| Type | Category | Why Graph Doesn't Help |
|------|----------|------------------------|
| what | factual, single source | Direct answer in one node |
| when | factual | Date lookup, single node |

---

## Current System Limitations

### 1. Sparse Graph (from previous investigation)
- Document upload pipeline incomplete
- Neo4j has ~1,504 nodes but few relationships
- Graph expansion finds 0-2 related nodes (expected: 10-30)

### 2. Namespace Mismatch
- QA data references documents like `16/2023/QH15`
- Neo4j Test_rel_2 namespace may not have these docs
- Need to verify available documents in Neo4j

### 3. Relationship Types Unknown
- Current graph may lack semantic relationships
- MENTIONS, REFERENCES, RELATED_TO may not exist
- Need schema inspection

---

## Demo Question Recommendations

### Category: Compare (Best for Graph)
Questions comparing multiple entities/articles work best because:
- Need info from multiple nodes
- Relationship traversal finds related concepts
- Vector alone may miss comparative context

### Example Structure
```
"So sanh [Entity A] va [Entity B] theo [Law/Article]"
"Lam the nao [Process A] khac [Process B] theo quy dinh"
```

### Category: How/Why (Good for Graph)
Explanatory questions benefit from:
- Cause-effect relationships
- Supporting context nodes
- Cross-references between articles

---

## Actionable Next Steps

1. **Query Neo4j for available docs:**
   ```cypher
   MATCH (n:Test_rel_2)
   RETURN DISTINCT split(n.id, '_')[0] as doc_id
   ```

2. **Filter QA data to match available docs**

3. **Prioritize questions with:**
   - multi_source=True
   - multi_clause=True
   - question_category=compare
   - supporting_context_node array length > 2

4. **Test candidates via /api/rag/compare**

5. **Select final demo set based on actual graph metrics**

---

## Files Referenced

| Path | Purpose |
|------|---------|
| `/api/services/tools.py` | Graph retrieval logic |
| `/api/routers/rag.py` | Compare endpoint |
| `/source/data/Research_sheet - QA_new.csv` | QA dataset |
| `/api/services/qa_questions.py` | Sample questions service |

---

## Conclusion

Best demo questions are **compare** or **multi-source** types from documents actually indexed in Neo4j. Current sparse graph limits effectiveness, but even with few relationships, selecting the right questions can demonstrate graph value.
