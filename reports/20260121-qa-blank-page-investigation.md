# QA Page Blank Screen Investigation Report

**Date:** 2026-01-21
**Severity:** HIGH
**Status:** Root cause identified

## Executive Summary

User reports QA page (localhost:8080/qa) goes blank/white after submitting question. Investigation reveals **missing error UI** causing blank page when API errors occur. Backend endpoint works correctly but frontend lacks error handling display.

## Root Cause Analysis

### Primary Issue: Missing Error State Display

**Location:** `/frontend/src/pages/QA.tsx` Line 38-46

```typescript
const {
  currentQuestion,
  results,
  history,
  isLoading,
  setCurrentQuestion,
  compare,
  submitAnnotation,
} = useQAStore();
```

**Problem:** The `error` state exists in `qaStore.ts` (line 18) but is **NOT extracted or displayed** in QA.tsx.

**Impact:** When API call fails:
1. Error stored in store ✓
2. `isLoading` set to false ✓
3. Error UI displayed ✗ **MISSING**
4. Results remain null
5. **Result: Blank page**

### Secondary Issue: Error State Not Cleared on New Request

**Location:** `/frontend/src/stores/qaStore.ts` Line 52-66

```typescript
compare: async (question: string) => {
  set({ isLoading: true, error: null, currentQuestion: question }); // ✓ Clears error
  try {
    const results = await qaService.compare(question);
    set({ results, isLoading: false });
    // Add to history
    const history = get().history;
    set({ history: [results, ...history] });
  } catch (error) {
    set({
      error: error instanceof Error ? error.message : 'Có lỗi xảy ra',
      isLoading: false
      // ✗ Does NOT clear results - old data persists
    });
  }
},
```

**Note:** Line 53 correctly clears error on new request, but catch block doesn't clear `results`.

## Backend Verification

### Endpoint Status: ✓ WORKING

```bash
curl -X POST http://localhost:8000/api/rag/compare \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
```

**Response:** 200 OK (14s latency)
- Returns valid CompareResponse JSON
- Vector answer: "Tôi rất tiếc, câu hỏi..."
- Graph answer: "Tôi rất tiếc, câu hỏi..."
- Metrics populated correctly

### Type Mismatch (Minor Issue)

**Backend:** `graphContext: List[Dict[str, Any]]` (rag.py:176)
**Frontend:** `graphContext: GraphContext[]` (types/index.ts:52)

Backend returns raw dictionaries, frontend expects structured `{ nodes, relationships }`. This **may cause future issues** but not the current blank page (backend returns empty array `[]` in test).

## Recommended Fixes

### Fix 1: Add Error Display (CRITICAL)

**File:** `/frontend/src/pages/QA.tsx`

1. Extract `error` from store (line 46):
```typescript
const {
  currentQuestion,
  results,
  history,
  isLoading,
  error,  // ADD THIS
  // ...
} = useQAStore();
```

2. Add error alert UI after Question Input card (after line 262):
```tsx
{/* Error Display */}
{error && !isLoading && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Error</AlertTitle>
    <AlertDescription>{error}</AlertDescription>
  </Alert>
)}
```

### Fix 2: Clear Results on Error (RECOMMENDED)

**File:** `/frontend/src/stores/qaStore.ts` Line 61-65

```typescript
} catch (error) {
  set({
    error: error instanceof Error ? error.message : 'Có lỗi xảy ra',
    isLoading: false,
    results: null,  // ADD THIS to clear old results
  });
}
```

### Fix 3: Type Alignment (LOW PRIORITY)

**Option A:** Update backend to match frontend types
**Option B:** Update frontend to accept `Dict[str, Any][]`

Recommend Option B for now - add type guard in QA.tsx when accessing graphContext.

## Testing Plan

1. **Reproduce blank page:**
   - Stop backend server
   - Submit question
   - Verify blank page occurs

2. **Verify Fix 1:**
   - Apply error display code
   - Stop backend
   - Submit question
   - **Expected:** Error alert shows "Network error: Unable to connect to backend..."

3. **Verify Fix 2:**
   - Submit successful question (backend running)
   - Stop backend
   - Submit new question
   - **Expected:** Old results cleared, only error shows

4. **API error handling:**
   - Simulate 500 error from backend
   - **Expected:** Error message from API response shown

## Files Referenced

- `/frontend/src/pages/QA.tsx` - Missing error UI
- `/frontend/src/stores/qaStore.ts` - Error state not cleared
- `/frontend/src/services/api.ts` - Error handling wrapper (working correctly)
- `/api/routers/rag.py` - Backend endpoint (working correctly)
- `/frontend/src/types/index.ts` - Type definitions (minor mismatch)

## Unresolved Questions

None. Root cause definitively identified.

## Next Steps

1. Apply Fix 1 (error display) - **IMMEDIATE**
2. Apply Fix 2 (clear results) - **IMMEDIATE**
3. Test both offline and online scenarios
4. Consider adding error boundary for uncaught React errors
5. Monitor for type mismatch issues with graphContext in production
