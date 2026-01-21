# Document Pipeline + Neo4j Integration Plan

**Date:** 2026-01-07
**Status:** Draft
**Priority:** High

## Overview

Automate document upload to Neo4j indexing pipeline. Currently: upload saves files but NOT indexed. Target: upload triggers async processing -> Neo4j graph with embeddings + relationships.

## Current State

| Component | Status | Issue |
|-----------|--------|-------|
| Upload endpoint | Working | Saves to disk only, no Neo4j |
| Doc processor | Exists | In notebook, not API-integrated |
| Relation extractor | Exists | Works but manual invocation |
| Neo4j client | Working | Read-only queries, no write path |
| Embeddings | Working | API uses different model than doc processor |

## Target State

Upload -> BackgroundTask -> Parse -> Extract Relations -> Create Nodes -> Embed -> Index

## Phase Overview

| Phase | Title | Status | Dependencies |
|-------|-------|--------|--------------|
| 1 | [Document Processing Service](./phase-01-document-processing-service.md) | Pending | None |
| 2 | [Neo4j Indexing](./phase-02-neo4j-indexing.md) | Pending | Phase 1 |
| 3 | [API Integration](./phase-03-api-integration.md) | Pending | Phase 1, 2 |
| 4 | [Data Reimport](./phase-04-data-reimport.md) | Pending | Phase 2, 3 |

## Key Decisions

1. **No new queue system** - Use FastAPI BackgroundTasks (KISS)
2. **Reuse existing models** - `final_doc_processor.py`, `final_relation_extractor.py`
3. **Embedding model** - Use BGE-M3 (research recommendation) or existing `paraphrase-multilingual-mpnet-base-v2`
4. **Namespace** - Continue using `Test_rel_2` for consistency

## Architecture

```
[Upload Endpoint] --> [BackgroundTask] --> [DocumentProcessor]
                                                   |
                                           [Text Extraction]
                                                   |
                                        [parse_legal_text()]
                                                   |
                              +--------------------+--------------------+
                              |                                         |
                    [Relation Extractor]                      [Hierarchy Builder]
                              |                                         |
                    [final_relation()]                         [MERGE nodes]
                              |                                         |
                    [Cross-ref edges]                          [HAS_* edges]
                              |                                         |
                              +--------------------+--------------------+
                                                   |
                                          [Embedding Service]
                                                   |
                                          [Vector Index]
```

## Risk Summary

| Risk | Mitigation |
|------|------------|
| Model loading blocks API | Lazy load + cache singleton |
| Neo4j Aura timeout | Already handled via retry in `dml_ddl_neo4j` |
| Large files OOM | Chunk processing, 50MB limit already exists |
| Embedding mismatch | Standardize on single model |

## Success Criteria

1. Upload endpoint triggers processing automatically
2. Documents appear in Neo4j within 60s of upload
3. Graph has hierarchy (CONTAINS/HAS_*) + cross-ref (CITES/AMENDS) relationships
4. Vector search returns newly uploaded documents
5. Existing tests pass

## Unresolved Questions

1. Should we support async status polling or just fire-and-forget?
2. Keep both embedding models (API vs processor) or unify?
3. Re-import all existing S3 documents or only new uploads?
