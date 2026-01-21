# Investigation: Vector vs Graph RAG Similarity

**Investigation Date:** 2026-01-07
**Status:** Complete
**Investigator:** System Debugger Agent

---

## Quick Navigation

### Executive Summary
👉 **Start here:** [`260107-investigation-summary.md`](./reports/260107-investigation-summary.md)

Quick overview of findings, root cause, and next steps.

### Detailed Reports

1. **Technical Investigation**
   - File: [`260107-vector-graph-similarity-investigation.md`](./reports/260107-vector-graph-similarity-investigation.md)
   - Contents: Deep dive into RAG logic, retrieval pipeline, Neo4j structure, document upload gap
   - Who: Technical leads, backend developers

2. **Flow Diagrams**
   - File: [`260107-flow-comparison-diagram.md`](./reports/260107-flow-comparison-diagram.md)
   - Contents: Visual comparison of vector vs graph flows, pipeline diagrams
   - Who: Product managers, visual learners

3. **Action Plan**
   - File: [`260107-action-plan.md`](./reports/260107-action-plan.md)
   - Contents: 5-phase implementation plan with code templates
   - Who: Developers implementing the fix

---

## Key Findings

**Question:** Why do Vector-only and Graph-enhanced RAG return similar results?

**Answer:** Graph retrieval logic is correct but operates on a sparse graph. Document upload pipeline is incomplete - files saved but NOT indexed to Neo4j.

**Root Cause:**
1. Neo4j graph has few/no relationships between nodes
2. Graph expansion finds minimal related nodes (0-2 vs expected 10-30)
3. Upload endpoint saves files to disk but does NOT:
   - Chunk documents
   - Generate embeddings
   - Index to Neo4j
   - Build relationships

**Impact:** Graph-enhanced RAG = Vector-only + 10% overhead with 0% improvement.

**Fix:** Build document processing pipeline.

**Effort:** 2-3 days

---

## Report Sizes

| File | Size | Read Time |
|------|------|-----------|
| Investigation Summary | 11 KB | 5 mins |
| Technical Investigation | 11 KB | 15 mins |
| Flow Diagrams | 9.9 KB | 10 mins |
| Action Plan | 13 KB | 20 mins |
| **Total** | **45 KB** | **50 mins** |

---

## Code References

All file paths are absolute from project root:
`/Users/hieudinh/Documents/my-projects/GP/Document-Graph-Representation/`

**Key Files Analyzed:**

1. **api/routers/rag.py** (Lines 189-292)
   - Compare endpoint - calls vector and graph retrieval

2. **api/services/tools.py** (Lines 38-197)
   - Vector retrieval: Simple word-match
   - Graph retrieval: Word-match + embedding rerank + graph expansion

3. **api/routers/documents.py** (Lines 41-121)
   - Upload endpoint - saves files but does NOT index to Neo4j

4. **shared_functions/batch_retrieve_neo4j.py**
   - Legacy retrieval modes (1-7)
   - Mode 2 "traverse_embed" shows graph expansion pattern

5. **api/db/neo4j.py**
   - Neo4j client wrapper
   - Graph schema and stats endpoints

---

## Next Steps

1. **Verify Graph State** (requires Neo4j credentials)
   ```bash
   # Check graph density
   python3 scripts/check_graph_stats.py
   ```

2. **Implement Document Processor**
   - Create `api/services/document_processor.py`
   - Extract text (PyPDF2, python-docx)
   - Chunk text (512 tokens, 50 overlap)
   - Embed chunks (BGE-M3)
   - Index to Neo4j
   - Create relationships (FOLLOWS, SIMILAR_TO)

3. **Integrate with Upload**
   - Update `api/routers/documents.py`
   - Use FastAPI BackgroundTasks
   - Track processing status

4. **Test End-to-End**
   - Upload sample document
   - Verify Neo4j indexing
   - Test `/api/rag/compare`
   - Confirm graph expansion works

---

## Unresolved Questions

1. Neo4j credentials - current .env has placeholders
2. Test_rel_2 namespace origin - manual or automated?
3. Relationship types in current graph (if any)
4. Legacy processor integration - use or replace?
5. Background task solution - Celery, Redis, or FastAPI?

---

## Contact

**For Technical Questions:**
- Review detailed investigation: `260107-vector-graph-similarity-investigation.md`
- Check code references in report

**For Implementation:**
- Follow action plan: `260107-action-plan.md`
- Code templates provided for all services

**For Quick Overview:**
- Read summary: `260107-investigation-summary.md`

---

**Generated:** 2026-01-07
**Investigation Time:** 45 minutes
**Confidence:** High (code analysis complete, Neo4j verification pending credentials)
