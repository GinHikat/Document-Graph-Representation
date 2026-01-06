# Tax Legal RAG System

A full-stack knowledge graph-based Retrieval Augmented Generation (RAG) system for Vietnamese tax law documents. Compares vector search vs graph-based retrieval approaches.

## Architecture

```
Document-Graph-Representation/
├── api/                    # FastAPI backend
│   ├── routers/           # API endpoints (graph, rag, health)
│   ├── services/          # Business logic
│   └── schemas/           # Pydantic models
├── frontend/              # React + TypeScript UI
│   ├── src/
│   │   ├── components/    # UI components (shadcn/ui)
│   │   ├── pages/         # App views
│   │   ├── services/      # API client
│   │   └── stores/        # Zustand state
├── rag_model/             # ML pipeline
│   ├── model/             # NER, RE, document processing
│   └── retrieval_pipeline/# Retrieval strategies
├── shared_functions/      # Utilities (Neo4j, S3, eval)
└── docs/                  # Documentation
```

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.115.6 |
| Graph DB | Neo4j 5.27.0 (AuraDB) |
| Storage | AWS S3 |
| Embeddings | sentence-transformers 3.3.1 |
| NLP | Underthesea (Vietnamese) |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18.3.1 |
| Language | TypeScript 5.8.3 |
| Build | Vite 5.4.19 |
| State | Zustand 5.0.8 |
| Data | TanStack Query 5.83.0 |
| UI | shadcn/ui + Tailwind CSS |
| Graph Viz | react-force-graph |

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Neo4j database (local or AuraDB) - **Required for backend to work**

### Step 1: Clone & Setup Environment

```bash
# Clone repo
git clone https://github.com/GinHikat/Document-Graph-Representation.git
cd Document-Graph-Representation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirement.txt
pip install -r requirements-api.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy example config
cp .env.example .env

# Ask team lead for the actual credentials to fill in:
# - NEO4J_URI, NEO4J_AUTH (Neo4j database)
# - GOOGLE_API_KEY (Gemini API for RAG answers)
```

**Note**: The project uses a shared Neo4j database. Contact the team for credentials - don't create a new one.

### Step 3: Run Backend Server

```bash
# From project root (NOT from api/ folder)
uvicorn api.main:app --reload --port 8000

# Verify: Open http://localhost:8000/api/health
# Should return {"status": "healthy", ...}
```

### Step 4: Run Frontend

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Default VITE_API_URL=http://localhost:8000/api is correct

# Run dev server
npm run dev
```

Frontend runs at `http://localhost:8080`, API at `http://localhost:8000`.

## API Endpoints

### Graph API (`/api/graph`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/nodes` | Fetch graph nodes with optional filters |
| POST | `/execute` | Execute Cypher queries |
| GET | `/schema` | Get graph schema |
| GET | `/stats` | Graph statistics |

### RAG API (`/api/rag`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | RAG query with SSE streaming |
| POST | `/retrieve` | Retrieve relevant context |
| POST | `/rerank` | Rerank retrieved results |
| GET | `/tools` | List available tools |

### Health API
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Retrieval Modes

```python
modes = {
    1: "default",           # Standard embedding search
    2: "traverse_embed",    # Graph traversal + embeddings
    3: "traverse_exact",    # Graph traversal + exact match
    4: "pagerank_embed",    # PageRank + embeddings
    5: "pagerank_exact",    # PageRank + exact match
    6: "exact_match",       # Pure exact match
    7: "exact_match_with_rerank"  # Exact + reranking
}
```

## Embedding Models

```python
models = {
    0: "paraphrase-multilingual-MiniLM-L12-v2",
    1: "distiluse-base-multilingual-cased-v2",
    2: "all-mpnet-base-v2",
    3: "all-MiniLM-L12-v2",
    4: "vinai/phobert-base",   # Vietnamese-specific
    5: "BAAI/bge-m3"           # Evaluation only
}
```

## Environment Variables

### Backend (.env)
```bash
# Neo4j
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_BUCKET_NAME=your-bucket
AWS_REGION=ap-southeast-1

# Optional
OPENAI_API_KEY=your-openai-key
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000/api
VITE_ENABLE_GRAPH_VIEW=true
VITE_ENABLE_ANNOTATIONS=true
```

## Usage Examples

### Python SDK

```python
from shared_functions.batch_retrieval_neo4j import Neo4j_retriever

retriever = Neo4j_retriever()

# Single query
result = retriever.query_neo4j(
    text="Thuế thu nhập cá nhân",
    mode=2,  # traverse_embed
    graph=1,
    chunks=1,
    hop=2
)

# Batch query
df = retriever.batch_query(df, mode=2, graph=1, chunks=1, hop=2)
```

### Evaluation

```python
from shared_functions.eval import Evaluator

eval = Evaluator(embedding_as_judge=5)

# Combined evaluation
result = eval.combined_evaluator(
    referenced_context="...",
    retrieved_context="...",
    embedding_threshold=0.7,
    jaccard_threshold=0.3,
    scaling_factor=0.5
)

# RAGAS evaluation
eval.ragas(df)  # df: question, answer, retrieved_contexts
```

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | Dashboard overview |
| Documents | `/documents` | Document management |
| Q&A | `/qa` | Query interface |
| Graph | `/graph` | Knowledge graph visualization |
| Annotate | `/annotate` | Document annotation |

## Development

### Run Tests

**Backend Tests**
```bash
# Run all tests (40 tests, 100% pass rate)
pytest api/tests/ -v

# Run with coverage (69% coverage)
pytest api/tests/ --cov=api --cov-report=html

# Run specific test file
pytest api/tests/test_auth.py -v      # 13 auth tests
pytest api/tests/test_documents.py -v # 17 document tests
pytest api/tests/test_rag.py -v       # 10 RAG tests

# See docs/testing.md for detailed testing documentation
```

**Frontend Tests**
```bash
# Linting
npm run lint

# Type checking
npm run build
```

### Build for Production
```bash
# Frontend
cd frontend
npm run build
# Output in frontend/dist/

# Serve with backend
# Configure FastAPI to serve static files
```

## Project Structure Details

See `docs/` for detailed documentation:
- `docs/system-architecture.md` - Architecture diagrams
- `docs/codebase-summary.md` - Component details
- `docs/code-standards.md` - Coding conventions
- `docs/project-roadmap.md` - Development roadmap
- `docs/testing.md` - Testing guide and coverage reports

## Troubleshooting

### "Cannot connect to backend server. Is it running on localhost:8000?"

**Cause**: Backend server is not running or crashed on startup.

**Solutions**:
1. Make sure you're running the backend from project root:
   ```bash
   # Correct (from project root)
   uvicorn api.main:app --reload --port 8000

   # Wrong (from api/ folder)
   cd api && uvicorn main:app --reload --port 8000
   ```

2. Check if `.env` has valid credentials (ask team for credentials):
   ```bash
   # Required in .env
   NEO4J_URI=<get from team>
   NEO4J_AUTH=<get from team>
   ```

3. Verify backend health:
   ```bash
   curl http://localhost:8000/api/health
   # Should return {"status": "healthy", ...}
   ```

### "Backend Disconnected" in UI

The frontend can't reach the API. Check:
1. Is backend running on port 8000?
2. Is `VITE_API_URL=http://localhost:8000/api` set in `frontend/.env`?
3. Any CORS errors in browser console?

### Port Already in Use

```bash
# Find process on port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

## License

MIT

## Contributors

- Tax Legal RAG Team
