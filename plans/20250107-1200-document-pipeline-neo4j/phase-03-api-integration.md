# Phase 3: API Integration

**Parent:** [plan.md](./plan.md)
**Dependencies:** [Phase 1](./phase-01-document-processing-service.md), [Phase 2](./phase-02-neo4j-indexing.md)
**Date:** 2026-01-07
**Priority:** High
**Status:** Pending

## Overview

Hook document processing and Neo4j indexing into the upload endpoint. Use FastAPI `BackgroundTasks` (no Celery/Redis - KISS principle). Update document status as processing progresses.

## Key Insights

1. **Existing upload endpoint** - `api/routers/documents.py:41-121` saves file + returns immediately
2. **Status tracking** - In-memory `documents_db` dict (L22) - sufficient for MVP
3. **Reprocess endpoint exists** - `POST /api/documents/{doc_id}/reprocess` (L220-235) has TODO
4. **BackgroundTasks** - FastAPI native, no infrastructure needed

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1 | Trigger indexing on upload automatically | High |
| R2 | Update document status: uploaded -> processing -> completed/failed | High |
| R3 | Track progress percentage (0-100) | Medium |
| R4 | Support reprocessing via existing endpoint | Medium |
| R5 | Non-blocking - upload returns immediately | High |
| R6 | Error handling with status update to "failed" | High |

## Architecture

```
POST /api/documents/upload
    |
    +-- Save file to disk
    +-- Store metadata in documents_db (status: "uploaded")
    +-- background_tasks.add_task(process_document, doc_id, filepath)
    +-- Return 200 immediately
           |
           +-- [BackgroundTask] process_document(doc_id, filepath)
                   |
                   +-- Update status: "processing", progress: 10
                   +-- Extract text (DocumentProcessorService)
                   +-- Update progress: 30
                   +-- Parse structure
                   +-- Update progress: 50
                   +-- Index to Neo4j (Neo4jIndexerService)
                   +-- Update progress: 90
                   +-- Update status: "completed", progress: 100
                   |
                   +-- On error: status: "failed", error message
```

## Related Code Files

| File | Lines | Purpose |
|------|-------|---------|
| `api/routers/documents.py` | 41-121 | Upload endpoint - add BackgroundTask |
| `api/routers/documents.py` | 220-235 | Reprocess endpoint - implement TODO |
| `api/routers/documents.py` | 22-23 | `documents_db` - status storage |
| `api/main.py` | 1-143 | App setup - no changes needed |

## Implementation Steps

### Step 1: Create Processing Function

Create `api/services/document_pipeline.py`:

```python
"""Document processing pipeline for background execution."""
import logging
from typing import Dict, Any

from api.routers.documents import documents_db
from api.services.document_processor import DocumentProcessorService
from api.services.neo4j_indexer import Neo4jIndexerService

logger = logging.getLogger(__name__)


def process_document(doc_id: str, filepath: str) -> Dict[str, Any]:
    """
    Full document processing pipeline.
    Updates documents_db with progress/status.
    """
    try:
        # Update status
        _update_doc(doc_id, status="processing", progress=10)

        # Initialize services
        processor = DocumentProcessorService()
        indexer = Neo4jIndexerService()

        # Step 1: Extract text
        logger.info(f"Extracting text from {filepath}")
        text = processor.extract_text(filepath)
        _update_doc(doc_id, progress=30)

        # Step 2: Get metadata
        metadata = processor.get_metadata(text)
        metadata["doc_id"] = doc_id
        _update_doc(doc_id, progress=40)

        # Step 3: Parse structure
        parsed = processor.parse_structure(text)
        _update_doc(doc_id, progress=50)

        # Step 4: Index to Neo4j
        logger.info(f"Indexing document {doc_id} to Neo4j")
        stats = indexer.index_document(
            doc_id=metadata.get("law_id", doc_id),
            text=text,
            parsed=parsed,
            metadata=metadata
        )
        _update_doc(doc_id, progress=90)

        # Done
        _update_doc(doc_id, status="completed", progress=100, neo4j_stats=stats)
        logger.info(f"Document {doc_id} indexed: {stats}")
        return {"success": True, "stats": stats}

    except Exception as e:
        logger.error(f"Failed to process document {doc_id}: {e}", exc_info=True)
        _update_doc(doc_id, status="failed", error=str(e))
        return {"success": False, "error": str(e)}


def _update_doc(doc_id: str, **updates):
    """Update document in documents_db."""
    if doc_id in documents_db:
        documents_db[doc_id].update(updates)
```

