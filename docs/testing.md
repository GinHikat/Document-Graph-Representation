# Testing Documentation

## Overview

The Document-Graph-Representation project includes a comprehensive test suite for the FastAPI backend, ensuring reliability and code quality across authentication, document management, and RAG functionality.

## Test Suite Summary

- **Location**: `api/tests/`
- **Total Tests**: 40
- **Test Files**: 3
  - `test_auth.py`: 13 authentication tests
  - `test_documents.py`: 17 document management tests
  - `test_rag.py`: 10 RAG endpoint tests
- **Pass Rate**: 100%
- **Code Coverage**: 69%

## Quick Start

### Run All Tests

```bash
# From project root
pytest api/tests/ -v

# Or from api directory
cd api
pytest tests/ -v
```

### Run Specific Test File

```bash
# Authentication tests only
pytest api/tests/test_auth.py -v

# Document tests only
pytest api/tests/test_documents.py -v

# RAG tests only
pytest api/tests/test_rag.py -v
```

### Run Specific Test Class or Function

```bash
# Run a specific test class
pytest api/tests/test_auth.py::TestRegister -v

# Run a specific test function
pytest api/tests/test_auth.py::TestRegister::test_register_user -v
```

## Coverage Reports

### Generate Coverage Report

```bash
# HTML coverage report
pytest api/tests/ --cov=api --cov-report=html

# View report in browser
open htmlcov/index.html
```

### Terminal Coverage Report

```bash
# Show coverage in terminal
pytest api/tests/ --cov=api --cov-report=term

# Show missing lines
pytest api/tests/ --cov=api --cov-report=term-missing
```

## Test Structure

### Test Files

```
api/tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication endpoint tests
├── test_documents.py        # Document management tests
└── test_rag.py             # RAG query and retrieval tests
```

### Fixtures (conftest.py)

Common fixtures available to all tests:

- **`client`**: FastAPI TestClient instance
- **`test_user`**: Pre-created test user
- **`auth_headers`**: Authentication headers with valid JWT token
- **`admin_user`**: Pre-created admin user
- **`admin_headers`**: Admin authentication headers
- **`test_document`**: Sample document for testing

## Test Categories

### 1. Authentication Tests (`test_auth.py`)

Tests for `/api/auth` endpoints:

**Registration Tests** (`TestRegister`)
- `test_register_user`: Successful user registration
- `test_register_duplicate_email`: Duplicate email handling
- `test_register_weak_password`: Password validation
- `test_register_invalid_email`: Email format validation

**Login Tests** (`TestLogin`)
- `test_login_user`: Successful login
- `test_login_invalid_credentials`: Wrong password handling
- `test_login_nonexistent_user`: Non-existent user handling
- `test_login_missing_fields`: Missing field validation

**Profile Tests** (`TestProfile`)
- `test_get_profile`: Retrieve user profile
- `test_get_profile_unauthorized`: Unauthorized access
- `test_update_profile`: Update user information
- `test_update_password`: Password change
- `test_logout`: Logout functionality

### 2. Document Tests (`test_documents.py`)

Tests for `/api/documents` endpoints:

**Document Upload Tests** (`TestDocumentUpload`)
- `test_upload_document`: Successful document upload
- `test_upload_unauthorized`: Upload without authentication
- `test_upload_invalid_file_type`: File type validation
- `test_upload_empty_file`: Empty file handling
- `test_upload_large_file`: File size validation

**Document Retrieval Tests** (`TestDocumentRetrieval`)
- `test_list_documents`: List all documents
- `test_list_documents_pagination`: Pagination support
- `test_list_documents_filtering`: Filter by status/type
- `test_get_document_by_id`: Retrieve specific document
- `test_get_document_not_found`: Handle non-existent document

**Document Update Tests** (`TestDocumentUpdate`)
- `test_update_document_metadata`: Update document info
- `test_update_document_status`: Change processing status
- `test_update_unauthorized`: Prevent unauthorized updates

**Document Deletion Tests** (`TestDocumentDeletion`)
- `test_delete_document`: Successful deletion
- `test_delete_unauthorized`: Prevent unauthorized deletion
- `test_delete_not_found`: Handle non-existent document
- `test_delete_cascade`: Verify cascade deletion in graph

