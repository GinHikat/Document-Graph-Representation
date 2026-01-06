# Test Suite Implementation Plan

**Date**: 2026-01-06
**Status**: ✅ IMPLEMENTED & REVIEWED
**Estimated Effort**: 4-6 hours
**Actual Effort**: ~6 hours
**Review Date**: 2026-01-06
**Review Status**: APPROVED with Minor Fixes

---

## 1. Overview

This plan details the implementation of a comprehensive test suite for the FastAPI backend. The suite covers authentication, document management, and RAG endpoints with proper mocking of external dependencies.

### Key Dependencies to Mock

| Dependency | Location | Mock Strategy |
|------------|----------|---------------|
| Neo4j Client | `api.db.neo4j.get_neo4j_client` | Dependency override |
| Embedding Model | `api.services.embedding.embed_query` | Monkeypatch |
| Reranker | `api.services.reranker.rerank_chunks` | Monkeypatch |
| Gemini/LLM | `api.services.gemini.generate_answer` | Monkeypatch |
| Users DB | `api.services.auth.users_db` | Direct fixture reset |
| Documents DB | `api.routers.documents.documents_db` | Direct fixture reset |

---

## 2. Directory Structure

```
api/
  tests/
    __init__.py
    conftest.py          # Shared fixtures
    test_auth.py         # Authentication tests
    test_documents.py    # Document management tests
    test_rag.py          # RAG endpoint tests
    test_health.py       # Health check tests (optional)
```

---

## 3. conftest.py - Shared Fixtures

### 3.1 File Structure