### Step 2: Modify Upload Endpoint

Edit `api/routers/documents.py`:

```python
# Add import at top
from fastapi import BackgroundTasks
from api.services.document_pipeline import process_document

# Modify upload_documents signature
@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None  # Add this
):
    # ... existing file saving logic (lines 48-113) ...

    # After saving file, add to line ~115:
    if background_tasks:
        background_tasks.add_task(process_document, doc_id, filepath)
        documents_db[doc_id]["status"] = "queued"

    # ... rest of function ...
```

### Step 3: Implement Reprocess Endpoint

Update `api/routers/documents.py:220-235`:

```python
@router.post("/{doc_id}/reprocess")
async def reprocess_document(
    doc_id: str,
    background_tasks: BackgroundTasks
):
    """Trigger reprocessing of a document."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_db[doc_id]
    filepath = doc.get("filepath")

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=400, detail="Source file not found")

    # Reset status and queue
    documents_db[doc_id]["status"] = "queued"
    documents_db[doc_id]["progress"] = 0
    documents_db[doc_id].pop("error", None)

    background_tasks.add_task(process_document, doc_id, filepath)

    return {"reprocessing": True, "id": doc_id}
```

### Step 4: Add Status Polling Endpoint (Optional)

```python
@router.get("/{doc_id}/status")
async def get_document_status(doc_id: str):
    """Get detailed processing status."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_db[doc_id]
    return {
        "id": doc_id,
        "status": doc.get("status"),
        "progress": doc.get("progress", 0),
        "error": doc.get("error"),
        "neo4j_stats": doc.get("neo4j_stats")
    }
```

### Step 5: Update DocumentResponse Schema

```python
class DocumentResponse(BaseModel):
    """Document response model."""
    id: str
    name: str
    status: str  # uploaded, queued, processing, completed, failed
    uploadedAt: str
    size: Optional[int] = None
    progress: Optional[int] = None
    error: Optional[str] = None  # Add this
```

## Todo

- [ ] Create `api/services/document_pipeline.py`
- [ ] Add `BackgroundTasks` to upload endpoint
- [ ] Implement reprocess endpoint logic
- [ ] Add `/status` endpoint for polling
- [ ] Update `DocumentResponse` schema
- [ ] Add integration tests for async flow
- [ ] Test error handling (file not found, Neo4j down)

## Success Criteria

1. Upload returns 200 immediately, processing happens in background
2. `GET /api/documents/{id}` shows status progression
3. `GET /api/documents/{id}/status` shows detailed progress
4. Reprocess works for completed/failed documents
5. Failed documents have error message in status
6. Existing tests still pass

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| BackgroundTask silently fails | Medium | High | Try/catch + status update |
| documents_db lost on restart | High | Medium | TODO: persist to DB in future |
| Concurrent processing same doc | Low | Medium | Check status before reprocess |
| Memory leak from hanging tasks | Low | Medium | Timeout wrapper (future) |

## Security Considerations

1. **No user input in background task** - Only doc_id and filepath (both generated server-side)
2. **Status updates atomic** - Single dict update, no race conditions for MVP
3. **Error messages sanitized** - Don't expose internal paths

## Next Steps

After completion:
1. Proceed to [Phase 4: Data Reimport](./phase-04-data-reimport.md)
2. Pipeline ready for production uploads
3. Consider adding persistence for documents_db
