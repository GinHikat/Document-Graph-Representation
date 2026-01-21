# Frontend UX Flow Optimization Plan

## Executive Summary

Comprehensive UX optimization for Tax Legal RAG frontend - a document management and Q&A comparison system. Focus on reducing friction, improving discoverability, and enhancing user productivity.

---

## Current State Analysis

### Pages & Core Flows
| Page | Purpose | Current Issues |
|------|---------|----------------|
| `/documents` | Upload & manage tax documents | Linear flow, no preview |
| `/graph` | Neo4j knowledge graph visualization | Dense controls, no onboarding |
| `/qa` | Compare Vector vs Graph+Vector answers | Long scroll, annotation friction |
| `/annotate` | RLHF evaluation | Separate from QA workflow |

### Identified UX Pain Points

#### 1. **Q&A Page** (High Priority)
- **Annotation workflow fragmented**: Must scroll down to annotate after viewing results
- **No Q&A history visible**: Past questions not accessible during session
- **Collapsible sections default closed**: Key info (sources) hidden
- **Mobile responsiveness**: Side-by-side comparison breaks on small screens
- **No keyboard shortcuts**: Power users can't work efficiently
- **Missing loading states**: No skeleton during API calls

#### 2. **Documents Page** (Medium Priority)
- **Upload progress simulated**: Not real backend progress
- **No document preview**: Can't inspect content before processing
- **Missing filter/search**: Hard to find docs in large lists
- **No processing ETA**: Users don't know when docs are ready
- **Single delete button**: Opens dialog but doesn't track selection properly

#### 3. **Graph Page** (Medium Priority)
- **No guided onboarding**: Users don't know how to start
- **Zoom controls non-functional**: Buttons exist but don't work
- **Fixed height visualization**: Doesn't adapt to screen
- **Language inconsistency**: Mix of Vietnamese and English in UI
- **Too many controls visible**: Overwhelms first-time users

#### 4. **Navigation & Global** (Low Priority)
- **No breadcrumbs**: Users lose context in deep flows
- **Hidden mobile nav**: Navigation not visible on mobile
- **No dark mode toggle**: Despite Tailwind dark mode support
- **Missing keyboard navigation**: Tab order not optimized

---

## Optimization Plan

### Phase 1: Critical Flow Improvements

#### 1.1 Q&A Sticky Annotation Bar Enhancement
**Problem**: Annotation requires scrolling; disconnected from results
**Solution**:
- Make annotation bar truly sticky with mini-preview of both answers
- Add keyboard shortcuts: `1`=Vector, `2`=Equivalent, `3`=Graph, `4`=Both Wrong
- Show annotation status indicator when submitted

**Files to modify**:
- `frontend/src/pages/QA.tsx`
- `frontend/src/stores/qaStore.ts`

#### 1.2 Q&A History Sidebar
**Problem**: No access to previous questions
**Solution**:
- Add collapsible history panel on left
- Click to replay any previous question
- Show annotation status per question

**Files to modify**:
- `frontend/src/pages/QA.tsx`
- `frontend/src/stores/qaStore.ts`

#### 1.3 Smart Defaults for Collapsibles
**Problem**: Important info hidden in collapsed sections
**Solution**:
- Auto-expand Sources section when results arrive
- Remember user preferences for expand/collapse state
- Add "Expand All" button

**Files to modify**:
- `frontend/src/pages/QA.tsx`

### Phase 2: Document Management UX

#### 2.1 Document Search & Filter
**Problem**: Can't find documents in long lists
**Solution**:
- Add search input filtering by name
- Add status filter chips (Processing, Completed, Failed)
- Add date range filter

**Files to modify**:
- `frontend/src/pages/Documents.tsx`
- `frontend/src/stores/documentStore.ts`

#### 2.2 Real Upload Progress
**Problem**: Progress bar is simulated, not real
**Solution**:
- Integrate with backend SSE for real progress
- Show multi-file progress individually
- Add cancel upload capability

**Files to modify**:
- `frontend/src/pages/Documents.tsx`
- `frontend/src/stores/documentStore.ts`
- `frontend/src/services/api.ts`

#### 2.3 Document Preview Modal
**Problem**: Can't inspect document content
**Solution**:
- Add preview button/click handler
- Show extracted text preview
- Show chunk count and processing details

**Files to create**:
- `frontend/src/components/DocumentPreviewModal.tsx`

### Phase 3: Graph Visualization Polish

