# Development Guide

## Setup

### Prerequisites

- Python 3.8+
- Node.js 18+
- Git

### Clone & Install

```bash
git clone https://github.com/GinHikat/Document-Graph-Representation.git
cd Document-Graph-Representation

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirement.txt
pip install -r requirements-api.txt

# Frontend
cd frontend
npm install
```

### Environment Setup

```bash
# Backend
cp .env.example .env

# Frontend
cd frontend
cp .env.example .env
```

## Development Workflow

### Running Both Services

Terminal 1 (Backend):
```bash
cd api
uvicorn main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### Code Style

**Python (Backend)**
- PEP 8 style
- Type hints required
- Docstrings for public functions

**TypeScript (Frontend)**
- ESLint + Prettier
- Explicit types (avoid `any`)
- Functional components

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes, commit
git add .
git commit -m "feat: add feature description"

# Push and create PR
git push -u origin feature/your-feature
```

### Commit Convention

```
<type>: <description>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructure
- test: Tests
- chore: Maintenance
```

## Testing

### Backend Tests

```bash
pytest
pytest --cov=api  # With coverage
```

### Frontend Tests

```bash
cd frontend
npm run lint
npm run build  # Type check
```

## Adding Features

### New API Endpoint

1. Add route in `api/routers/`
2. Add schema in `api/schemas/`
3. Add service logic in `api/services/`
4. Register router in `api/main.py`

### New Frontend Page

1. Create page in `frontend/src/pages/`
2. Add route in `App.tsx`
3. Add navigation link

### New UI Component

```bash
cd frontend
npx shadcn-ui@latest add <component>
```

## Troubleshooting

### Neo4j Connection

```python
# Test connection
from neo4j import GraphDatabase
driver = GraphDatabase.driver(uri, auth=(user, password))
driver.verify_connectivity()
```

### Frontend Build Errors

```bash
# Clear cache
rm -rf node_modules/.vite
npm run dev
```

### Port Conflicts

```bash
# Find process on port
lsof -i :8000
lsof -i :8080

# Kill process
kill -9 <PID>
```
