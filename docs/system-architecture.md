# System Architecture

## Overview

The Tax Legal RAG System is a full-stack application for knowledge graph-based document retrieval, comparing vector search vs graph traversal approaches.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Home    │ │Documents │ │   Q&A    │ │  Graph   │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       └────────────┴────────────┴────────────┘                  │
│                         │                                       │
│              ┌──────────▼──────────┐                            │
│              │   API Service       │ (TanStack Query + Zustand) │
│              └──────────┬──────────┘                            │
└─────────────────────────┼───────────────────────────────────────┘
                          │ HTTP/SSE
┌─────────────────────────▼───────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Graph Router │ │  RAG Router  │ │Health Router │            │
│  └──────┬───────┘ └──────┬───────┘ └──────────────┘            │
│         └────────────────┴────────────────┐                     │
│                                           │                     │
│  ┌──────────────────────────────────────────────────────┐      │
│  │                    Services Layer                     │      │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐        │      │
│  │  │Neo4j Client│ │RAG Service │ │ Embeddings │        │      │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘        │      │
│  └────────┼──────────────┼──────────────┼───────────────┘      │
└───────────┼──────────────┼──────────────┼───────────────────────┘
            │              │              │
┌───────────▼──────────────▼──────────────▼───────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   Neo4j      │ │    AWS S3    │ │   ML Models  │             │
│  │  (AuraDB)    │ │  (Documents) │ │ (Embeddings) │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | React 18 + TypeScript | Component-based UI |
| State Management | Zustand | Client state (auth, documents, QA) |
| Data Fetching | TanStack Query | Server state, caching |
| Styling | Tailwind CSS + shadcn/ui | Design system |
| Routing | React Router 6 | SPA navigation |
| Graph Visualization | react-force-graph | Knowledge graph rendering |

### Backend Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | FastAPI | Async API server |
| Graph Router | `/api/graph/*` | Neo4j operations |
| RAG Router | `/api/rag/*` | Retrieval operations |
| Streaming | SSE | Real-time query results |

### Data Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Graph Database | Neo4j AuraDB | Knowledge graph storage |
| Document Storage | AWS S3 | PDF/document files |
| Embeddings | sentence-transformers | Vector representations |
| Vietnamese NLP | Underthesea | Tokenization, NER |

## Data Flow

### Document Processing Pipeline

```
PDF Document
    │
    ▼
┌─────────────────┐
│ PDF Extraction  │ (PyMuPDF)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Chunking   │ (Sentence-level)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vietnamese NLP  │ (Underthesea)
│ - Tokenization  │
│ - NER           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Relation        │
│ Extraction      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding       │ (sentence-transformers)
│ Generation      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Neo4j Storage   │
│ (Nodes + Edges) │
└─────────────────┘
```

### Query Pipeline

```
User Query
    │
    ▼
┌─────────────────┐
│ Query Embedding │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│     Retrieval Strategy          │
│  ┌───────────┐ ┌───────────┐   │
│  │  Vector   │ │   Graph   │   │
│  │  Search   │ │ Traversal │   │
│  └─────┬─────┘ └─────┬─────┘   │
│        └──────┬──────┘          │
└───────────────┼─────────────────┘
                │
                ▼
┌─────────────────┐
│    Reranking    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Assembly│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Response   │ (Optional)
└────────┬────────┘
         │
         ▼
    SSE Stream
```

## Neo4j Graph Schema

### Node Types

| Label | Properties | Description |
|-------|-----------|-------------|
| Document | id, title, source_url | Legal document |
| Chapter | id, title, doc_id | Document chapter |
| Article | id, number, title | Law article |
| Clause | id, content, embedding | Text chunk |
| Entity | name, type, embedding | Named entity (NER) |

### Relationship Types

| Type | From | To | Description |
|------|------|-----|-------------|
| HAS_CHAPTER | Document | Chapter | Document structure |
| HAS_ARTICLE | Chapter | Article | Chapter content |
| HAS_CLAUSE | Article | Clause | Article text |
| MENTIONS | Clause | Entity | Entity reference |
| RELATED_TO | Entity | Entity | Extracted relation |
| REFERENCES | Article | Article | Cross-reference |

## API Design

### REST Endpoints

```
/api
├── /health          GET    Health check
├── /graph
│   ├── /nodes       GET    Fetch nodes
│   ├── /execute     POST   Cypher query
│   ├── /schema      GET    Graph schema
│   └── /stats       GET    Statistics
└── /rag
    ├── /query       POST   RAG query (SSE)
    ├── /retrieve    POST   Context retrieval
    ├── /rerank      POST   Result reranking
    └── /tools       GET    Available tools
```

### SSE Streaming Format

```typescript
// Query endpoint streams events:
event: status
data: {"stage": "retrieving", "progress": 0.2}

event: context
data: {"chunks": [...], "sources": [...]}

event: answer
data: {"text": "...", "complete": false}

event: done
data: {"total_time": 1.234}
```

## Security Considerations

- Environment variables for all secrets
- No credentials in source control
- CORS configuration for frontend origin
- Input validation with Pydantic schemas
