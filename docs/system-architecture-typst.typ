=== System Architecture

The application implements a modular five-layer architecture designed for scalability, maintainability, and clear separation of concerns. Each layer has distinct responsibilities and communicates through well-defined interfaces.

#figure(
  image("images/system-architecture-detailed.png", width: 95%),
  caption: [Detailed System Architecture showing all five layers and their interactions]
) <fig:system_arch_detailed>

==== Layer Descriptions

*1. Presentation Layer*

The presentation layer handles all user-facing interactions through a modern React-based single-page application. Built with *React 18* and *TypeScript*, it provides type-safe component development with strong IDE support. *Vite* serves as the build tool, offering fast hot module replacement during development. State management is handled by *Zustand*, a lightweight yet powerful store that avoids Redux boilerplate while maintaining predictable state updates. *TanStack Query* manages server state synchronization, providing automatic caching, background refetching, and optimistic updates for API calls. The *react-force-graph* library renders interactive knowledge graph visualizations, allowing users to explore document relationships visually. *Tailwind CSS* with *shadcn/ui* components ensures consistent, accessible styling across all interface elements.

#figure(
  caption: [Presentation Layer Technology Stack],
  table(
    columns: (auto, auto, auto),
    align: (left, left, left),
    inset: (x: 8pt, y: 4pt),
    stroke: (x, y) => (top: 0.5pt, bottom: 0.5pt, left: 0.5pt, right: 0.5pt),
    fill: (x, y) => if y > 0 and calc.rem(y, 2) == 0 { rgb("#efefef") },
    table.header[*Component*][*Technology*][*Purpose*],
    [Framework], [React 18 + TypeScript], [Component-based UI with type safety],
    [Build Tool], [Vite 5], [Fast development server and optimized builds],
    [State], [Zustand 5.0], [Global application state management],
    [Data Fetching], [TanStack Query 5], [Server state caching and synchronization],
    [Graph Viz], [react-force-graph], [Interactive knowledge graph rendering],
    [Styling], [Tailwind CSS + shadcn/ui], [Utility-first CSS with accessible components],
  ),
)

*2. API Layer*

The API layer exposes RESTful endpoints through *FastAPI*, a modern Python web framework chosen for its automatic OpenAPI documentation, native async support, and Pydantic-based request validation. *Uvicorn* serves as the ASGI server, providing high-performance async request handling. The layer is organized into modular routers, each responsible for a specific domain:

- *Graph Router* (`/api/graph/*`): Handles graph visualization data retrieval and Cypher query execution
- *RAG Router* (`/api/rag/*`): Manages retrieval-augmented generation queries with streaming support
- *Stats Router* (`/api/stats/*`): Provides system metrics and dashboard statistics
- *Auth Router* (`/api/auth/*`): Handles user authentication and session management
- *Annotation Router* (`/api/annotation/*`): Manages quality evaluation submissions

CORS middleware enables secure cross-origin requests from the React frontend, while global exception handlers ensure consistent error responses across all endpoints.

*3. Service Layer*

The service layer encapsulates core business logic and ML model orchestration. The *RAG Agent* implements a tool-calling pattern that orchestrates the complete retrieval-generation pipeline:

1. *Embedding Service*: Transforms queries and documents into dense vector representations using PhoBERT or multilingual sentence transformers
2. *Retrieval Tools*: Execute both vector similarity search and graph-based traversal against Neo4j
3. *Reranker Service*: Applies cross-encoder reranking using *BAAI/bge-reranker-base* to improve precision
4. *Gemini Service*: Generates natural language answers using *Gemini 2.0 Flash* with streaming support via Server-Sent Events (SSE)

#figure(
  image("images/rag-pipeline-flow.png", width: 90%),
  caption: [RAG Pipeline Flow: Query → Retrieval → Reranking → Generation]
) <fig:rag_pipeline>

The RAG pipeline flow illustrates the complete journey of a user query:

1. *Input Processing*: The user query is received and preprocessed
2. *Dual Retrieval*: Both vector search (cosine similarity) and graph traversal (k-hop neighbors) execute in parallel
3. *Reranking*: Retrieved chunks are reranked using a cross-encoder model to improve relevance ordering
4. *Context Assembly*: Top-K chunks are assembled into a coherent context window
5. *Generation*: The LLM generates an answer with real-time streaming to the frontend
6. *Citation*: Source document references are extracted and returned alongside the answer

*4. Data Layer*

The data layer persists all graph structures, embeddings, and metadata in *Neo4j AuraDB*, a fully managed cloud graph database. Neo4j was selected for its native graph storage model, which efficiently represents the hierarchical document structure and cross-document relationships without the impedance mismatch of relational databases. The database stores:

- *Graph Store*: Document nodes with structural relationships (HAS_CHAPTER, HAS_CLAUSE, HAS_POINT) and semantic relationships (PURSUANT, REFERENCE, AMENDS)
- *Vector Index*: Node embeddings indexed for approximate nearest neighbor search, enabling fast semantic retrieval

A singleton connection pool managed by the `Neo4jClient` class ensures efficient connection reuse across requests while handling automatic reconnection on transient failures.

*5. Processing Pipeline*

The offline processing pipeline transforms raw legal documents into the knowledge graph. This layer operates independently of the real-time API:

1. *Document Crawler*: Playwright-based headless browser extracts HTML from LuatVietnam.vn
2. *Structure Parser*: BeautifulSoup identifies hierarchical document structure (Chapter → Clause → Point → Subpoint)
3. *NER Model*: BiLSTM-CRF architecture extracts document metadata (title, date, issuer, document ID)
4. *RE Model*: Transformer encoder-decoder extracts cross-document relationships
5. *Graph Builder*: Constructs Neo4j nodes and relationships from parsed structures

