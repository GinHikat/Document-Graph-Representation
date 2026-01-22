# Plan: Find Demo Questions with Good Graph Context

**Date:** 2026-01-07
**Status:** Ready for Execution
**Goal:** Identify demo questions from QA dataset where graph context significantly improves RAG retrieval

---

## Problem Statement

Current RAG demo lacks impactful examples showing graph-enhanced retrieval superiority over vector-only. Need to find questions that:
1. Benefit from multi-hop graph traversal
2. Show clear graph context contribution
3. Demonstrate relationship-based retrieval value

---

## Key Findings from Research

### Current Data Sources
- **QA Dataset:** `source/data/Research_sheet - QA_new.csv` (36,847 lines, ~36K questions)
- **Fallback Questions:** Hardcoded in `api/services/qa_questions.py` (8 tax-related questions)
- **Example Questions:** Hardcoded in `frontend/src/pages/QA.tsx` (3 questions)
- **Google Sheet:** Tabs: QA_sample, QA_Gen, QA_Crawled, Potential QA Question, gen_100, hybrid

### Graph Context Mechanics (from `api/services/tools.py`)
```
Vector-only: word-match -> top_k results
Graph-enhanced: word-match(20) -> embedding rerank(5) -> graph expansion(10 related nodes)
```

### Good Graph Context Criteria
1. **Multi-clause questions:** Require info from multiple related articles
2. **Cross-reference questions:** Mention other laws/articles (e.g., "theo Dieu 45 cua Luat nay")
3. **Comparative questions:** Compare entities needing relationship traversal
4. **Multi-source questions:** Span multiple documents

### QA Data Fields Available
- `question_type`: what, why, how, when, who, where
- `question_category`: factual, explain, compare, summarize, analyze, clarify
- `multi_clause`: True/False (questions spanning clauses)
- `multi_source`: True/False (questions spanning documents)
- `cognitive`: True/False (requires reasoning)
- `supporting_context_node`: Array of context nodes needed

---

## Execution Plan

### Phase 1: Extract and Analyze QA Data (1 hour)
- Parse CSV file, filter by `multi_clause=True` or `multi_source=True`
- Group by `question_category` and `question_type`
- Output: Candidate list ranked by potential graph benefit

### Phase 2: Test Graph Context Retrieval (2 hours)
- For each candidate, call `/api/rag/compare`
- Measure: `graphContext.length`, `graphNodesUsed`, `graphHops`
- Compare vector vs graph answer quality
- Output: Ranked list by graph improvement

### Phase 3: Select Final Demo Questions (30 min)
- Select 5-10 questions across categories
- Verify supporting_context_node matches graph context
- Document expected vs actual graph traversal

---

## Files

| File | Purpose |
|------|---------|
| plan.md | This overview |
| phase-1-data-analysis.md | Detailed data extraction steps |
| phase-2-graph-testing.md | Testing methodology and metrics |
| demo-questions-final.md | Selected demo questions list |

---

## Success Metrics

1. **Graph Nodes Used > 3** for selected questions
2. **Graph Hops >= 1** showing actual traversal
3. **Vector vs Graph answer difference** is visible
4. **At least 5 questions** with clear graph superiority

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Neo4j has sparse graph | Focus on existing indexed docs (Test_rel_2 namespace) |
| QA data docs not in Neo4j | Cross-reference with available docs |
| Embedding service failure | Fallback to word-match only |

---

## Unresolved Questions

1. Which documents are actually indexed in Test_rel_2 namespace?
2. What relationship types exist in current graph?
3. How many nodes have valid embeddings?
