# Phase 2: Neo4j Indexing Service

**Parent:** [plan.md](./plan.md)
**Dependencies:** [Phase 1](./phase-01-document-processing-service.md)
**Date:** 2026-01-07
**Priority:** High
**Status:** Pending

## Overview

Create Neo4j indexing service that takes parsed document structure and creates graph nodes with embeddings + relationships. Wraps existing `saving_neo4j()` logic for API use.

## Key Insights

1. **Existing logic in `final_doc_processor.py:403-700`** - `saving_neo4j()` creates full hierarchy
2. **Relationship types from research:**
   - Hierarchy: `HAS_CHAPTER`, `HAS_CLAUSE`, `HAS_POINT`, `HAS_SUBPOINT`
   - Cross-ref: `CITES`, `AMENDS`, `REPEALS`, `REFERENCES`
3. **Embedding strategy** - Use BGE-M3 (research) or existing 768-dim model
4. **Neo4j Aura retry logic** - Already exists in `dml_ddl_neo4j()` (global_functions.py:306-358)

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1 | Create document root node with metadata | High |
| R2 | Create hierarchy nodes (Chapter/Clause/Point/etc) | High |
| R3 | Create HAS_* relationships between hierarchy levels | High |
| R4 | Extract cross-references and create CITES/AMENDS edges | High |
| R5 | Generate embeddings for Chunk nodes | High |
| R6 | Create vector index for semantic search | Medium |
| R7 | Use namespace label (e.g., Test_rel_2) | High |

## Architecture

```
api/services/neo4j_indexer.py
    |
    +-- Neo4jIndexerService (class)
            |
            +-- index_document(doc_id, text, parsed_structure, metadata)
            +-- create_hierarchy_nodes(namespace, parsed)
            +-- create_cross_references(namespace, text, node_id)
            +-- embed_and_store(namespace, node_ids)
            |
            +-- _embedding_model (lazy)
            +-- _relation_extractor (lazy)
```

## Related Code Files

| File | Lines | Purpose |
|------|-------|---------|
| `rag_model/model/Final_pipeline/final_doc_processor.py` | 403-700 | `saving_neo4j()` - full indexing logic |
| `rag_model/model/Final_pipeline/final_doc_processor.py` | 269-341 | `very_cool_chunking_with_graph()` - chunk creation |
| `rag_model/model/Final_pipeline/final_relation_extractor.py` | 383-407 | `extract_relation_entities()` |
| `shared_functions/global_functions.py` | 306-358 | `dml_ddl_neo4j()` - safe Neo4j writes |
| `api/db/neo4j.py` | 37-41 | `execute_query()` - existing query method |
| `api/services/embedding.py` | 46-68 | `embed_query()` - existing embedding |

## Implementation Steps

### Step 1: Create Service Skeleton

Create `api/services/neo4j_indexer.py`:

```python
"""Neo4j indexing service for document graph creation."""
import logging
from typing import Dict, Any, List, Optional

from api.db.neo4j import get_neo4j_client
from api.services.embedding import embed_texts

logger = logging.getLogger(__name__)

class Neo4jIndexerService:
    """Indexes documents into Neo4j knowledge graph."""

    def __init__(self, namespace: str = "Test_rel_2"):
        self.namespace = namespace
        self.client = get_neo4j_client()
        self._relation_extractor = None
```

### Step 2: Implement Document Root Node

```python
def create_document_node(self, metadata: Dict[str, str]) -> str:
    """Create root document node with metadata."""
    doc_type = metadata.get("document_type", "Document").replace(" ", "_")
    doc_id = metadata.get("law_id") or metadata.get("document_id")

    query = f"""
    MERGE (doc:`{doc_type}`:`{self.namespace}` {{id: $doc_id}})
    SET doc += $props
    RETURN doc.id as id
    """
    result = self._execute(query, doc_id=doc_id, props=metadata)
    return result[0]["id"] if result else doc_id
```

### Step 3: Implement Hierarchy Creation

Port logic from `saving_neo4j()` lines 490-700:

```python
def create_hierarchy(self, doc_id: str, parsed: Dict[str, Any]) -> List[str]:
    """Create hierarchy nodes from parsed structure."""
    created_ids = []

    if "chapters" in parsed:
        for ch_key, ch_obj in parsed["chapters"].items():
            ch_id = f"{doc_id}_{ch_key.replace(' ', '_')}"
            self._create_chapter(ch_id, ch_obj, doc_id)
            created_ids.append(ch_id)

            for clause in ch_obj.get("clauses", []):
                cl_id = f"{ch_id}_C_{clause.get('clause')}"
                self._create_clause(cl_id, clause, ch_id)
                created_ids.append(cl_id)
                # ... points, subpoints
    else:
        # No chapters - clauses at top level
        for clause in parsed.get("clauses", []):
            # ...
```

