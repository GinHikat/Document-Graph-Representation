# Research: Neo4j Knowledge Graph for Legal Documents

## 1. Neo4j Relationship Modeling for Legal Documents

Legal documents inherently possess a rigid hierarchical structure combined with a complex web of cross-references. Modeling this in Neo4j requires a dual approach: structural backbone and semantic connective tissue.

### Hierarchical Structures (The Backbone)
The recommended pattern follows a "Tree in Graph" model to represent the granular structure of legal texts.

*   **Nodes**: `Document`, `Part`, `Chapter`, `Section`, `Article`, `Clause`, `SubClause`.
*   **Structural Relationships**: `[:CONTAINS]`, `[:HAS_PART]`, `[:HAS_SECTION]`.
*   **Ordering**: `[:NEXT]` relationships between sibling nodes (e.g., Article 1 `[:NEXT]->` Article 2) allow for precise reconstruction of document flow.

**Example Cypher Pattern:**
```cypher
(doc:Document {id: "GDPR"})-[:HAS_CHAPTER]->(ch:Chapter {id: "1"})
(ch)-[:HAS_ARTICLE]->(art:Article {id: "4"})
(art)-[:HAS_CLAUSE]->(cl:Clause {id: "1"})
```

### Cross-Reference Relationships (The Connective Tissue)
Legal texts define relationships between entities. These should be explicit edges, not just text properties.

*   **Citation Types**: `[:CITES]`, `[:AMENDS]`, `[:REPEALS]`, `[:DEFINES]`, `[:REFERENCES]`.
*   **Properties on Relationships**: Store context like `{date: '2023-01-01', nature: 'explicit'}`.
*   **Definition Graph**: Link terms in text to their definitions: `(clause)-[:USES_TERM]->(term:Definition)`.

## 2. Graph-Enhanced RAG Best Practices

GraphRAG outperforms standard RAG by injecting structured context into the retrieval process.

### Improving Retrieval Quality
*   **Context Extension**: When a chunk (e.g., a Clause) is retrieved via vector search, traverse the graph to pull its parent (Article context) and referenced nodes (definitions or related laws) before feeding the LLM.
*   **Hybrid Retrieval**: Combine unstructured vector search with structured graph queries.
    *   *Query*: "What are the penalties for data breach?"
    *   *Graph Action*: Find `(penalty)-[:APPLIES_TO]->(data_breach)` paths directly, rather than relying solely on semantic similarity.

### Optimal Graph Density
*   **Avoid "Supernodes"**: Extremely dense nodes (e.g., a node for the country "USA" connected to every law) dilute retrieval relevance.
*   **Sparsity is key**: Focus on meaningful legal relationships (`AMENDS`, `EXCEPTS`) rather than generic ones (`HAS_WORD`).
*   **Chunking Strategy**: Map embedding chunks 1:1 to graph nodes (e.g., one node per Clause) to align the vector space with the graph topology.

## 3. Neo4j Indexing Strategies

A robust legal graph requires a multi-layered indexing strategy to support hybrid search.

### Vector Indexes (Semantic Search)
Use Neo4j's native vector search for conceptual retrieval.
```cypher
CREATE VECTOR INDEX legal_embeddings IF NOT EXISTS
FOR (n:Clause) ON (n.embedding)
OPTIONS {indexConfig: {
 `vector.dimensions`: 1536,
 `vector.similarity_function`: 'cosine'
}}
```

### Full-Text Search Indexes (Lexical Search)
Legal professionals often search for exact phrases or specific case numbers.
```cypher
CREATE FULLTEXT INDEX legal_text_idx IF NOT EXISTS
FOR (n:Clause|Article) ON EACH [n.text, n.heading]
```

### Hybrid Strategy
1.  **Vector Search**: Finds relevant concepts ("obligations of controller").
2.  **Full-Text Search**: Filters for specific keywords ("Article 5").
3.  **Graph Filter**: Restricts results based on metadata or graph path (e.g., "only effective laws").

## Unresolved Questions
1.  What is the optimal chunk size for legal clauses—sentence level or paragraph level?
2.  Should "Definitions" be global nodes shared across all documents, or scoped to specific documents?
3.  How to handle versioning of laws (temporal graph modeling) effectively in RAG?

## Sources
*   Neo4j Graph Data Modeling Docs: [https://neo4j.com/docs/graph-data-science/current/algorithms/](https://neo4j.com/docs/graph-data-science/current/algorithms/)
*   Legal Graph Modeling Patterns: [https://neo4j.com/blog/modeling-legal-documents-neo4j/](https://neo4j.com/blog/modeling-legal-documents-neo4j/)
*   GraphRAG & Microsoft Research: [https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/)