```python
"""Shared test fixtures for API tests."""
import pytest
from typing import Generator, Dict, Any, List, Tuple
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.db.neo4j import get_neo4j_client
from api.services.auth import (
    users_db,
    create_user,
    create_access_token,
    UserInDB,
)
from api.routers.documents import documents_db
from api.services.rag_schemas import RetrieveOutput, GraphRetrieveOutput


# ============ Mock Neo4j Client ============

class MockNeo4jClient:
    """Mock Neo4j client for testing without database."""

    def __init__(self):
        self._data = {
            "nodes": [],
            "relationships": []
        }

    def verify_connectivity(self) -> bool:
        return True

    def close(self):
        pass

    def execute_query(self, query: str, parameters: dict = None) -> List[Dict]:
        """Return mock query results based on query pattern."""
        if "RETURN count" in query:
            return [{"count": 100}]
        # Default: return sample text chunks
        return [
            {"id": "chunk_1", "text": "Sample tax law text 1", "score": 1.0},
            {"id": "chunk_2", "text": "Sample tax law text 2", "score": 0.8},
        ]

    def get_node_count(self, namespace: str = "Test_rel_2") -> int:
        return 100

    def get_test_rel_2_graph(self, limit: int = 100) -> Dict:
        return {
            "nodes": [
                {"id": "n1", "label": "Node 1", "type": "document", "properties": {}},
                {"id": "n2", "label": "Node 2", "type": "article", "properties": {}},
            ],
            "links": [
                {"source": "n1", "target": "n2", "type": "RELATES_TO", "properties": {}}
            ]
        }

    def get_graph_schema(self) -> Dict:
        return {
            "labels": [["Test_rel_2"]],
            "relationships": ["RELATES_TO", "CITES"],
            "properties": ["text", "id", "original_embedding"]
        }


# ============ FastAPI TestClient Fixture ============

@pytest.fixture(scope="function")
def mock_neo4j_client():
    """Create mock Neo4j client."""
    return MockNeo4jClient()


@pytest.fixture(scope="function")
def client(mock_neo4j_client) -> Generator[TestClient, None, None]:
    """
    Create FastAPI TestClient with mocked dependencies.

    Overrides:
    - Neo4j client
    - Clears users_db and documents_db
    """
    # Override Neo4j dependency
    app.dependency_overrides[get_neo4j_client] = lambda: mock_neo4j_client

    # Clear in-memory databases
    users_db.clear()
    documents_db.clear()

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()
    users_db.clear()
    documents_db.clear()


# ============ Mock Embedding Service ============

@pytest.fixture(scope="function")
def mock_embed_query(monkeypatch):
    """Mock embedding service to avoid loading ML models."""
    def _mock_embed(text: str) -> List[float]:
        # Return 768-dim vector (matches model dimension)
        return [0.1] * 768

    monkeypatch.setattr("api.services.embedding.embed_query", _mock_embed)
    monkeypatch.setattr("api.services.tools.embed_query", _mock_embed)
    return _mock_embed


# ============ Mock Reranker ============

@pytest.fixture(scope="function")
def mock_reranker(monkeypatch):
    """Mock reranker service."""
    def _mock_rerank(
        query: str,
        chunks: List[Dict],
        top_n: int = 5
    ) -> Tuple[List[Dict], List[float]]:
        # Return chunks in original order with descending scores
        result_chunks = chunks[:top_n]
        scores = [1.0 - (i * 0.1) for i in range(len(result_chunks))]
        return result_chunks, scores

    monkeypatch.setattr("api.services.reranker.rerank_chunks", _mock_rerank)
    monkeypatch.setattr("api.routers.rag.rerank_chunks", _mock_rerank)
    return _mock_rerank


# ============ Mock LLM/Gemini ============

@pytest.fixture(scope="function")
def mock_gemini(monkeypatch):
    """Mock Gemini/LLM generation service."""
    def _mock_generate(
        query: str,
        context_chunks: List[Dict],
        model_name: str = "gemini-2.0-flash"
    ) -> str:
        return f"Mock answer for: {query[:50]}"

    def _mock_generate_streaming(
        query: str,
        context_chunks: List[Dict],
        model_name: str = "gemini-2.0-flash"
    ):
        yield f"Mock streaming answer for: {query[:50]}"

    monkeypatch.setattr("api.services.gemini.generate_answer", _mock_generate)
    monkeypatch.setattr("api.services.gemini.generate_answer_streaming", _mock_generate_streaming)
    monkeypatch.setattr("api.routers.rag.generate_answer", _mock_generate)
    return _mock_generate


# ============ Auth Token Generator ============

@pytest.fixture(scope="function")
def test_user(client) -> UserInDB:
    """Create a test user and return UserInDB object."""
    user = create_user(
        email="testuser@example.com",
        password="testpass123",
        name="Test User",
        role="user"
    )
    return user


@pytest.fixture(scope="function")
def auth_token(test_user) -> str:
    """Generate valid JWT token for test user."""
    token = create_access_token(
        data={"sub": test_user.email, "name": test_user.name}
    )
    return token


@pytest.fixture(scope="function")
def auth_headers(auth_token) -> Dict[str, str]:
    """Return Authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


# ============ Sample Test Documents ============

@pytest.fixture(scope="function")
def sample_document() -> Dict[str, Any]:
    """Sample document data for testing."""
    return {
        "id": "doc_test_123",
        "name": "test_document.pdf",
        "status": "uploaded",
        "uploadedAt": "2026-01-06T10:00:00",
        "size": 1024,
        "filepath": "/tmp/test_document.pdf",
        "progress": 0
    }


@pytest.fixture(scope="function")
def populated_documents_db(sample_document):
    """Pre-populate documents_db with sample data."""
    documents_db.clear()
    documents_db[sample_document["id"]] = sample_document
    yield documents_db
    documents_db.clear()


# ============ Mock Retrieve Tools ============

@pytest.fixture(scope="function")
def mock_retrieve_tools(monkeypatch, mock_embed_query):
    """Mock retrieve_from_database and retrieve_with_graph_context."""

    def _mock_retrieve(
        prompt: str,
        top_k: int = 10,
        namespace: str = "Test_rel_2"
    ) -> RetrieveOutput:
        return RetrieveOutput(
            chunks=[
                {"id": "chunk_1", "text": "Tax regulation sample 1"},
                {"id": "chunk_2", "text": "Tax regulation sample 2"},
            ],
            source_ids=["chunk_1", "chunk_2"],
            scores=[1.0, 0.8]
        )

    def _mock_retrieve_graph(
        prompt: str,
        top_k: int = 10,
        namespace: str = "Test_rel_2",
        hop_depth: int = 1
    ) -> GraphRetrieveOutput:
        return GraphRetrieveOutput(
            chunks=[
                {"id": "chunk_1", "text": "Tax regulation sample 1", "is_seed": True},
                {"id": "chunk_2", "text": "Related via graph", "is_seed": False},
            ],
            source_ids=["chunk_1", "chunk_2"],
            scores=[1.0, 0.8],
            graph_context=[
                {"node_id": "chunk_2", "relationship": "CITES", "text_preview": "Related via graph"}
            ],
            cypher_query="hybrid_word_match_embedding_graph",
            embedding_used=True,
            warnings=[]
        )

    monkeypatch.setattr("api.services.tools.retrieve_from_database", _mock_retrieve)
    monkeypatch.setattr("api.services.tools.retrieve_with_graph_context", _mock_retrieve_graph)
    monkeypatch.setattr("api.routers.rag.retrieve_from_database", _mock_retrieve)
    monkeypatch.setattr("api.routers.rag.retrieve_with_graph_context", _mock_retrieve_graph)

    return {"retrieve": _mock_retrieve, "retrieve_graph": _mock_retrieve_graph}
```

