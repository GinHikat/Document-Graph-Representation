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
- Neo4j database (local or AuraDB)

### Backend Setup

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

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run API server
cd api
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env - set VITE_API_URL=http://localhost:8000/api

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
    1: "default",           		# Standard embedding search
    2: "traverse_embed",    		# Embeddings + Graph Traversal
    3: "traverse_exact",    		# Exact Match + Graph TRaversal
    4: "exact_match",  	    		# Exact Match
    5: "exact_match_with_rerank",    	# Exact match then Rerank with embeddings
    6: "hybrid_search",       		# Top k by both Embeddings and Exact match
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
    mode=2,  		# traverse_embed
    graph=True,		# Use Graph Embedding, None if only use Textual Embedding
    chunks=True,	# Include chunk nodes (only available in GraphSAGE integrated database)
    hop=2		# Number of hops in traversal
)

# Batch query, df should include "question" column
df = retriever.batch_query(df, mode=2, graph=True, chunks=True, hop=2, namespace = 'Test')
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
```bash
# Backend
pytest

# Frontend
npm run lint
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

## License

MIT

## Contributors

- Tax Legal RAG Team
