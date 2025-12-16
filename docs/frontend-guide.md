# Frontend Documentation

## Overview

React 18 + TypeScript SPA for the Tax Legal RAG System.

## Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/            # shadcn/ui components
│   │   └── layout/        # Layout components
│   ├── pages/
│   │   ├── Home.tsx       # Dashboard
│   │   ├── Documents.tsx  # Document management
│   │   ├── QA.tsx         # Query interface
│   │   ├── Graph.tsx      # Knowledge graph
│   │   └── Annotate.tsx   # Annotation tool
│   ├── services/
│   │   └── api.ts         # API client
│   ├── stores/
│   │   ├── authStore.ts   # Auth state
│   │   ├── documentStore.ts
│   │   └── qaStore.ts
│   ├── hooks/             # Custom hooks
│   ├── types/             # TypeScript types
│   └── lib/
│       └── utils.ts       # Utilities
├── public/                # Static assets
└── index.html
```

## Key Technologies

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.3.1 | UI framework |
| typescript | 5.8.3 | Type safety |
| vite | 5.4.19 | Build tool |
| zustand | 5.0.8 | State management |
| @tanstack/react-query | 5.83.0 | Data fetching |
| react-router-dom | 6.30.1 | Routing |
| tailwindcss | 3.4.17 | Styling |
| react-force-graph | 1.48.1 | Graph visualization |

## State Management

### Zustand Stores

```typescript
// authStore.ts
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials) => Promise<void>;
  logout: () => void;
}

// documentStore.ts
interface DocumentState {
  documents: Document[];
  selectedDoc: Document | null;
  fetchDocuments: () => Promise<void>;
  selectDocument: (id: string) => void;
}

// qaStore.ts
interface QAState {
  query: string;
  results: SearchResult[];
  isLoading: boolean;
  search: (query: string) => Promise<void>;
}
```

## API Integration

### API Client (`services/api.ts`)

```typescript
const API_URL = import.meta.env.VITE_API_URL;

// Graph endpoints
export const graphApi = {
  getNodes: (params) => fetch(`${API_URL}/graph/nodes?${params}`),
  execute: (query) => fetch(`${API_URL}/graph/execute`, {
    method: 'POST',
    body: JSON.stringify({ query })
  }),
};

// RAG endpoints with SSE
export const ragApi = {
  query: (text: string) => {
    const eventSource = new EventSource(
      `${API_URL}/rag/query?q=${encodeURIComponent(text)}`
    );
    return eventSource;
  },
};
```

## Pages

### Home (`/`)
Dashboard with system stats, recent queries, quick actions.

### Documents (`/documents`)
- List uploaded documents
- Upload new documents
- View document details
- Delete documents

### Q&A (`/qa`)
- Query input
- Mode selection (vector/graph)
- Streaming results
- Source citations

### Graph (`/graph`)
- Interactive knowledge graph
- Node filtering by type
- Zoom/pan controls
- Node details on click

### Annotate (`/annotate`)
- Document viewer
- Entity highlighting
- Relation annotation
- Export annotations

## Components

### UI Components (shadcn/ui)
Pre-built accessible components:
- Button, Input, Select
- Dialog, Sheet, Popover
- Table, Card, Tabs
- Toast notifications

### Custom Components

```typescript
// Example: SearchBar
interface SearchBarProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  loading?: boolean;
}
```

## Environment Variables

```bash
# .env
VITE_API_URL=http://localhost:8000/api
VITE_ENABLE_GRAPH_VIEW=true
VITE_ENABLE_ANNOTATIONS=true
```

## Scripts

```bash
npm run dev      # Start dev server (port 8080)
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # ESLint check
```

## Build Output

Production build outputs to `dist/`:
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   └── index-[hash].css
└── favicon.ico
```