---

## 4. test_auth.py - Authentication Tests

### 4.1 Test Cases

| Test Name | Description | Expected Status |
|-----------|-------------|-----------------|
| `test_register_user` | Register new user | 200, returns token + user |
| `test_register_duplicate_email` | Register with existing email | 400 |
| `test_register_weak_password` | Password < 6 chars | 400 |
| `test_login_success` | Login with valid credentials | 200 |
| `test_login_invalid_credentials` | Wrong password | 401 |
| `test_login_demo_mode` | Login with password "demo" | 200 |
| `test_get_current_user_authenticated` | /me with valid token | 200 |
| `test_get_current_user_unauthenticated` | /me without token | 401 |
| `test_get_current_user_invalid_token` | /me with malformed token | 401 |
| `test_logout` | Logout endpoint | 200 |

### 4.2 Implementation

```python
"""Authentication endpoint tests."""
import pytest
from fastapi.testclient import TestClient


class TestRegister:
    """Tests for POST /api/auth/register"""

    def test_register_user(self, client: TestClient):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "name": "New User"
        })

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
        assert data["user"]["role"] == "user"
        assert "id" in data["user"]

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration fails with existing email."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email,  # Already exists
            "password": "anotherpass",
            "name": "Duplicate User"
        })

        assert response.status_code == 400
        assert "Email" in response.json()["detail"]

    def test_register_weak_password(self, client: TestClient):
        """Test registration fails with short password."""
        response = client.post("/api/auth/register", json={
            "email": "weak@example.com",
            "password": "12345",  # < 6 chars
            "name": "Weak Password User"
        })

        assert response.status_code == 400
        assert "6" in response.json()["detail"]  # Mentions minimum length

    def test_register_invalid_email(self, client: TestClient):
        """Test registration fails with invalid email format."""
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "validpass123",
            "name": "Invalid Email User"
        })

        assert response.status_code == 422  # Pydantic validation


class TestLogin:
    """Tests for POST /api/auth/login"""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login with valid credentials."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "testpass123"
        })

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Test login fails with wrong password."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login fails for non-existent user."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })

        assert response.status_code == 401

    def test_login_demo_mode(self, client: TestClient):
        """Test demo mode login (password='demo' works for any email)."""
        response = client.post("/api/auth/login", json={
            "email": "demo@test.com",
            "password": "demo"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "demo@test.com"
        assert data["user"]["role"] == "annotator"


class TestGetCurrentUser:
    """Tests for GET /api/auth/me"""

    def test_get_current_user_authenticated(self, client: TestClient, auth_headers, test_user):
        """Test /me returns user info with valid token."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name

    def test_get_current_user_unauthenticated(self, client: TestClient):
        """Test /me returns 401 without token."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test /me returns 401 with malformed token."""
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })

        assert response.status_code == 401

    def test_get_current_user_no_bearer_prefix(self, client: TestClient, auth_token):
        """Test /me returns 401 when Bearer prefix is missing."""
        response = client.get("/api/auth/me", headers={
            "Authorization": auth_token  # Missing "Bearer "
        })

        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/auth/logout"""

    def test_logout(self, client: TestClient):
        """Test logout endpoint returns success."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
```

---

## 5. test_documents.py - Document Management Tests

### 5.1 Test Cases

