"""RAG endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from api.services.rag_schemas import RetrieveOutput, GraphRetrieveOutput


# ============ Mock Retrieve Tools Fixture ============

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
    monkeypatch.setattr("api.routers.rag.retrieve_from_database", _mock_retrieve)
    monkeypatch.setattr("api.services.tools.retrieve_with_graph_context", _mock_retrieve_graph)
    monkeypatch.setattr("api.routers.rag.retrieve_with_graph_context", _mock_retrieve_graph)

    return {"retrieve": _mock_retrieve, "retrieve_graph": _mock_retrieve_graph}


@pytest.fixture(scope="function")
def mock_gemini(monkeypatch):
    """Mock Gemini/LLM generation service."""
    def _mock_generate(
        query: str,
        context_chunks,
        model_name: str = "gemini-2.0-flash"
    ) -> str:
        return f"Mock answer for: {query[:50]}"

    monkeypatch.setattr("api.services.gemini.generate_answer", _mock_generate)
    monkeypatch.setattr("api.routers.rag.generate_answer", _mock_generate)
    return _mock_generate


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

    def test_sample_questions(self, client: TestClient):
        """Test getting sample questions."""
        response = client.get("/api/rag/sample-questions")

        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert isinstance(data["questions"], list)

    def test_sample_questions_with_count(self, client: TestClient):
        """Test sample questions with count parameter."""
        response = client.get("/api/rag/sample-questions?count=3")

        assert response.status_code == 200
        assert len(response.json()["questions"]) <= 3

    def test_sample_questions_no_shuffle(self, client: TestClient):
        """Test sample questions without shuffling."""
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
