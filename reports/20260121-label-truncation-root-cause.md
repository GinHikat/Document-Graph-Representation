# Root Cause Analysis: Label Truncation in NodeDetailsPanel

**Date:** 2026-01-21
**Issue:** Labels showing truncated text like "5. Cổ tức là khoản lợi nhuận ròng được trả cho..." despite UI code implementing expand/collapse

---

## Executive Summary

**Root Cause:** Data truncation at API source layer, not UI rendering issue.

**Impact:** All node labels >50 chars truncated to 47 chars + "..." before reaching frontend, making expand/collapse UI logic ineffective.

**Location:** `/api/db/neo4j.py:66-67` and `80-82`

---

## Technical Analysis

### 1. Data Flow Investigation

Traced data flow from Neo4j → API → Frontend:

```
Neo4j (full text)
  → api/db/neo4j.py::get_test_rel_2_graph() [TRUNCATION HERE]
  → api/routers/graph.py::get_graph_nodes()
  → Frontend GraphVisualization
  → NodeDetailsPanel [ALREADY TRUNCATED]
```

### 2. Root Cause Code

**File:** `/Users/hieudinh/Documents/school/GP/Document-Graph-Representation/api/db/neo4j.py`

**Lines 64-67 (source node):**
```python
label = n.get('text', n.get('id', n.get('name', 'Unknown')))
if isinstance(label, str) and len(label) > 50:
    label = label[:47] + "..."  # TRUNCATION HAPPENS HERE
```

**Lines 80-82 (target node):**
```python
label = m.get('text', m.get('id', m.get('name', 'Unknown')))
if isinstance(label, str) and len(label) > 50:
    label = label[:47] + "..."  # TRUNCATION HAPPENS HERE
```

### 3. Why UI Code Didn't Work

**Frontend code analysis** (`NodeDetailsPanel.tsx:198-225`):
- Implements expand/collapse logic correctly
- Uses `needsExpand(node.label)` to check if text >80 chars
- Shows "line-clamp-2" with blur gradient + "Xem thêm" button

**Problem:**
- `node.label` received is already "5. Cổ tức là khoản lợi nhuận ròng được trả cho..." (50 chars)
- Frontend checks `node.label.length > 80` → FALSE (50 < 80)
- Expand/collapse never triggers because data already truncated

### 4. Evidence

**API Layer (neo4j.py:66-67):**
```python
# Hard-coded 50 char limit
if isinstance(label, str) and len(label) > 50:
    label = label[:47] + "..."
```

**Frontend Layer (NodeDetailsPanel.tsx:200):**
```tsx
{/* Only shows expand if >80 chars, but data already <50 */}
{needsExpand(node.label) && !isExpanded('label') ? (
  <p className="font-medium text-base leading-relaxed break-words line-clamp-2">
    {node.label}
  </p>
```

**Data Storage:**
- Full text stored in `node.properties.text` ✓
- Truncated text in `node.label` ✗
- Frontend only displays `node.label` in title section

---

## Solution Strategies

### Option A: Remove API Truncation (Recommended)
**Change:** Remove lines 66-67, 81-82 in `api/db/neo4j.py`
**Pros:**
- Frontend expand/collapse works as designed
- Users see full text
- No data loss
**Cons:**
- Larger payload for graph visualization (manageable)
- Graph node tooltips might show long text (can be handled in viz component)

### Option B: Frontend Fallback
**Change:** Use `node.properties.text` if `node.label` ends with "..."
**Pros:**
- Quick fix without backend changes
**Cons:**
- Hacky workaround
- Doesn't fix root cause
- Label still shows truncated in graph visualization

### Option C: Dual-Field Approach
**Change:** Backend provides both `label` (short) and `fullLabel` (full)
**Pros:**
- Graph viz uses short labels
- Detail panel uses full labels
- Clean separation of concerns
**Cons:**
- Data duplication
- Requires schema change

---

## Recommended Fix

**Remove truncation at API layer** (Option A):

```python
# BEFORE (lines 64-68):
label = n.get('text', n.get('id', n.get('name', 'Unknown')))
if isinstance(label, str) and len(label) > 50:
    label = label[:47] + "..."

# AFTER:
label = n.get('text', n.get('id', n.get('name', 'Unknown')))
```

Apply same change to lines 80-82 for target node.

---

## Verification Steps

1. Remove truncation in `api/db/neo4j.py`
2. Restart backend server
3. Reload graph in frontend
4. Click node with long text
5. Verify:
   - Label shows >50 chars
   - "Xem thêm" button appears
   - Expand/collapse works
   - Full text visible when expanded

---

## Additional Findings

### CSS Truncation Issues Found

**File:** `NodeDetailsPanel.tsx`

**Line 200:** Label with `line-clamp-2` when collapsed ✓ (intended)
**Line 271:** Properties with `line-clamp-3` for long text ✓ (intended)
**Line 275:** Properties with `truncate` for short text ✓ (intended)

These are intentional UI truncations with proper expand controls - NOT the root cause.

---

## Unresolved Questions

None. Root cause clearly identified.

---

## Impact Assessment

**Severity:** Medium
**User Impact:** Cannot read full node labels/descriptions
**Workaround:** Check properties panel (text still in `node.properties.text`)
**Fix Effort:** Low (2 line removal, 1 backend restart)
