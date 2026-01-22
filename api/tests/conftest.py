"""Shared test fixtures for API tests."""
import pytest
from typing import Generator, Dict, Any, List, Tuple
from fastapi.testclient import TestClient

# Test credentials constants
TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "testpass123"
TEST_USER_NAME = "Test User"

from api.main import app
from api.db.neo4j import get_neo4j_client
from api.services.auth import (
    users_db,
    create_user,
    create_access_token,
    UserInDB,
)
from api.routers.documents import documents_db


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
    return _mock_rerank


# ============ Auth Token Generator ============

@pytest.fixture(scope="function")
def test_user(client) -> UserInDB:
    """Create a test user and return UserInDB object."""
    user = create_user(
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        name=TEST_USER_NAME,
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
def sample_document(tmp_path) -> Dict[str, Any]:
    """Sample document data for testing with actual temp file."""
    # Create a temporary test file (TXT format for easy processing)
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("""
Chương I
QUY ĐỊNH CHUNG
Điều 1. Phạm vi điều chỉnh
Luật này quy định về thuế giá trị gia tăng.
""", encoding="utf-8")

    return {
        "id": "doc_test_123",
        "name": "test_document.txt",
        "status": "uploaded",
        "uploadedAt": "2026-01-06T10:00:00",
        "size": 1024,
        "filepath": str(test_file),
        "progress": 0
    }


@pytest.fixture(scope="function")
def populated_documents_db(sample_document):
    """Pre-populate documents_db with sample data."""
    documents_db.clear()
    documents_db[sample_document["id"]] = sample_document
    yield documents_db
    documents_db.clear()