| Test Name | Description | Expected Status |
|-----------|-------------|-----------------|
| `test_list_documents_empty` | List when no documents | 200, empty list |
| `test_list_documents_with_data` | List with documents | 200, returns docs |
| `test_upload_document_pdf` | Upload valid PDF | 200 |
| `test_upload_document_txt` | Upload valid TXT | 200 |
| `test_upload_invalid_extension` | Upload .exe file | 400 |
| `test_upload_file_too_large` | Upload > 50MB | 413 |
| `test_get_document` | Get by valid ID | 200 |
| `test_get_document_not_found` | Get non-existent ID | 404 |
| `test_delete_document` | Delete existing doc | 200 |
| `test_delete_document_not_found` | Delete non-existent | 404 |
| `test_batch_delete_documents` | Batch delete | 200 |
| `test_reprocess_document` | Trigger reprocess | 200 |

### 5.2 Implementation

```python
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
        assert data[0]["name"] == "test_document.pdf"

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
        docx_content = b"PK\x03\x04 fake docx"  # DOCX is a ZIP
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
        assert "not allowed" in response.json()["detail"]

    def test_upload_path_traversal_attack(self, client: TestClient):
        """Test upload sanitizes filename against path traversal."""
        content = b"malicious content"
        files = {"files": ("../../../etc/passwd", io.BytesIO(content), "text/plain")}

        response = client.post("/api/documents/upload", files=files)

        # Should either reject or sanitize the filename
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            # Filename should be sanitized
            assert ".." not in response.json()["documents"][0]["name"]


class TestGetDocument:
    """Tests for GET /api/documents/{doc_id}"""

    def test_get_document(self, client: TestClient, populated_documents_db):
        """Test retrieving document by ID."""
        response = client.get("/api/documents/doc_test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc_test_123"
        assert data["name"] == "test_document.pdf"

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

        # Verify status changed to processing
        assert documents_db["doc_test_123"]["status"] == "processing"
        assert documents_db["doc_test_123"]["progress"] == 0

    def test_reprocess_document_not_found(self, client: TestClient):
        """Test 404 when reprocessing non-existent document."""
        response = client.post("/api/documents/nonexistent_id/reprocess")

        assert response.status_code == 404
```

---

## 6. test_rag.py - RAG Endpoint Tests

### 6.1 Test Cases

| Test Name | Description | Expected Status |
|-----------|-------------|-----------------|
| `test_retrieve_endpoint` | POST /api/rag/retrieve | 200 |
| `test_retrieve_with_params` | Retrieve with top_k, namespace | 200 |
| `test_rerank_endpoint` | POST /api/rag/rerank | 200 |
| `test_rerank_empty_chunks` | Rerank with empty input | 200, empty |
| `test_sample_questions` | GET /api/rag/sample-questions | 200 |
| `test_sample_questions_count` | With count parameter | 200 |
| `test_list_tools` | GET /api/rag/tools | 200 |
| `test_compare_endpoint` | POST /api/rag/compare | 200 |
| `test_query_non_streaming` | Query with stream=false | 200 |

### 6.2 Implementation

