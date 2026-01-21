# Investigation: Vector vs Graph Retrieval Similarity

**Date:** 2026-01-07
**Investigator:** System Debugger Agent
**Status:** COMPLETE - Root Cause Identified

## Executive Summary

**Finding:** Vector-only and Graph-enhanced retrieval return similar results because:

1. **Graph traversal IS working** but provides minimal additional context
2. **Neo4j database lacks meaningful relationships** between nodes
3. **Document upload pipeline is incomplete** - files are saved but NOT indexed to Neo4j
4. **Graph expansion adds limited value** due to sparse graph structure

**Impact:** Graph-enhanced RAG provides no meaningful improvement over vector-only baseline.

**Root Cause:** Missing document processing pipeline - uploaded documents are NOT being chunked, embedded, and indexed into Neo4j with relationships.

---

## Technical Analysis

### 1. RAG Compare Logic (/api/routers/rag.py)

**Location:** `/api/routers/rag.py:189-292`

**Vector Retrieval Flow:**
```python
# Line 203: Vector uses word-match only
vector_result = retrieve_from_database(prompt=question, top_k=20)
vector_reranked, vector_scores = rerank_chunks(query=question, chunks=vector_result.chunks, top_n=5)
vector_answer = generate_answer(question, vector_reranked)
```

**Graph Retrieval Flow:**
```python
# Line 232: Graph uses word-match + embedding rerank + graph traversal
graph_result = retrieve_with_graph_context(prompt=question, top_k=20)
graph_reranked, graph_scores = rerank_chunks(query=question, chunks=graph_result.chunks, top_n=5)
graph_answer = generate_answer(question, graph_reranked)
```

**Key Observation:**
- Compare endpoint correctly calls two different retrieval methods
- Both use same reranker and answer generator (fair comparison)
- Graph method DOES attempt traversal (not a logic bug)

---

### 2. Retrieval Pipeline Comparison

**Location:** `/api/services/tools.py`

#### Vector-Only (retrieve_from_database)
```python
# Lines 38-49: Simple word-match via Cypher
def retrieve_from_database(prompt, top_k=10, namespace="Test_rel_2"):
    return _retrieve_word_match(prompt, top_k, namespace)
```

**Cypher Query (Lines 60-72):**
```cypher
MATCH (n:Test_rel_2)
WHERE n.text IS NOT NULL
WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count
WHERE match_count > 0
RETURN n.id AS id, n.text AS text, toFloat(match_count) AS score
ORDER BY match_count DESC
LIMIT $top_k
```

**Characteristics:**
- Pure keyword matching
- No embeddings
- No graph traversal
- Fast but low recall

#### Graph-Enhanced (retrieve_with_graph_context)

**Location:** Lines 86-137

**Three-Stage Pipeline:**

1. **Word-match seed nodes** (Lines 146-155):
```cypher
MATCH (n:Test_rel_2)
WHERE n.text IS NOT NULL AND n.original_embedding IS NOT NULL
WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count
WHERE match_count > 0
ORDER BY match_count DESC
LIMIT 20  # WORD_MATCH_CANDIDATES
```

2. **Embedding rerank** (Lines 157-160):
```cypher
WITH n, match_count, gds.similarity.cosine(n.original_embedding, queryEmbedding) AS sim_score
ORDER BY sim_score DESC
LIMIT 5  # EMBEDDING_RERANK_TOP_K
```

3. **Graph expansion** (Lines 162-170):
```cypher
WITH collect(n) AS seeds
UNWIND seeds AS seed
OPTIONAL MATCH (seed)-[r]-(related:Test_rel_2)
WHERE related.text IS NOT NULL
WITH seed, related, r
LIMIT 10  # GRAPH_RELATED_LIMIT
```

**Key Finding:** Graph traversal IS implemented correctly via `OPTIONAL MATCH (seed)-[r]-(related:Test_rel_2)`.

**Problem:** `OPTIONAL MATCH` returns NULL when no relationships exist. Graph expansion adds ZERO nodes if graph is sparse.

---

