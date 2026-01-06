# FastAPI Backend Analysis Report

**Date:** 2026-01-06
**Analyst:** Investigation Agent
**Purpose:** Comprehensive analysis for test mocking strategy

---

## 1. AUTHENTICATION SYSTEM

### Endpoints

**Router:** `/api/auth` (prefix)

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/login` | POST | `LoginRequest` | `AuthResponse` | Authenticate user, return JWT |
| `/register` | POST | `RegisterRequest` | `AuthResponse` | Create user, return JWT |
| `/me` | GET | - | `UserResponse` | Get current user (requires auth) |
| `/logout` | POST | - | `{message: str}` | Client-side logout signal |

### Authentication Method

**JWT (JSON Web Tokens)**

**Implementation Details:**
- Library: `python-jose[cryptography]`
- Algorithm: HS256
- Token expiry: 1440 minutes (24 hours) default
- Password hashing: bcrypt via `passlib`
- Token format: `Bearer <token>` in Authorization header

**Environment Variables:**
```bash
JWT_SECRET=<secret-key>          # Default: "change-me-in-production"
JWT_ALGORITHM=HS256              # Fixed
JWT_EXPIRE_MINUTES=1440          # Default: 24 hours
```

### Request/Response Schemas

```python
# Request Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

# Response Models
class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

class AuthResponse(BaseModel):
    token: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str]
    name: Optional[str]
```

### Authentication Dependencies

**Two dependency functions:**

1. **`get_current_user`** (Optional auth)
   - Usage: `Depends(get_current_user)`
   - Returns: `Optional[UserResponse]`
   - No exception if missing token

2. **`require_auth`** (Required auth)
   - Usage: `Depends(require_auth)`
   - Returns: `UserResponse`
   - Raises: `HTTPException(401)` if not authenticated

### User Storage

**In-memory dict** (development only):
- `users_db: dict = {}`
- Key: email
- Value: `UserInDB` object

**Demo Mode:**
- Password "demo" works for any email
- Creates temporary user on-the-fly with role "annotator"
- Demo user exists: `demo@example.com / demo123`

### Key Functions

```python
# api/services/auth.py
create_access_token(data: dict, expires_delta: Optional[timedelta]) -> str
decode_access_token(token: str) -> Optional[TokenData]
hash_password(password: str) -> str
verify_password(plain_password: str, hashed_password: str) -> bool
authenticate_user(email: str, password: str) -> Optional[UserInDB]
create_user(email: str, password: str, name: str, role: str = "user") -> UserInDB
get_user_by_email(email: str) -> Optional[UserInDB]
```

---

## 2. DOCUMENTS ROUTER

**Router:** `/api/documents` (prefix)

### Endpoints

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/upload` | POST | `List[UploadFile]` | `UploadResponse` | Upload documents (PDF/DOCX/TXT) |
| `/` | GET | `?status=...&limit=100` | `List[DocumentResponse]` | List uploaded docs |
| `/{doc_id}` | GET | - | `DocumentResponse` | Get single doc metadata |
| `/{doc_id}` | DELETE | - | `{deleted: bool, id: str}` | Delete document |
| `/batch-delete` | POST | `List[str]` | `{deleted: [], notFound: []}` | Delete multiple docs |
| `/{doc_id}/reprocess` | POST | - | `{reprocessing: bool, id: str}` | Trigger reprocessing |

### Request/Response Schemas

```python
class DocumentResponse(BaseModel):
    id: str
    name: str
    status: str  # uploaded, processing, completed, failed
    uploadedAt: str  # ISO datetime
    size: Optional[int]
    progress: Optional[int]  # 0-100

class UploadResponse(BaseModel):
    documents: List[DocumentResponse]
    taskId: str
```

### Database Operations

**In-memory store:**
- `documents_db: dict = {}`
- Key: doc_id (UUID)
- Value: document metadata dict

**File storage:**
- Directory: `api/uploads/`
- Filename format: `{doc_id}_{original_name}`
- Max file size: 50MB
- Allowed extensions: `.pdf`, `.docx`, `.doc`, `.txt`

**Security measures:**
- Path traversal prevention (checks absolute path)
- Filename sanitization (removes path components)
- Extension whitelist enforcement

---

## 3. RAG ROUTER

**Router:** `/api/rag` (prefix)

