# Frontend UX Optimization Plan

**Created**: 2025-01-07
**Priority**: High
**Status**: In Progress

## Overview

Comprehensive UX optimization for Tax Legal RAG frontend covering Q&A, Documents, and Graph pages. Session-only history persistence, all P0+P1 features.

## Phases

| Phase | Name | Status | Link |
|-------|------|--------|------|
| 1 | Q&A Annotation Enhancement | Pending | [phase-01](./phase-01-qa-annotation.md) |
| 2 | Smart Collapsible Defaults | Pending | [phase-02](./phase-02-collapsibles.md) |
| 3 | Q&A History Sidebar | Pending | [phase-03](./phase-03-history-sidebar.md) |
| 4 | Document Search/Filter | Pending | [phase-04](./phase-04-document-filter.md) |
| 5 | Graph Zoom Controls | Pending | [phase-05](./phase-05-graph-zoom.md) |

## Key Research Insights

### Keyboard Shortcuts (from research)
- `1` = Vector better
- `2` = Equivalent
- `3` = Graph better
- `4` = Both wrong
- `Cmd+Enter` = Submit

### Progressive Disclosure
- Auto-expand sources when results arrive
- Keep metrics in subtle footer
- Use hover tooltips for source previews

### History Panel
- Group by time (Today, Yesterday, etc.)
- Collapsible sidebar on desktop
- Search within history

## Files to Modify

```
frontend/src/
├── pages/
│   ├── QA.tsx           (keyboard, annotation, history)
│   ├── Documents.tsx    (search, filter)
│   └── Graph.tsx        (zoom controls)
├── components/
│   ├── GraphVisualization.tsx (expose zoom methods)
│   └── qa/
│       └── HistorySidebar.tsx (new)
├── stores/
│   ├── qaStore.ts       (history state)
│   └── documentStore.ts (filter state)
└── hooks/
    └── useKeyboardShortcuts.ts (new)
```

## Success Criteria

1. Keyboard shortcuts work on Q&A page (1/2/3/4 keys)
2. Sources auto-expand when results load
3. History sidebar shows past questions with annotation status
4. Document list searchable by name and filterable by status
5. Graph zoom controls functional (zoom in/out/fit)
6. All builds and type checks pass
7. No regressions in existing functionality

## Dependencies

- shadcn/ui components (already installed)
- react-force-graph-2d (already installed)
- Zustand stores (already configured)
