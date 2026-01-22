# Fix QA Page White Screen Issue

**Created:** 2026-01-21
**Status:** Ready for implementation
**Estimated Effort:** 15 minutes
**Risk Level:** Low

---

## Problem Summary

The QA page shows a white screen because the frontend calls the wrong API endpoint:
- **Current:** `POST /api/rag/query` - returns flat RAG response structure
- **Required:** `POST /api/rag/compare` - returns `CompareResponse` with both vector and graph results

The `/api/rag/query` endpoint returns a streaming or flat response format, but the frontend expects the `CompareResponse` structure with separate `vector` and `graph` results.

---

## Root Cause Analysis

### Current Flow (Broken)
```
QA.tsx → useQAStore.compare() → qaService.compare()
       → POST /api/rag/query
       → Returns flat {answer, sources, metrics}
       → Frontend tries to parse as CompareResponse → FAILS
       → results.vector undefined → White screen
```

### Expected Flow (Fixed)
```
QA.tsx → useQAStore.compare() → qaService.compare()
       → POST /api/rag/compare
       → Returns {questionId, question, vector, graph, timestamp}
       → Frontend renders both panels correctly
```

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `/frontend/src/services/api.ts` | Endpoint + Simplify | Change endpoint, remove manual response mapping |

---

## Implementation Steps

### Step 1: Update `qaService.compare()` in `api.ts`

**Location:** `/Users/hieudinh/Documents/school/GP/Document-Graph-Representation/frontend/src/services/api.ts`
**Lines:** 134-163

**Current Code (BROKEN):**
```typescript
compare: async (question: string): Promise<CompareResponse> => {
  const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, stream: false }),
  });

  const data = await response.json();
  return {
    questionId: `q_${Date.now()}`,
    question,
    vector: {
      answer: data.answer || '',
      sources: data.sources || [],
      metrics: data.metrics || { latencyMs: 0, chunksUsed: 0 },
    },
    graph: {
      answer: data.answer || '',
      sources: data.sources || [],
      cypherQuery: data.cypher_query || '',
      graphContext: data.graph_context || [],
      metrics: {
        ...(data.metrics || { latencyMs: 0, chunksUsed: 0 }),
        graphNodesUsed: data.graph_nodes_used || 0,
        graphHops: data.graph_hops || 0,
      },
    },
    timestamp: new Date().toISOString(),
  };
},
```

**Fixed Code:**
```typescript
compare: async (question: string): Promise<CompareResponse> => {
  const response = await fetchWithErrorHandling(`${API_BASE_URL}/api/rag/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  return await response.json();
},
```

### Why This Works

The `/api/rag/compare` endpoint already returns the exact `CompareResponse` structure:

```typescript
// Backend returns this structure directly:
{
  questionId: string,      // e.g., "q_abc12345"
  question: string,        // The original question
  vector: {
    answer: string,
    sources: SourceItem[],
    metrics: { latencyMs, chunksUsed }
  },
  graph: {
    answer: string,
    sources: SourceItem[],
    cypherQuery: string | null,
    graphContext: Dict[],
    metrics: { latencyMs, chunksUsed, graphNodesUsed, graphHops }
  },
  timestamp: string        // ISO format
}
```

This matches the frontend `CompareResponse` type exactly, so no manual mapping is needed.

---

## Verification Steps

1. **Start backend:** `cd api && uvicorn main:app --reload`
2. **Start frontend:** `cd frontend && pnpm dev`
3. **Test QA page:**
   - Navigate to `/qa`
   - Enter a question
   - Click "Compare"
   - Verify both Vector and Graph panels render with answers
4. **Check network tab:** Confirm request goes to `/api/rag/compare`
5. **Verify metrics display:** Latency, chunks, nodes, hops should show

---

## Rollback Plan

If issues occur, revert to calling `/api/rag/query` with the manual mapping, but ensure proper null checks:

```typescript
compare: async (question: string): Promise<CompareResponse> => {
  // Fallback: call /query and construct response
  // ... original code with better error handling
},
```

---

## Related Files (No Changes Needed)

- `qaStore.ts` - Correctly expects `CompareResponse` from `qaService.compare()`
- `QA.tsx` - Already handles `results.vector` and `results.graph` with optional chaining
- `types/index.ts` - `CompareResponse` type matches backend response
- `api/routers/rag.py` - `/api/rag/compare` endpoint already correct

---

## Notes

- The streaming endpoint (`compareStreaming`) still uses `/api/rag/query` which is correct for streaming SSE responses
- Only the non-streaming `compare()` function needs this fix
- Backend field names use camelCase (e.g., `questionId`, `cypherQuery`) which matches TypeScript conventions