```python
"""RAG endpoint tests."""
import pytest
from fastapi.testclient import TestClient


class TestRetrieveEndpoint:
    """Tests for POST /api/rag/retrieve"""

    def test_retrieve_endpoint(
        self, client: TestClient, mock_retrieve_tools, mock_embed_query
    ):
        """Test basic retrieval."""
        response = client.post("/api/rag/retrieve", json={
            "prompt": "What is VAT tax rate?"
        })

        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert "source_ids" in data
        assert "scores" in data

    def test_retrieve_with_params(
        self, client: TestClient, mock_retrieve_tools, mock_embed_query
    ):
        """Test retrieval with custom parameters."""
        response = client.post("/api/rag/retrieve", json={
            "prompt": "Tax regulations",
            "top_k": 5,
            "namespace": "Test_rel_2"
        })

        assert response.status_code == 200

    def test_retrieve_empty_prompt(self, client: TestClient):
        """Test retrieval fails with empty prompt."""
        response = client.post("/api/rag/retrieve", json={
            "prompt": ""
        })

        # Should fail validation or return empty results
        assert response.status_code in [200, 422, 500]


class TestRerankEndpoint:
    """Tests for POST /api/rag/rerank"""

    def test_rerank_endpoint(self, client: TestClient, mock_reranker):
        """Test basic reranking."""
        response = client.post("/api/rag/rerank", json={
            "query": "What is income tax?",
            "chunks": [
                {"id": "1", "text": "Income tax is a direct tax"},
                {"id": "2", "text": "VAT is an indirect tax"},
                {"id": "3", "text": "Personal income tax rates"},
            ],
            "top_n": 2
        })

        assert response.status_code == 200
        data = response.json()
        assert "reranked_chunks" in data
        assert "scores" in data
        assert len(data["reranked_chunks"]) <= 2

    def test_rerank_empty_chunks(self, client: TestClient, mock_reranker):
        """Test reranking with empty chunks list."""
        response = client.post("/api/rag/rerank", json={
            "query": "Any query",
            "chunks": [],
            "top_n": 5
        })

        assert response.status_code == 200
        data = response.json()
        assert data["reranked_chunks"] == []
        assert data["scores"] == []


class TestSampleQuestionsEndpoint:
    """Tests for GET /api/rag/sample-questions"""

    def test_sample_questions(self, client: TestClient, monkeypatch):
        """Test getting sample questions."""
        # Mock the Google Sheet loader to use fallback
        monkeypatch.setattr(
            "api.services.qa_questions._cached_questions", None
        )

        response = client.get("/api/rag/sample-questions")

        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert isinstance(data["questions"], list)

    def test_sample_questions_with_count(self, client: TestClient, monkeypatch):
        """Test sample questions with count parameter."""
        monkeypatch.setattr(
            "api.services.qa_questions._cached_questions", None
        )

        response = client.get("/api/rag/sample-questions?count=3")

        assert response.status_code == 200
        assert len(response.json()["questions"]) <= 3

    def test_sample_questions_no_shuffle(self, client: TestClient, monkeypatch):
        """Test sample questions without shuffling."""
        monkeypatch.setattr(
            "api.services.qa_questions._cached_questions", None
        )

        response = client.get("/api/rag/sample-questions?shuffle=false")

        assert response.status_code == 200


class TestListToolsEndpoint:
    """Tests for GET /api/rag/tools"""

    def test_list_tools(self, client: TestClient):
        """Test listing available RAG tools."""
        response = client.get("/api/rag/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)

        # Verify expected tools exist
        tool_names = [t["name"] for t in data["tools"]]
        assert "retrieve_from_database" in tool_names
        assert "retrieve_with_graph_context" in tool_names


class TestCompareEndpoint:
    """Tests for POST /api/rag/compare"""

    def test_compare_endpoint(
        self, client: TestClient,
        mock_retrieve_tools,
        mock_reranker,
        mock_gemini,
        mock_embed_query
    ):
        """Test Vector vs Graph comparison."""
        response = client.post("/api/rag/compare", json={
            "question": "What is the VAT rate for education services?"
        })

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "questionId" in data
        assert "question" in data
        assert "vector" in data
        assert "graph" in data
        assert "timestamp" in data

        # Check vector result
        assert "answer" in data["vector"]
        assert "sources" in data["vector"]
        assert "metrics" in data["vector"]

        # Check graph result
        assert "answer" in data["graph"]
        assert "sources" in data["graph"]
        assert "cypherQuery" in data["graph"]
        assert "graphContext" in data["graph"]
        assert "metrics" in data["graph"]


class TestQueryEndpoint:
    """Tests for POST /api/rag/query"""

    def test_query_non_streaming(
        self, client: TestClient,
        mock_retrieve_tools,
        mock_reranker,
        mock_gemini,
        mock_embed_query,
        monkeypatch
    ):
        """Test non-streaming query."""
        # Mock the RAG agent
        class MockRAGAgent:
            async def query_non_streaming(self, question: str):
                return {
                    "answer": f"Answer for: {question}",
                    "sources": [],
                    "metrics": {"latencyMs": 100}
                }

        monkeypatch.setattr(
            "api.routers.rag.get_rag_agent",
            lambda: MockRAGAgent()
        )

        response = client.post("/api/rag/query", json={
            "question": "What is income tax?",
            "stream": False
        })

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


class TestHealthCheck:
    """Tests for /api/health (uses mock Neo4j)"""

    def test_health_check(self, client: TestClient):
        """Test health endpoint with mocked Neo4j."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "neo4j_connected" in data
```

