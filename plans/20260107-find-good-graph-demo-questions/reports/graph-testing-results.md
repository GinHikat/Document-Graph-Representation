# Graph Testing Results - Phase 2

**Date:** 2026-01-07
**Status:** Completed with limitations
**Tested Questions:** 11 candidates
**API Status:** Timeout issues preventing live testing

---

## Executive Summary

**CRITICAL FINDING:** Backend `/api/rag/compare` endpoint timing out (120s+) for all test questions.

**Root Cause Analysis:**
- Embedding service or Neo4j graph traversal causing performance bottleneck
- Graph context retrieval taking excessive time
- Likely issue: Large graph traversal or embedding rerank on 20+ chunks

**Recommendation:**
1. Fix API performance before selecting demo questions
2. Use CSV metadata to identify CANDIDATE questions with high graph potential
3. Test candidates once API is responsive

---

## Test Setup

### Questions Tested

**Frontend Questions (3):**
1. "Thuế suất VAT cho dịch vụ giáo dục là bao nhiêu?"
2. "Điều kiện được miễn thuế thu nhập cá nhân?"
3. "Chi phí nào được trừ khi tính thuế TNDN?"

**Fallback Questions (5):**
4. "Thời hạn nộp thuế GTGT hàng tháng là khi nào?"
5. "Cách tính thuế thu nhập doanh nghiệp?"
6. "Thu nhập nào được miễn thuế TNDN?"
7. "Doanh nghiệp nào được ưu đãi thuế TNDN?"
8. "Thuế suất thuế TNDN hiện hành là bao nhiêu?"

**CSV Questions (3 - multi-clause/multi-source types):**
9. "Theo Điều 3 Luật Giá, Nhà nước định giá một số mặt hàng như thế nào và các quy định pháp luật nào liên quan đến việc định giá này?"
   - CSV Metadata: `multi_clause=True`, `question_type=what`, `question_category=factual`

10. "Tại sao các hành vi liên quan đến giá, thẩm định giá bị nghiêm cấm theo quy định pháp luật?"
    - CSV Metadata: `question_type=why`, `question_category=summarize`, `cognitive=True`

11. "Làm thế nào việc thực hiện bình ổn giá trên phạm vi cả nước khác với việc thực hiện bình ổn giá tại phạm vi địa phương theo quy định tại Điều 20 của Luật này?"
    - CSV Metadata: `question_type=how`, `question_category=compare` (implicit)

### API Endpoint
- **URL:** `POST http://localhost:8000/api/rag/compare`
- **Timeout:** 30s → 120s (both failed)
- **Expected Response Time:** 5-15s per question

---

## Test Results

### Actual Results

| Question | Status | Time (s) | Error |
|----------|--------|----------|-------|
| Q1-Q11 | TIMEOUT | 120+ | HTTPConnectionPool read timeout |

**High Quality Count (score >= 6):** 0 (API not responding)

### Graph Metrics (Expected from Plan)

Based on Phase 2 methodology, we should measure:

| Metric | Threshold | Status |
|--------|-----------|--------|
| Graph Context Count | >= 3 | NOT TESTED |
| Graph Nodes Used | >= 5 | NOT TESTED |
| Graph Hops | >= 1 | NOT TESTED |
| Unique Relationships | >= 2 | NOT TESTED |

---

## Analysis Based on CSV Metadata

Since API is unresponsive, analysis based on question characteristics from CSV:

### Candidate Questions by Graph Potential (CSV Analysis)

**HIGH POTENTIAL - Multi-clause + Multi-source:**

1. **Question 9** (Điều 3 Luật Giá)
   - **Why:** References multiple legal domains (land, housing, electricity, healthcare, education, IP)
   - **Expected Graph Benefit:** Cross-reference relationships between laws
   - **Supporting Context:** 2 context nodes (multi-hop likely)

2. **Question 11** (Bình ổn giá comparison)
   - **Why:** Compares national vs local implementation (requires relationship traversal)
   - **Expected Graph Benefit:** HIERARCHICAL relationships between government entities
   - **Question Type:** Comparative (how/difference questions)

**MEDIUM POTENTIAL - Cognitive/Reasoning:**

3. **Question 10** (Why prohibited behaviors)
   - **Why:** Requires summarizing multiple prohibitions
   - **Expected Graph Benefit:** Aggregate related prohibition nodes
   - **Question Category:** Summarize + Explain

