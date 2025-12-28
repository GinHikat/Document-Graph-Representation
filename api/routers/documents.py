"""Document management router for file uploads and listing."""
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Configuration
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# In-memory document store (replace with DB in production)
documents_db: dict = {}


class DocumentResponse(BaseModel):
    """Document response model."""
    id: str
    name: str
    status: str
    uploadedAt: str
    size: Optional[int] = None
    progress: Optional[int] = None


class UploadResponse(BaseModel):
    """Upload response model."""
    documents: List[DocumentResponse]
    taskId: str


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more documents.

    Accepts PDF, DOCX, and TXT files.
    Returns document metadata and a task ID for tracking processing.
    """
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    results = []
    task_id = f"task_{uuid.uuid4().hex[:8]}"

    for file in files:
        # Validate filename exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Sanitize filename - remove path components to prevent path traversal
        safe_name = Path(file.filename).name
        if not safe_name or safe_name.startswith('.'):
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Validate file extension
        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {ext} not allowed. Allowed: {allowed_extensions}"
            )

        # Generate unique ID and safe filepath
        doc_id = str(uuid.uuid4())
        safe_filename = f"{doc_id}_{safe_name}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)

        # Verify filepath is within UPLOAD_DIR (prevent path traversal)
        if not os.path.abspath(filepath).startswith(os.path.abspath(UPLOAD_DIR)):
            raise HTTPException(status_code=400, detail="Invalid filename")

        try:
            content = await file.read()

            # Check file size
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
                )

            with open(filepath, "wb") as f:
                f.write(content)

            file_size = len(content)

            # Store document metadata
            doc_data = {
                "id": doc_id,
                "name": file.filename,
                "status": "uploaded",
                "uploadedAt": datetime.now().isoformat(),
                "size": file_size,
                "filepath": filepath,
                "progress": 0
            }
            documents_db[doc_id] = doc_data

            results.append(DocumentResponse(
                id=doc_id,
                name=file.filename or "unknown",
                status="uploaded",
                uploadedAt=doc_data["uploadedAt"],
                size=file_size
            ))

            logger.info(f"Uploaded document: {file.filename} (ID: {doc_id})")

        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return UploadResponse(documents=results, taskId=task_id)


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List all uploaded documents.

    Optionally filter by status: uploaded, processing, completed, failed
    """
    docs = list(documents_db.values())

    if status:
        docs = [d for d in docs if d.get("status") == status]

    # Sort by upload date descending
    docs.sort(key=lambda x: x.get("uploadedAt", ""), reverse=True)

    return [
        DocumentResponse(
            id=d["id"],
            name=d["name"],
            status=d["status"],
            uploadedAt=d["uploadedAt"],
            size=d.get("size"),
            progress=d.get("progress")
        )
        for d in docs[:limit]
    ]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get a specific document by ID."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    d = documents_db[doc_id]
    return DocumentResponse(
        id=d["id"],
        name=d["name"],
        status=d["status"],
        uploadedAt=d["uploadedAt"],
        size=d.get("size"),
        progress=d.get("progress")
    )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document by ID."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_db[doc_id]

    # Delete file from disk
    filepath = doc.get("filepath")
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(f"Deleted file: {filepath}")
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {e}")

    # Remove from DB
    del documents_db[doc_id]

    return {"deleted": True, "id": doc_id}


@router.post("/batch-delete")
async def batch_delete_documents(doc_ids: List[str]):
    """Delete multiple documents by IDs."""
    deleted = []
    not_found = []

    for doc_id in doc_ids:
        if doc_id in documents_db:
            doc = documents_db[doc_id]
            filepath = doc.get("filepath")

            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.error(f"Failed to delete file {filepath}: {e}")

            del documents_db[doc_id]
            deleted.append(doc_id)
        else:
            not_found.append(doc_id)

    return {"deleted": deleted, "notFound": not_found}


@router.post("/{doc_id}/reprocess")
async def reprocess_document(doc_id: str):
    """
    Trigger reprocessing of a document.

    Resets status to 'processing' and queues for re-extraction.
    """
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    documents_db[doc_id]["status"] = "processing"
    documents_db[doc_id]["progress"] = 0

    # TODO: Queue background task for processing

    return {"reprocessing": True, "id": doc_id}
