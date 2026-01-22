# Action Plan: Fix Vector-Graph Similarity Issue

**Date:** 2026-01-07
**Priority:** HIGH
**Estimated Effort:** 2-3 days

---

## Root Cause

Graph-enhanced RAG returns similar results to vector-only because:
1. Neo4j graph is sparse (few/no relationships between nodes)
2. Document upload pipeline is incomplete - files saved but NOT indexed
3. No background processing to chunk, embed, and index documents

---

## Action Items

### Phase 1: Verify Graph State (30 mins)

**Task 1.1: Check Neo4j credentials**
- [ ] Get real Neo4j credentials (not placeholders)
- [ ] Update `.env` file with valid `NEO4J_URI` and `NEO4J_AUTH`

**Task 1.2: Query graph statistics**
```bash
# Run this Python script to verify graph density
python3 -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=('neo4j', os.getenv('NEO4J_AUTH')))

with driver.session() as session:
    nodes = session.run('MATCH (n:Test_rel_2) RETURN count(n) as count').single()['count']
    rels = session.run('MATCH (:Test_rel_2)-[r]-() RETURN count(r) as count').single()['count']
    rel_types = session.run('MATCH (:Test_rel_2)-[r]-() RETURN type(r) as type, count(*) as count').data()

    print(f'Nodes: {nodes}')
    print(f'Relationships: {rels}')
    print(f'Avg connections: {rels/nodes if nodes > 0 else 0:.2f}')
    print('Relationship types:', rel_types)

driver.close()
"
```

**Expected findings:**
- If relationships < 100: Graph is too sparse
- If avg connections < 1: Graph expansion adds minimal value

---

### Phase 2: Build Document Processing Service (4-6 hours)

**Task 2.1: Create document processor service**

File: `api/services/document_processor.py`

```python
import logging
from typing import List, Dict
from api.db.neo4j import get_neo4j_client
from api.services.embedding import embed_chunks
import PyPDF2
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.neo4j = get_neo4j_client()

    def extract_text(self, filepath: str) -> str:
        """Extract text from PDF/DOCX/TXT"""
        ext = filepath.lower().split('.')[-1]

        if ext == 'pdf':
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return '\n'.join(page.extract_text() for page in reader.pages)
        elif ext in ['docx', 'doc']:
            doc = DocxDocument(filepath)
            return '\n'.join(para.text for para in doc.paragraphs)
        elif ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    def index_to_neo4j(self, doc_id: str, chunks: List[str], embeddings: List[List[float]], namespace: str = "Test_rel_2"):
        """Index chunks to Neo4j with embeddings"""
        query = f"""
        UNWIND $chunks AS chunk
        CREATE (n:{namespace} {{
            id: chunk.id,
            text: chunk.text,
            original_embedding: chunk.embedding,
            document_id: $doc_id,
            chunk_index: chunk.index
        }})
        """

        chunk_data = [
            {
                "id": f"{doc_id}_chunk_{i}",
                "text": chunk,
                "embedding": emb,
                "index": i
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

        self.neo4j.execute_query(query, {"chunks": chunk_data, "doc_id": doc_id})
        logger.info(f"Indexed {len(chunks)} chunks for document {doc_id}")

    def create_relationships(self, doc_id: str, namespace: str = "Test_rel_2"):
        """Create relationships between chunks"""

        # 1. Sequential relationships (FOLLOWS)
        follows_query = f"""
        MATCH (a:{namespace}), (b:{namespace})
        WHERE a.document_id = $doc_id AND b.document_id = $doc_id
        AND b.chunk_index = a.chunk_index + 1
        CREATE (a)-[:FOLLOWS]->(b)
        """
        self.neo4j.execute_query(follows_query, {"doc_id": doc_id})

        # 2. Semantic similarity relationships (SIMILAR_TO)
        # Find similar chunks across documents
        similarity_query = f"""
        MATCH (a:{namespace}), (b:{namespace})
        WHERE a.document_id = $doc_id
        AND b.id <> a.id
        AND a.original_embedding IS NOT NULL
        AND b.original_embedding IS NOT NULL
        WITH a, b, gds.similarity.cosine(a.original_embedding, b.original_embedding) AS sim
        WHERE sim > 0.85
        CREATE (a)-[:SIMILAR_TO {{score: sim}}]->(b)
        """
        self.neo4j.execute_query(similarity_query, {"doc_id": doc_id})

        logger.info(f"Created relationships for document {doc_id}")

    async def process_document(self, doc_id: str, filepath: str, namespace: str = "Test_rel_2"):
        """Full processing pipeline"""
        try:
            # 1. Extract text
            logger.info(f"Extracting text from {filepath}")
            text = self.extract_text(filepath)

            # 2. Chunk
            logger.info(f"Chunking document {doc_id}")
            chunks = self.chunk_text(text, chunk_size=512, overlap=50)

            # 3. Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = embed_chunks(chunks)

            # 4. Index to Neo4j
            logger.info(f"Indexing to Neo4j namespace {namespace}")
            self.index_to_neo4j(doc_id, chunks, embeddings, namespace)

            # 5. Create relationships
            logger.info(f"Creating relationships")
            self.create_relationships(doc_id, namespace)

            return {"status": "completed", "chunks": len(chunks)}

        except Exception as e:
            logger.error(f"Processing failed for {doc_id}: {e}")
            raise

# Singleton
_processor = None

def get_document_processor() -> DocumentProcessor:
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
```