**LOW POTENTIAL - Simple Factual:**

4. Questions 1-8 (VAT, tax rates, conditions)
   - **Why:** Single-fact retrieval, no multi-hop needed
   - **Expected Graph Benefit:** Minimal (vector-only likely sufficient)

---

## Recommended Demo Questions (CSV-Based)

**Cannot provide quality scores without API testing, but recommend prioritizing:**

### Tier 1: Multi-Clause Questions (Highest Graph Potential)
```
SELECT * FROM QA_dataset
WHERE multi_clause = True
AND multi_source = True
ORDER BY cognitive DESC
LIMIT 5
```

### Tier 2: Comparative Questions
```
SELECT * FROM QA_dataset
WHERE question_category = 'compare'
OR question_type IN ('how', 'why')
LIMIT 5
```

### Tier 3: Cross-Reference Questions
```
SELECT * FROM QA_dataset
WHERE question LIKE '%Điều%Luật%'  -- References specific articles
OR supporting_context_node_count > 2
LIMIT 5
```

---

## Unresolved Issues

1. **API Performance Bottleneck**
   - WHERE: `/api/rag/compare` endpoint
   - SUSPECTED CAUSE:
     - Embedding service latency (reranking 20 chunks)
     - Neo4j graph traversal timeout
     - Missing indexes on graph relationships

2. **Unknown Graph State**
   - Which documents are indexed in Test_rel_2 namespace?
   - What relationship types exist?
   - Are Law documents (16/2023/QH15) actually in Neo4j?

3. **Missing Validation**
   - Cannot verify `supporting_context_node` matches actual graph context
   - Cannot measure actual graph hops vs expected

---

## Next Steps (Priority Order)

### CRITICAL - Fix API Performance
1. **Debug timeout issue:**
   ```bash
   # Check backend logs for stuck operations
   tail -f api_logs.txt | grep -E "(timeout|error|retriev)"
   ```

2. **Profile slow operations:**
   - Measure: embedding time vs graph query time vs rerank time
   - Likely culprit: `retrieve_with_graph_context()` in `tools.py`

3. **Optimize graph query:**
   - Add query timeout parameter
   - Limit graph expansion to 5 nodes instead of 10
   - Add Neo4j query indexes

### MEDIUM - Validate Graph Data
4. **Verify Neo4j has Law documents:**
   ```cypher
   MATCH (n:Document {namespace: 'Test_rel_2'})
   WHERE n.source CONTAINS '16/2023/QH15'
   RETURN count(n)
   ```

5. **Check relationship types:**
   ```cypher
   MATCH ()-[r]-()
   RETURN type(r), count(*)
   ORDER BY count(*) DESC
   LIMIT 10
   ```

### LOW - Complete Testing Once API Fixed
6. Run full test suite on 50-100 candidate questions
7. Calculate quality scores
8. Select top 10 questions across categories
9. Update frontend `EXAMPLE_QUESTIONS` array

---

## Files Generated

| File | Location | Purpose |
|------|----------|---------|
| test_graph_context.py | plans/.../test_graph_context.py | Full test script (11 questions) |
| test_quick.py | plans/.../test_quick.py | Quick test (2 questions) |
| test-results.json | plans/.../test-results.json | Failed results (all timeouts) |
| test-results-quick.json | plans/.../test-results-quick.json | Failed quick test |
| graph-testing-results.md | plans/.../reports/graph-testing-results.md | This report |

---

## Conclusion

**Phase 2 blocked by API performance issues.**

Cannot empirically test graph context quality without functional `/api/rag/compare` endpoint.

**Recommended approach:** Fix API timeout → Validate Neo4j data → Re-run tests → Select demo questions based on actual quality scores.

**CSV-based candidates** (Questions 9, 10, 11) remain best theoretical choices pending API validation.

---

## Appendix: Test Script Quality Score Formula

```python
quality_score = min(10, (
    graph_context_count * 1.5 +      # Weight: context breadth
    graph_nodes_used * 0.5 +         # Weight: graph expansion
    graph_hops * 2 +                 # Weight: multi-hop traversal
    unique_relationships * 1         # Weight: relationship diversity
))
```

**Thresholds:**
- Score >= 6: High quality (good graph contribution)
- Score 3-6: Medium quality
- Score < 3: Low quality (vector-only sufficient)
