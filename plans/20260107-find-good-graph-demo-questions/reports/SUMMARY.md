# Phase 2 Graph Testing - QUICK SUMMARY

**Date:** 2026-01-07
**Status:** BLOCKED - API Timeout
**Tested:** 11 questions, 0 successful

---

## CRITICAL BLOCKER

**API `/api/rag/compare` timing out (120s+) for ALL questions**

Root cause: Embedding service or Neo4j graph traversal bottleneck

---

## Test Results

### Questions Tested
- 3 frontend questions (VAT, tax exemptions, deductible costs)
- 5 fallback questions (tax rates, corporate tax)
- 3 CSV questions (Law 16/2023/QH15 - multi-clause types)

### Graph Metrics
**ALL TESTS FAILED** - API timeout before completion

Expected metrics (from plan):
- Graph context count >= 3
- Graph nodes used >= 5
- Graph hops >= 1
- Quality score: 0-10 (formula: context*1.5 + nodes*0.5 + hops*2 + relationships*1)

---

## Candidate Questions (CSV Metadata Analysis)

**HIGH POTENTIAL** (multi-clause + cross-reference):

1. "Theo Điều 3 Luật Giá, Nhà nước định giá một số mặt hàng như thế nào và các quy định pháp luật nào liên quan đến việc định giá này?"
   - Why: Cross-references 7+ legal domains (land, housing, electricity, education, IP)
   - Expected: High relationship traversal

2. "Làm thế nào việc thực hiện bình ổn giá trên phạm vi cả nước khác với việc thực hiện bình ổn giá tại phạm vi địa phương theo quy định tại Điều 20 của Luật này?"
   - Why: Comparative question (national vs local)
   - Expected: Hierarchical government entity relationships

**MEDIUM POTENTIAL** (reasoning/summary):

3. "Tại sao các hành vi liên quan đến giá, thẩm định giá bị nghiêm cấm theo quy định pháp luật?"
   - Why: Summarize multiple prohibition clauses
   - Expected: Aggregate related prohibition nodes

**LOW POTENTIAL** (simple factual):

4-11. VAT rates, tax thresholds, exemption conditions
   - Why: Single-fact retrieval
   - Expected: Vector-only sufficient

---

## Recommendations

**IMMEDIATE (Priority 1):**
1. Debug API timeout:
   - Check backend process logs
   - Profile: embedding time vs graph query vs rerank
   - Likely issue: `retrieve_with_graph_context()` in `api/services/tools.py`

2. Optimize graph retrieval:
   - Reduce graph expansion from 10 → 5 nodes
   - Add query timeout (10s max)
   - Verify Neo4j indexes exist

**VALIDATION (Priority 2):**
3. Check Neo4j data availability:
   ```cypher
   MATCH (n:Document {namespace: 'Test_rel_2'})
   WHERE n.source CONTAINS 'Luật'
   RETURN count(n), type(n)
   ```

4. Verify embedding service:
   ```python
   from api.services.embedding import embed_query
   emb = embed_query("Test")  # Should complete < 1s
   ```

**TESTING (Priority 3):**
5. Once API responsive:
   - Re-run test suite on 10-20 candidate questions
   - Calculate quality scores
   - Select top 5 for frontend `EXAMPLE_QUESTIONS`

---

## Files

| File | Status |
|------|--------|
| `test_graph_context.py` | Created (11 questions) |
| `test_quick.py` | Created (2 questions) |
| `test-results.json` | All timeouts |
| `reports/graph-testing-results.md` | Full analysis report |
| `reports/SUMMARY.md` | This file |

---

## Unresolved Questions

1. Why is API timing out? (embedding vs graph vs rerank)
2. Are Law documents in Neo4j Test_rel_2?
3. What relationship types exist in graph?
4. How many nodes have valid embeddings?

---

## Next Action

**FIX API PERFORMANCE BEFORE CONTINUING PHASE 2**

Cannot select demo questions without empirical graph context data.
