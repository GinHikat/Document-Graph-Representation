# Backend Scout Report

## 1. QA Dataset & Questions
- **Source:** Dynamic loading from Google Sheet (primary) or hardcoded fallback.
- **File:** `api/services/qa_questions.py`
- **Google Sheet ID:** `1xBgBiA1KwTNdqPfrqH5p_Sf-MhTCXMfy4ousb0WE4Ik`
- **Tabs:** "QA_sample", "QA_Gen", "QA_Crawled", etc.
- **Fallback:** 8 hardcoded Vietnamese tax questions in `api/services/qa_questions.py` (lines 11-20).
- **Training Data:** CSVs found in `rag_model/model/RE/artifact/` and `rag_model/model/NER/artifact/` (e.g., `RE_training_final.csv`).

## 2. Metrics & Logging
- **Status:** Basic application logging only. No dedicated metrics middleware (Prometheus/Grafana) found.
- **Implementation:** Standard Python `logging` used in `api/main.py` and routers.
- **Missing:** Response time tracking, latency histograms, request counters.
- **Offline Eval:** `rag_model/retrieval_pipeline/evaluation.ipynb` contains custom logic for Precision, Recall, F1, and MRR calculation.

## 3. Evaluation Data
- **Location:** MLflow artifacts and Google Sheets.
- **Script:** `rag_model/retrieval_pipeline/retrieve_test_result.ipynb` fetches results from MLflow and writes to Google Sheet.
- **Metrics Calculated:** Precision, Recall, F1-Score, MRR (in `evaluation.ipynb`).
- **Tools:** Uses `ragas` library for LLM-based evaluation (ContextPrecision, LLMContextRecall).

## 4. Neo4j Connection Patterns
- **Pattern:** Singleton wrapper around the official driver.
- **File:** `api/db/neo4j.py`
- **Class:** `Neo4jClient`
- **Lifecycle:** Initialized in `api/main.py` lifespan event (startup/shutdown).
- **Execution:** `execute_query` method uses ephemeral sessions (`with self.driver.session() as session`).
- **Safety:** `api/routers/graph.py` enforces read-only access (blocks write keywords).

## 5. Document Counting
- **Graph Nodes:** `api/db/neo4j.py` -> `get_node_count("Test_rel_2")` executes Cypher: `MATCH (n:Test_rel_2) RETURN count(n)`.
- **Uploaded Files:** `api/routers/documents.py` uses in-memory dict `documents_db` (reset on restart). `len(documents_db)` gives current count.

## Unresolved Questions
1. **Production Persistence:** Uploaded document metadata is in-memory only (`documents_db`). Is there a plan to persist this to a DB?
2. **Hardcoded Graph Namespace:** `Test_rel_2` is hardcoded in `get_node_count`. Should this be configurable?
