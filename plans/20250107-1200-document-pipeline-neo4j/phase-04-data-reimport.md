# Phase 4: Data Reimport

**Parent:** [plan.md](./plan.md)
**Dependencies:** [Phase 2](./phase-02-neo4j-indexing.md), [Phase 3](./phase-03-api-integration.md)
**Date:** 2026-01-07
**Priority:** Medium
**Status:** Pending

## Overview

Re-import existing documents from S3/Google Drive to Neo4j with proper relationships. Current graph has sparse relationships - need to rebuild with full hierarchy + cross-references.

## Key Insights

1. **Existing data sources:**
   - S3: `legaldocstorage` bucket (global_functions.py:27-39)
   - Google Drive: Multiple folders by document type (upload_file.ipynb output)
2. **Document types:** Luat, Nghi Dinh, Nghi Quyet, Quyet Dinh, Thong Tu (from notebook)
3. **Current namespace:** `Test_rel_2` - may want new namespace for clean reimport
4. **Existing notebook:** `upload_file.ipynb` - has `process_document()` function

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1 | List all documents from S3/Drive | High |
| R2 | Process each document through new pipeline | High |
| R3 | Track reimport progress | Medium |
| R4 | Handle failures gracefully (continue on error) | High |
| R5 | Option to use new namespace or clear existing | Medium |
| R6 | CLI script for one-time execution | High |

## Architecture

```
scripts/reimport_documents.py
    |
    +-- main()
            |
            +-- List documents from source (S3 or Drive)
            +-- For each document:
                    |
                    +-- Download to temp file
                    +-- DocumentProcessorService.extract_text()
                    +-- DocumentProcessorService.parse_structure()
                    +-- DocumentProcessorService.get_metadata()
                    +-- Neo4jIndexerService.index_document()
                    +-- Log progress
                    +-- Cleanup temp file
```

## Related Code Files

| File | Lines | Purpose |
|------|-------|---------|
| `shared_functions/global_functions.py` | 27-39 | `list_files_recursive()` - S3 listing |
| `shared_functions/global_functions.py` | 107-163 | `get_text_from_s3()` - download + extract |
| `shared_functions/gg_sheet_drive.py` | - | Google Drive functions |
| `rag_model/neo4j/upload_file.ipynb` | Cell 4 | `process_document()` - existing logic |

## Implementation Steps

### Step 1: Create Reimport Script

Create `scripts/reimport_documents.py`:

```python
#!/usr/bin/env python3
"""Reimport existing documents to Neo4j with proper relationships."""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared_functions.global_functions import list_files_recursive, download_s3_to_temp
from api.services.document_processor import DocumentProcessorService
from api.services.neo4j_indexer import Neo4jIndexerService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def list_documents(source: str = "s3", bucket: str = "legaldocstorage") -> List[str]:
    """List all documents from source."""
    if source == "s3":
        files = list_files_recursive(bucket, file_types=["pdf", "docx", "doc"])
        return files
    elif source == "drive":
        # TODO: Implement Google Drive listing
        from shared_functions.gg_sheet_drive import list_drive_files
        return list_drive_files()
    else:
        raise ValueError(f"Unknown source: {source}")


def reimport_document(
    file_key: str,
    processor: DocumentProcessorService,
    indexer: Neo4jIndexerService,
    source: str = "s3"
) -> Dict:
    """Process and index a single document."""
    temp_path = None
    try:
        # Download to temp
        if source == "s3":
            bucket_object = f"legaldocstorage/{file_key}"
            temp_path = download_s3_to_temp(bucket_object)
        else:
            # Drive: already have local path or download
            temp_path = file_key

        # Process
        text = processor.extract_text(temp_path)
        metadata = processor.get_metadata(text)
        metadata["source_file"] = file_key
        parsed = processor.parse_structure(text)

        # Index
        doc_id = metadata.get("law_id") or metadata.get("document_id") or Path(file_key).stem
        stats = indexer.index_document(doc_id, text, parsed, metadata)

        return {"success": True, "file": file_key, "doc_id": doc_id, "stats": stats}

    except Exception as e:
        logger.error(f"Failed to process {file_key}: {e}")
        return {"success": False, "file": file_key, "error": str(e)}

    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path) and source == "s3":
            os.remove(temp_path)


def main():
    parser = argparse.ArgumentParser(description="Reimport documents to Neo4j")
    parser.add_argument("--source", choices=["s3", "drive"], default="s3")
    parser.add_argument("--namespace", default="Test_rel_2")
    parser.add_argument("--limit", type=int, default=None, help="Limit documents to process")
    parser.add_argument("--dry-run", action="store_true", help="List files without processing")
    args = parser.parse_args()

    # List documents
    logger.info(f"Listing documents from {args.source}...")
    documents = list_documents(args.source)
    logger.info(f"Found {len(documents)} documents")

    if args.limit:
        documents = documents[:args.limit]

    if args.dry_run:
        for doc in documents:
            print(doc)
        return

    # Initialize services
    processor = DocumentProcessorService()
    indexer = Neo4jIndexerService(namespace=args.namespace)

    # Ensure vector index
    indexer.ensure_vector_index()

    # Process each document
    results = {"success": 0, "failed": 0, "total_nodes": 0, "total_rels": 0}

    for i, file_key in enumerate(documents):
        logger.info(f"Processing [{i+1}/{len(documents)}]: {file_key}")
        result = reimport_document(file_key, processor, indexer, args.source)

        if result["success"]:
            results["success"] += 1
            results["total_nodes"] += result["stats"].get("nodes", 0)
            results["total_rels"] += result["stats"].get("relationships", 0)
        else:
            results["failed"] += 1

    # Summary
    logger.info("=" * 50)
    logger.info("REIMPORT COMPLETE")
    logger.info(f"Success: {results['success']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Total nodes created: {results['total_nodes']}")
    logger.info(f"Total relationships: {results['total_rels']}")


if __name__ == "__main__":
    main()
```

