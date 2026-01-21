# Phase 1: Q&A Annotation Enhancement

## Context
- [Main Plan](./plan.md)
- [QA.tsx](../../frontend/src/pages/QA.tsx)
- [qaStore.ts](../../frontend/src/stores/qaStore.ts)

## Overview
| Field | Value |
|-------|-------|
| Priority | P0 |
| Status | In Progress |
| Estimated Effort | Low |

## Key Insights
- Keyboard shortcuts: 1=Vector, 2=Equivalent, 3=Graph, 4=Both Wrong
- Cmd+Enter to submit annotation
- Visual feedback via toast on shortcut use
- Shortcuts only active when results are visible

## Requirements
1. Global keyboard listener for annotation shortcuts
2. Visual indicator showing available shortcuts
3. Toast confirmation on annotation selection
4. Submit via Cmd+Enter or button

## Implementation Steps

- [ ] Create `useKeyboardShortcuts.ts` hook
- [ ] Add keyboard event listeners to QA page
- [ ] Add shortcut hints to annotation buttons
- [ ] Add Cmd+Enter submit handler
- [ ] Test keyboard interactions

## Related Files
- `frontend/src/pages/QA.tsx`
- `frontend/src/hooks/useKeyboardShortcuts.ts` (new)

## Success Criteria
- Pressing 1/2/3/4 selects annotation preference
- Pressing Cmd+Enter submits annotation
- Toast shows confirmation
- No interference with other inputs