### Endpoints

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/query` | POST | `QueryRequest` | SSE stream or JSON | RAG query with streaming |
| `/retrieve` | POST | `RetrieveRequest` | `RetrieveResponse` | Direct vector retrieval |
| `/rerank` | POST | `RerankRequest` | `RerankResponse` | Direct reranking |
| `/tools` | GET | - | `{tools: [...]}` | List available tools |
| `/sample-questions` | GET | `?count=8&shuffle=true` | `{questions: [...]}` | Sample QA questions |
| `/compare` | POST | `CompareRequest` | `CompareResponse` | Compare Vector vs Graph RAG |

### Request/Response Schemas

```python
class QueryRequest(BaseModel):
    question: str
    stream: bool = True  # SSE or JSON response

class RetrieveRequest(BaseModel):
    prompt: str
    top_k: int = 10  # 1-50
    namespace: str = "Test_rel_2"

class RetrieveChunk(BaseModel):
    id: str
    text: str
    score: float = 0.0

class RetrieveResponse(BaseModel):
    chunks: List[RetrieveChunk]
    source_ids: List[str]
    scores: List[float]

class RerankRequest(BaseModel):
    query: str
    chunks: List[Dict[str, Any]]
    top_n: int = 5  # 1-20

class RerankResponse(BaseModel):
    reranked_chunks: List[Dict[str, Any]]
    scores: List[float]

class CompareRequest(BaseModel):
    question: str

class CompareResponse(BaseModel):
    questionId: str
    question: str
    vector: VectorResult
    graph: GraphResult
    timestamp: str
```

### Service Dependencies

**Key services used:**

1. **RAG Agent** (`api/services/rag_agent.py`)
   - `get_rag_agent()` - Singleton
   - `agent.query(question)` - Streaming generator
   - `agent.query_non_streaming(question)` - JSON response

2. **Retrieval Tools** (`api/services/tools.py`)
   - `retrieve_from_database(prompt, top_k, namespace)` - Vector baseline
   - `retrieve_with_graph_context(prompt, top_k)` - Graph-enhanced

3. **Reranker** (`api/services/reranker.py`)
   - `rerank_chunks(query, chunks, top_n)` - BGE reranker
   - Model: BAAI/bge-reranker-base

4. **Gemini LLM** (`api/services/gemini.py`)
   - `generate_answer(question, chunks)` - Answer generation
   - Falls back to OpenAI if Gemini unavailable

5. **Embedding** (`api/services/embedding.py`)
   - `embed_query(text)` - Query embedding (768-dim)
   - Model: paraphrase-multilingual-mpnet-base-v2

### Query Parameters

**SSE Streaming Events:**
- `tool_start` - Tool execution begins
- `tool_end` - Tool execution completes
- `text` - LLM text chunk
- `sources` - Retrieved sources
- `done` - Query complete

**Configuration (from `api/config.py`):**
```python
RAG_TOP_K = 20
RAG_RERANK_TOP_N = 5
DEFAULT_NAMESPACE = "Test_rel_2"
STREAM_CHUNK_SIZE = 100
```

---

## 4. GRAPH ROUTER

**Router:** `/api/graph` (prefix)

### Endpoints

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/nodes` | GET | `?limit=100` | `GraphData` | Get nodes/relationships |
| `/execute` | POST | `CypherRequest` | `CypherResponse` | Execute Cypher query (read-only) |
| `/schema` | GET | - | `GraphSchemaResponse` | Get graph schema |
| `/stats` | GET | - | `{node_count, relationship_count, avg_connections}` | Graph statistics |

### Schemas

```python
class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "document"
    properties: Dict[str, Any] = {}

class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    properties: Optional[Dict[str, Any]]

class GraphData(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]

class CypherRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]]

class CypherResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int
```

**Security:**
- Only MATCH/WITH queries allowed
- Blocks: CREATE, DELETE, MERGE, SET, REMOVE, DROP
- Read-only enforcement

---

## 5. ANNOTATION ROUTER

**Router:** `/api/annotations` (prefix)

### Endpoints

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/submit` | POST | `AnnotationSubmitRequest` | `AnnotationResponse` | Submit detailed annotation |
| `/simple` | POST | `SimpleAnnotationRequest` | `AnnotationResponse` | Submit simple preference |
| `/pending` | GET | - | `List[AnnotationTask]` | Get pending tasks |
| `/stats` | GET | - | `AnnotatorStats` | Get annotator stats |

### Schemas

```python
class AnnotationSubmitRequest(BaseModel):
    questionId: str
    vectorCorrectness: int = 0  # 0-5
    vectorCompleteness: int = 0
    vectorRelevance: int = 0
    graphCorrectness: int = 0
    graphCompleteness: int = 0
    graphRelevance: int = 0
    overallComparison: str  # vector_much_better|vector_better|equivalent|graph_better|graph_much_better
    comment: Optional[str]

