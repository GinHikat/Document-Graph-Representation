# System Architecture Diagram

**File:** `system-architecture.excalidraw`

## Overview

This diagram illustrates the Tax Legal RAG (Retrieval-Augmented Generation) System for Vietnamese tax law documents.

## Architecture Layers

### 1. Presentation Layer
| Component | Technology | Description |
|-----------|------------|-------------|
| React Frontend | React 18 + TypeScript | Main UI application |
| Build Tool | Vite 5.4 | Fast development server |
| State Management | Zustand 5.0 | Lightweight state |
| Data Fetching | TanStack Query 5.8 | Server state cache |
| Graph Visualization | react-force-graph | Knowledge graph rendering |

### 2. API Layer
| Endpoint | Purpose |
|----------|---------|
| `/api/graph` | Graph nodes, Cypher queries, schema, stats |
| `/api/rag` | RAG query with SSE streaming, retrieve, rerank |
| `/api/auth` | Authentication |
| `/api/stats` | System statistics |

### 3. Service Layer
| Service | Technology | Function |
|---------|------------|----------|
| RAG Agent | Custom | 7 retrieval modes orchestration |
| Embedding | MiniLM / PhoBERT | Text vectorization |
| Reranker | Cross-Encoder | Result reranking |
| Gemini LLM | Google Gemini | Answer generation with SSE streaming |

### 4. Data Layer
| Store | Technology | Purpose |
|-------|------------|---------|
| Neo4j AuraDB | Neo4j 5.27 | Graph database + vector index |
| AWS S3 | Amazon S3 | Document storage |

### 5. Offline Processing Pipeline
```
Crawler (Playwright) → Parser → NER (Underthesea) → RE Model → Graph Builder → Neo4j
```

## Retrieval Modes

| Mode | Name | Description |
|------|------|-------------|
| 1 | default | Standard embedding search |
| 2 | traverse_embed | Graph traversal + embeddings |
| 3 | traverse_exact | Graph traversal + exact match |
| 4 | pagerank_embed | PageRank + embeddings |
| 5 | pagerank_exact | PageRank + exact match |
| 6 | exact_match | Pure exact match |
| 7 | exact_match_with_rerank | Exact + reranking |

## Color Legend

| Color | Component Type |
|-------|---------------|
| 🔵 Blue (`#a5d8ff`) | Frontend/UI |
| 🟣 Purple (`#d0bfff`) | Backend/API |
| 🟢 Green (`#b2f2bb`) | Database |
| 🟡 Yellow (`#ffec99`) | Storage |
| 🩷 Pink (`#e599f7`) | AI/ML Services |
| 🔴 Red (`#ffc9c9`) | External APIs |
| 🧡 Coral (`#ffa8a8`) | Orchestration |
| 🩵 Cyan (`#99e9f2`) | Processing |

## How to View

1. **Excalidraw.com**: Open https://excalidraw.com → File → Open → Select `system-architecture.excalidraw`
2. **VS Code**: Install "Excalidraw" extension → Open file directly
3. **Export**: Open in Excalidraw → Export as PNG/SVG for documentation