#figure(
  image("images/document-processing-pipeline.png", width: 90%),
  caption: [Document Processing Pipeline: Collection → Parsing → NLP → Graph Construction]
) <fig:doc_pipeline>

==== Graph Node Structure

The knowledge graph follows a hierarchical model that mirrors the legal document structure while adding semantic enrichment through cross-document relationships.

#figure(
  image("images/graph-node-structure.png", width: 85%),
  caption: [Graph Node Hierarchy with Structural and Cross-Reference Relationships]
) <fig:graph_structure>

#figure(
  caption: [Node Types and Their Attributes],
  table(
    columns: (auto, auto, auto),
    align: (left, left, left),
    inset: (x: 8pt, y: 4pt),
    stroke: (x, y) => (top: 0.5pt, bottom: 0.5pt, left: 0.5pt, right: 0.5pt),
    fill: (x, y) => if y > 0 and calc.rem(y, 2) == 0 { rgb("#efefef") },
    table.header[*Node Type*][*Key Attributes*][*Description*],
    [Document], [id, title, type, issue_date, issuer], [Root node for each legal document],
    [Chapter], [id, text, number], [Top-level structural division (Chương)],
    [Clause], [id, text, number], [Article-level content (Điều)],
    [Point], [id, text, number], [Numbered paragraph (Khoản)],
    [Subpoint], [id, text, label], [Lettered items (Điểm a, b, c)],
    [Chunk], [id, text, embedding], [Retrieval unit with vector embedding],
  ),
)

#figure(
  caption: [Relationship Types],
  table(
    columns: (auto, auto, auto),
    align: (left, left, left),
    inset: (x: 8pt, y: 4pt),
    stroke: (x, y) => (top: 0.5pt, bottom: 0.5pt, left: 0.5pt, right: 0.5pt),
    fill: (x, y) => if y > 0 and calc.rem(y, 2) == 0 { rgb("#efefef") },
    table.header[*Relationship*][*Direction*][*Semantics*],
    [HAS_CHAPTER], [Document → Chapter], [Structural containment],
    [HAS_CLAUSE], [Chapter → Clause], [Structural containment],
    [HAS_POINT], [Clause → Point], [Structural containment],
    [HAS_SUBPOINT], [Point → Subpoint], [Structural containment],
    [IS_IN], [Node → Chunk], [Maps structural node to retrieval chunk],
    [PURSUANT], [Document → Document], [Legal basis reference (Căn cứ)],
    [REFERENCE], [Node → Node], [Cross-reference within/between docs],
    [AMENDS], [Document → Document], [Amendment relationship],
  ),
)

==== API Endpoints

#figure(
  caption: [Core REST API Routes],
  table(
    columns: (auto, auto, auto),
    align: (left, left, left),
    inset: (x: 8pt, y: 4pt),
    stroke: (x, y) => (top: 0.5pt, bottom: 0.5pt, left: 0.5pt, right: 0.5pt),
    fill: (x, y) => if y > 0 and calc.rem(y, 2) == 0 { rgb("#efefef") },
    table.header[*Endpoint*][*Method*][*Description*],
    [/api/health], [GET], [System health and Neo4j connectivity],
    [/api/stats], [GET], [Dashboard metrics (nodes, questions, response time)],
    [/api/graph/nodes], [GET], [Graph nodes for force-graph visualization],
    [/api/graph/execute], [POST], [Execute read-only Cypher queries],
    [/api/graph/schema], [GET], [Graph schema (node labels, relationship types)],
    [/api/rag/query], [POST], [RAG query with SSE streaming],
    [/api/rag/compare], [POST], [Side-by-side Vector vs Graph comparison],
    [/api/rag/retrieve], [POST], [Direct retrieval tool access],
    [/api/rag/rerank], [POST], [Direct reranker tool access],
    [/api/auth/login], [POST], [User authentication],
    [/api/annotation], [POST], [Submit quality evaluations],
  ),
)

==== Use Case Diagram

#figure(
  image("images/use-case-diagram.png", width: 75%),
  caption: [Use Case Diagram showing actor interactions with the system]
) <fig:use_case>

The system supports three distinct actor types with progressive access levels:

- *Public User*: Can browse documents, explore graph visualization, submit queries, and compare Vector vs Graph retrieval results
- *Annotator*: Inherits public user capabilities plus ability to rate response quality and select preferred retrieval method for benchmark construction
- *Administrator*: Full system access including document upload, reprocessing triggers, and annotation data export

==== Technology Summary

#figure(
  caption: [Complete Technology Stack by Layer],
  table(
    columns: (auto, auto),
    align: (left, left),
    inset: (x: 8pt, y: 4pt),
    stroke: (x, y) => (top: 0.5pt, bottom: 0.5pt, left: 0.5pt, right: 0.5pt),
    fill: (x, y) => if y > 0 and calc.rem(y, 2) == 0 { rgb("#efefef") },
    table.header[*Layer*][*Technologies*],
    [Presentation], [React 18, TypeScript 5.8, Vite 5, Zustand, TanStack Query, react-force-graph, Tailwind CSS, shadcn/ui],
    [API], [FastAPI 0.115, Python 3.11, Uvicorn, Pydantic],
    [Service], [Sentence-Transformers, BAAI/bge-reranker, Google Gemini API],
    [Data], [Neo4j AuraDB 5.x, Vector Index],
    [Processing], [Playwright, BeautifulSoup, PyTorch, VnCoreNLP, PhoBERT],
  ),
)
