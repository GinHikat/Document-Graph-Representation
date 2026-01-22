# Research Report: Document Processing Pipeline for Vietnamese Legal RAG

**Date:** 2026-01-07
**Status:** Completed
**Focus:** Chunking, Architecture, and Embeddings for Vietnamese Legal Text

## 1. Vietnamese Legal Document Chunking Strategy

Standard fixed-size chunking fails with legal documents due to the loss of hierarchical context.

### Best Practices
- **Structure-Aware Splitting:** Legal documents follow a strict hierarchy (Phần -> Chương -> Mục -> Điều -> Khoản).
  - **Strategy:** Chunk by **Article (Điều)** as the atomic unit.
  - **Context Window:** If an article exceeds the token limit, split by **Clause (Khoản)** but prepend the Article Title/ID to each chunk.
- **Vietnamese Segmentation:**
  - Vietnamese is monosyllabic but words can be multi-word compounds (e.g., "trách nhiệm").
  - **Requirement:** Use a Vietnamese tokenizer (e.g., `VnCoreNLP`, `UnderTheSea`, or `PyVi`) *before* embedding to ensure semantic boundaries are respected.
- **Hybrid Approach:**
  - **Parent Chunk:** The full Article text (for context).
  - **Child Chunks:** Individual Clauses (for precise retrieval).
  - *Recommendation:* Store Parent ID in metadata for efficient retrieval of the full context.

## 2. Pipeline Architecture

A robust RAG pipeline for legal documents must handle long-running processes (OCR, parsing) without blocking.

### Architecture Components
1. **Ingestion Layer:**
   - Accepts PDF/DOCX.
   - Generates a unique Job ID.
2. **Async Processing Queue:**
   - **Tools:** **Celery** with **Redis** (broker) is the industry standard for Python.
   - **Alternative:** **Ray** for high-scale distributed processing if throughput is massive.
   - **Pattern:** `Producer` (API) pushes file path -> `Consumer` (Worker) picks up task.
3. **Processing Steps (Worker):**
   - **Extraction:** `PyMuPDF` or `Unstructured` for PDF; `python-docx` for DOCX.
   - **Cleaning:** Remove headers/footers, fix line breaks.
   - **Segmentation & Chunking:** Apply hierarchy-aware splitting.
   - **Embedding:** Batch processing for GPU efficiency.
   - **Storage:** Write to Vector DB (Neo4j/Qdrant).

## 3. Embedding Models for Vietnamese

### Model Comparison
| Model Category | Top Contenders | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Multilingual (Rec)** | **BGE-M3**, **multilingual-e5-large** | Excellent retrieval performance; handles mixed EN/VN terms common in tech law. | Larger model size. |
| **Vietnamese Native** | **PhoBERT**, **ViBERT** | Deep understanding of Vietnamese nuance/grammar. | Requires fine-tuning for retrieval tasks (originally for NLU). |
| **Commercial** | **OpenAI text-embedding-3**, **Cohere** | Easy integration; huge context window. | Cost scales with volume; data privacy concerns. |

### Recommendation
**Use BGE-M3 (BAAI/bge-m3)**.
- **Reasoning:** It is currently SOTA for multilingual retrieval, supports dense + sparse (hybrid) search, and handles long contexts (8192 tokens) well, which fits legal articles.
- **Alternative:** `multilingual-e5-large` if hardware is constrained.

## Unresolved Questions / Next Steps
1. **OCR Quality:** How to handle scanned legal PDFs (legacy documents)? Need to evaluate OCR tools (Tesseract vs. commercial) for Vietnamese accuracy.
2. **Table Extraction:** Legal docs often have appendices in tables. Standard text splitters destroy table structure. Need a specialized table parsing strategy.

## Sources
- [Building Scalable RAG Pipelines (Medium)](https://medium.com/@ai-engineering/building-scalable-document-processing-pipeline-rag)
- [LangChain Document Loaders](https://python.langchain.com/docs/modules/data_connection/document_loaders/)
- [Vietnamese Embedding Evaluation](https://github.com/underthesea/underthesea)
- [BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3)
