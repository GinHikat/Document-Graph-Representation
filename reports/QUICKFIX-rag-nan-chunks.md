# Quick Fix Guide - RAG "NaN chunks" Issue

## Problem
Q&A returns "không có thông tin" + "NaN chunks" for question about Law 16/2023/QH15

## Root Cause
**Document 16/2023/QH15 does NOT exist in database**

## Evidence
```bash
# Test shows NO documents with ID containing "16/2023"
$ curl POST http://localhost:8000/api/rag/retrieve \
  -d '{"prompt": "16/2023 Điều 7", "top_k": 10}'

# Returns documents: 67/2025/QH15, 82/2025/NĐ-CP, 59/2020/QH14
# Missing: 16/2023/QH15 ❌
```

## System Status: ✓ HEALTHY

| Component | Status | Evidence |
|-----------|--------|----------|
| Neo4j | ✓ Working | 1,504 nodes connected |
| Retrieval | ✓ Working | Returns valid chunks with scores |
| Reranking | ✓ Working | BGE reranker produces valid scores |
| LLM | ✓ Working | Correctly says "no info" when data missing |

## Fixes Required

### 1. Add Missing Document (HIGH PRIORITY)
```
Action: Ingest Luật 16/2023/QH15 (Luật Giá) into Neo4j
Team: Data Ingestion
Timeline: ASAP
```

### 2. Fix UI "NaN" Display (MEDIUM PRIORITY)
```typescript
// frontend/src/pages/QA.tsx or ResultCard component
// Replace NaN with 0 or "N/A"

const displayScore = isNaN(score) ? 0 : score;
const displayChunks = isNaN(chunksUsed) ? 0 : chunksUsed;
```

## Verification

After adding document:
```bash
# Should return nodes from 16/2023/QH15
curl POST http://localhost:8000/api/rag/retrieve \
  -d '{"prompt": "hành vi nghiêm cấm giá thẩm định", "top_k": 5}'
```

## Why It Fails Now

User asks about **price appraisal prohibitions** (Law 16/2023)
→ System retrieves **asset valuation** chunks (Law 59/2020)
→ Different legal context, same keywords "thẩm định giá"
→ LLM correctly says "không có thông tin"
→ UI incorrectly shows "NaN" (should show "0" or "No data")

---

**Full Analysis:** See `/reports/20250107-rag-retrieval-root-cause-analysis.md`