### Step 4: Cross-Reference Extraction

Port from `final_relation_extractor.py:extract_relation_entities()`:

```python
def create_cross_references(self, node_id: str, text: str) -> int:
    """Extract and create cross-reference relationships."""
    if self._relation_extractor is None:
        self._init_relation_extractor()

    _, relation, entities = self._relation_extractor.extract_relation_entities(text, node_id)

    count = 0
    for entity in entities or []:
        target_id = list(entity.keys())[0]
        target_type = list(entity.values())[0]
        if target_id and relation:
            self._create_relationship(node_id, target_id, relation, target_type)
            count += 1
    return count
```

### Step 5: Embedding and Vector Index

```python
def embed_nodes(self, node_ids: List[str]) -> int:
    """Embed text for nodes and store vectors."""
    # Get node texts
    query = f"""
    MATCH (n:{self.namespace})
    WHERE n.id IN $ids AND n.text IS NOT NULL
    RETURN n.id as id, n.text as text
    """
    nodes = self._execute(query, ids=node_ids)

    if not nodes:
        return 0

    texts = [n["text"] for n in nodes]
    embeddings = embed_texts(texts)

    # Store embeddings
    for node, emb in zip(nodes, embeddings):
        self._execute(f"""
        MATCH (n:{self.namespace} {{id: $id}})
        SET n.embedding = $embedding
        """, id=node["id"], embedding=emb)

    return len(nodes)
```

### Step 6: Ensure Vector Index Exists

```python
def ensure_vector_index(self):
    """Create vector index if not exists."""
    query = f"""
    CREATE VECTOR INDEX {self.namespace}_embedding IF NOT EXISTS
    FOR (n:{self.namespace}) ON (n.embedding)
    OPTIONS {{indexConfig: {{
        `vector.dimensions`: 768,
        `vector.similarity_function`: 'cosine'
    }}}}
    """
    self._execute(query)
```

### Step 7: Main Entry Point

```python
def index_document(
    self,
    doc_id: str,
    text: str,
    parsed: Dict[str, Any],
    metadata: Dict[str, str]
) -> Dict[str, int]:
    """Full indexing pipeline for a document."""
    stats = {"nodes": 0, "relationships": 0, "embeddings": 0}

    # 1. Create document root
    self.create_document_node(metadata)
    stats["nodes"] += 1

    # 2. Create hierarchy
    node_ids = self.create_hierarchy(doc_id, parsed)
    stats["nodes"] += len(node_ids)

    # 3. Extract cross-references for each node
    for node_id in node_ids:
        # Get node text
        node_text = self._get_node_text(node_id)
        if node_text:
            stats["relationships"] += self.create_cross_references(node_id, node_text)

    # 4. Embed all nodes
    stats["embeddings"] = self.embed_nodes(node_ids)

    return stats
```

## Todo

- [ ] Create `api/services/neo4j_indexer.py`
- [ ] Port `saving_neo4j()` hierarchy creation logic
- [ ] Integrate relation extractor for cross-references
- [ ] Add embedding storage using existing `embed_texts()`
- [ ] Create vector index setup method
- [ ] Add retry wrapper using existing `dml_ddl_neo4j()` pattern
- [ ] Write unit tests with Neo4j mock
- [ ] Integration test with real Neo4j

## Success Criteria

1. `Neo4jIndexerService().index_document(...)` creates full graph
2. Hierarchy nodes connected: Document -> Chapter -> Clause -> Point
3. Cross-references detected and stored as relationships
4. Embeddings stored on nodes
5. Vector search works: `db.index.vector.queryNodes()` returns results

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Neo4j Aura timeout | Medium | Medium | Retry wrapper exists |
| Relation extractor OOM | Low | High | Process sentence-by-sentence |
| Embedding batch too large | Low | Medium | Batch in chunks of 100 |
| Cypher injection | Low | High | Use parameterized queries |

## Security Considerations

1. **Parameterized queries** - Always use `$param` syntax, never f-strings with user input
2. **Namespace isolation** - Use label-based namespacing
3. **Connection handling** - Singleton client, proper close on shutdown

## Next Steps

After completion:
1. Proceed to [Phase 3: API Integration](./phase-03-api-integration.md)
2. Indexer will be called from upload endpoint via BackgroundTask