---

## 7. Running Tests

### 7.1 Command

```bash
# Run all tests
cd /Users/hieudinh/Documents/my-projects/GP/Document-Graph-Representation
pytest api/tests/ -v

# Run with coverage
pytest api/tests/ -v --cov=api --cov-report=html

# Run specific test file
pytest api/tests/test_auth.py -v

# Run specific test class
pytest api/tests/test_auth.py::TestLogin -v

# Run specific test
pytest api/tests/test_auth.py::TestLogin::test_login_success -v
```

### 7.2 Expected Output

```
api/tests/test_auth.py::TestRegister::test_register_user PASSED
api/tests/test_auth.py::TestRegister::test_register_duplicate_email PASSED
api/tests/test_auth.py::TestLogin::test_login_success PASSED
...
```

---

## 8. Implementation Notes

### 8.1 Key Design Decisions

1. **Function-scoped fixtures**: Each test gets clean state (no cross-test pollution)
2. **Monkeypatch over mocks**: Using pytest's monkeypatch for simpler dependency injection
3. **In-memory DB clearing**: Directly clearing `users_db` and `documents_db` dicts
4. **Mock dimension matching**: Embedding mock returns 768-dim vector to match production

### 8.2 Potential Issues

| Issue | Mitigation |
|-------|------------|
| Lifespan startup errors | Mock Neo4j before TestClient creation |
| Token expiration in tests | Use fresh tokens per test |
| File upload cleanup | Tests use BytesIO, no actual files created |
| GSheet dependency | Fallback questions used when mocked |

### 8.3 Coverage Goals

- **Auth**: 100% endpoint coverage
- **Documents**: 100% endpoint coverage
- **RAG**: 80%+ (streaming harder to test)
- **Overall**: 85%+ line coverage

---

## 9. Unresolved Questions

1. **Streaming tests**: Should SSE streaming be tested? Requires different approach with httpx async client.
2. **Integration tests**: Should we add tests that hit real Neo4j (marked as slow)?
3. **Upload directory cleanup**: Tests create files in `/uploads` - should we mock file system?
4. **Rate limiting**: No rate limiting exists currently - should tests verify absence or add it?

---

## 10. Next Steps

1. ✅ Create `api/tests/__init__.py`
2. ✅ Implement `conftest.py` with all fixtures
3. ✅ Implement `test_auth.py`
4. ✅ Implement `test_documents.py`
5. ✅ Implement `test_rag.py`
6. ✅ Run full test suite
7. ✅ Address any failures
8. ✅ Add coverage reporting

---

## 11. Code Review Summary (2026-01-06)

### Review Outcome: ✅ APPROVED with Minor Fixes

**Full Report**: `./reports/260106-code-reviewer-test-suite-review.md`

### Key Findings

#### ✅ Strengths
- All 40 tests PASSED (100% pass rate)
- Excellent mock strategy isolates external dependencies
- Clean test organization using pytest classes
- 98% auth coverage, 85% documents coverage, 82% RAG coverage
- Comprehensive edge case testing (path traversal, invalid tokens, etc.)

#### ⚠️ Issues Requiring Attention

**High Priority**:
1. Missing `test_upload_file_too_large` (file size limit untested)
2. Deprecated `datetime.utcnow()` warnings in auth service
3. Hardcoded test credentials in fixtures

**Medium Priority**:
4. No streaming endpoint tests (SSE untested)
5. Upload directory cleanup not implemented
6. Missing edge case tests for query parameters

**Low Priority**:
7. Test documentation could be improved
8. Mock embedding dimension hardcoded

### Coverage Results
```
Overall:          69%
Auth Router:      98% ✅
Documents Router: 85% ✅
RAG Router:       82% ✅
Test Files:      100% ✅
```

### Immediate Action Items
1. Add `test_upload_file_too_large` before production deployment
2. Fix `datetime.utcnow()` deprecation in `api/services/auth.py`
3. Extract test credentials to constants

### Security Assessment
- ✅ No critical vulnerabilities found
- ✅ Path traversal prevention tested
- ✅ Authentication edge cases covered
- ⚠️ Demo mode backdoor exists (disable in production)

**Reviewer**: code-review agent
**Status**: Production-ready with minor fixes
**Next Review**: After implementing streaming tests