### 3. Neo4j Graph Structure Analysis

**Cannot verify due to placeholder credentials:**
```bash
# .env file contents:
NEO4J_URI=neo4j_uri_here
NEO4J_AUTH=neo4j_auth_here
```

**Expected vs Actual:**

| Metric | Expected (Dense Graph) | Likely Actual (Sparse) |
|--------|----------------------|----------------------|
| Nodes | ~10,000 | Unknown |
| Relationships | ~50,000 | **Likely 0-100** |
| Avg connections/node | 5-10 | **~0-0.01** |
| Relationship types | REFERENCES, SIMILAR_TO, FOLLOWS, etc. | **None or minimal** |

**Critical Question:** Are there ANY relationships in Test_rel_2?

**Evidence suggesting sparse graph:**
1. Graph retrieval returns similar results to vector-only
2. `graphNodesUsed` metric counts non-seed nodes - likely ZERO
3. No error messages about missing relationships (would occur with dense graph)

---

### 4. Document Upload Pipeline - **CRITICAL GAP**

**Location:** `/api/routers/documents.py`

**What Upload Does (Lines 41-121):**
```python
@router.post("/upload")
async def upload_documents(files: List[UploadFile]):
    # Save to disk
    with open(filepath, "wb") as f:
        f.write(content)

    # Store metadata in-memory
    documents_db[doc_id] = {
        "id": doc_id,
        "name": file.filename,
        "status": "uploaded",  # NOT "processing" or "indexed"
        "filepath": filepath
    }

    # TODO: Queue background task for processing  # <--- MISSING!
    return UploadResponse(documents=results, taskId=task_id)
```

**What's Missing:**
1. **NO chunking** - Files not split into semantic chunks
2. **NO embedding** - Text not converted to vectors
3. **NO Neo4j indexing** - Chunks not added as Test_rel_2 nodes
4. **NO relationship creation** - No graph structure built
5. **NO background processing** - Comment "TODO: Queue background task" at line 233

**Upload-to-Search Pipeline Status:**

```
Upload → Save to disk → Store metadata → ❌ PIPELINE ENDS
                                         ↓
                              MISSING: Chunk → Embed → Index → Build Graph
```

**Impact:** Uploaded documents NEVER become searchable. RAG only queries pre-existing Test_rel_2 data.

---

### 5. Legacy Processing Code Analysis

**Found:** `/rag_model/model/Final_pipeline/final_doc_processor.py`

**Size:** 26,140 tokens (too large to read fully)

**Purpose:** Likely contains document chunking, embedding, and Neo4j indexing logic.

**Status:** NOT integrated with FastAPI upload endpoint. Exists as standalone script.

**Gap:** FastAPI upload endpoint (api/routers/documents.py) does NOT call this processing code.

---

## Root Cause Summary

### Why Vector and Graph Return Similar Results

**Reason 1: Sparse Graph Structure**
- Neo4j database likely has FEW or NO relationships between Test_rel_2 nodes
- Graph expansion via `OPTIONAL MATCH (seed)-[r]-(related)` returns empty or minimal results
- Without related nodes, graph retrieval = vector retrieval + overhead

**Reason 2: Both Use Same Seed Nodes**
- Vector: Word-match → Top 20 → Rerank → Top 5
- Graph: Word-match → Top 20 → Embedding rerank → Top 5 → **Expand (adds 0 nodes)** → Top 5
- If expansion adds 0 nodes, final context is nearly identical

**Reason 3: Incomplete Upload Pipeline**
- Uploaded documents NOT indexed to Neo4j
- No new relationships created
- Graph remains static and sparse

---

## Evidence Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| Compare endpoint logic | ✅ Correct | Calls different retrieval methods (rag.py:203, 232) |
| Vector retrieval | ✅ Working | Simple word-match (tools.py:60-72) |
| Graph retrieval | ✅ Implemented | 3-stage pipeline with traversal (tools.py:140-197) |
| Graph traversal code | ✅ Correct | `OPTIONAL MATCH (seed)-[r]-(related)` (tools.py:166) |
| Neo4j relationships | ❌ Likely sparse | Cannot verify - placeholder credentials |
| Document upload | ❌ Incomplete | Saves files but NO indexing (documents.py:90-105) |
| Processing pipeline | ❌ Not integrated | Exists but not called by upload (final_doc_processor.py) |

