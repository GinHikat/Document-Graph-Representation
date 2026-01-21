"""Document management endpoint tests."""
import pytest
import io
from fastapi.testclient import TestClient
from api.routers.documents import documents_db


class TestListDocuments:
    """Tests for GET /api/documents"""

    def test_list_documents_empty(self, client: TestClient):
        """Test listing returns empty list when no documents."""
        response = client.get("/api/documents")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_documents_with_data(self, client: TestClient, populated_documents_db):
        """Test listing returns documents when populated."""
        response = client.get("/api/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "doc_test_123"
        assert data[0]["name"] == "test_document.txt"

    def test_list_documents_filter_by_status(self, client: TestClient):
        """Test filtering by status parameter."""
        # Add documents with different statuses
        documents_db["doc1"] = {
            "id": "doc1", "name": "doc1.pdf", "status": "uploaded",
            "uploadedAt": "2026-01-01T10:00:00", "size": 100
        }
        documents_db["doc2"] = {
            "id": "doc2", "name": "doc2.pdf", "status": "processing",
            "uploadedAt": "2026-01-01T11:00:00", "size": 200
        }

        response = client.get("/api/documents?status=uploaded")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "uploaded"

    def test_list_documents_with_limit(self, client: TestClient):
        """Test limit parameter."""
        # Add multiple documents
        for i in range(5):
            documents_db[f"doc{i}"] = {
                "id": f"doc{i}", "name": f"doc{i}.pdf", "status": "uploaded",
                "uploadedAt": f"2026-01-0{i+1}T10:00:00", "size": 100
            }

        response = client.get("/api/documents?limit=2")

        assert response.status_code == 200
        assert len(response.json()) == 2


class TestUploadDocument:
    """Tests for POST /api/documents/upload"""

    def test_upload_document_pdf(self, client: TestClient):
        """Test uploading a valid PDF file."""
        # Create fake PDF content
        pdf_content = b"%PDF-1.4 fake pdf content"
        files = {"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}

        response = client.post("/api/documents/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "taskId" in data
        assert len(data["documents"]) == 1
        assert data["documents"][0]["name"] == "test.pdf"
        assert data["documents"][0]["status"] == "uploaded"

    def test_upload_document_txt(self, client: TestClient):
        """Test uploading a valid TXT file."""
        txt_content = b"Sample text content"
        files = {"files": ("test.txt", io.BytesIO(txt_content), "text/plain")}

        response = client.post("/api/documents/upload", files=files)

        assert response.status_code == 200
        assert response.json()["documents"][0]["name"] == "test.txt"

    def test_upload_document_docx(self, client: TestClient):
        """Test uploading a valid DOCX file."""
        docx_content = b"PK\\x03\\x04 fake docx"
        files = {"files": ("test.docx", io.BytesIO(docx_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

        response = client.post("/api/documents/upload", files=files)

        assert response.status_code == 200

    def test_upload_multiple_documents(self, client: TestClient):
        """Test uploading multiple files at once."""
        files = [
            ("files", ("doc1.pdf", io.BytesIO(b"%PDF content1"), "application/pdf")),
            ("files", ("doc2.pdf", io.BytesIO(b"%PDF content2"), "application/pdf")),
        ]

        response = client.post("/api/documents/upload", files=files)

        assert response.status_code == 200
        assert len(response.json()["documents"]) == 2

    def test_upload_invalid_extension(self, client: TestClient):
        """Test upload fails for disallowed file types."""
        exe_content = b"MZ fake exe"
        files = {"files": ("malware.exe", io.BytesIO(exe_content), "application/octet-stream")}

        response = client.post("/api/documents/upload", files=files)

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()


class TestGetDocument:
    """Tests for GET /api/documents/{doc_id}"""

    def test_get_document(self, client: TestClient, populated_documents_db):
        """Test retrieving document by ID."""
        response = client.get("/api/documents/doc_test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc_test_123"
        assert data["name"] == "test_document.txt"

    def test_get_document_not_found(self, client: TestClient):
        """Test 404 for non-existent document."""
        response = client.get("/api/documents/nonexistent_id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDeleteDocument:
    """Tests for DELETE /api/documents/{doc_id}"""

    def test_delete_document(self, client: TestClient, populated_documents_db):
        """Test deleting existing document."""
        response = client.delete("/api/documents/doc_test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == True
        assert data["id"] == "doc_test_123"

        # Verify document is gone
        assert "doc_test_123" not in documents_db

    def test_delete_document_not_found(self, client: TestClient):
        """Test 404 when deleting non-existent document."""
        response = client.delete("/api/documents/nonexistent_id")

        assert response.status_code == 404


class TestBatchDeleteDocuments:
    """Tests for POST /api/documents/batch-delete"""

    def test_batch_delete_documents(self, client: TestClient):
        """Test batch deletion of multiple documents."""
        # Setup: Add documents
        for i in range(3):
            documents_db[f"doc{i}"] = {
                "id": f"doc{i}", "name": f"doc{i}.pdf", "status": "uploaded",
                "uploadedAt": "2026-01-01T10:00:00", "size": 100
            }

        response = client.post("/api/documents/batch-delete", json=["doc0", "doc1"])

        assert response.status_code == 200
        data = response.json()
        assert set(data["deleted"]) == {"doc0", "doc1"}
        assert data["notFound"] == []

        # Verify doc2 still exists
        assert "doc2" in documents_db

    def test_batch_delete_partial_not_found(self, client: TestClient):
        """Test batch delete with some non-existent IDs."""
        documents_db["existing"] = {
            "id": "existing", "name": "existing.pdf", "status": "uploaded",
            "uploadedAt": "2026-01-01T10:00:00", "size": 100
        }

        response = client.post("/api/documents/batch-delete", json=["existing", "nonexistent"])

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == ["existing"]
        assert data["notFound"] == ["nonexistent"]


class TestReprocessDocument:
    """Tests for POST /api/documents/{doc_id}/reprocess"""

    def test_reprocess_document(self, client: TestClient, populated_documents_db):
        """Test triggering document reprocessing."""
        response = client.post("/api/documents/doc_test_123/reprocess")

        assert response.status_code == 200
        data = response.json()
        assert data["reprocessing"] == True
        assert data["id"] == "doc_test_123"

        # Background task runs synchronously in test mode, so status may already be updated
        # Check that status is either "processing" (queued) or "completed"/"failed" (task ran)
        status = documents_db["doc_test_123"]["status"]
        assert status in ["processing", "completed", "failed"]

    def test_reprocess_document_not_found(self, client: TestClient):
        """Test 404 when reprocessing non-existent document."""
        response = client.post("/api/documents/nonexistent_id/reprocess")

        assert response.status_code == 404