class SimpleAnnotationRequest(BaseModel):
    questionId: str
    preference: str  # vector|equivalent|graph|both_wrong
    comment: Optional[str]
```

**Service:** `api/services/annotation.py`
- `get_annotation_service()` - Singleton

---

## 6. STATS ROUTER

**Router:** `/api/stats` (prefix)

### Endpoints

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/` | GET | `SystemStats` | System metrics for dashboard |

### Schema

```python
class SystemStats(BaseModel):
    document_count: int
    question_count: int
    relationship_count: int
    avg_connections: float
    accuracy_rate: Optional[float]
    avg_response_time: Optional[float]
```

**Features:**
- Thread-safe response time tracking (deque with lock)
- Records last 100 response times
- Queries Neo4j for graph stats

---

## 7. MAIN APP CONFIGURATION

**File:** `api/main.py`

### Router Inclusion

```python
app.include_router(graph.router)
app.include_router(rag.router)
app.include_router(documents.router)
app.include_router(auth.router)
app.include_router(annotation.router)
app.include_router(stats.router)
```

### Middleware

**CORS Configuration:**
```python
CORSMiddleware(
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:8080",   # Custom Vite
        "http://localhost:3000",   # React
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### Lifespan Events

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify Neo4j connectivity
    client = get_neo4j_client()
    client.verify_connectivity()

    yield

    # Shutdown: close Neo4j connection
    client.close()
```

### Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Returns JSON with error, message, path, timestamp
    return JSONResponse(status_code=500, content={...})
```

### Health Check

```
GET /api/health -> HealthResponse
```

---

## 8. DATABASE DEPENDENCIES

### Neo4j Client

**File:** `api/db/neo4j.py`

**Connection:**
```python
class Neo4jClient:
    def __init__(self):
        uri = os.getenv('NEO4J_URI')
        username = 'neo4j'
        password = os.getenv('NEO4J_AUTH')
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
```

**Key Methods:**
```python
verify_connectivity() -> bool
execute_query(query: str, parameters: dict) -> List[Dict]
get_test_rel_2_graph(limit: int) -> Dict[str, List]
get_graph_schema() -> Dict[str, List]
get_node_count(namespace: str) -> int
```

**Singleton pattern:**
```python
_neo4j_client = None

def get_neo4j_client() -> Neo4jClient:
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
```

**Environment Variables:**
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_AUTH=<password>
```

---

## 9. CONFIGURATION

**File:** `api/config.py`

```python
class Config:
    # RAG Pipeline
    RAG_TOP_K: int = 20
    RAG_RERANK_TOP_N: int = 5
    DEFAULT_NAMESPACE: str = os.getenv("RAG_NAMESPACE", "Test_rel_2")
    STREAM_CHUNK_SIZE: int = 100

    # JWT Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

config = Config()
```

---

## 10. CRITICAL DEPENDENCIES FOR MOCKING

### External Services

1. **Neo4j Database**
   - Mock: `api.db.neo4j.get_neo4j_client`
   - Methods: `verify_connectivity`, `execute_query`, `get_test_rel_2_graph`, `get_node_count`

2. **Embedding Model** (SentenceTransformers)
   - Mock: `api.services.embedding.get_embedding_model`
   - Mock: `api.services.embedding.embed_query`
   - Returns: np.ndarray (768-dim)

3. **Reranker Model** (BGE)
   - Mock: `api.services.reranker.rerank_chunks`
   - Returns: (reranked_chunks: List[Dict], scores: List[float])

4. **Gemini/OpenAI LLM**
   - Mock: `api.services.gemini.generate_answer`
   - Mock: `api.services.gemini.stream_answer` (generator)
   - Returns: str or Generator[str]

5. **RAG Agent**
   - Mock: `api.services.rag_agent.get_rag_agent`
   - Methods: `query` (generator), `query_non_streaming`

### Environment Variables Required

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_AUTH=<password>

# LLM APIs
GOOGLE_API_KEY=<gemini-key>
OPENAI_API_KEY=<openai-key>  # Fallback

# JWT
JWT_SECRET=<secret>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# RAG
RAG_NAMESPACE=Test_rel_2
```

### In-Memory Stores (Non-persistent)

```python
# api/services/auth.py
users_db: dict = {}

# api/routers/documents.py
documents_db: dict = {}

