# Phase 1: Document Processing Service

**Parent:** [plan.md](./plan.md)
**Dependencies:** None
**Date:** 2026-01-07
**Priority:** High
**Status:** Pending

## Overview

Create a reusable document processing service for the API layer that wraps existing `Doc_processor` logic. Service handles text extraction, parsing, and structure extraction.

## Key Insights

1. **Existing code in `final_doc_processor.py`** - Contains `parse_legal_text()`, `pre_process()`, already handles hierarchy
2. **Vietnamese hierarchy** - Document -> Chapter -> Clause -> Point -> Subpoint (research confirmed)
3. **File formats** - PDF primary, DOCX/DOC via conversion (existing `docx_to_pdf()`)
4. **Dependencies** - NER + RE models required for relation extraction

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1 | Extract text from PDF/DOCX/TXT | High |
| R2 | Parse Vietnamese legal hierarchy | High |
| R3 | Return structured dict (chapters, clauses, points) | High |
| R4 | Handle Unicode normalization | Medium |
| R5 | Lazy-load heavy models (NER, RE, PhoBERT) | High |
| R6 | Thread-safe for BackgroundTasks | High |

## Architecture

```
api/services/document_processor.py
    |
    +-- DocumentProcessorService (class)
            |
            +-- extract_text(filepath) -> str
            +-- parse_structure(text) -> dict
            +-- get_metadata(text) -> dict
            |
            +-- _ner (lazy)
            +-- _re_model (lazy)
            +-- _extractor (lazy)
```

## Related Code Files

| File | Lines | Purpose |
|------|-------|---------|
| `rag_model/model/Final_pipeline/final_doc_processor.py` | 75-220 | `parse_legal_text()` - structure parsing |
| `rag_model/model/Final_pipeline/final_doc_processor.py` | 403-700 | `saving_neo4j()` - full pipeline (reference) |
| `rag_model/model/NER/final_ner.py` | - | NER model for metadata extraction |
| `rag_model/model/RE/final_re.py` | - | Relation extraction model |
| `shared_functions/global_functions.py` | 107-163 | `get_text_from_s3()` - text extraction logic |

## Implementation Steps

### Step 1: Create Service Skeleton

Create `api/services/document_processor.py`:

```python
"""Document processing service for API layer."""
import os
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentProcessorService:
    """Handles document text extraction and structure parsing."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._ner = None
        self._re_model = None
        self._doc_processor = None
        self._initialized = True
```

### Step 2: Implement Text Extraction

Port logic from `global_functions.py:get_text_from_s3()`:

```python
def extract_text(self, filepath: str) -> str:
    """Extract text from PDF/DOCX/TXT file."""
    ext = Path(filepath).suffix.lower()

    if ext == '.pdf':
        return self._extract_pdf(filepath)
    elif ext == '.docx':
        return self._extract_docx(filepath)
    elif ext == '.txt':
        return self._extract_txt(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
```

### Step 3: Implement Structure Parsing

Port `parse_legal_text()` from `final_doc_processor.py:112-220`:

```python
def parse_structure(self, text: str) -> Dict[str, Any]:
    """Parse Vietnamese legal document hierarchy."""
    # Reuse existing parse_legal_text logic
    # Returns: {"chapters": {...}} or {"clauses": [...]}
```

### Step 4: Lazy Model Loading

```python
@property
def ner(self):
    if self._ner is None:
        from rag_model.model.NER.final_ner import NER
        self._ner = NER(
            model_path="path/to/model_bilstm_crf.pt",
            token2idx_path="path/to/token2idx.json",
            label2idx_path="path/to/label2idx.json"
        )
    return self._ner
```

### Step 5: Add Metadata Extraction

```python
def get_metadata(self, text: str) -> Dict[str, str]:
    """Extract document metadata using NER."""
    df = self.ner.extract_document_metadata(text)
    return df.iloc[0].to_dict() if not df.empty else {}
```

## Todo

- [ ] Create `api/services/document_processor.py`
- [ ] Port `parse_legal_text()` from notebook code
- [ ] Implement PDF/DOCX extraction (copy from global_functions)
- [ ] Add lazy loading for NER/RE models
- [ ] Add singleton pattern for thread safety
- [ ] Write unit tests for text extraction
- [ ] Write unit tests for structure parsing

## Success Criteria

1. `DocumentProcessorService().extract_text(pdf_path)` returns text
2. `DocumentProcessorService().parse_structure(text)` returns hierarchy dict
3. Models loaded only on first use (lazy)
4. Thread-safe singleton pattern works with BackgroundTasks
5. Tests pass: `pytest api/tests/test_document_processor.py`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Model paths hardcoded | High | Medium | Use config/env vars |
| NER model large (memory) | Medium | High | Lazy load + singleton |
| DOCX conversion Windows-only | Medium | Low | pdfplumber fallback |
| Unicode issues | Low | Medium | NFC normalization (already exists) |

## Security Considerations

1. **Path traversal** - Already handled in `documents.py` (L77)
2. **File size** - 50MB limit exists (L19)
3. **File type validation** - Extension whitelist exists (L49)

## Next Steps

After completion:
1. Proceed to [Phase 2: Neo4j Indexing](./phase-02-neo4j-indexing.md)
2. Service will be consumed by Neo4j indexer