**Task 2.2: Create embedding service**

File: `api/services/embedding.py`

```python
import os
from typing import List
from sentence_transformers import SentenceTransformer

# Use BGE-M3 model (same as evaluation)
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('BAAI/bge-m3')
    return _model

def embed_query(text: str) -> List[float]:
    """Embed single query"""
    model = get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()

def embed_chunks(texts: List[str]) -> List[List[float]]:
    """Embed multiple chunks"""
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()
```

---

### Phase 3: Integrate with Upload Endpoint (1 hour)

**Task 3.1: Update documents router**

File: `api/routers/documents.py`

```python
from fastapi import BackgroundTasks  # Add import
from api.services.document_processor import get_document_processor

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None  # Add parameter
):
    processor = get_document_processor()
    results = []

    for file in files:
        # ... existing file validation ...

        # Save file (existing code)
        with open(filepath, "wb") as f:
            f.write(content)

        # Store metadata
        doc_data = {
            "id": doc_id,
            "name": file.filename,
            "status": "processing",  # Changed from "uploaded"
            "uploadedAt": datetime.now().isoformat(),
            "size": file_size,
            "filepath": filepath,
            "progress": 0
        }
        documents_db[doc_id] = doc_data

        # Queue background processing
        if background_tasks:
            background_tasks.add_task(
                process_document_background,
                doc_id,
                filepath
            )

        results.append(DocumentResponse(...))

    return UploadResponse(documents=results, taskId=task_id)

async def process_document_background(doc_id: str, filepath: str):
    """Background task for processing"""
    from api.routers.documents import documents_db

    try:
        processor = get_document_processor()
        result = await processor.process_document(doc_id, filepath)

        documents_db[doc_id]["status"] = "completed"
        documents_db[doc_id]["progress"] = 100
        logger.info(f"Document {doc_id} processing completed: {result}")

    except Exception as e:
        documents_db[doc_id]["status"] = "failed"
        logger.error(f"Document {doc_id} processing failed: {e}")
```

---

### Phase 4: Testing (2 hours)

**Task 4.1: Test document upload and indexing**

```bash
# 1. Upload test document
curl -X POST http://localhost:8000/api/documents/upload \
  -F "files=@test_document.pdf"

# 2. Check processing status
curl http://localhost:8000/api/documents

# 3. Verify Neo4j indexing
# Query Neo4j to confirm chunks were created
```