# api/routers/stats.py
_response_times: deque = deque(maxlen=100)
```

---

## 11. TEST MOCKING STRATEGY

### Pytest Fixtures Needed

```python
@pytest.fixture
def mock_neo4j_client(monkeypatch):
    """Mock Neo4j client with fake data"""
    mock = MagicMock()
    mock.verify_connectivity.return_value = True
    mock.execute_query.return_value = []
    mock.get_node_count.return_value = 100
    monkeypatch.setattr("api.db.neo4j.get_neo4j_client", lambda: mock)
    return mock

@pytest.fixture
def mock_embedding(monkeypatch):
    """Mock embedding service"""
    mock_embed = MagicMock(return_value=np.zeros(768))
    monkeypatch.setattr("api.services.embedding.embed_query", mock_embed)
    return mock_embed

@pytest.fixture
def mock_reranker(monkeypatch):
    """Mock BGE reranker"""
    def fake_rerank(query, chunks, top_n):
        return chunks[:top_n], [0.9] * top_n
    monkeypatch.setattr("api.services.reranker.rerank_chunks", fake_rerank)

@pytest.fixture
def mock_gemini(monkeypatch):
    """Mock Gemini LLM"""
    monkeypatch.setattr("api.services.gemini.generate_answer",
                       lambda q, chunks: "Mock answer")

@pytest.fixture
def auth_token():
    """Generate valid JWT token for testing"""
    from api.services.auth import create_access_token
    return create_access_token({"sub": "test@example.com", "name": "Test"})

@pytest.fixture
def auth_headers(auth_token):
    """Auth headers for authenticated requests"""
    return {"Authorization": f"Bearer {auth_token}"}
```

### Critical Mock Points

1. **FastAPI TestClient**
   ```python
   from fastapi.testclient import TestClient
   from api.main import app

   client = TestClient(app)
   ```

2. **Override dependencies**
   ```python
   app.dependency_overrides[get_neo4j_client] = mock_neo4j_client
   app.dependency_overrides[require_auth] = lambda: UserResponse(...)
   ```

3. **Environment setup**
   ```python
   @pytest.fixture(autouse=True)
   def setup_env(monkeypatch):
       monkeypatch.setenv("NEO4J_URI", "bolt://mock:7687")
       monkeypatch.setenv("JWT_SECRET", "test-secret")
   ```

---

## 12. ENDPOINT SUMMARY TABLE

| Router | Endpoint | Method | Auth Required | External Deps |
|--------|----------|--------|---------------|---------------|
| Auth | `/api/auth/login` | POST | No | In-memory DB |
| Auth | `/api/auth/register` | POST | No | In-memory DB |
| Auth | `/api/auth/me` | GET | Yes | In-memory DB |
| Docs | `/api/documents/upload` | POST | No | File system |
| Docs | `/api/documents` | GET | No | In-memory DB |
| Docs | `/api/documents/{id}` | GET/DELETE | No | In-memory DB, File system |
| RAG | `/api/rag/query` | POST | No | Neo4j, Embedding, Reranker, LLM |
| RAG | `/api/rag/retrieve` | POST | No | Neo4j, Embedding |
| RAG | `/api/rag/rerank` | POST | No | Reranker |
| RAG | `/api/rag/compare` | POST | No | Neo4j, Embedding, Reranker, LLM |
| Graph | `/api/graph/nodes` | GET | No | Neo4j |
| Graph | `/api/graph/execute` | POST | No | Neo4j |
| Graph | `/api/graph/schema` | GET | No | Neo4j |
| Graph | `/api/graph/stats` | GET | No | Neo4j |
| Annotation | `/api/annotations/submit` | POST | No | Annotation service |
| Annotation | `/api/annotations/simple` | POST | No | Annotation service |
| Stats | `/api/stats` | GET | No | Neo4j, QA service |
| Health | `/api/health` | GET | No | Neo4j |

---

## 13. UNRESOLVED QUESTIONS

1. **Annotation Service Implementation:** Where is `api/services/annotation.py` fully implemented?
2. **QA Questions Source:** How does `api/services/qa_questions.py` fetch questions? Google Sheets?
3. **Background Task Processing:** Documents have "processing" status - is there a Celery/background worker?
4. **Production Database:** Users and documents use in-memory stores - what's the production plan (PostgreSQL, MongoDB)?
5. **Token Blacklisting:** Logout endpoint mentions potential blacklist - is this implemented?
6. **Model Download:** Do embedding/reranker models need to be pre-downloaded for tests?

---

**END OF REPORT**