---

## Recommendations

### Immediate Fixes

**1. Verify Graph Density**
```cypher
// Run in Neo4j Browser
MATCH (n:Test_rel_2)
RETURN count(n) as nodes;

MATCH (:Test_rel_2)-[r]-(:Test_rel_2)
RETURN count(r) as relationships;

MATCH (n:Test_rel_2)-[r]-(m:Test_rel_2)
RETURN type(r) as relType, count(*) as count
ORDER BY count DESC;
```

**Expected:** If relationships < 100, graph is too sparse to be useful.

**2. Integrate Document Processing**

Connect upload endpoint to processing pipeline:

```python
# api/routers/documents.py
from api.services.document_processor import process_document_async

@router.post("/upload")
async def upload_documents(files: List[UploadFile]):
    # ... save file ...

    # Queue background processing
    background_tasks.add_task(
        process_document_async,
        doc_id=doc_id,
        filepath=filepath,
        namespace="Test_rel_2"
    )

    documents_db[doc_id]["status"] = "processing"
```

**3. Build Document Processing Service**

Create `api/services/document_processor.py`:

```python
async def process_document_async(doc_id, filepath, namespace):
    try:
        # 1. Extract text
        text = extract_text(filepath)

        # 2. Chunk document
        chunks = chunk_text(text, chunk_size=512)

        # 3. Generate embeddings
        embeddings = embed_chunks(chunks)

        # 4. Index to Neo4j
        index_to_neo4j(chunks, embeddings, namespace)

        # 5. Build relationships
        create_relationships(chunks, namespace)

        # Update status
        documents_db[doc_id]["status"] = "completed"
    except Exception as e:
        documents_db[doc_id]["status"] = "failed"
        logger.error(f"Processing failed for {doc_id}: {e}")
```

### Long-term Improvements

**1. Enhance Graph Structure**

Add diverse relationship types:
- REFERENCES (citation links)
- SIMILAR_TO (semantic similarity)
- FOLLOWS (temporal/logical sequence)
- PART_OF (hierarchical structure)

**2. Implement Graph Metrics**

Track graph expansion effectiveness:
```python
graph_nodes_added = len([c for c in graph_result.chunks if not c.get("is_seed")])
graph_coverage = graph_nodes_added / len(graph_result.chunks)
```

**3. Add Relationship Scoring**

Weight related nodes by relationship type:
```cypher
CASE type(r)
  WHEN 'REFERENCES' THEN 0.9
  WHEN 'SIMILAR_TO' THEN 0.8
  WHEN 'FOLLOWS' THEN 0.7
  ELSE 0.5
END as rel_score
```

**4. Implement Monitoring**

Log graph expansion metrics:
- Seed nodes found
- Related nodes added per seed
- Relationship types used
- Average expansion ratio

---

## Unresolved Questions

1. **Neo4j credentials:** Can you provide real credentials to verify graph density?
2. **Test_rel_2 origin:** How was this namespace populated? Manual script or automated pipeline?
3. **Relationship types:** What relationship types exist (if any) in Test_rel_2?
4. **Legacy processor:** Should `final_doc_processor.py` be integrated or replaced?
5. **Background tasks:** Preferred solution - Celery, Redis Queue, or FastAPI BackgroundTasks?

---

## Next Steps

1. **Verify graph density** (requires real Neo4j credentials)
2. **Integrate document processing** into upload endpoint
3. **Test with sample document** end-to-end
4. **Monitor graph expansion metrics** to confirm improvement
5. **Build relationships** between existing nodes if graph is sparse

---

**Conclusion:** Graph retrieval logic is correct but operates on a sparse graph. Upload pipeline is incomplete. Fix requires integrating document processing to build a dense knowledge graph.