### Step 2: Add Namespace Cleanup (Optional)

```python
def clear_namespace(indexer: Neo4jIndexerService, confirm: bool = False):
    """Clear all nodes in namespace before reimport."""
    if not confirm:
        count = indexer.get_node_count()
        logger.warning(f"About to delete {count} nodes in namespace {indexer.namespace}")
        response = input("Type 'yes' to confirm: ")
        if response != "yes":
            logger.info("Aborted")
            return False

    query = f"MATCH (n:{indexer.namespace}) DETACH DELETE n"
    indexer._execute(query)
    logger.info(f"Cleared namespace {indexer.namespace}")
    return True
```

### Step 3: Add Progress Tracking

```python
import json
from datetime import datetime

PROGRESS_FILE = "reimport_progress.json"

def save_progress(processed: List[str], failed: List[str]):
    """Save progress for resume capability."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "processed": processed,
            "failed": failed
        }, f, indent=2)

def load_progress() -> Dict:
    """Load previous progress."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"processed": [], "failed": []}
```

### Step 4: Add Resume Capability

```python
# In main():
parser.add_argument("--resume", action="store_true", help="Resume from last progress")

# Before processing loop:
if args.resume:
    progress = load_progress()
    processed_set = set(progress["processed"])
    documents = [d for d in documents if d not in processed_set]
    logger.info(f"Resuming: {len(documents)} remaining after {len(processed_set)} processed")
```

## Todo

- [ ] Create `scripts/reimport_documents.py`
- [ ] Implement S3 listing and download
- [ ] Add Google Drive support (optional)
- [ ] Add progress tracking with resume
- [ ] Add namespace cleanup option
- [ ] Add dry-run mode
- [ ] Test with small subset (--limit 5)
- [ ] Run full reimport
- [ ] Verify graph quality in Neo4j Browser

## Success Criteria

1. Script runs: `python scripts/reimport_documents.py --source s3 --limit 10`
2. Documents from S3 appear in Neo4j with hierarchy
3. Cross-references detected (more than just hierarchy edges)
4. Vector search works for reimported documents
5. Resume works after interruption
6. Full reimport completes without manual intervention

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| S3 credentials expired | Medium | High | Check before batch |
| Network timeout mid-batch | Medium | Medium | Resume capability |
| Duplicate nodes | Low | Medium | MERGE not CREATE |
| OOM on large batch | Low | High | Process one at a time |
| Neo4j rate limiting | Low | Medium | Add delay between docs |

## Security Considerations

1. **AWS credentials** - Use environment variables, not hardcoded
2. **Temp files cleanup** - Always delete after processing
3. **No PII in logs** - Only log file names, not content

## Verification Steps

After reimport, run these checks in Neo4j Browser:

```cypher
-- Node count by type
MATCH (n:Test_rel_2) RETURN labels(n), count(n)

-- Relationship count by type
MATCH ()-[r]-() WHERE type(r) <> 'HAS_CLAUSE'
RETURN type(r), count(r)

-- Sample document with hierarchy
MATCH (doc:Test_rel_2)-[:HAS_CHAPTER]->(ch)-[:HAS_CLAUSE]->(cl)
RETURN doc.id, ch.id, cl.id LIMIT 10

-- Cross-references
MATCH (a)-[r:CITES|AMENDS|REFERENCES]->(b)
RETURN a.id, type(r), b.id LIMIT 20

-- Vector search test
CALL db.index.vector.queryNodes('Test_rel_2_embedding', 5, $embedding)
YIELD node, score
RETURN node.id, score
```

## Next Steps

After completion:
1. Validate graph quality manually
2. Compare RAG results before/after
3. Document lessons learned
4. Consider scheduled re-sync for updates