**Document Processing Tests** (`TestDocumentProcessing`)
- `test_process_document`: Trigger document processing

### 3. RAG Tests (`test_rag.py`)

Tests for `/api/rag` endpoints:

**Query Tests** (`TestRAGQuery`)
- `test_rag_query_default_mode`: Standard embedding search
- `test_rag_query_graph_mode`: Graph traversal retrieval
- `test_rag_query_unauthorized`: Authentication requirement
- `test_rag_query_empty_query`: Empty query validation

**Retrieval Tests** (`TestRAGRetrieval`)
- `test_retrieve_context`: Context retrieval
- `test_retrieve_with_filters`: Filter by mode/parameters
- `test_retrieve_top_k`: Limit result count

**Reranking Tests** (`TestRAGRerank`)
- `test_rerank_results`: Result reranking
- `test_rerank_empty_contexts`: Empty context handling

**Tools Tests** (`TestRAGTools`)
- `test_list_tools`: Available RAG tools

## Adding New Tests

### 1. Create Test Function

```python
def test_new_feature(client: TestClient, auth_headers):
    """Test description."""
    response = client.post(
        "/api/endpoint",
        headers=auth_headers,
        json={"key": "value"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

### 2. Use Fixtures

```python
def test_with_user(client: TestClient, test_user, auth_headers):
    """Test using existing user fixture."""
    response = client.get(
        f"/api/users/{test_user.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
```

### 3. Create New Fixture

Add to `conftest.py`:

```python
@pytest.fixture
def custom_fixture(client: TestClient):
    """Custom fixture for specific tests."""
    # Setup
    data = create_test_data()

    yield data

    # Teardown
    cleanup_test_data(data)
```

### 4. Test Classes

Group related tests:

```python
class TestNewFeature:
    """Tests for new feature."""

    def test_case_1(self, client: TestClient):
        """Test case 1."""
        pass

    def test_case_2(self, client: TestClient):
        """Test case 2."""
        pass
```

## Testing Best Practices

### 1. Test Naming

- Use descriptive names: `test_<action>_<expected_result>`
- Example: `test_register_duplicate_email`

### 2. Test Independence

- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 3. Assertions

```python
# Clear assertions
assert response.status_code == 200
assert "token" in response.json()
assert response.json()["user"]["email"] == "test@example.com"
```

### 4. Test Data

- Use meaningful test data
- Keep test data isolated
- Clean up after tests

### 5. Error Cases

Test both success and failure scenarios:

```python
def test_success_case(client):
    """Test successful operation."""
    response = client.post("/api/endpoint", json=valid_data)
    assert response.status_code == 200

def test_validation_error(client):
    """Test validation error handling."""
    response = client.post("/api/endpoint", json=invalid_data)
    assert response.status_code == 400
```

## Continuous Integration

### GitHub Actions

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirement.txt
          pip install -r requirements-api.txt

      - name: Run tests
        run: pytest api/tests/ -v --cov=api

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the correct directory
cd /path/to/Document-Graph-Representation
pytest api/tests/ -v
```

**Database Connection Errors**
```bash
# Check Neo4j connection
# Ensure .env has correct NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
```

**Fixture Not Found**
```python
# Make sure conftest.py is in the tests directory
# Check fixture name matches usage
```

**Test Hangs**
```bash
# Use timeout
pytest api/tests/ -v --timeout=10
```

### Debugging Tests

```bash
# Run with print statements
pytest api/tests/ -v -s

# Run with debugging
pytest api/tests/ -v --pdb

# Stop on first failure
pytest api/tests/ -v -x
```

## Test Metrics

### Current Coverage (69%)

Key coverage areas:
- Authentication flows: 85%
- Document management: 70%
- RAG endpoints: 60%
- Error handling: 65%

### Coverage Goals

Target coverage areas for improvement:
- Edge case handling
- Error recovery paths
- Background job processing
- WebSocket connections

## Related Files

- See `api/tests/conftest.py` for available fixtures
- See `docs/development-guide.md` for development workflow
- See `docs/api-reference.md` for endpoint documentation

## Changelog

### Recent Changes

**v1.0.0** (Jan 6, 2026)
- Added comprehensive test suite (40 tests)
- Implemented auth, document, and RAG tests
- Achieved 69% code coverage
- Fixed syntax error in `final_doc_processor.py`