#### 3.1 Working Zoom Controls
**Problem**: Zoom/fit buttons don't work
**Solution**:
- Wire up ForceGraph ref methods
- Add zoom slider control
- Implement fit-to-screen logic

**Files to modify**:
- `frontend/src/pages/Graph.tsx`
- `frontend/src/components/GraphVisualization.tsx`

#### 3.2 First-time User Onboarding
**Problem**: New users don't know where to start
**Solution**:
- Add empty state with guided steps
- Show example queries as clickable chips
- Add inline tooltips on controls

**Files to modify**:
- `frontend/src/pages/Graph.tsx`

#### 3.3 Responsive Height
**Problem**: Fixed 600px height wastes space
**Solution**:
- Use `calc(100vh - header)` for full height
- Add mobile-optimized layout (stacked controls)

**Files to modify**:
- `frontend/src/pages/Graph.tsx`
- `frontend/src/components/GraphVisualization.tsx`

### Phase 4: Global UX Enhancements

#### 4.1 Mobile Navigation
**Problem**: Nav hidden on mobile
**Solution**:
- Add hamburger menu for mobile
- Slide-in drawer navigation
- Bottom tab bar alternative

**Files to modify**:
- `frontend/src/components/layout/Header.tsx`

**Files to create**:
- `frontend/src/components/layout/MobileNav.tsx`

#### 4.2 Keyboard Shortcuts System
**Problem**: No keyboard shortcuts
**Solution**:
- Global shortcut handler hook
- `Cmd+K` for command palette
- Page-specific shortcuts

**Files to create**:
- `frontend/src/hooks/useKeyboardShortcuts.ts`
- `frontend/src/components/CommandPalette.tsx`

#### 4.3 Dark Mode Toggle
**Problem**: No user control over theme
**Solution**:
- Add theme toggle in header
- Persist preference in localStorage
- Use existing Tailwind dark classes

**Files to create**:
- `frontend/src/components/ThemeToggle.tsx`
- `frontend/src/hooks/useTheme.ts`

---

## Implementation Priority Matrix

| Priority | Optimization | Impact | Effort |
|----------|--------------|--------|--------|
| P0 | Q&A Sticky Annotation Enhancement | High | Low |
| P0 | Smart Collapsible Defaults | High | Low |
| P1 | Q&A History Sidebar | High | Medium |
| P1 | Document Search/Filter | Medium | Low |
| P1 | Working Zoom Controls | Medium | Low |
| P2 | Mobile Navigation | Medium | Medium |
| P2 | Document Preview Modal | Medium | Medium |
| P2 | Keyboard Shortcuts | Medium | Medium |
| P3 | Real Upload Progress | Low | High |
| P3 | Dark Mode Toggle | Low | Low |
| P3 | Graph Onboarding | Low | Medium |

---

## Component Architecture Changes

```
src/
├── components/
│   ├── layout/
│   │   ├── Header.tsx (modify)
│   │   └── MobileNav.tsx (new)
│   ├── qa/
│   │   ├── AnnotationBar.tsx (extract)
│   │   ├── HistorySidebar.tsx (new)
│   │   └── ResultCard.tsx (extract)
│   ├── documents/
│   │   ├── DocumentFilters.tsx (new)
│   │   └── DocumentPreviewModal.tsx (new)
│   ├── graph/
│   │   └── GraphOnboarding.tsx (new)
│   ├── CommandPalette.tsx (new)
│   └── ThemeToggle.tsx (new)
├── hooks/
│   ├── useKeyboardShortcuts.ts (new)
│   ├── useTheme.ts (new)
│   └── useLocalStorage.ts (new)
└── stores/
    └── uiStore.ts (new - for UI preferences)
```

---

## Quick Wins (Can Implement Today)

1. **Auto-expand sources on result load** - 3 lines change
2. **Add keyboard hints to buttons** - CSS tooltips
3. **Fix language consistency** - Use i18n keys
4. **Add loading skeletons** - shadcn/ui Skeleton component
5. **Improve mobile breakpoints** - Tailwind responsive classes

---

## Unresolved Questions

1. Should Q&A history persist across sessions (backend) or be session-only?
2. Is document preview needed if processing shows extracted chunks?
3. Command palette scope - global nav only or feature search?
4. Mobile-first redesign vs responsive patches?

---

## Metrics to Track Post-Implementation

- Time to first annotation (reduce by 30%)
- Mobile session completion rate (increase by 50%)
- Feature discoverability via command palette usage
- Error recovery rate (failed uploads, disconnections)