**Task 4.2: Test RAG comparison**

```bash
# Compare vector vs graph retrieval
curl -X POST http://localhost:8000/api/rag/compare \
  -H "Content-Type: application/json" \
  -d '{"question": "Test question about uploaded document"}'

# Verify:
# - graph.metrics.graphNodesUsed > 5
# - graph.graphContext has entries
# - graph.answer differs from vector.answer
```

**Task 4.3: Verify graph expansion**

```python
# Check that related nodes are found
from api.db.neo4j import get_neo4j_client

client = get_neo4j_client()

# Query for a sample document
result = client.execute_query("""
MATCH (seed:Test_rel_2 {document_id: $doc_id})
OPTIONAL MATCH (seed)-[r]-(related:Test_rel_2)
RETURN seed.id, type(r) as relType, count(related) as related_count
LIMIT 10
""", {"doc_id": "your_doc_id"})

print(result)
# Expected: Each seed should have 2-10 related nodes
```

---

### Phase 5: Performance Optimization (1 day - optional)

**Task 5.1: Add progress tracking**

Update document processor to report progress:

```python
def update_progress(doc_id: str, progress: int, status: str):
    documents_db[doc_id]["progress"] = progress
    documents_db[doc_id]["status"] = status

# In process_document:
update_progress(doc_id, 20, "extracting")  # After text extraction
update_progress(doc_id, 40, "chunking")    # After chunking
update_progress(doc_id, 60, "embedding")   # After embedding
update_progress(doc_id, 80, "indexing")    # After Neo4j indexing
update_progress(doc_id, 100, "completed")  # After relationships
```

**Task 5.2: Add batch processing**

For large documents, process in batches:

```python
def index_to_neo4j_batch(chunks, embeddings, batch_size=100):
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_embs = embeddings[i:i+batch_size]
        # ... index batch ...
        yield i + len(batch_chunks)  # Progress
```

---

## Dependencies

**Python packages to add:**

```bash
# requirements.txt
PyPDF2>=3.0.0
python-docx>=1.1.0
sentence-transformers>=2.2.2
```

**Install:**
```bash
cd /path/to/project
pip install PyPDF2 python-docx sentence-transformers
```

---

## Success Criteria

- [ ] Documents uploaded via `/api/documents/upload` are indexed to Neo4j
- [ ] Each document creates 20-100 chunks in Neo4j (depends on size)
- [ ] Chunks have relationships: FOLLOWS (sequential), SIMILAR_TO (semantic)
- [ ] Graph stats show relationship count increasing after uploads
- [ ] `/api/rag/compare` returns `graphNodesUsed > 5` for most queries
- [ ] Graph answer differs from vector answer (qualitatively better)

---

## Rollback Plan

If issues occur:

1. Disable background processing:
   ```python
   # Comment out background_tasks.add_task() in upload endpoint
   ```

2. Revert to in-memory status:
   ```python
   documents_db[doc_id]["status"] = "uploaded"  # Not "processing"
   ```

3. Manual cleanup of test data:
   ```cypher
   MATCH (n:Test_rel_2 {document_id: "test_doc_id"})
   DETACH DELETE n
   ```

---

## Timeline

| Phase | Effort | Timeline |
|-------|--------|----------|
| Phase 1: Verify graph state | 30 mins | Day 1 morning |
| Phase 2: Build processor | 4-6 hours | Day 1 afternoon |
| Phase 3: Integrate upload | 1 hour | Day 2 morning |
| Phase 4: Testing | 2 hours | Day 2 afternoon |
| Phase 5: Optimization | 1 day | Day 3 (optional) |

**Total:** 2-3 days

---

## Next Steps

1. Get Neo4j credentials to verify current graph state
2. Create document processor service with chunking/embedding
3. Integrate processor with upload endpoint
4. Test end-to-end with sample document
5. Monitor graph expansion metrics
