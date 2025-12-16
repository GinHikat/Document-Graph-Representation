# Backend API Documentation

## Overview

FastAPI backend providing REST APIs for graph operations and RAG queries.

## Directory Structure

```
api/
├── main.py              # FastAPI app entry
├── routers/
│   ├── graph.py         # Graph endpoints
│   ├── rag.py           # RAG endpoints
│   └── health.py        # Health check
├── services/
│   ├── neo4j_client.py  # Neo4j operations
│   ├── rag_service.py   # RAG logic
│   └── embeddings.py    # Embedding service
└── schemas/
    ├── graph.py         # Graph models
    └── rag.py           # RAG models
```

## Running the Server

```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Reference

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "neo4j": "connected",
  "version": "1.0.0"
}
```

### Graph API

#### Get Nodes

```
GET /api/graph/nodes
```

Query params:
- `label`: Filter by node label
- `limit`: Max nodes (default: 100)
- `skip`: Offset for pagination

Response:
```json
{
  "nodes": [
    {"id": "1", "label": "Document", "properties": {...}},
    ...
  ],
  "total": 1234
}
```

#### Execute Cypher

```
POST /api/graph/execute
```

Body:
```json
{
  "query": "MATCH (n:Document) RETURN n LIMIT 10",
  "params": {}
}
```

Response:
```json
{
  "results": [...],
  "execution_time": 0.045
}
```

#### Get Schema

```
GET /api/graph/schema
```

Response:
```json
{
  "node_labels": ["Document", "Chapter", "Article", "Clause", "Entity"],
  "relationship_types": ["HAS_CHAPTER", "MENTIONS", "RELATED_TO"],
  "constraints": [...],
  "indexes": [...]
}
```

#### Get Stats

```
GET /api/graph/stats
```

Response:
```json
{
  "node_count": 15234,
  "relationship_count": 45678,
  "labels": {"Document": 50, "Entity": 3456, ...}
}
```

### RAG API

#### Query (SSE Streaming)

```
POST /api/rag/query
```

Body:
```json
{
  "query": "Thuế thu nhập cá nhân là gì?",
  "mode": 2,
  "top_k": 5,
  "use_graph": true
}
```

SSE Events:
```
event: status
data: {"stage": "embedding", "progress": 0.1}

event: status
data: {"stage": "retrieving", "progress": 0.3}

event: context
data: {"chunks": [...], "count": 5}

event: answer
data: {"text": "Thuế thu nhập...", "complete": false}

event: done
data: {"total_time": 1.234, "tokens": 156}
```

#### Retrieve Context

```
POST /api/rag/retrieve
```

Body:
```json
{
  "query": "Thuế GTGT",
  "mode": 1,
  "top_k": 10,
  "graph": 1,
  "chunks": 1,
  "hop": 2
}
```

Response:
```json
{
  "contexts": [
    {"content": "...", "score": 0.95, "source": "..."},
    ...
  ]
}
```

#### Rerank Results

```
POST /api/rag/rerank
```

Body:
```json
{
  "query": "...",
  "contexts": ["...", "..."],
  "top_k": 3
}
```

Response:
```json
{
  "reranked": [
    {"content": "...", "score": 0.98},
    ...
  ]
}
```

#### List Tools

```
GET /api/rag/tools
```

Response:
```json
{
  "tools": [
    {"name": "retrieve", "description": "..."},
    {"name": "rerank", "description": "..."}
  ]
}
```

## Pydantic Schemas

```python
# schemas/rag.py
class RAGQuery(BaseModel):
    query: str
    mode: int = 1
    top_k: int = 5
    use_graph: bool = True

class Context(BaseModel):
    content: str
    score: float
    source: str
    metadata: dict = {}
```

## Error Handling

All errors return:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {...}
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad request
- 404: Not found
- 500: Internal error
